from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import func, insert, select

from app.core.assets import AssetStatus
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Asset,
    AssetCategory,
    AssetContract,
    AuditLog,
    Dept,
    Role,
    User,
    user_roles,
)
from app.models.base import now_cst
from app.services.contract_service import ContractService
from tests.helpers import auth_headers, login

TEST_PASSWORD = "Test@12345"


async def _ensure_user(
    username: str, real_name: str, role_code: str, dept_code: str = "IT"
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


async def _dept_id(code: str) -> int:
    async with AsyncSessionLocal() as session:
        dept = (
            await session.execute(select(Dept).where(Dept.code == code))
        ).scalar_one()
        return dept.id


async def _ensure_asset(asset_no: str, name: str) -> int:
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
            status=AssetStatus.IN_STOCK,
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


def _contract_payload(
    *,
    name: str,
    start_date,
    end_date,
    dept_id: int | None,
    asset_ids: list[int] | None = None,
) -> dict:
    return {
        "name": name,
        "contract_type": "MAINTENANCE",
        "supplier": "测试供应商",
        "amount": "12000.00",
        "sign_date": start_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "dept_id": dept_id,
        "remark": "测试合同",
        "asset_ids": asset_ids or [],
    }


async def test_contract_flow_notifications_and_optimistic_lock(client: AsyncClient):
    token = (await login(client))["access_token"]
    headers = auth_headers(token)
    today = now_cst().date()
    it_dept = await _dept_id("IT")
    asset_one = await _ensure_asset("HT-ASSET-001", "合同测试笔记本 1")
    asset_two = await _ensure_asset("HT-ASSET-002", "合同测试笔记本 2")

    created = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="机房设备维保合同",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=10),
            dept_id=it_dept,
            asset_ids=[asset_one],
        ),
        headers=headers,
    )
    assert created.status_code == 200, created.text
    contract = created.json()["data"]
    assert contract["status"] == "EXPIRING"
    assert contract["contract_no"].startswith("HT-")
    assert contract["asset_count"] == 1
    assert contract["can_edit"] is True

    listed = await client.get(
        "/api/v1/contracts",
        params={"status": "EXPIRING", "page": 1, "page_size": 20},
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    listed_data = listed.json()["data"]
    assert any(item["id"] == contract["id"] for item in listed_data["items"])

    summary = await client.get("/api/v1/contracts/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["data"]["expiring_count"] >= 1

    notifications = await client.get("/api/v1/notifications/summary", headers=headers)
    assert notifications.status_code == 200, notifications.text
    notification_ids = [item["id"] for item in notifications.json()["data"]["items"]]
    assert "contract-expiring-30d" in notification_ids

    updated = await client.put(
        f"/api/v1/contracts/{contract['id']}",
        json={
            **_contract_payload(
                name="机房设备维保合同（更新）",
                start_date=today - timedelta(days=30),
                end_date=today + timedelta(days=10),
                dept_id=it_dept,
            ),
            "version": contract["version"],
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    updated_data = updated.json()["data"]
    assert updated_data["name"].endswith("（更新）")
    assert updated_data["version"] == contract["version"] + 1

    conflict = await client.put(
        f"/api/v1/contracts/{contract['id']}",
        json={
            **_contract_payload(
                name="并发覆盖",
                start_date=today - timedelta(days=30),
                end_date=today + timedelta(days=10),
                dept_id=it_dept,
            ),
            "version": contract["version"],
        },
        headers=headers,
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == 40911

    linked = await client.post(
        f"/api/v1/contracts/{contract['id']}/assets",
        json={"asset_ids": [asset_two, asset_two]},
        headers=headers,
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["data"]["asset_count"] == 2

    unlinked = await client.delete(
        f"/api/v1/contracts/{contract['id']}/assets/{asset_one}",
        headers=headers,
    )
    assert unlinked.status_code == 200, unlinked.text
    assert unlinked.json()["data"]["asset_count"] == 1

    renewed = await client.post(
        f"/api/v1/contracts/{contract['id']}/renew",
        json={
            "version": linked.json()["data"]["version"],
            "end_date": (today + timedelta(days=400)).isoformat(),
            "amount": "15000.00",
        },
        headers=headers,
    )
    assert renewed.status_code == 200, renewed.text
    renewed_data = renewed.json()["data"]
    assert renewed_data["status"] == "ACTIVE"
    assert renewed_data["amount"] == "15000.00"

    terminated = await client.post(
        f"/api/v1/contracts/{contract['id']}/terminate",
        json={"version": renewed_data["version"], "reason": "供应商停止服务"},
        headers=headers,
    )
    assert terminated.status_code == 200, terminated.text
    terminated_data = terminated.json()["data"]
    assert terminated_data["status"] == "TERMINATED"
    assert terminated_data["can_edit"] is False

    blocked = await client.post(
        f"/api/v1/contracts/{contract['id']}/assets",
        json={"asset_ids": [asset_one]},
        headers=headers,
    )
    assert blocked.status_code == 400, blocked.text
    assert "已终止" in blocked.json()["message"]

    expiring = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="即将到期合同",
            start_date=today - timedelta(days=100),
            end_date=today + timedelta(days=5),
            dept_id=it_dept,
        ),
        headers=headers,
    )
    assert expiring.status_code == 200, expiring.text
    expired = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="已过期合同",
            start_date=today - timedelta(days=400),
            end_date=today - timedelta(days=3),
            dept_id=it_dept,
        ),
        headers=headers,
    )
    assert expired.status_code == 200, expired.text
    assert expired.json()["data"]["status"] == "EXPIRED"

    async with AsyncSessionLocal() as session:
        service = ContractService(session)
        first_scan = await service.scan_due_reminders()
        second_scan = await service.scan_due_reminders()
        reminder_logs = int(
            await session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == "asset.contract.due_reminder"
                )
            )
            or 0
        )
    assert first_scan >= 2
    assert second_scan == 0
    assert reminder_logs == first_scan


