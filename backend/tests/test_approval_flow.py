from httpx import AsyncClient
from sqlalchemy import func, insert, select

from app.core.assets import AssetStatus
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import Asset, AssetCategory, AuditLog, Dept, Role, User, user_roles
from tests.helpers import auth_headers, login

TEST_PASSWORD = "Test@12345"


async def _dept_id(code: str) -> int:
    async with AsyncSessionLocal() as session:
        return int(
            (await session.execute(select(Dept.id).where(Dept.code == code))).scalar_one()
        )


async def _ensure_user(
    username: str,
    real_name: str,
    role_code: str,
    dept_code: str = "IT",
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


async def _set_manager(dept_code: str, user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        dept = (
            await session.execute(select(Dept).where(Dept.code == dept_code))
        ).scalar_one()
        dept.manager_id = user_id
        await session.commit()


async def _category_id(code: str = "HW-LAPTOP") -> int:
    async with AsyncSessionLocal() as session:
        return int(
            (
                await session.execute(
                    select(AssetCategory.id).where(AssetCategory.code == code)
                )
            ).scalar_one()
        )


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


def _node(
    name: str,
    approver_type: str,
    *,
    manager_level: int = 1,
    user_id: int | None = None,
    role_code: str | None = None,
    approve_mode: str = "OR",
    fallback_type: str = "ASSET_ADMIN",
) -> dict:
    return {
        "name": name,
        "approver_type": approver_type,
        "manager_level": manager_level,
        "user_id": user_id,
        "role_code": role_code,
        "approve_mode": approve_mode,
        "fallback_type": fallback_type,
    }


async def _create_flow(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str,
    dept_ids: list[int],
    nodes: list[dict],
    is_default: bool = False,
) -> dict:
    response = await client.post(
        "/api/v1/approval-flows",
        json={
            "name": name,
            "description": f"{name}说明",
            "dept_ids": dept_ids,
            "nodes": nodes,
            "is_default": is_default,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _create_request(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    category_id: int | None = None,
    reason: str = "流程测试",
) -> dict:
    response = await client.post(
        "/api/v1/asset-requests",
        json={
            "request_type": "REQUISITION",
            "category_id": category_id or await _category_id(),
            "reason": reason,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _audit_count(action: str) -> int:
    async with AsyncSessionLocal() as session:
        return int(
            (
                await session.execute(
                    select(func.count(AuditLog.id)).where(AuditLog.action == action)
                )
            ).scalar_one()
        )


async def test_flow_config_crud_permissions_and_options(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    await _ensure_user("cfg_emp", "配置员工", "EMPLOYEE")
    mgr_id = await _ensure_user("cfg_mgr", "配置经理", "EMPLOYEE")
    approver_id = await _ensure_user("cfg_approver", "指定审批人", "DEPT_ADMIN")
    await _set_manager("IT", mgr_id)
    it_id = await _dept_id("IT")
    emp_headers = await _login_as(client, "cfg_emp")

    options = await client.get("/api/v1/approval-flows/options", headers=admin_headers)
    assert options.status_code == 200, options.text
    options_data = options.json()["data"]
    it_option = next(
        item for item in options_data["departments"] if item["id"] == it_id
    )
    assert it_option["manager_id"] == mgr_id
    assert it_option["manager_name"] == "配置经理"
    assert "ASSET_ADMIN" in {role["code"] for role in options_data["roles"]}
    assert "指定审批人" in {user["real_name"] for user in options_data["users"]}

    filtered = await client.get(
        "/api/v1/approval-flows/options",
        params={"keyword": "指定审批人"},
        headers=admin_headers,
    )
    assert filtered.status_code == 200, filtered.text
    assert [user["real_name"] for user in filtered.json()["data"]["users"]] == [
        "指定审批人"
    ]

    forbidden_options = await client.get(
        "/api/v1/approval-flows/options", headers=emp_headers
    )
    assert forbidden_options.status_code == 403

    nodes = [
        _node("部门负责人审批", "DEPT_MANAGER"),
        _node(
            "指定人员审批",
            "USER",
            user_id=approver_id,
            fallback_type="SUPER_ADMIN",
        ),
    ]
    forbidden_create = await client.post(
        "/api/v1/approval-flows",
        json={"name": "员工流程", "dept_ids": [it_id], "nodes": nodes},
        headers=emp_headers,
    )
    assert forbidden_create.status_code == 403

    created = await _create_flow(
        client,
        admin_headers,
        name="IT 专属审批",
        dept_ids=[it_id],
        nodes=nodes,
    )
    assert created["dept_ids"] == [it_id]
    assert created["dept_names"] == ["信息技术部"]
    assert [node["step_no"] for node in created["nodes"]] == [1, 2]
    assert [node["step_code"] for node in created["nodes"]] == ["S1", "S2"]
    assert created["nodes"][1]["user_id"] == approver_id
    assert created["nodes"][1]["fallback_type"] == "SUPER_ADMIN"
    assert created["version"] == 1

    duplicated_dept = await client.post(
        "/api/v1/approval-flows",
        json={
            "name": "重复绑定",
            "dept_ids": [it_id],
            "nodes": nodes,
        },
        headers=admin_headers,
    )
    assert duplicated_dept.status_code == 409, duplicated_dept.text
    assert duplicated_dept.json()["code"] == 40921

    duplicated_name = await client.post(
        "/api/v1/approval-flows",
        json={"name": "IT 专属审批", "dept_ids": [], "nodes": nodes},
        headers=admin_headers,
    )
    assert duplicated_name.status_code == 409, duplicated_name.text
    assert duplicated_name.json()["code"] == 40920

    listed = await client.get("/api/v1/approval-flows", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["data"]) == 1

    stale = await client.put(
        f"/api/v1/approval-flows/{created['id']}",
        json={
            "name": "IT 专属审批（改）",
            "dept_ids": [it_id],
            "nodes": nodes,
            "version": 99,
        },
        headers=admin_headers,
    )
    assert stale.status_code == 409, stale.text

    updated_nodes = [
        _node("部门负责人审批", "DEPT_MANAGER"),
        _node("部门管理员复核", "ROLE", role_code="DEPT_ADMIN"),
        _node(
            "指定人员审批",
            "USER",
            user_id=approver_id,
            fallback_type="SUPER_ADMIN",
        ),
    ]
    updated = await client.put(
        f"/api/v1/approval-flows/{created['id']}",
        json={
            "name": "IT 专属审批（改）",
            "dept_ids": [it_id],
            "nodes": updated_nodes,
            "version": created["version"],
        },
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text
    updated_data = updated.json()["data"]
    assert updated_data["name"] == "IT 专属审批（改）"
    assert len(updated_data["nodes"]) == 3
    assert updated_data["nodes"][1]["role_code"] == "DEPT_ADMIN"
    assert updated_data["version"] == created["version"] + 1

    disabled = await client.put(
        f"/api/v1/approval-flows/{created['id']}/status",
        json={"status": 0, "version": updated_data["version"]},
        headers=admin_headers,
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["data"]["status"] == 0
    assert disabled.json()["data"]["status_label"] == "停用"

    assert await _audit_count("asset.request.flow.create") == 1
    assert await _audit_count("asset.request.flow.update") == 1
    assert await _audit_count("asset.request.flow.status") == 1


async def test_department_flow_multilevel_and_countersign(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    await _ensure_asset("ITAM-AF-0001", "审批流程测试笔记本")
    mgr_id = await _ensure_user("af_mgr", "IT 经理", "EMPLOYEE")
    await _ensure_user("af_emp", "IT 员工", "EMPLOYEE")
    await _ensure_user("af_ops", "运维员工", "EMPLOYEE", "OPS")
    await _ensure_user("af_fin", "财务员工", "EMPLOYEE", "FIN")
    first_asset_admin = await _ensure_user(
        "af_asset_a", "资产管理员甲", "ASSET_ADMIN"
    )
    second_asset_admin = await _ensure_user(
        "af_asset_b", "资产管理员乙", "ASSET_ADMIN"
    )
    await _set_manager("IT", mgr_id)
    it_id = await _dept_id("IT")

    flow = await _create_flow(
        client,
        admin_headers,
        name="IT 两级会签流程",
        dept_ids=[it_id],
        nodes=[
            _node("部门负责人审批", "DEPT_MANAGER"),
            _node(
                "资产管理员会签",
                "ROLE",
                role_code="ASSET_ADMIN",
                approve_mode="ALL",
                fallback_type="SUPER_ADMIN",
            ),
        ],
    )

    emp_headers = await _login_as(client, "af_emp")
    mgr_headers = await _login_as(client, "af_mgr")
    fin_headers = await _login_as(client, "af_fin")
    first_headers = await _login_as(client, "af_asset_a")
    second_headers = await _login_as(client, "af_asset_b")

    request = await _create_request(client, emp_headers)
    request_id = request["id"]
    assert request["flow_id"] == flow["id"]
    assert request["flow_name"] == "IT 两级会签流程"
    assert request["current_step_no"] == 1
    assert request["current_step_name"] == "部门负责人审批"
    assert request["current_approvers"] == ["IT 经理"]
    assert request["total_steps"] == 2
    assert [step["status"] for step in request["approval_steps"]] == [
        "PENDING",
        "WAITING",
    ]
    assert request["can_approve"] is False
    assert request["approval_stage"] is None

    own_review = await client.get(
        "/api/v1/asset-requests/review", headers=emp_headers
    )
    assert own_review.status_code == 200, own_review.text
    assert own_review.json()["data"]["total"] == 0

    mgr_review = await client.get(
        "/api/v1/asset-requests/review", headers=mgr_headers
    )
    assert mgr_review.status_code == 200, mgr_review.text
    mgr_page = mgr_review.json()["data"]
    assert mgr_page["total"] == 1
    assert mgr_page["items"][0]["current_approvers"] == ["IT 经理"]
    assert mgr_page["items"][0]["can_approve"] is True

    fin_attempt = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "越权审批"},
        headers=fin_headers,
    )
    assert fin_attempt.status_code == 403, fin_attempt.text

    first_step = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "部门同意"},
        headers=mgr_headers,
    )
    assert first_step.status_code == 200, first_step.text
    after_first = first_step.json()["data"]
    assert after_first["status"] == "PENDING_APPROVAL"
    assert after_first["current_step_no"] == 2
    assert after_first["current_step_name"] == "资产管理员会签"
    assert sorted(after_first["current_approvers"]) == ["资产管理员乙", "资产管理员甲"]
    assert [step["status"] for step in after_first["approval_steps"]] == [
        "APPROVED",
        "PENDING",
    ]
    assert len(after_first["approvals"]) == 1
    assert after_first["approvals"][0]["task_id"] is not None
    assert after_first["approvals"][0]["step_name"] == "部门负责人审批"

    countersign_first = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "资产同意甲"},
        headers=first_headers,
    )
    assert countersign_first.status_code == 200, countersign_first.text
    countersign_data = countersign_first.json()["data"]
    assert countersign_data["status"] == "PENDING_APPROVAL"
    assert countersign_data["current_step_no"] == 2
    assert countersign_data["current_approvers"] == ["资产管理员乙"]
    assert [step["status"] for step in countersign_data["approval_steps"]] == [
        "APPROVED",
        "PENDING",
    ]
    assert len(countersign_data["approvals"]) == 2

    duplicate = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "重复审批"},
        headers=first_headers,
    )
    assert duplicate.status_code == 403, duplicate.text

    final_step = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "资产同意乙"},
        headers=second_headers,
    )
    assert final_step.status_code == 200, final_step.text
    final_data = final_step.json()["data"]
    assert final_data["status"] == "PENDING_OUTBOUND"
    assert final_data["current_step_no"] is None
    assert final_data["current_approvers"] == []
    assert [step["status"] for step in final_data["approval_steps"]] == [
        "APPROVED",
        "APPROVED",
    ]
    assert len(final_data["approvals"]) == 3
    assert final_data["can_approve"] is False

    assert await _audit_count("asset.request.approve") == 3

    ops_headers = await _login_as(client, "af_ops")
    ops_request = await _create_request(client, ops_headers)
    assert ops_request["flow_id"] == flow["id"]
    assert ops_request["current_step_no"] == 1
    assert ops_request["current_approvers"] == ["资产管理员甲", "资产管理员乙"]

    fin_request = await _create_request(client, fin_headers)
    assert fin_request["flow_id"] is None
    assert fin_request["approval_stage"] == "DEPT"
    assert fin_request["dept_approval_required"] is True

    stale_disable = await client.put(
        f"/api/v1/approval-flows/{flow['id']}/status",
        json={"status": 0, "version": 99},
        headers=admin_headers,
    )
    assert stale_disable.status_code == 409

    disabled = await client.put(
        f"/api/v1/approval-flows/{flow['id']}/status",
        json={"status": 0, "version": flow["version"]},
        headers=admin_headers,
    )
    assert disabled.status_code == 200, disabled.text

    after_disable = await _create_request(client, emp_headers)
    assert after_disable["flow_id"] is None
    assert after_disable["approval_stage"] == "DEPT"


