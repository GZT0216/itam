from datetime import timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import func, insert, select

from app.core.assets import AssetStatus
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Asset,
    AssetCategory,
    AssetContract,
    AssetRequest,
    AuditLog,
    Dept,
    InventoryTask,
    Role,
    User,
    user_roles,
)
from app.models.base import now_cst
from tests.helpers import auth_headers, login

TEST_PASSWORD = "Test@12345"


async def _dept_id(code: str) -> int:
    async with AsyncSessionLocal() as session:
        dept = (
            await session.execute(select(Dept).where(Dept.code == code))
        ).scalar_one()
        return dept.id


async def _ensure_user(
    username: str, real_name: str, role_code: str, dept_code: str
) -> int:
    async with AsyncSessionLocal() as session:
        role = (
            await session.execute(select(Role).where(Role.code == role_code))
        ).scalar_one()
        dept = (
            await session.execute(select(Dept).where(Dept.code == dept_code))
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


async def _create_asset(
    asset_no: str,
    name: str,
    *,
    dept_id: int,
    status: str,
    custodian_id: int | None = None,
    warranty_end=None,
) -> int:
    async with AsyncSessionLocal() as session:
        category = (
            await session.execute(
                select(AssetCategory).where(AssetCategory.code == "HW-LAPTOP")
            )
        ).scalar_one()
        asset = Asset(
            asset_no=asset_no,
            name=name,
            category_id=category.id,
            dept_id=dept_id,
            custodian_id=custodian_id,
            status=status,
            warranty_end=warranty_end,
        )
        session.add(asset)
        await session.commit()
        return asset.id


async def _create_contract(
    contract_no: str,
    name: str,
    *,
    dept_id: int,
    end_date,
    status: str = "ACTIVE",
) -> int:
    async with AsyncSessionLocal() as session:
        today = now_cst().date()
        contract = AssetContract(
            contract_no=contract_no,
            name=name,
            contract_type="PURCHASE",
            status=status,
            amount=Decimal("1000.00"),
            start_date=today - timedelta(days=100),
            end_date=end_date,
            dept_id=dept_id,
        )
        session.add(contract)
        await session.commit()
        return contract.id


async def _create_borrow(
    request_no: str,
    *,
    asset_id: int,
    asset_no: str,
    asset_name: str,
    applicant_id: int,
    applicant_name: str,
    applicant_dept_id: int,
    expected_return_date,
) -> int:
    async with AsyncSessionLocal() as session:
        asset = await session.get(Asset, asset_id)
        request = AssetRequest(
            request_no=request_no,
            request_type="BORROW",
            status="BORROWED",
            category_id=asset.category_id,
            category_name=asset.category.name if asset.category else "",
            include_child=False,
            asset_id=asset_id,
            asset_no=asset_no,
            asset_name=asset_name,
            asset_version=1,
            applicant_id=applicant_id,
            applicant_name=applicant_name,
            applicant_dept_id=applicant_dept_id,
            expected_return_date=expected_return_date,
        )
        session.add(request)
        await session.commit()
        return request.id


async def _create_inventory(
    task_no: str,
    name: str,
    *,
    dept_id: int,
    planned_date,
    status: str = "IN_PROGRESS",
) -> int:
    async with AsyncSessionLocal() as session:
        task = InventoryTask(
            task_no=task_no,
            name=name,
            status=status,
            scope_dept_id=dept_id,
            planned_date=planned_date,
        )
        session.add(task)
        await session.commit()
        return task.id


async def test_reminder_summary_filters_scan_and_dedup(client: AsyncClient):
    token = (await login(client))["access_token"]
    headers = auth_headers(token)
    today = now_cst().date()
    it_dept = await _dept_id("IT")
    fin_dept = await _dept_id("FIN")
    async with AsyncSessionLocal() as session:
        admin = (
            await session.execute(select(User).where(User.username == "admin"))
        ).scalar_one()
        admin_id = admin.id

    expiring_id = await _create_asset(
        "REM-ASSET-001",
        "临期保修笔记本",
        dept_id=it_dept,
        status=AssetStatus.IN_USE,
        custodian_id=admin_id,
        warranty_end=today + timedelta(days=5),
    )
    await _create_asset(
        "REM-ASSET-002",
        "过保笔记本",
        dept_id=it_dept,
        status=AssetStatus.IN_STOCK,
        warranty_end=today - timedelta(days=3),
    )
    await _create_asset(
        "REM-ASSET-003",
        "远期保修笔记本",
        dept_id=it_dept,
        status=AssetStatus.IN_USE,
        custodian_id=admin_id,
        warranty_end=today + timedelta(days=60),
    )
    await _create_asset(
        "REM-ASSET-004",
        "已报废过保笔记本",
        dept_id=it_dept,
        status=AssetStatus.SCRAPPED,
        warranty_end=today - timedelta(days=10),
    )
    await _create_contract(
        "REM-HT-001", "临期采购合同", dept_id=it_dept, end_date=today + timedelta(days=10)
    )
    await _create_contract(
        "REM-HT-002", "已到期采购合同", dept_id=it_dept, end_date=today - timedelta(days=2)
    )
    await _create_contract(
        "REM-HT-003",
        "已终止合同",
        dept_id=it_dept,
        end_date=today + timedelta(days=2),
        status="TERMINATED",
    )
    await _create_borrow(
        "REM-JY-001",
        asset_id=expiring_id,
        asset_no="REM-ASSET-001",
        asset_name="临期保修笔记本",
        applicant_id=admin_id,
        applicant_name="系统管理员",
        applicant_dept_id=it_dept,
        expected_return_date=today + timedelta(days=1),
    )
    await _create_borrow(
        "REM-JY-002",
        asset_id=expiring_id,
        asset_no="REM-ASSET-001",
        asset_name="临期保修笔记本",
        applicant_id=admin_id,
        applicant_name="系统管理员",
        applicant_dept_id=it_dept,
        expected_return_date=today - timedelta(days=2),
    )
    await _create_inventory(
        "REM-PD-001", "IT 部门盘点", dept_id=it_dept, planned_date=today - timedelta(days=1)
    )
    await _create_inventory(
        "REM-PD-002", "远期盘点", dept_id=it_dept, planned_date=today + timedelta(days=10)
    )
    await _create_inventory(
        "REM-PD-003",
        "已完成盘点",
        dept_id=it_dept,
        planned_date=today - timedelta(days=1),
        status="COMPLETED",
    )
    await _create_contract(
        "REM-HT-FIN", "财务合同", dept_id=fin_dept, end_date=today + timedelta(days=5)
    )
    await _create_inventory(
        "REM-PD-FIN", "财务盘点", dept_id=fin_dept, planned_date=today - timedelta(days=1)
    )

    summary = await client.get("/api/v1/reminders/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    data = summary.json()["data"]
    counts = {item["category"]: item["count"] for item in data["categories"]}
    assert counts == {
        "WARRANTY": 2,
        "CONTRACT": 3,
        "BORROW": 2,
        "INVENTORY": 2,
    }
    assert data["total"] == 9
    assert data["danger_count"] == 5
    assert data["email_enabled"] is False

    warranty = await client.get(
        "/api/v1/reminders",
        params={"category": "WARRANTY", "page": 1, "page_size": 10},
        headers=headers,
    )
    assert warranty.status_code == 200, warranty.text
    warranty_data = warranty.json()["data"]
    assert warranty_data["total"] == 2
    assert warranty_data["items"][0]["level"] == "danger"

    danger = await client.get(
        "/api/v1/reminders",
        params={"level": "danger", "page": 1, "page_size": 10},
        headers=headers,
    )
    assert danger.status_code == 200, danger.text
    assert danger.json()["data"]["total"] == 5

    keyword = await client.get(
        "/api/v1/reminders",
        params={"keyword": "REM-ASSET-002", "page": 1, "page_size": 10},
        headers=headers,
    )
    assert keyword.status_code == 200, keyword.text
    assert keyword.json()["data"]["total"] == 1
    assert keyword.json()["data"]["items"][0]["source_no"] == "REM-ASSET-002"

    scan = await client.post("/api/v1/reminders/scan", headers=headers)
    assert scan.status_code == 200, scan.text
    scan_data = scan.json()["data"]
    assert scan_data["already_scanned"] is False
    assert scan_data["created"] == 4
    assert scan_data["email_status"] == "SKIPPED"
    assert scan_data["total"] == 9

    again = await client.post("/api/v1/reminders/scan", headers=headers)
    assert again.status_code == 200, again.text
    assert again.json()["data"]["already_scanned"] is True
    assert again.json()["data"]["created"] == 0

    async with AsyncSessionLocal() as session:
        scan_audits = int(
            await session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == "asset.reminder.scan"
                )
            )
            or 0
        )
        warranty_audits = int(
            await session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == "asset.warranty.due_reminder"
                )
            )
            or 0
        )
        inventory_audits = int(
            await session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == "asset.inventory.due_reminder"
                )
            )
            or 0
        )
    assert scan_audits == 1
    assert warranty_audits == 2
    assert inventory_audits == 2


