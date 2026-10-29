from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import insert, select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    Asset,
    AssetCategory,
    AssetInbound,
    AssetMaintenance,
    AssetRequest,
    AssetScrap,
    AssetTransfer,
    Dept,
    InventoryTask,
    Role,
    User,
    user_roles,
)
from tests.helpers import auth_headers, login

TEST_PASSWORD = "Test@12345"
DEPT_NAME = "信息技术部"


async def _ensure_user(username: str, real_name: str, role_code: str) -> int:
    async with AsyncSessionLocal() as session:
        role = (await session.execute(select(Role).where(Role.code == role_code))).scalar_one()
        dept = (await session.execute(select(Dept).where(Dept.code == "IT"))).scalar_one()
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
        await session.execute(insert(user_roles).values(user_id=user.id, role_id=role.id))
        await session.commit()
        return user.id


async def _login_as(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return auth_headers(response.json()["data"]["access_token"])


async def _seed(admin_id: int, emp_id: int, repairer_id: int) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        dept = (await session.execute(select(Dept).where(Dept.code == "IT"))).scalar_one()
        category = (
            await session.execute(select(AssetCategory).where(AssetCategory.code == "HW-LAPTOP"))
        ).scalar_one()

        assets = [
            Asset(
                asset_no="TODO-ASSET-0001",
                name="待办测试笔记本 A",
                category_id=category.id,
                dept_id=dept.id,
                custodian_id=emp_id,
                status="IN_USE",
                location="A 座 301",
            ),
            Asset(
                asset_no="TODO-ASSET-0002",
                name="待办测试笔记本 B",
                category_id=category.id,
                dept_id=dept.id,
                custodian_id=emp_id,
                status="IN_USE",
                location="A 座 301",
            ),
        ]
        session.add_all(assets)
        await session.flush()

        def request_row(
            no: str,
            request_type: str,
            status: str,
            *,
            asset: Asset | None = None,
            expected_return: date | None = None,
            stage: str | None = None,
        ) -> AssetRequest:
            return AssetRequest(
                request_no=no,
                request_type=request_type,
                status=status,
                category_id=category.id,
                category_name=category.name,
                include_child=True,
                asset_id=asset.id if asset else None,
                asset_no=asset.asset_no if asset else None,
                asset_name=asset.name if asset else None,
                asset_version=1,
                applicant_id=emp_id,
                applicant_name="待办员工",
                applicant_dept_id=dept.id,
                applicant_dept_name=DEPT_NAME,
                reason=f"{no} 测试事由",
                expected_return_date=expected_return,
                approval_stage=stage,
                dept_approval_required=False,
            )

        pending_approval = request_row(
            "TODO-REQ-0001", "REQUISITION", "PENDING_APPROVAL", stage="DEPT"
        )
        pending_outbound = request_row("TODO-REQ-0002", "REQUISITION", "PENDING_OUTBOUND")
        pending_return = request_row("TODO-REQ-0003", "RETURN", "PENDING_RETURN")
        borrowed = request_row(
            "TODO-REQ-0004",
            "BORROW",
            "BORROWED",
            asset=assets[0],
            expected_return=date.today() + timedelta(days=1),
        )
        session.add_all([pending_approval, pending_outbound, pending_return, borrowed])
        await session.flush()

        transfer_approval = AssetTransfer(
            transfer_no="TODO-TR-0001",
            status="PENDING_APPROVAL",
            asset_id=assets[0].id,
            asset_no=assets[0].asset_no,
            asset_name=assets[0].name,
            asset_version=1,
            from_dept_id=dept.id,
            from_dept_name=DEPT_NAME,
            from_custodian_id=emp_id,
            from_custodian_name="待办员工",
            to_dept_id=dept.id,
            to_dept_name=DEPT_NAME,
            reason="调拨审批待办",
            applicant_id=emp_id,
            applicant_name="待办员工",
            applicant_dept_id=dept.id,
            applicant_dept_name=DEPT_NAME,
        )
        transfer_confirm = AssetTransfer(
            transfer_no="TODO-TR-0002",
            status="PENDING_TRANSFER",
            asset_id=assets[1].id,
            asset_no=assets[1].asset_no,
            asset_name=assets[1].name,
            asset_version=1,
            from_dept_id=dept.id,
            from_dept_name=DEPT_NAME,
            from_custodian_id=emp_id,
            from_custodian_name="待办员工",
            to_dept_id=dept.id,
            to_dept_name=DEPT_NAME,
            reason="调拨确认待办",
            applicant_id=emp_id,
            applicant_name="待办员工",
            applicant_dept_id=dept.id,
            applicant_dept_name=DEPT_NAME,
        )
        session.add_all([transfer_approval, transfer_confirm])

        scrap_approval = AssetScrap(
            scrap_no="TODO-SC-0001",
            status="PENDING_APPROVAL",
            asset_id=assets[0].id,
            asset_no=assets[0].asset_no,
            asset_name=assets[0].name,
            asset_version=1,
            from_status="IN_USE",
            from_dept_id=dept.id,
            from_dept_name=DEPT_NAME,
            from_custodian_id=emp_id,
            from_custodian_name="待办员工",
            reason="报废审批待办",
            applicant_id=emp_id,
            applicant_name="待办员工",
            applicant_dept_id=dept.id,
            applicant_dept_name=DEPT_NAME,
        )
        scrap_confirm = AssetScrap(
            scrap_no="TODO-SC-0002",
            status="PENDING_DISPOSAL",
            asset_id=assets[1].id,
            asset_no=assets[1].asset_no,
            asset_name=assets[1].name,
            asset_version=1,
            from_status="IN_USE",
            from_dept_id=dept.id,
            from_dept_name=DEPT_NAME,
            from_custodian_id=emp_id,
            from_custodian_name="待办员工",
            reason="报废处置待办",
            applicant_id=emp_id,
            applicant_name="待办员工",
            applicant_dept_id=dept.id,
            applicant_dept_name=DEPT_NAME,
        )
        session.add_all([scrap_approval, scrap_confirm])

        def maintenance_row(
            no: str, status: str, *, repairer: int | None = None
        ) -> AssetMaintenance:
            return AssetMaintenance(
                maintenance_no=no,
                status=status,
                priority="NORMAL",
                asset_id=assets[0].id,
                asset_no=assets[0].asset_no,
                asset_name=assets[0].name,
                asset_version=1,
                from_status="IN_USE",
                from_dept_id=dept.id,
                from_dept_name=DEPT_NAME,
                from_custodian_id=emp_id,
                from_custodian_name="待办员工",
                fault_description=f"{no} 故障描述",
                applicant_id=emp_id,
                applicant_name="待办员工",
                applicant_dept_id=dept.id,
                applicant_dept_name=DEPT_NAME,
                repairer_id=repairer,
                repairer_name="维修人员" if repairer else None,
            )

        maintenance_approval = maintenance_row("TODO-MT-0001", "PENDING_APPROVAL")
        maintenance_repair = maintenance_row(
            "TODO-MT-0002", "PENDING_REPAIR", repairer=repairer_id
        )
        maintenance_accept = maintenance_row("TODO-MT-0003", "PENDING_ACCEPTANCE")
        session.add_all([maintenance_approval, maintenance_repair, maintenance_accept])

        inbound = AssetInbound(
            inbound_no="TODO-IN-0001",
            inbound_type="PURCHASE",
            status="PENDING",
            supplier="待办供应商",
            dept_id=dept.id,
            dept_name=DEPT_NAME,
            total_quantity=1,
            created_by_id=admin_id,
            created_by_name="系统管理员",
        )
        inventory = InventoryTask(
            task_no="TODO-IV-0001",
            name="待办盘点任务",
            status="IN_PROGRESS",
            scope_dept_id=dept.id,
            scope_dept_name=DEPT_NAME,
            created_by_id=admin_id,
            created_by_name="系统管理员",
        )
        session.add_all([inbound, inventory])
        await session.commit()

        return {
            "transfer_approval": transfer_approval.id,
            "inbound": inbound.id,
            "inventory": inventory.id,
        }


def _counts(summary: dict) -> dict[str, int]:
    return {
        item["todo_type"]: item["count"]
        for category in summary["categories"]
        for item in category["types"]
    }


async def test_todo_summary_empty(client: AsyncClient):
    admin = await login(client)
    headers = auth_headers(admin["access_token"])

    response = await client.get("/api/v1/todos/summary", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total"] == 0
    assert [category["category"] for category in data["categories"]] == [
        "APPROVAL",
        "CONFIRM",
        "HANDLE",
        "MINE",
        "DUE",
    ]
    assert all(category["count"] == 0 for category in data["categories"])
    assert all(not category["items"] for category in data["categories"])

    listing = await client.get("/api/v1/todos", headers=headers)
    assert listing.status_code == 200, listing.text
    assert listing.json()["data"] == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
    }


async def test_todo_summary_covers_all_types_and_role_scopes(client: AsyncClient):
    admin = await login(client)
    admin_headers = auth_headers(admin["access_token"])
    emp_id = await _ensure_user("todo_emp", "待办员工", "EMPLOYEE")
    repairer_id = await _ensure_user("todo_repairer", "维修人员", "REPAIRER")
    ids = await _seed(admin["user"]["id"], emp_id, repairer_id)

    response = await client.get("/api/v1/todos/summary", headers=admin_headers)
    data = response.json()["data"]
    counts = _counts(data)
    assert data["total"] == 12
    assert counts == {
        "request_approval": 1,
        "transfer_approval": 1,
        "scrap_approval": 1,
        "maintenance_approval": 1,
        "inventory_approval": 0,
        "request_outbound": 1,
        "request_return": 1,
        "transfer_confirm": 1,
        "scrap_confirm": 1,
        "inbound_confirm": 1,
        "maintenance_repair": 1,
        "maintenance_accept": 1,
        "inventory": 1,
        "my_business": 0,
        "borrow_due": 0,
    }

    inbound_list = await client.get(
        "/api/v1/todos",
        params={"todo_type": "inbound_confirm"},
        headers=admin_headers,
    )
    inbound_items = inbound_list.json()["data"]["items"]
    assert len(inbound_items) == 1
    assert inbound_items[0]["link"] == f"/assets/inbounds?focus={ids['inbound']}"
    assert inbound_items[0]["todo_type_label"] == "入库确认"

    inventory_list = await client.get(
        "/api/v1/todos",
        params={"category": "HANDLE"},
        headers=admin_headers,
    )
    assert inventory_list.json()["data"]["total"] == 3

    emp_headers = await _login_as(client, "todo_emp")
    emp_data = (
        await client.get("/api/v1/todos/summary", headers=emp_headers)
    ).json()["data"]
    emp_counts = _counts(emp_data)
    assert emp_data["total"] == 11
    assert emp_counts["my_business"] == 10
    assert emp_counts["borrow_due"] == 1
    assert emp_counts["request_approval"] == 0
    assert emp_counts["transfer_confirm"] == 0

    emp_approvals = await client.get(
        "/api/v1/todos",
        params={"todo_type": "transfer_approval"},
        headers=emp_headers,
    )
    assert emp_approvals.json()["data"]["total"] == 0

    repairer_headers = await _login_as(client, "todo_repairer")
    repairer_data = (
        await client.get("/api/v1/todos/summary", headers=repairer_headers)
    ).json()["data"]
    assert repairer_data["total"] == 1
    assert _counts(repairer_data)["maintenance_repair"] == 1
    assert _counts(repairer_data)["maintenance_accept"] == 0

    rejected = await client.post(
        f"/api/v1/asset-transfers/{ids['transfer_approval']}/reject",
        json={"comment": "测试驳回"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["code"] == 0

    after_admin = (
        await client.get("/api/v1/todos/summary", headers=admin_headers)
    ).json()["data"]
    assert after_admin["total"] == 11
    assert _counts(after_admin)["transfer_approval"] == 0

    after_emp = (
        await client.get("/api/v1/todos/summary", headers=emp_headers)
    ).json()["data"]
    assert after_emp["total"] == 10
    assert _counts(after_emp)["my_business"] == 9