async def test_flow_rejection_and_progress_visibility(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    await _ensure_asset("ITAM-AF-0002", "驳回流程测试笔记本")
    await _ensure_user("rj_emp", "财务申请人", "EMPLOYEE", "FIN")
    await _ensure_user("rj_mgr_a", "财务审批甲", "DEPT_ADMIN", "FIN")
    await _ensure_user("rj_mgr_b", "财务审批乙", "DEPT_ADMIN", "FIN")
    approver_id = await _ensure_user(
        "rj_final", "财务终审人", "EMPLOYEE", "FIN"
    )
    await _ensure_user("rj_other", "其他部门员工", "EMPLOYEE", "IT")
    fin_id = await _dept_id("FIN")

    flow = await _create_flow(
        client,
        admin_headers,
        name="财务审批流程",
        dept_ids=[fin_id],
        nodes=[
            _node(
                "财务管理员审批",
                "ROLE",
                role_code="DEPT_ADMIN",
            ),
            _node(
                "财务终审",
                "USER",
                user_id=approver_id,
                fallback_type="SUPER_ADMIN",
            ),
        ],
    )
    assert flow["dept_ids"] == [fin_id]

    emp_headers = await _login_as(client, "rj_emp")
    first_headers = await _login_as(client, "rj_mgr_a")
    second_headers = await _login_as(client, "rj_mgr_b")
    final_headers = await _login_as(client, "rj_final")
    other_headers = await _login_as(client, "rj_other")

    request = await _create_request(client, emp_headers)
    request_id = request["id"]
    assert request["flow_id"] == flow["id"]
    assert sorted(request["current_approvers"]) == ["财务审批乙", "财务审批甲"]

    first = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "财务管理员同意"},
        headers=first_headers,
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["current_step_no"] == 2
    assert first_data["current_approvers"] == ["财务终审人"]
    assert first_data["approval_steps"][0]["status"] == "APPROVED"

    orphan_attempt = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "不应生效"},
        headers=second_headers,
    )
    assert orphan_attempt.status_code == 403, orphan_attempt.text

    other_attempt = await client.post(
        f"/api/v1/asset-requests/{request_id}/reject",
        json={"comment": "旁观者驳回"},
        headers=other_headers,
    )
    assert other_attempt.status_code == 403, other_attempt.text

    missing_reason = await client.post(
        f"/api/v1/asset-requests/{request_id}/reject",
        json={"comment": ""},
        headers=final_headers,
    )
    assert missing_reason.status_code == 400, missing_reason.text
    assert "驳回原因" in missing_reason.json()["message"]

    rejected = await client.post(
        f"/api/v1/asset-requests/{request_id}/reject",
        json={"comment": "预算不足，暂不采购"},
        headers=final_headers,
    )
    assert rejected.status_code == 200, rejected.text
    rejected_data = rejected.json()["data"]
    assert rejected_data["status"] == "REJECTED"
    assert rejected_data["current_step_no"] is None
    assert rejected_data["current_approvers"] == []
    assert rejected_data["approval_comment"] == "预算不足，暂不采购"
    assert [step["status"] for step in rejected_data["approval_steps"]] == [
        "APPROVED",
        "REJECTED",
    ]
    assert rejected_data["approval_steps"][1]["comment"] == "预算不足，暂不采购"
    last_record = rejected_data["approvals"][-1]
    assert last_record["action"] == "REJECT"
    assert last_record["comment"] == "预算不足，暂不采购"
    assert last_record["task_id"] is not None

    progress = await client.get(
        f"/api/v1/asset-requests/{request_id}", headers=emp_headers
    )
    assert progress.status_code == 200, progress.text
    progress_data = progress.json()["data"]
    assert progress_data["flow_name"] == "财务审批流程"
    assert [step["step_name"] for step in progress_data["approval_steps"]] == [
        "财务管理员审批",
        "财务终审",
    ]
    assert progress_data["approval_steps"][1]["status"] == "REJECTED"

    assert await _audit_count("asset.request.reject") == 1