async def test_reminder_scope_and_permissions(client: AsyncClient):
    today = now_cst().date()
    it_dept = await _dept_id("IT")
    fin_dept = await _dept_id("FIN")
    employee_id = await _ensure_user("rem_employee", "提醒员工", "EMPLOYEE", "IT")
    await _ensure_user("rem_dept_admin", "IT 提醒管理员", "DEPT_ADMIN", "IT")
    async with AsyncSessionLocal() as session:
        admin = (
            await session.execute(select(User).where(User.username == "admin"))
        ).scalar_one()
        admin_id = admin.id

    own_asset = await _create_asset(
        "REM-EMP-001",
        "员工保修笔记本",
        dept_id=it_dept,
        status=AssetStatus.IN_USE,
        custodian_id=employee_id,
        warranty_end=today + timedelta(days=4),
    )
    await _create_asset(
        "REM-FIN-001",
        "财务保修笔记本",
        dept_id=fin_dept,
        status=AssetStatus.IN_USE,
        warranty_end=today + timedelta(days=4),
    )
    await _create_contract(
        "REM-SCOPE-FIN", "财务合同", dept_id=fin_dept, end_date=today + timedelta(days=3)
    )
    await _create_contract(
        "REM-SCOPE-IT", "IT 合同", dept_id=it_dept, end_date=today + timedelta(days=3)
    )
    await _create_inventory(
        "REM-SCOPE-INV-IT", "IT 盘点", dept_id=it_dept, planned_date=today
    )
    await _create_inventory(
        "REM-SCOPE-INV-FIN", "财务盘点", dept_id=fin_dept, planned_date=today - timedelta(days=1)
    )
    await _create_borrow(
        "REM-SCOPE-JY-EMP",
        asset_id=own_asset,
        asset_no="REM-EMP-001",
        asset_name="员工保修笔记本",
        applicant_id=employee_id,
        applicant_name="提醒员工",
        applicant_dept_id=it_dept,
        expected_return_date=today + timedelta(days=1),
    )
    await _create_borrow(
        "REM-SCOPE-JY-ADMIN",
        asset_id=own_asset,
        asset_no="REM-EMP-001",
        asset_name="员工保修笔记本",
        applicant_id=admin_id,
        applicant_name="系统管理员",
        applicant_dept_id=it_dept,
        expected_return_date=today + timedelta(days=1),
    )

    employee_headers = await _login_as(client, "rem_employee")
    summary = await client.get("/api/v1/reminders/summary", headers=employee_headers)
    assert summary.status_code == 200, summary.text
    data = summary.json()["data"]
    categories = {item["category"]: item["count"] for item in data["categories"]}
    assert categories == {"WARRANTY": 1, "BORROW": 1}
    assert data["total"] == 2

    forbidden = await client.post("/api/v1/reminders/scan", headers=employee_headers)
    assert forbidden.status_code == 403

    dept_headers = await _login_as(client, "rem_dept_admin")
    dept_summary = await client.get(
        "/api/v1/reminders/summary", headers=dept_headers
    )
    assert dept_summary.status_code == 200, dept_summary.text
    dept_categories = {
        item["category"]: item["count"]
        for item in dept_summary.json()["data"]["categories"]
    }
    assert dept_categories["CONTRACT"] == 1
    assert dept_categories["INVENTORY"] == 1
    dept_items = await client.get(
        "/api/v1/reminders",
        params={"category": "CONTRACT", "page": 1, "page_size": 10},
        headers=dept_headers,
    )
    assert dept_items.status_code == 200, dept_items.text
    assert dept_items.json()["data"]["items"][0]["source_no"] == "REM-SCOPE-IT"


async def _login_as(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return auth_headers(response.json()["data"]["access_token"])
