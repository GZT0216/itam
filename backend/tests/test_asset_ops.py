from httpx import AsyncClient
from sqlalchemy import insert, select

from app.core.assets import AssetStatus
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Asset,
    AssetCategory,
    AssetHistory,
    AssetRequest,
    AssetScrap,
    AssetTransfer,
    Dept,
    Role,
    User,
    user_roles,
)
from tests.helpers import auth_headers, login

TEST_PASSWORD = "Test@12345"


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


async def _dept_id(code: str) -> int:
    async with AsyncSessionLocal() as session:
        return (await session.execute(select(Dept.id).where(Dept.code == code))).scalar_one()


async def _category_id(code: str = "HW-LAPTOP") -> int:
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(
                select(AssetCategory.id).where(AssetCategory.code == code)
            )
        ).scalar_one()


async def _ensure_asset(
    asset_no: str,
    name: str,
    status: str = AssetStatus.IN_STOCK,
    *,
    custodian_id: int | None = None,
) -> int:
    async with AsyncSessionLocal() as session:
        category = (
            await session.execute(
                select(AssetCategory).where(AssetCategory.code == "HW-LAPTOP")
            )
        ).scalar_one()
        dept = (
            await session.execute(select(Dept).where(Dept.code == "IT"))
        ).scalar_one()
        asset = Asset(
            asset_no=asset_no,
            name=name,
            category_id=category.id,
            dept_id=dept.id,
            custodian_id=custodian_id,
            status=status,
            location="A 座 101",
        )
        session.add(asset)
        await session.commit()
        return asset.id