async def test_flow_fallback_asset_admin_and_skip(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    await _ensure_asset("ITAM-AF-0003", "兜底流程测试笔记本")
    await _ensure_user("fb_emp", "人事员工", "EMPLOYEE", "HR")
    await _ensure_user("fb_asset", "兜底资产管理员", "ASSET_ADMIN")
    hr_id = await _dept_id("HR")

    flow = await _create_flow(
        client,
        admin_headers,
        name="HR 兜底流程",
        dept_ids=[hr_id],
        nodes=[
            _node("负责人审批", "DEPT_MANAGER", fallback_type="ASSET_ADMIN"),
            _node("二次确认", "DEPT_MANAGER", fallback_type="SKIP"),
        ],
    )

    emp_headers = await _login_as(client, "fb_emp")
    asset_headers = await _login_as(client, "fb_asset")
    request = await _create_request(client, emp_headers)
    request_id = request["id"]
    assert request["flow_id"] == flow["id"]
    assert request["current_step_no"] == 1
    assert request["current_approvers"] == ["兜底资产管理员"]
    assert request["approval_steps"][0]["approvers"] == ["兜底资产管理员"]
    assert request["approval_steps"][1]["status"] == "SKIPPED"
    assert request["approval_steps"][1]["approvers"] == []

    asset_review = await client.get(
        "/api/v1/asset-requests/review", headers=asset_headers
    )
    assert asset_review.status_code == 200, asset_review.text
    assert asset_review.json()["data"]["total"] == 1
    assert asset_review.json()["data"]["items"][0]["can_approve"] is True

    approved = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "兜底审批通过"},
        headers=asset_headers,
    )
    assert approved.status_code == 200, approved.text
    approved_data = approved.json()["data"]
    assert approved_data["status"] == "PENDING_OUTBOUND"
    assert approved_data["current_step_no"] is None
    assert [step["status"] for step in approved_data["approval_steps"]] == [
        "APPROVED",
        "SKIPPED",
    ]


