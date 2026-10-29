from sqlalchemy import insert, select

from httpx import AsyncClient

from app.core.assets import AssetStatus
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Asset,
    AssetCategory,
    AssetHistory,
    AssetInbound,
    Dept,
    Role,
    User,
    user_roles,
)
from tests.helpers import auth_headers, login

TEST_PASSWORD = "Test@12345"


async def _category(code: str = "HW-LAPTOP") -> AssetCategory:
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(
                select(AssetCategory).where(AssetCategory.code == code)
            )
        ).scalar_one()


async def _ensure_user(username: str, real_name: str, role_code: str) -> int:
    async with AsyncSessionLocal() as session:
        role = (
            await session.execute(select(Role).where(Role.code == role_code))
        ).scalar_one()
        dept = (
            await session.execute(select(Dept).where(Dept.code == "IT"))
        ).scalar_one()
        user = User(
            username=username,
            password_hash=hash_password(TEST_PASSWORD),
            real_name=real_name,
            dept_id=dept.id,
            status=1,
            must_change_password=False,
        )
        session.add(user)
        await session.flush()
        await session.execute(
            insert(user_roles).values(user_id=user.id, role_id=role.id)
        )
        await session.commit()
        return user.id


async def _login_as(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return auth_headers(response.json()["data"]["access_token"])


async def test_inbound_create_confirm_generates_assets(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    category = await _category()
    async with AsyncSessionLocal() as session:
        dept = (
            await session.execute(select(Dept).where(Dept.code == "IT"))
        ).scalar_one()
        dept_id = dept.id

    created = await client.post(
        "/api/v1/inbounds",
        json={
            "inbound_type": "PURCHASE",
            "supplier": "联想华东供应商",
            "location": "A 座 101",
            "dept_id": dept_id,
            "remark": "季度采购",
            "items": [
                {
                    "category_id": category.id,
                    "name": "ThinkPad T14 笔记本",
                    "quantity": 2,
                    "unit_price": 5600,
                },
                {
                    "category_id": category.id,
                    "name": "USB-C 扩展坞",
                    "quantity": 1,
                    "unit_price": 300,
                },
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 200, created.text
    inbound = created.json()["data"]
    assert inbound["inbound_no"].startswith("RK-")
    assert inbound["status"] == "PENDING"
    assert inbound["total_quantity"] == 3
    assert inbound["total_amount"] == 11500
    assert inbound["can_confirm"] is True
    inbound_id = inbound["id"]

    confirmed = await client.post(
        f"/api/v1/inbounds/{inbound_id}/confirm",
        json={"version": inbound["version"], "comment": "验收合格"},
        headers=admin_headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    result = confirmed.json()["data"]
    assert result["status"] == "COMPLETED"
    assert result["confirmed_by_name"] == "系统管理员"
    assert result["can_confirm"] is False
    assert result["version"] == inbound["version"] + 1

    async with AsyncSessionLocal() as session:
        assets = list(
            (
                await session.execute(
                    select(Asset)
                    .where(Asset.name.in_(["ThinkPad T14 笔记本", "USB-C 扩展坞"]))
                    .order_by(Asset.id)
                )
            )
            .scalars()
            .all()
        )
        histories = list(
            (
                await session.execute(
                    select(AssetHistory).where(
                        AssetHistory.asset_id.in_([asset.id for asset in assets])
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(assets) == 3
    assert {asset.status for asset in assets} == {AssetStatus.IN_STOCK}
    assert {asset.location for asset in assets} == {"A 座 101"}
    assert {asset.dept_id for asset in assets} == {dept_id}
    assert all(asset.asset_no.startswith("ITAM-") for asset in assets)
    assert len({asset.asset_no for asset in assets}) == 3
    assert len(histories) == 3
    assert {record.action for record in histories} == {"INBOUND"}
    assert {record.from_status for record in histories} == {AssetStatus.PENDING_STOCK}
    assert {record.to_status for record in histories} == {AssetStatus.IN_STOCK}
    assert all(
        record.summary == f"入库单 {inbound['inbound_no']} 验收入库"
        for record in histories
    )

    duplicate = await client.post(
        f"/api/v1/inbounds/{inbound_id}/confirm",
        json={"version": result["version"]},
        headers=admin_headers,
    )
    assert duplicate.status_code == 400


async def test_inbound_stale_version_conflict(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    category = await _category()
    created = await client.post(
        "/api/v1/inbounds",
        json={
            "inbound_type": "OTHER",
            "items": [
                {
                    "category_id": category.id,
                    "name": "测试入库资产",
                    "quantity": 1,
                }
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 200, created.text
    inbound = created.json()["data"]

    async with AsyncSessionLocal() as session:
        record = await session.get(AssetInbound, inbound["id"])
        record.remark = "并发修改"
        await session.commit()

    conflict = await client.post(
        f"/api/v1/inbounds/{inbound['id']}/confirm",
        json={"version": inbound["version"]},
        headers=admin_headers,
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == 40911
    assert conflict.json()["message"] == "入库单状态已变更，请刷新后重试"

    async with AsyncSessionLocal() as session:
        record = await session.get(AssetInbound, inbound["id"])
        assert record.status == "PENDING"
        asset_count = await session.scalar(
            select(Asset.id).where(Asset.name == "测试入库资产")
        )
    assert asset_count is None


async def test_inbound_permissions_and_cancel(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    category = await _category()
    await _ensure_user("inbound_dept", "入库部门管理员", "DEPT_ADMIN")
    dept_headers = await _login_as(client, "inbound_dept")

    dept_list = await client.get("/api/v1/inbounds", headers=dept_headers)
    assert dept_list.status_code == 200, dept_list.text
    assert dept_list.json()["data"]["total"] == 0

    forbidden = await client.post(
        "/api/v1/inbounds",
        json={
            "items": [
                {"category_id": category.id, "name": "无权入库", "quantity": 1}
            ]
        },
        headers=dept_headers,
    )
    assert forbidden.status_code == 403

    created = await client.post(
        "/api/v1/inbounds",
        json={
            "items": [
                {"category_id": category.id, "name": "取消测试资产", "quantity": 1}
            ]
        },
        headers=admin_headers,
    )
    inbound = created.json()["data"]

    cancelled = await client.post(
        f"/api/v1/inbounds/{inbound['id']}/cancel",
        json={"reason": "采购计划调整"},
        headers=admin_headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["status"] == "CANCELLED"
    assert cancelled.json()["data"]["cancel_reason"] == "采购计划调整"

    confirm_cancelled = await client.post(
        f"/api/v1/inbounds/{inbound['id']}/confirm",
        json={"version": cancelled.json()["data"]["version"]},
        headers=admin_headers,
    )
    assert confirm_cancelled.status_code == 400


async def test_stock_overview_location_warnings_and_items(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    category = await _category()

    confirmations = []
    for location, quantity in (("Z 座 901", 2), (None, 1)):
        created = await client.post(
            "/api/v1/inbounds",
            json={
                "location": location,
                "items": [
                    {
                        "category_id": category.id,
                        "name": f"库存测试资产-{location or '无位置'}",
                        "quantity": quantity,
                        "unit_price": 100,
                    }
                ],
            },
            headers=admin_headers,
        )
        assert created.status_code == 200, created.text
        inbound = created.json()["data"]
        confirmed = await client.post(
            f"/api/v1/inbounds/{inbound['id']}/confirm",
            json={"version": inbound["version"]},
            headers=admin_headers,
        )
        assert confirmed.status_code == 200, confirmed.text
        confirmations.append(confirmed.json()["data"])

    async with AsyncSessionLocal() as session:
        record = (
            await session.execute(
                select(AssetCategory).where(AssetCategory.id == category.id)
            )
        ).scalar_one()
        record.safety_stock = 5
        await session.commit()

    overview = await client.get("/api/v1/stock/overview", headers=admin_headers)
    assert overview.status_code == 200, overview.text
    data = overview.json()["data"]
    assert data["in_stock_count"] == 3
    locations = {item["location"]: item for item in data["locations"]}
    assert locations["Z 座 901"]["asset_count"] == 2
    assert locations["Z 座 901"]["total_value"] == 200
    assert locations[None]["asset_count"] == 1
    assert locations[None]["location_label"] == "未指定位置"
    assert data["warning_count"] >= 1
    warning = next(
        item for item in data["warnings"] if item["category_id"] == category.id
    )
    assert warning["stock_count"] == 3
    assert warning["safety_stock"] == 5
    assert warning["shortage"] == 2

    filtered = await client.get(
        "/api/v1/stock/items",
        params={
            "location": "__none__",
            "category_id": category.id,
            "keyword": "无位置",
        },
        headers=admin_headers,
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["data"]["total"] == 1
    item = filtered.json()["data"]["items"][0]
    assert item["location"] is None
    assert item["purchase_price"] == 100
    assert item["category_name"] == category.name