async def test_contract_data_scope_and_permissions(client: AsyncClient):
    token = (await login(client))["access_token"]
    headers = auth_headers(token)
    today = now_cst().date()
    it_dept = await _dept_id("IT")
    fin_dept = await _dept_id("FIN")

    it_contract = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="IT 部门合同",
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=200),
            dept_id=it_dept,
        ),
        headers=headers,
    )
    assert it_contract.status_code == 200, it_contract.text
    fin_contract = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="财务部门合同",
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=200),
            dept_id=fin_dept,
        ),
        headers=headers,
    )
    assert fin_contract.status_code == 200, fin_contract.text
    fin_id = fin_contract.json()["data"]["id"]

    await _ensure_user("dept_admin_contract", "部门管理员", "DEPT_ADMIN")
    dept_headers = await _login_as(client, "dept_admin_contract")
    dept_list = await client.get(
        "/api/v1/contracts", params={"page": 1, "page_size": 50}, headers=dept_headers
    )
    assert dept_list.status_code == 200, dept_list.text
    visible_ids = {item["id"] for item in dept_list.json()["data"]["items"]}
    assert it_contract.json()["data"]["id"] in visible_ids
    assert fin_id not in visible_ids

    forbidden_detail = await client.get(
        f"/api/v1/contracts/{fin_id}", headers=dept_headers
    )
    assert forbidden_detail.status_code == 403, forbidden_detail.text

    forbidden_create = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="越权合同",
            start_date=today,
            end_date=today + timedelta(days=100),
            dept_id=fin_dept,
        ),
        headers=dept_headers,
    )
    assert forbidden_create.status_code == 403, forbidden_create.text

    own_create = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="部门管理员合同",
            start_date=today,
            end_date=today + timedelta(days=100),
            dept_id=it_dept,
        ),
        headers=dept_headers,
    )
    assert own_create.status_code == 200, own_create.text

    await _ensure_user("auditor_contract", "审计员", "AUDITOR")
    auditor_headers = await _login_as(client, "auditor_contract")
    auditor_list = await client.get(
        "/api/v1/contracts", params={"page": 1, "page_size": 20}, headers=auditor_headers
    )
    assert auditor_list.status_code == 200, auditor_list.text
    auditor_create = await client.post(
        "/api/v1/contracts",
        json=_contract_payload(
            name="审计越权合同",
            start_date=today,
            end_date=today + timedelta(days=100),
            dept_id=it_dept,
        ),
        headers=auditor_headers,
    )
    assert auditor_create.status_code == 403, auditor_create.text

    await _ensure_user("employee_contract", "普通员工", "EMPLOYEE")
    employee_headers = await _login_as(client, "employee_contract")
    employee_list = await client.get(
        "/api/v1/contracts", params={"page": 1, "page_size": 20}, headers=employee_headers
    )
    assert employee_list.status_code == 403, employee_list.text

    async with AsyncSessionLocal() as session:
        count = int(
            await session.scalar(select(func.count(AssetContract.id))) or 0
        )
    assert count >= 3