async def test_flow_manager_levels_and_empty_flow_fallback(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    first_asset_id = await _ensure_asset("ITAM-AF-0010", "多级上级审批笔记本")
    await _ensure_asset("ITAM-AF-0011", "无流程兜底笔记本")
    await _ensure_user("ml_emp", "运维申请人", "EMPLOYEE", "OPS")
    ops_manager_id = await _ensure_user("ml_ops_mgr", "运维组长", "EMPLOYEE", "OPS")
    it_manager_id = await _ensure_user("ml_it_mgr", "IT 总监", "EMPLOYEE", "IT")
    await _ensure_user("ml_fin_emp", "财务申请人", "EMPLOYEE", "FIN")
    await _ensure_user("ml_fin_admin", "财务部门管理员", "DEPT_ADMIN", "FIN")
    await _ensure_user("ml_asset", "多级流程资产管理员", "ASSET_ADMIN")
    await _set_manager("OPS", ops_manager_id)
    await _set_manager("IT", it_manager_id)
    ops_id = await _dept_id("OPS")

    flow = await _create_flow(
        client,
        admin_headers,
        name="运维组两级上级审批",
        dept_ids=[ops_id],
        nodes=[
            _node("运维组长审批", "DEPT_MANAGER", manager_level=1),
            _node("IT 总监审批", "DEPT_MANAGER", manager_level=2),
        ],
    )

    emp_headers = await _login_as(client, "ml_emp")
    ops_manager_headers = await _login_as(client, "ml_ops_mgr")
    it_manager_headers = await _login_as(client, "ml_it_mgr")
    fin_headers = await _login_as(client, "ml_fin_emp")
    fin_admin_headers = await _login_as(client, "ml_fin_admin")
    asset_headers = await _login_as(client, "ml_asset")

    request = await _create_request(client, emp_headers)
    request_id = request["id"]
    assert request["flow_id"] == flow["id"]
    assert request["current_step_no"] == 1
    assert request["current_approvers"] == ["运维组长"]

    first = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "组长同意"},
        headers=ops_manager_headers,
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["current_step_no"] == 2
    assert first_data["current_step_name"] == "IT 总监审批"
    assert first_data["current_approvers"] == ["IT 总监"]

    second = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "总监同意"},
        headers=it_manager_headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["data"]["status"] == "PENDING_OUTBOUND"

    candidates = await client.get(
        f"/api/v1/asset-requests/{request_id}/outbound-assets",
        headers=asset_headers,
    )
    assert candidates.status_code == 200, candidates.text
    candidate = candidates.json()["data"]["items"][0]
    assert candidate["id"] == first_asset_id
    outbound = await client.post(
        f"/api/v1/asset-requests/{request_id}/outbound",
        json={
            "asset_id": candidate["id"],
            "version": candidate["version"],
            "location": "运维机房",
        },
        headers=asset_headers,
    )
    assert outbound.status_code == 200, outbound.text
    assert outbound.json()["data"]["status"] == "COMPLETED"

    # 财务部未绑定任何流程：回退到系统原有「部门管理员 → 资产管理员」两级审批
    fallback = await _create_request(client, fin_headers)
    fallback_id = fallback["id"]
    assert fallback["flow_id"] is None
    assert fallback["approval_stage"] == "DEPT"
    assert fallback["dept_approval_required"] is True
    assert fallback["total_steps"] == 0
    assert fallback["current_approvers"] == []

    dept_step = await client.post(
        f"/api/v1/asset-requests/{fallback_id}/approve",
        json={"comment": "财务部门同意"},
        headers=fin_admin_headers,
    )
    assert dept_step.status_code == 200, dept_step.text
    assert dept_step.json()["data"]["approval_stage"] == "ASSET"

    asset_step = await client.post(
        f"/api/v1/asset-requests/{fallback_id}/approve",
        json={"comment": "资产同意"},
        headers=asset_headers,
    )
    assert asset_step.status_code == 200, asset_step.text
    assert asset_step.json()["data"]["status"] == "PENDING_OUTBOUND"

    fallback_candidates = await client.get(
        f"/api/v1/asset-requests/{fallback_id}/outbound-assets",
        headers=asset_headers,
    )
    assert fallback_candidates.status_code == 200, fallback_candidates.text
    fallback_candidate = fallback_candidates.json()["data"]["items"][0]
    fallback_outbound = await client.post(
        f"/api/v1/asset-requests/{fallback_id}/outbound",
        json={
            "asset_id": fallback_candidate["id"],
            "version": fallback_candidate["version"],
            "location": "财务办公室",
        },
        headers=asset_headers,
    )
    assert fallback_outbound.status_code == 200, fallback_outbound.text
    assert fallback_outbound.json()["data"]["status"] == "COMPLETED"


