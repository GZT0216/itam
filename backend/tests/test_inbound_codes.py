from httpx import AsyncClient
from sqlalchemy import insert, select

from app.core.assets import AssetStatus
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Asset,
    AssetCategory,
    AssetHistory,
    AssetInbound,
    AssetInboundCode,
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


async def _dept_id() -> int:
    async with AsyncSessionLocal() as session:
        dept = (
            await session.execute(select(Dept).where(Dept.code == "IT"))
        ).scalar_one()
        return dept.id


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


async def _create_inbound(
    client: AsyncClient,
    headers: dict[str, str],
    category_id: int,
    *,
    name: str,
    quantity: int,
    base_asset_no: str | None = None,
    asset_nos: list[str] | None = None,
):
    payload: dict[str, object] = {
        "dept_id": await _dept_id(),
        "location": "编码测试仓",
        "items": [
            {
                "category_id": category_id,
                "name": name,
                "quantity": quantity,
            }
        ],
    }
    item = payload["items"][0]
    if base_asset_no is not None:
        item["base_asset_no"] = base_asset_no
    if asset_nos is not None:
        item["asset_nos"] = asset_nos
    return await client.post("/api/v1/inbounds", json=payload, headers=headers)


async def test_base_codes_generated_confirmed_and_flowable(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    category = await _category()

    created = await client.post(
        "/api/v1/inbounds",
        json={
            "dept_id": await _dept_id(),
            "location": "A 座 301",
            "items": [
                {
                    "category_id": category.id,
                    "name": "Dell 笔记本",
                    "quantity": 3,
                    "base_asset_no": "1001",
                    "unit_price": 5000,
                },
                {
                    "category_id": category.id,
                    "name": "联想笔记本",
                    "quantity": 2,
                    "base_asset_no": "1002",
                    "unit_price": 4500,
                },
            ],
        },
        headers=admin_headers,
    )
    assert created.status_code == 200, created.text
    inbound = created.json()["data"]
    assert inbound["items"][0]["base_asset_no"] == "1001"
    assert inbound["items"][0]["asset_nos"] == ["1001-1", "1001-2", "1001-3"]
    assert inbound["items"][1]["asset_nos"] == ["1002-1", "1002-2"]

    confirmed = await client.post(
        f"/api/v1/inbounds/{inbound['id']}/confirm",
        json={"version": inbound["version"]},
        headers=admin_headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["status"] == "COMPLETED"

    async with AsyncSessionLocal() as session:
        assets = list(
            (
                await session.execute(
                    select(Asset)
                    .where(Asset.asset_no.in_(["1001-1", "1001-2", "1001-3", "1002-1", "1002-2"]))
                    .order_by(Asset.asset_no)
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
        dell = next(asset for asset in assets if asset.asset_no == "1001-1")
        dell_id = dell.id
    assert len(assets) == 5
    assert {asset.status for asset in assets} == {AssetStatus.IN_STOCK}
    assert {asset.location for asset in assets} == {"A 座 301"}
    assert len(histories) == 5
    assert {history.action for history in histories} == {"INBOUND"}

    employee_id = await _ensure_user("code_emp", "编码员工", "EMPLOYEE")
    await _ensure_user("code_dept", "编码部门管理员", "DEPT_ADMIN")
    await _ensure_user("code_asset", "编码资产管理员", "ASSET_ADMIN")
    emp_headers = await _login_as(client, "code_emp")
    dept_headers = await _login_as(client, "code_dept")
    asset_headers = await _login_as(client, "code_asset")

    available = await client.get(
        "/api/v1/asset-requests/available-assets",
        params={"category_id": category.id},
        headers=emp_headers,
    )
    assert available.status_code == 200, available.text
    assert available.json()["data"]["total"] == 5

    request_created = await client.post(
        "/api/v1/asset-requests",
        json={"request_type": "REQUISITION", "category_id": category.id},
        headers=emp_headers,
    )
    assert request_created.status_code == 200, request_created.text
    request_id = request_created.json()["data"]["id"]

    dept_approved = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "部门同意领用"},
        headers=dept_headers,
    )
    assert dept_approved.status_code == 200, dept_approved.text

    approved = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "同意领用"},
        headers=asset_headers,
    )
    assert approved.status_code == 200, approved.text

    candidates = await client.get(
        f"/api/v1/asset-requests/{request_id}/outbound-assets",
        params={"page_size": 50},
        headers=asset_headers,
    )
    assert candidates.status_code == 200, candidates.text
    candidate = next(
        item for item in candidates.json()["data"]["items"] if item["id"] == dell_id
    )

    outbound = await client.post(
        f"/api/v1/asset-requests/{request_id}/outbound",
        json={
            "asset_id": dell_id,
            "version": candidate["version"],
            "location": "B 座 201",
        },
        headers=asset_headers,
    )
    assert outbound.status_code == 200, outbound.text
    assert outbound.json()["data"]["asset_status"] == "IN_USE"

    detail = await client.get(f"/api/v1/assets/{dell_id}", headers=admin_headers)
    assert detail.json()["data"]["status"] == "IN_USE"
    assert detail.json()["data"]["custodian_id"] == employee_id
    assert detail.json()["data"]["asset_no"] == "1001-1"

    return_created = await client.post(
        "/api/v1/asset-returns",
        json={"asset_id": dell_id, "reason": "编码回归归还"},
        headers=emp_headers,
    )
    assert return_created.status_code == 200, return_created.text
    return_data = return_created.json()["data"]
    returned = await client.post(
        f"/api/v1/asset-requests/{return_data['id']}/return-confirm",
        json={"version": return_data["asset_version"], "location": "A 座 301"},
        headers=asset_headers,
    )
    assert returned.status_code == 200, returned.text

    detail = await client.get(f"/api/v1/assets/{dell_id}", headers=admin_headers)
    assert detail.json()["data"]["status"] == "IN_STOCK"
    history = await client.get(
        f"/api/v1/assets/{dell_id}/history", headers=admin_headers
    )
    assert [item["action"] for item in history.json()["data"]] == [
        "RETURN",
        "OUTBOUND",
        "INBOUND",
    ]


async def test_manual_codes_override_and_uniqueness(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    category = await _category()

    manual = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="手工编码笔记本",
        quantity=2,
        base_asset_no="2001",
        asset_nos=["2001-1", "2001-9"],
    )
    assert manual.status_code == 200, manual.text
    manual_data = manual.json()["data"]
    assert manual_data["items"][0]["asset_nos"] == ["2001-1", "2001-9"]
    confirmed = await client.post(
        f"/api/v1/inbounds/{manual_data['id']}/confirm",
        json={"version": manual_data["version"]},
        headers=admin_headers,
    )
    assert confirmed.status_code == 200, confirmed.text

    async with AsyncSessionLocal() as session:
        asset_nos = set(
            (
                await session.execute(
                    select(Asset.asset_no).where(
                        Asset.asset_no.in_(["2001-1", "2001-9"])
                    )
                )
            )
            .scalars()
            .all()
        )
    assert asset_nos == {"2001-1", "2001-9"}

    duplicate_in_line = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="行内重复",
        quantity=2,
        base_asset_no="2002",
        asset_nos=["2002-1", "2002-1"],
    )
    assert duplicate_in_line.status_code == 422, duplicate_in_line.text
    assert "重复" in duplicate_in_line.json()["message"]

    duplicate_across_lines = await client.post(
        "/api/v1/inbounds",
        json={
            "items": [
                {
                    "category_id": category.id,
                    "name": "跨行重复一",
                    "quantity": 1,
                    "asset_nos": ["2003-1"],
                },
                {
                    "category_id": category.id,
                    "name": "跨行重复二",
                    "quantity": 1,
                    "asset_nos": ["2003-1"],
                },
            ]
        },
        headers=admin_headers,
    )
    assert duplicate_across_lines.status_code == 422, duplicate_across_lines.text
    assert "重复" in duplicate_across_lines.json()["message"]

    existing = await client.post(
        "/api/v1/assets",
        json={
            "asset_no": "2004-1",
            "name": "已存在资产",
            "category_id": category.id,
        },
        headers=admin_headers,
    )
    assert existing.status_code == 200, existing.text

    duplicate_existing = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="与台账重复",
        quantity=1,
        base_asset_no="2004",
        asset_nos=["2004-1"],
    )
    assert duplicate_existing.status_code == 409, duplicate_existing.text
    assert duplicate_existing.json()["code"] == 40902
    assert "已存在" in duplicate_existing.json()["message"]

    pending = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="预占编码",
        quantity=2,
        base_asset_no="2005",
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()["data"]["items"][0]["asset_nos"] == ["2005-1", "2005-2"]

    manual_conflict = await client.post(
        "/api/v1/assets",
        json={"asset_no": "2005-2", "name": "手工占用", "category_id": category.id},
        headers=admin_headers,
    )
    assert manual_conflict.status_code == 409, manual_conflict.text
    assert manual_conflict.json()["code"] == 40930
    assert "待确认入库单占用" in manual_conflict.json()["message"]