async def _login_as(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return auth_headers(response.json()["data"]["access_token"])


async def test_transfer_flow_with_optimistic_lock(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    holder_id = await _ensure_user("ops_holder", "资产持有人", "EMPLOYEE")
    target_id = await _ensure_user("ops_target", "接收人", "EMPLOYEE")
    await _ensure_user("ops_asset", "资产管理员", "ASSET_ADMIN")
    await _ensure_user("ops_dept", "部门管理员", "DEPT_ADMIN")
    asset_id = await _ensure_asset(
        "ITAM-OPS-0001",
        "调拨测试笔记本",
        AssetStatus.IN_USE,
        custodian_id=holder_id,
    )
    fin_id = await _dept_id("FIN")
    asset_headers = await _login_as(client, "ops_asset")
    dept_headers = await _login_as(client, "ops_dept")
    employee_headers = await _login_as(client, "ops_holder")

    forbidden = await client.post(
        "/api/v1/asset-transfers",
        json={"asset_id": asset_id, "to_dept_id": fin_id},
        headers=employee_headers,
    )
    assert forbidden.status_code == 403

    created = await client.post(
        "/api/v1/asset-transfers",
        json={
            "asset_id": asset_id,
            "to_dept_id": fin_id,
            "to_custodian_id": target_id,
            "to_location": "B 座 302",
            "reason": "岗位调整",
        },
        headers=asset_headers,
    )
    assert created.status_code == 200, created.text
    transfer = created.json()["data"]
    assert transfer["transfer_no"].startswith("DB-")
    assert transfer["status"] == "PENDING_APPROVAL"
    assert transfer["from_dept_name"] == "信息技术部"
    transfer_id = transfer["id"]

    forbidden_confirm = await client.post(
        f"/api/v1/asset-transfers/{transfer_id}/confirm",
        json={"version": transfer["asset_version"]},
        headers=dept_headers,
    )
    assert forbidden_confirm.status_code == 403

    approved = await client.post(
        f"/api/v1/asset-transfers/{transfer_id}/approve",
        json={"comment": "同意调拨"},
        headers=dept_headers,
    )
    assert approved.status_code == 200, approved.text
    approved_data = approved.json()["data"]
    assert approved_data["status"] == "PENDING_TRANSFER"
    stale_version = approved_data["asset_version"]

    async with AsyncSessionLocal() as session:
        asset = await session.get(Asset, asset_id)
        asset.location = "并发修改位置"
        await session.commit()

    conflict = await client.post(
        f"/api/v1/asset-transfers/{transfer_id}/confirm",
        json={"version": stale_version},
        headers=asset_headers,
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == 40911
    assert conflict.json()["message"] == "资产状态已变更，请刷新后重试"

    async with AsyncSessionLocal() as session:
        row = await session.get(AssetTransfer, transfer_id)
        assert row.status == "PENDING_TRANSFER"
        histories = (
            await session.execute(
                select(AssetHistory).where(AssetHistory.asset_id == asset_id)
            )
        ).scalars().all()
    assert histories == []

    confirmed = await client.post(
        f"/api/v1/asset-transfers/{transfer_id}/confirm",
        json={"version": stale_version + 1, "comment": "实物已交接"},
        headers=asset_headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["status"] == "COMPLETED"

    detail = await client.get(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    asset = detail.json()["data"]
    assert asset["dept_id"] == fin_id
    assert asset["custodian_id"] == target_id
    assert asset["location"] == "B 座 302"
    assert asset["status"] == "IN_USE"

    history = await client.get(
        f"/api/v1/assets/{asset_id}/history", headers=admin_headers
    )
    items = history.json()["data"]
    assert len(items) == 1
    assert items[0]["action"] == "TRANSFER"
    assert items[0]["before_snapshot"]["dept_name"] == "信息技术部"
    assert items[0]["after_snapshot"]["dept_name"] == "财务部"
    assert items[0]["after_snapshot"]["custodian_name"] == "接收人"


async def test_scrap_flow_and_cross_module_guard(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    await _ensure_user("scrap_asset", "报废管理员", "ASSET_ADMIN")
    await _ensure_user("scrap_dept", "报废部门管理员", "DEPT_ADMIN")
    await _ensure_user("scrap_emp", "报废员工", "EMPLOYEE")
    asset_id = await _ensure_asset("ITAM-OPS-0002", "报废测试台式机", AssetStatus.IN_STOCK)
    asset_headers = await _login_as(client, "scrap_asset")
    dept_headers = await _login_as(client, "scrap_dept")
    emp_headers = await _login_as(client, "scrap_emp")

    created = await client.post(
        "/api/v1/asset-scraps",
        json={
            "asset_id": asset_id,
            "reason": "主板损坏无法维修",
            "disposal_method": "环保回收",
            "residual_value": 120.5,
        },
        headers=asset_headers,
    )
    assert created.status_code == 200, created.text
    scrap = created.json()["data"]
    assert scrap["scrap_no"].startswith("BF-")
    assert scrap["status"] == "PENDING_APPROVAL"
    assert scrap["residual_value"] == 120.5
    scrap_id = scrap["id"]

    request_created = await client.post(
        "/api/v1/asset-requests",
        json={
            "request_type": "REQUISITION",
            "category_id": await _category_id(),
        },
        headers=emp_headers,
    )
    assert request_created.status_code == 200, request_created.text
    request_id = request_created.json()["data"]["id"]

    dept_approved = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "部门同意"},
        headers=dept_headers,
    )
    assert dept_approved.status_code == 200, dept_approved.text
    asset_approved = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "资产同意"},
        headers=asset_headers,
    )
    assert asset_approved.status_code == 200, asset_approved.text

    candidates = await client.get(
        f"/api/v1/asset-requests/{request_id}/outbound-assets",
        headers=asset_headers,
    )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()["data"]["total"] == 0

    blocked_outbound = await client.post(
        f"/api/v1/asset-requests/{request_id}/outbound",
        json={"asset_id": asset_id, "version": scrap["asset_version"]},
        headers=asset_headers,
    )
    assert blocked_outbound.status_code == 409
    assert "报废" in blocked_outbound.json()["message"]

    cancelled = await client.post(
        f"/api/v1/asset-requests/{request_id}/cancel",
        headers=emp_headers,
    )
    assert cancelled.status_code == 200, cancelled.text

    approved = await client.post(
        f"/api/v1/asset-scraps/{scrap_id}/approve",
        json={"version": scrap["asset_version"], "comment": "同意报废"},
        headers=dept_headers,
    )
    assert approved.status_code == 200, approved.text
    approved_data = approved.json()["data"]
    assert approved_data["status"] == "PENDING_DISPOSAL"
    assert approved_data["asset_status"] == "PENDING_SCRAP"

    stale = await client.post(
        f"/api/v1/asset-scraps/{scrap_id}/confirm",
        json={"version": scrap["asset_version"]},
        headers=asset_headers,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["code"] == 40911
    assert stale.json()["message"] == "资产状态已变更，请刷新后重试"

    confirmed = await client.post(
        f"/api/v1/asset-scraps/{scrap_id}/confirm",
        json={"version": approved_data["asset_version"], "comment": "已完成回收"},
        headers=asset_headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["status"] == "COMPLETED"

    detail = await client.get(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    asset = detail.json()["data"]
    assert asset["status"] == "SCRAPPED"
    assert asset["custodian_id"] is None

    history = await client.get(
        f"/api/v1/assets/{asset_id}/history", headers=admin_headers
    )
    actions = [item["action"] for item in history.json()["data"]]
    assert actions == ["SCRAP_COMPLETED", "SCRAP_PENDING"]

    async with AsyncSessionLocal() as session:
        row = await session.get(AssetScrap, scrap_id)
        assert row.status == "COMPLETED"
        request_row = await session.get(AssetRequest, request_id)
    assert request_row.status == "CANCELLED"
    assert request_row.asset_id is None


async def test_inventory_task_scan_and_complete(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    await _ensure_user("inv_asset", "盘点管理员", "ASSET_ADMIN")
    await _ensure_user("inv_emp", "盘点员工", "EMPLOYEE")
    first_id = await _ensure_asset("ITAM-OPS-0101", "盘点笔记本一")
    second_id = await _ensure_asset("ITAM-OPS-0102", "盘点笔记本二")
    it_id = await _dept_id("IT")
    asset_headers = await _login_as(client, "inv_asset")
    emp_headers = await _login_as(client, "inv_emp")

    forbidden = await client.post(
        "/api/v1/inventory-tasks",
        json={"name": "越权盘点", "scope_dept_id": it_id},
        headers=emp_headers,
    )
    assert forbidden.status_code == 403

    created = await client.post(
        "/api/v1/inventory-tasks",
        json={"name": "IT 部季度盘点", "scope_dept_id": it_id, "include_child": False},
        headers=asset_headers,
    )
    assert created.status_code == 200, created.text
    task = created.json()["data"]
    assert task["task_no"].startswith("PD-")
    assert task["total_assets"] == 2
    assert task["pending_count"] == 2
    task_id = task["id"]

    items_page = await client.get(
        f"/api/v1/inventory-tasks/{task_id}/items",
        params={"page_size": 50},
        headers=asset_headers,
    )
    assert items_page.status_code == 200, items_page.text
    items = items_page.json()["data"]["items"]
    assert len(items) == 2

    early_complete = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/complete", headers=asset_headers
    )
    assert early_complete.status_code == 400
    assert "未盘点" in early_complete.json()["message"]

    scanned = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/scan",
        json={"code": "ITAM-OPS-0101"},
        headers=asset_headers,
    )
    assert scanned.status_code == 200, scanned.text
    assert scanned.json()["data"]["result"] == "NORMAL"

    second_item = next(item for item in items if item["asset_id"] == second_id)
    updated = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/items/{second_item['id']}",
        json={"result": "MISSING", "remark": "现场未找到"},
        headers=asset_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["result"] == "MISSING"

    completed = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/complete", headers=asset_headers
    )
    assert completed.status_code == 200, completed.text
    data = completed.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["normal_count"] == 1
    assert data["missing_count"] == 1
    assert data["pending_count"] == 0

    detail = await client.get(f"/api/v1/assets/{first_id}", headers=admin_headers)
    assert detail.json()["data"]["status"] == "IN_STOCK"


async def test_inventory_surplus_adjustment_and_report(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    await _ensure_user("inv_adj_asset", "盘点处理员", "ASSET_ADMIN")
    await _ensure_user("inv_adj_emp", "盘点普通员工", "EMPLOYEE")
    missing_asset_id = await _ensure_asset("ITAM-OPS-0301", "盘亏笔记本")
    it_id = await _dept_id("IT")
    category_id = await _category_id("HW-LAPTOP")
    asset_headers = await _login_as(client, "inv_adj_asset")
    emp_headers = await _login_as(client, "inv_adj_emp")

    created = await client.post(
        "/api/v1/inventory-tasks",
        json={"name": "IT 部差异盘点", "scope_dept_id": it_id, "include_child": False},
        headers=asset_headers,
    )
    assert created.status_code == 200, created.text
    task_id = created.json()["data"]["id"]

    items = (
        await client.get(
            f"/api/v1/inventory-tasks/{task_id}/items",
            params={"page_size": 50},
            headers=asset_headers,
        )
    ).json()["data"]["items"]
    item = next(row for row in items if row["asset_id"] == missing_asset_id)
    marked = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/items/{item['id']}",
        json={"result": "MISSING", "remark": "现场未找到"},
        headers=asset_headers,
    )
    assert marked.status_code == 200, marked.text

    surplus = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/surplus-items",
        json={
            "asset_no": "ITAM-OPS-0302",
            "name": "盘盈笔记本",
            "category_id": category_id,
            "dept_id": it_id,
            "serial_no": "SN-SURPLUS-0302",
            "purchase_price": 5200.5,
            "remark": "现场发现未入账设备",
        },
        headers=asset_headers,
    )
    assert surplus.status_code == 200, surplus.text
    surplus_row = surplus.json()["data"]
    assert surplus_row["asset_no"] == "ITAM-OPS-0302"
    assert surplus_row["purchase_price"] == 5200.5

    duplicate = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/surplus-items",
        json={
            "asset_no": "ITAM-OPS-0302",
            "name": "重复登记",
            "category_id": category_id,
        },
        headers=asset_headers,
    )
    assert duplicate.status_code == 400
    assert "已" in duplicate.json()["message"]

    completed = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/complete", headers=asset_headers
    )
    assert completed.status_code == 200, completed.text
    task_data = completed.json()["data"]
    assert task_data["status"] == "COMPLETED"
    assert task_data["missing_count"] == 1
    assert task_data["surplus_count"] == 1
    assert task_data["can_submit_adjustment"] is True

    forbidden = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/adjustment",
        json={"reason": "越权提交"},
        headers=emp_headers,
    )
    assert forbidden.status_code == 403

    submitted = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/adjustment",
        json={"reason": "季度盘点差异核销"},
        headers=asset_headers,
    )
    assert submitted.status_code == 200, submitted.text
    adjustment = submitted.json()["data"]
    assert adjustment["adjustment_no"].startswith("TZ-")
    assert adjustment["status"] == "PENDING"
    assert adjustment["loss_count"] == 1
    assert adjustment["surplus_count"] == 1

    duplicate_submit = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/adjustment",
        json={"reason": "重复提交"},
        headers=asset_headers,
    )
    assert duplicate_submit.status_code == 400

    summary = await client.get("/api/v1/todos/summary", headers=admin_headers)
    summary_counts = {
        row["todo_type"]: row["count"]
        for category in summary.json()["data"]["categories"]
        for row in category["types"]
    }
    assert summary_counts["inventory_approval"] == 1

    rejected = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/adjustment/reject",
        json={"version": adjustment["version"], "comment": "请补充差异说明"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["status"] == "REJECTED"

    resubmitted = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/adjustment",
        json={"reason": "已补充现场核查说明"},
        headers=asset_headers,
    )
    assert resubmitted.status_code == 200, resubmitted.text
    resubmitted_data = resubmitted.json()["data"]
    assert resubmitted_data["status"] == "PENDING"

    emp_approve = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/adjustment/approve",
        json={"version": resubmitted_data["version"]},
        headers=emp_headers,
    )
    assert emp_approve.status_code == 403

    approved = await client.post(
        f"/api/v1/inventory-tasks/{task_id}/adjustment/approve",
        json={"version": resubmitted_data["version"], "comment": "同意核销并补建档"},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    approved_data = approved.json()["data"]
    assert approved_data["status"] == "APPROVED"
    assert approved_data["reviewed_by_name"]

    detail = await client.get(
        f"/api/v1/assets/{missing_asset_id}", headers=admin_headers
    )
    assert detail.json()["data"]["status"] == "SCRAPPED"
    assert detail.json()["data"]["custodian_id"] is None
    history = await client.get(
        f"/api/v1/assets/{missing_asset_id}/history", headers=admin_headers
    )
    actions = [row["action"] for row in history.json()["data"]]
    assert "INVENTORY_LOSS" in actions

    created_asset = await client.get(
        "/api/v1/assets",
        params={"keyword": "ITAM-OPS-0302"},
        headers=admin_headers,
    )
    assert created_asset.status_code == 200, created_asset.text
    rows = created_asset.json()["data"]["items"]
    assert len(rows) == 1
    assert rows[0]["status"] == "IN_STOCK"
    assert rows[0]["dept_id"] == it_id

    surplus_list = await client.get(
        f"/api/v1/inventory-tasks/{task_id}/surplus-items", headers=asset_headers
    )
    surplus_items = surplus_list.json()["data"]
    assert len(surplus_items) == 1
    assert surplus_items[0]["applied_at"] is not None
    assert surplus_items[0]["created_asset_id"] == rows[0]["id"]

    report = await client.get(
        f"/api/v1/inventory-tasks/{task_id}/report", headers=asset_headers
    )
    assert report.status_code == 200, report.text
    report_data = report.json()["data"]
    assert report_data["task"]["surplus_count"] == 1
    assert len(report_data["missing_items"]) == 1
    assert len(report_data["surplus_items"]) == 1
    assert report_data["adjustment"]["status"] == "APPROVED"

    exported = await client.get(
        f"/api/v1/inventory-tasks/{task_id}/report/export", headers=admin_headers
    )
    assert exported.status_code == 200, exported.text
    assert (
        exported.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(exported.content) > 1000