async def test_flow_full_chain_requires_outbound_and_return(client: AsyncClient):
    admin_headers = auth_headers((await login(client))["access_token"])
    asset_id = await _ensure_asset("ITAM-AF-0004", "全链路流程笔记本")
    mgr_id = await _ensure_user("fc_mgr", "全链路经理", "EMPLOYEE")
    await _ensure_user("fc_emp", "全链路员工", "EMPLOYEE")
    asset_admin_id = await _ensure_user(
        "fc_asset", "全链路资产管理员", "ASSET_ADMIN"
    )
    await _set_manager("IT", mgr_id)
    it_id = await _dept_id("IT")

    flow = await _create_flow(
        client,
        admin_headers,
        name="全链路审批流程",
        dept_ids=[it_id],
        nodes=[
            _node("部门负责人审批", "DEPT_MANAGER"),
            _node(
                "资产管理员审批",
                "USER",
                user_id=asset_admin_id,
                fallback_type="SUPER_ADMIN",
            ),
        ],
    )

    emp_headers = await _login_as(client, "fc_emp")
    mgr_headers = await _login_as(client, "fc_mgr")
    asset_headers = await _login_as(client, "fc_asset")

    request = await _create_request(
        client,
        emp_headers,
        category_id=await _category_id(),
        reason="全链路流程测试",
    )
    request_id = request["id"]
    assert request["flow_id"] == flow["id"]

    first = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "经理同意"},
        headers=mgr_headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["data"]["current_step_no"] == 2

    second = await client.post(
        f"/api/v1/asset-requests/{request_id}/approve",
        json={"comment": "资产同意"},
        headers=asset_headers,
    )
    assert second.status_code == 200, second.text
    approved_data = second.json()["data"]
    assert approved_data["status"] == "PENDING_OUTBOUND"
    assert approved_data["current_step_no"] is None

    candidates = await client.get(
        f"/api/v1/asset-requests/{request_id}/outbound-assets",
        headers=asset_headers,
    )
    assert candidates.status_code == 200, candidates.text
    candidate = candidates.json()["data"]["items"][0]
    assert candidate["id"] == asset_id

    outbound = await client.post(
        f"/api/v1/asset-requests/{request_id}/outbound",
        json={
            "asset_id": candidate["id"],
            "version": candidate["version"],
            "location": "C 座 303",
        },
        headers=asset_headers,
    )
    assert outbound.status_code == 200, outbound.text
    assert outbound.json()["data"]["status"] == "COMPLETED"

    return_created = await client.post(
        "/api/v1/asset-returns",
        json={"asset_id": asset_id, "reason": "流程结束归还"},
        headers=emp_headers,
    )
    assert return_created.status_code == 200, return_created.text
    return_request = return_created.json()["data"]
    assert return_request["status"] == "PENDING_RETURN"

    returned = await client.post(
        f"/api/v1/asset-requests/{return_request['id']}/return-confirm",
        json={
            "version": return_request["asset_version"],
            "location": "A 座 101",
            "comment": "设备完好",
        },
        headers=asset_headers,
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["data"]["status"] == "COMPLETED"

    detail = await client.get(
        f"/api/v1/asset-requests/{request_id}", headers=emp_headers
    )
    assert detail.status_code == 200, detail.text
    detail_data = detail.json()["data"]
    assert detail_data["flow_name"] == "全链路审批流程"
    assert [step["status"] for step in detail_data["approval_steps"]] == [
        "APPROVED",
        "APPROVED",
    ]

    async with AsyncSessionLocal() as session:
        asset = await session.get(Asset, asset_id)
        assert asset is not None
        assert asset.status == AssetStatus.IN_STOCK
        assert asset.custodian_id is None