async def test_base_code_suffix_increments_across_inbounds(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    category = await _category()

    first = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="第一批",
        quantity=3,
        base_asset_no="3001",
    )
    assert first.status_code == 200, first.text
    assert first.json()["data"]["items"][0]["asset_nos"] == [
        "3001-1",
        "3001-2",
        "3001-3",
    ]

    preview = await client.get(
        "/api/v1/inbounds/options/next-codes",
        params={"base_no": "3001", "quantity": 2},
        headers=admin_headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["codes"] == ["3001-4", "3001-5"]

    second = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="第二批",
        quantity=2,
        base_asset_no="3001",
    )
    assert second.status_code == 200, second.text
    assert second.json()["data"]["items"][0]["asset_nos"] == ["3001-4", "3001-5"]

    bad_manual = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="占用已预占编码",
        quantity=1,
        base_asset_no="3001",
        asset_nos=["3001-4"],
    )
    assert bad_manual.status_code == 409, bad_manual.text
    assert "已存在" in bad_manual.json()["message"]

    cancelled = await _create_inbound(
        client,
        admin_headers,
        category.id,
        name="待取消批次",
        quantity=2,
        base_asset_no="3001",
    )
    assert cancelled.status_code == 200, cancelled.text
    cancelled_data = cancelled.json()["data"]
    assert cancelled_data["items"][0]["asset_nos"] == ["3001-6", "3001-7"]
    cancel_response = await client.post(
        f"/api/v1/inbounds/{cancelled_data['id']}/cancel",
        json={"reason": "测试取消"},
        headers=admin_headers,
    )
    assert cancel_response.status_code == 200, cancel_response.text

    next_preview = await client.get(
        "/api/v1/inbounds/options/next-codes",
        params={"base_no": "3001", "quantity": 1},
        headers=admin_headers,
    )
    assert next_preview.status_code == 200, next_preview.text
    assert next_preview.json()["data"]["codes"] == ["3001-8"]

    async with AsyncSessionLocal() as session:
        codes = list(
            (
                await session.execute(
                    select(AssetInboundCode.asset_no)
                    .where(AssetInboundCode.asset_no.like("3001-%"))
                    .order_by(AssetInboundCode.asset_no)
                )
            )
            .scalars()
            .all()
        )
        cancelled_row = await session.get(AssetInbound, cancelled_data["id"])
    assert cancelled_row.status == "CANCELLED"
    assert codes == ["3001-1", "3001-2", "3001-3", "3001-4", "3001-5"]
