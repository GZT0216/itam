from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core.approval import (
    APPROVAL_FLOW_STATUS_LABELS,
    APPROVE_MODE_LABELS,
    APPROVER_TYPE_LABELS,
    FALLBACK_TYPE_LABELS,
    STEP_STATUS_LABELS,
    ApproveMode,
    ApproverType,
    ApprovalTaskStatus,
    FallbackType,
)
from app.core.asset_flow import (
    APPROVAL_ACTION_LABELS,
    ApprovalAction,
    RequestStatus,
)
from app.core.exceptions import BizError, ConflictError, NotFoundError, PermissionDenied
from app.core.permissions import SUPER_ADMIN_ROLE, DataScope
from app.models import (
    ApprovalFlow,
    ApprovalFlowNode,
    ApprovalTask,
    AssetRequest,
    AssetRequestApproval,
    Dept,
    Role,
    User,
    approval_flow_depts,
    user_roles,
)
from app.models.base import now_cst
from app.schemas.approval_flow import (
    ApprovalFlowCreate,
    ApprovalFlowNodeIn,
    ApprovalFlowNodeOut,
    ApprovalFlowOptionsOut,
    ApprovalFlowOut,
    ApprovalFlowStatusUpdate,
    ApprovalFlowUpdate,
    ApprovalStepOut,
    DeptOptionOut,
    RoleOptionOut,
    UserOptionOut,
)
from app.services.audit_service import AuditService
from app.services.permission_service import AuthContext
from app.services.txn import commit_or_conflict


@dataclass(slots=True)
class FlowStartResult:
    flow_id: int
    flow_name: str
    total_steps: int
    current_step_no: int | None
    current_step_name: str | None
    current_approvers: list[str] = field(default_factory=list)
    auto_skipped: bool = False


@dataclass(slots=True)
class FlowActionResult:
    step_no: int
    step_code: str
    step_name: str
    finished: bool
    next_step_no: int | None = None
    next_step_name: str | None = None
    rejected: bool = False
    admin_override: bool = False


@dataclass(slots=True)
class FlowDescription:
    total_steps: int
    current_step_no: int | None
    current_step_name: str | None
    current_approvers: list[str]
    steps: list[ApprovalStepOut]


@dataclass(slots=True)
class _Candidate:
    user_id: int
    name: str
    is_fallback: bool = False


class ApprovalFlowService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditService(session)

    # ---------- 流程配置 ----------

    @staticmethod
    def _assert_manage(context: AuthContext) -> None:
        if not context.has_permission("asset:request:flow:manage"):
            raise PermissionDenied("无权维护审批流程配置")

    async def _role_names(self) -> dict[str, str]:
        roles = list((await self.session.execute(select(Role))).scalars().all())
        return {role.code: role.name for role in roles}

    async def _flow_out(self, flow: ApprovalFlow) -> ApprovalFlowOut:
        return self._flow_out_with_roles(flow, await self._role_names())

    def _flow_out_with_roles(
        self, flow: ApprovalFlow, role_names: dict[str, str]
    ) -> ApprovalFlowOut:
        departments = sorted(flow.departments, key=lambda item: (item.sort, item.id))
        nodes = sorted(flow.nodes, key=lambda item: item.step_no)
        return ApprovalFlowOut(
            id=flow.id,
            name=flow.name,
            description=flow.description,
            is_default=flow.is_default,
            status=flow.status,
            status_label=APPROVAL_FLOW_STATUS_LABELS.get(flow.status, str(flow.status)),
            dept_ids=[dept.id for dept in departments],
            dept_names=[dept.name for dept in departments],
            nodes=[
                ApprovalFlowNodeOut(
                    id=node.id,
                    step_no=node.step_no,
                    step_code=node.step_code,
                    name=node.name,
                    approver_type=node.approver_type,
                    approver_type_label=APPROVER_TYPE_LABELS.get(
                        node.approver_type, node.approver_type
                    ),
                    user_id=node.user_id,
                    user_name=node.user.real_name if node.user else None,
                    role_code=node.role_code,
                    role_name=role_names.get(node.role_code or ""),
                    manager_level=node.manager_level,
                    approve_mode=node.approve_mode,
                    approve_mode_label=APPROVE_MODE_LABELS.get(
                        node.approve_mode, node.approve_mode
                    ),
                    fallback_type=node.fallback_type,
                    fallback_type_label=FALLBACK_TYPE_LABELS.get(
                        node.fallback_type, node.fallback_type
                    ),
                )
                for node in nodes
            ],
            version=flow.version,
            created_by_name=flow.created_by_name,
            updated_by_name=flow.updated_by_name,
            created_at=flow.created_at,
            updated_at=flow.updated_at,
        )

    async def list_flows(self, context: AuthContext) -> list[ApprovalFlowOut]:
        if not context.has_permission("asset:request:flow:view"):
            raise PermissionDenied("无权查看审批流程配置")
        flows = list(
            (
                await self.session.execute(
                    select(ApprovalFlow).order_by(
                        ApprovalFlow.is_default.desc(),
                        ApprovalFlow.status.desc(),
                        ApprovalFlow.id.asc(),
                    )
                )
            )
            .scalars()
            .all()
        )
        role_names = await self._role_names()
        return [self._flow_out_with_roles(flow, role_names) for flow in flows]

    async def get_flow(self, flow_id: int, context: AuthContext) -> ApprovalFlowOut:
        if not context.has_permission("asset:request:flow:view"):
            raise PermissionDenied("无权查看审批流程配置")
        flow = await self.session.get(ApprovalFlow, flow_id)
        if flow is None:
            raise NotFoundError("审批流程不存在")
        return await self._flow_out(flow)

    async def _validate_name(self, name: str, flow_id: int | None = None) -> None:
        stmt = select(ApprovalFlow.id).where(ApprovalFlow.name == name)
        if flow_id is not None:
            stmt = stmt.where(ApprovalFlow.id != flow_id)
        if await self.session.scalar(stmt.limit(1)):
            raise ConflictError("审批流程名称已存在", code=40920)

    async def _load_depts(self, dept_ids: list[int]) -> list[Dept]:
        if not dept_ids:
            return []
        depts = list(
            (
                await self.session.execute(
                    select(Dept).where(Dept.id.in_(dept_ids)).order_by(Dept.id)
                )
            )
            .scalars()
            .all()
        )
        found = {dept.id for dept in depts}
        missing = [dept_id for dept_id in dept_ids if dept_id not in found]
        if missing:
            raise NotFoundError(f"部门不存在：{missing[0]}")
        return depts

    async def _assert_depts_unbound(
        self, dept_ids: list[int], flow_id: int | None
    ) -> None:
        if not dept_ids:
            return
        stmt = (
            select(Dept.name, ApprovalFlow.name)
            .select_from(approval_flow_depts)
            .join(Dept, Dept.id == approval_flow_depts.c.dept_id)
            .join(ApprovalFlow, ApprovalFlow.id == approval_flow_depts.c.flow_id)
            .where(approval_flow_depts.c.dept_id.in_(dept_ids))
        )
        if flow_id is not None:
            stmt = stmt.where(approval_flow_depts.c.flow_id != flow_id)
        rows = (await self.session.execute(stmt.limit(1))).all()
        if rows:
            dept_name, flow_name = rows[0]
            raise ConflictError(
                f"部门「{dept_name}」已绑定审批流程「{flow_name}」，请先解除原绑定",
                code=40921,
            )

    async def _build_nodes(
        self, items: list[ApprovalFlowNodeIn]
    ) -> list[ApprovalFlowNode]:
        user_ids = {
            item.user_id
            for item in items
            if item.approver_type == ApproverType.USER and item.user_id
        }
        users: dict[int, User] = {}
        if user_ids:
            users = {
                user.id: user
                for user in (
                    (
                        await self.session.execute(
                            select(User).where(
                                User.id.in_(user_ids), User.deleted_at.is_(None)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            }

        role_codes = {
            item.role_code
            for item in items
            if item.approver_type == ApproverType.ROLE and item.role_code
        }
        roles: set[str] = set()
        if role_codes:
            roles = set(
                (
                    await self.session.execute(
                        select(Role.code).where(
                            Role.code.in_(role_codes), Role.status == 1
                        )
                    )
                ).scalars()
            )

        nodes: list[ApprovalFlowNode] = []
        for index, item in enumerate(items, start=1):
            if not item.name:
                raise BizError(f"第 {index} 级审批节点名称不能为空")
            user_id: int | None = None
            role_code: str | None = None
            if item.approver_type == ApproverType.USER:
                if item.user_id is None:
                    raise BizError(f"第 {index} 级审批节点请选择指定用户")
                user = users.get(item.user_id)
                if user is None:
                    raise BizError(f"第 {index} 级审批节点指定的用户不存在")
                if user.status != 1:
                    raise BizError(f"第 {index} 级审批节点指定的用户已停用")
                user_id = user.id
            elif item.approver_type == ApproverType.ROLE:
                if not item.role_code:
                    raise BizError(f"第 {index} 级审批节点请选择指定角色")
                if item.role_code not in roles:
                    raise BizError(f"第 {index} 级审批节点指定的角色不存在或已停用")
                role_code = item.role_code
            elif item.approver_type == ApproverType.DEPT_MANAGER:
                if item.manager_level < 1:
                    raise BizError(f"第 {index} 级审批节点的负责人层级不正确")
            else:
                raise BizError(f"第 {index} 级审批节点的审批人类型不正确")

            node = ApprovalFlowNode(
                step_no=index,
                step_code=f"S{index}",
                name=item.name,
                approver_type=item.approver_type,
                user_id=user_id,
                role_code=role_code,
                manager_level=item.manager_level,
                approve_mode=item.approve_mode,
                fallback_type=item.fallback_type,
            )
            if user_id is not None:
                node.user = users[user_id]
            nodes.append(node)
        return nodes

    async def _unset_other_defaults(self, flow_id: int | None) -> None:
        stmt = select(ApprovalFlow).where(ApprovalFlow.is_default.is_(True))
        if flow_id is not None:
            stmt = stmt.where(ApprovalFlow.id != flow_id)
        for other in (await self.session.execute(stmt)).scalars().all():
            other.is_default = False

    async def create_flow(
        self, payload: ApprovalFlowCreate, context: AuthContext
    ) -> ApprovalFlowOut:
        self._assert_manage(context)
        await self._validate_name(payload.name)
        await self._assert_depts_unbound(payload.dept_ids, None)
        depts = await self._load_depts(payload.dept_ids)
        nodes = await self._build_nodes(payload.nodes)
        if payload.is_default:
            await self._unset_other_defaults(None)

        flow = ApprovalFlow(
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
            status=payload.status,
            created_by_id=context.user.id,
            created_by_name=context.user.real_name,
            updated_by_id=context.user.id,
            updated_by_name=context.user.real_name,
        )
        flow.departments = depts
        flow.nodes = nodes
        self.session.add(flow)
        await self.session.flush()

        await self.audit.record(
            action="asset.request.flow.create",
            module="审批流程",
            summary=f"新增审批流程：{flow.name}",
            actor=context.user,
            resource_type="approval_flow",
            resource_id=flow.id,
            after=self._flow_snapshot(flow),
        )
        await commit_or_conflict(self.session)
        return await self._flow_out(flow)

    async def update_flow(
        self,
        flow_id: int,
        payload: ApprovalFlowUpdate,
        context: AuthContext,
    ) -> ApprovalFlowOut:
        self._assert_manage(context)
        flow = await self.session.get(ApprovalFlow, flow_id)
        if flow is None:
            raise NotFoundError("审批流程不存在")
        if flow.version != payload.version:
            raise ConflictError("审批流程已被他人修改，请刷新后重试")
        await self._validate_name(payload.name, flow_id)
        await self._assert_depts_unbound(payload.dept_ids, flow_id)
        depts = await self._load_depts(payload.dept_ids)
        nodes = await self._build_nodes(payload.nodes)
        if payload.is_default:
            await self._unset_other_defaults(flow_id)

        before = self._flow_snapshot(flow)
        for node in list(flow.nodes):
            await self.session.delete(node)
        flow.nodes = []
        await self.session.flush()

        flow.name = payload.name
        flow.description = payload.description
        flow.is_default = payload.is_default
        flow.status = payload.status
        flow.updated_by_id = context.user.id
        flow.updated_by_name = context.user.real_name
        flow.departments = depts
        flow.nodes = nodes
        await self.session.flush()

        await self.audit.record(
            action="asset.request.flow.update",
            module="审批流程",
            summary=f"编辑审批流程：{flow.name}",
            actor=context.user,
            resource_type="approval_flow",
            resource_id=flow.id,
            before=before,
            after=self._flow_snapshot(flow),
        )
        await commit_or_conflict(self.session)
        return await self._flow_out(flow)

    async def update_status(
        self,
        flow_id: int,
        payload: ApprovalFlowStatusUpdate,
        context: AuthContext,
    ) -> ApprovalFlowOut:
        self._assert_manage(context)
        flow = await self.session.get(ApprovalFlow, flow_id)
        if flow is None:
            raise NotFoundError("审批流程不存在")
        if flow.version != payload.version:
            raise ConflictError("审批流程已被他人修改，请刷新后重试")
        before = {"status": flow.status}
        flow.status = payload.status
        flow.updated_by_id = context.user.id
        flow.updated_by_name = context.user.real_name
        await self.audit.record(
            action="asset.request.flow.status",
            module="审批流程",
            summary=(
                f"{'启用' if payload.status == 1 else '停用'}审批流程：{flow.name}"
            ),
            actor=context.user,
            resource_type="approval_flow",
            resource_id=flow.id,
            before=before,
            after={"status": flow.status},
        )
        await commit_or_conflict(self.session)
        return await self._flow_out(flow)

    @staticmethod
    def _flow_snapshot(flow: ApprovalFlow) -> dict[str, object]:
        return {
            "name": flow.name,
            "description": flow.description,
            "is_default": flow.is_default,
            "status": flow.status,
            "dept_ids": sorted(dept.id for dept in flow.departments),
            "nodes": [
                {
                    "step_no": node.step_no,
                    "name": node.name,
                    "approver_type": node.approver_type,
                    "user_id": node.user_id,
                    "role_code": node.role_code,
                    "manager_level": node.manager_level,
                    "approve_mode": node.approve_mode,
                    "fallback_type": node.fallback_type,
                }
                for node in sorted(flow.nodes, key=lambda item: item.step_no)
            ],
            "version": flow.version,
        }

    async def options(
        self, context: AuthContext, *, keyword: str | None = None
    ) -> ApprovalFlowOptionsOut:
        if not context.has_permission("asset:request:flow:view"):
            raise PermissionDenied("无权查看审批流程配置")

        depts = list(
            (
                await self.session.execute(
                    select(Dept).order_by(Dept.level, Dept.sort, Dept.id)
                )
            )
            .scalars()
            .all()
        )
        dept_names = {dept.id: dept.name for dept in depts}
        dept_options = []
        for dept in depts:
            path_ids = [token for token in dept.path.split("/") if token.isdigit()]
            path = " / ".join(
                dept_names[int(token)]
                for token in path_ids
                if int(token) in dept_names
            ) or dept.name
            dept_options.append(
                DeptOptionOut(
                    id=dept.id,
                    name=dept.name,
                    path=path,
                    level=dept.level,
                    manager_id=dept.manager_id,
                    manager_name=dept.manager_name,
                )
            )

        stmt = select(User).where(User.status == 1, User.deleted_at.is_(None))
        if keyword and keyword.strip():
            pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(
                (User.username.like(pattern))
                | (User.real_name.like(pattern))
                | (User.employee_no.like(pattern))
            )
        users = list(
            (
                await self.session.execute(stmt.order_by(User.id).limit(50))
            )
            .scalars()
            .all()
        )

        roles = list(
            (
                await self.session.execute(
                    select(Role).where(Role.status == 1).order_by(Role.sort, Role.id)
                )
            )
            .scalars()
            .all()
        )
        return ApprovalFlowOptionsOut(
            departments=dept_options,
            users=[
                UserOptionOut(
                    id=user.id,
                    username=user.username,
                    real_name=user.real_name,
                    dept_id=user.dept_id,
                    dept_name=user.dept.name if user.dept else None,
                    status=user.status,
                )
                for user in users
            ],
            roles=[
                RoleOptionOut(
                    code=role.code,
                    name=role.name,
                    data_scope=role.data_scope,
                )
                for role in roles
            ],
        )

    # ---------- 流程解析 ----------

    async def _dept_chain(self, dept_id: int | None) -> list[Dept]:
        chain: list[Dept] = []
        seen: set[int] = set()
        current_id = dept_id
        while current_id is not None and current_id not in seen:
            seen.add(current_id)
            dept = await self.session.get(Dept, current_id)
            if dept is None:
                break
            chain.append(dept)
            current_id = dept.parent_id
        return chain

    async def resolve_flow(self, dept_id: int | None) -> ApprovalFlow | None:
        for dept in await self._dept_chain(dept_id):
            flow = (
                await self.session.execute(
                    select(ApprovalFlow)
                    .join(
                        approval_flow_depts,
                        approval_flow_depts.c.flow_id == ApprovalFlow.id,
                    )
                    .where(
                        ApprovalFlow.status == 1,
                        approval_flow_depts.c.dept_id == dept.id,
                    )
                    .order_by(ApprovalFlow.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if flow is not None and flow.nodes:
                return flow
        flow = (
            await self.session.execute(
                select(ApprovalFlow)
                .where(ApprovalFlow.status == 1, ApprovalFlow.is_default.is_(True))
                .order_by(ApprovalFlow.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if flow is not None and not flow.nodes:
            return None
        return flow

    @staticmethod
    def _role_covers(role: Role, user: User, applicant_dept: Dept | None) -> bool:
        if role.data_scope == DataScope.ALL:
            return True
        if applicant_dept is None:
            return False
        if role.data_scope in (DataScope.DEPT, DataScope.SELF):
            return user.dept_id == applicant_dept.id
        if role.data_scope == DataScope.DEPT_AND_CHILD:
            return bool(
                user.dept
                and user.dept.path
                and applicant_dept.path.startswith(user.dept.path)
            )
        if role.data_scope == DataScope.CUSTOM:
            return applicant_dept.id in {dept.id for dept in role.depts}
        return False

    async def _users_by_role(
        self,
        role_code: str,
        *,
        applicant_id: int,
        applicant_dept: Dept | None,
        require_scope: bool,
    ) -> list[_Candidate]:
        role = (
            await self.session.execute(
                select(Role).where(Role.code == role_code, Role.status == 1)
            )
        ).scalar_one_or_none()
        if role is None:
            return []
        users = list(
            (
                await self.session.execute(
                    select(User)
                    .join(user_roles, user_roles.c.user_id == User.id)
                    .where(
                        user_roles.c.role_id == role.id,
                        User.status == 1,
                        User.deleted_at.is_(None),
                    )
                    .order_by(User.id)
                )
            )
            .scalars()
            .all()
        )
        return [
            _Candidate(user_id=user.id, name=user.real_name)
            for user in users
            if user.id != applicant_id
            and (not require_scope or self._role_covers(role, user, applicant_dept))
        ]

    async def _manager_candidates(
        self,
        node: ApprovalFlowNode,
        chain: list[Dept],
        applicant_id: int,
    ) -> list[_Candidate]:
        index = node.manager_level - 1
        if index < 0 or index >= len(chain):
            return []
        dept = chain[index]
        if dept.manager_id is None or dept.manager_id == applicant_id:
            return []
        manager = dept.manager or await self.session.get(User, dept.manager_id)
        if manager is None or manager.status != 1 or manager.deleted_at is not None:
            return []
        if manager.id == applicant_id:
            return []
        return [_Candidate(user_id=manager.id, name=manager.real_name)]

    async def _user_candidates(
        self, user_id: int | None, applicant_id: int
    ) -> list[_Candidate]:
        if user_id is None or user_id == applicant_id:
            return []
        user = await self.session.get(User, user_id)
        if user is None or user.status != 1 or user.deleted_at is not None:
            return []
        return [_Candidate(user_id=user.id, name=user.real_name)]

    async def _fallback_candidates(
        self,
        fallback_type: str,
        *,
        applicant_id: int,
        applicant_dept: Dept | None,
    ) -> list[_Candidate]:
        if fallback_type == FallbackType.ASSET_ADMIN:
            return await self._users_by_role(
                "ASSET_ADMIN",
                applicant_id=applicant_id,
                applicant_dept=applicant_dept,
                require_scope=False,
            )
        if fallback_type == FallbackType.DEPT_ADMIN:
            return await self._users_by_role(
                "DEPT_ADMIN",
                applicant_id=applicant_id,
                applicant_dept=applicant_dept,
                require_scope=True,
            )
        if fallback_type == FallbackType.SUPER_ADMIN:
            return await self._users_by_role(
                SUPER_ADMIN_ROLE,
                applicant_id=applicant_id,
                applicant_dept=applicant_dept,
                require_scope=False,
            )
        return []

    async def _node_candidates(
        self,
        node: ApprovalFlowNode,
        chain: list[Dept],
        *,
        applicant_id: int,
        applicant_dept: Dept | None,
    ) -> tuple[list[_Candidate], bool]:
        if node.approver_type == ApproverType.DEPT_MANAGER:
            candidates = await self._manager_candidates(node, chain, applicant_id)
        elif node.approver_type == ApproverType.USER:
            candidates = await self._user_candidates(node.user_id, applicant_id)
        elif node.approver_type == ApproverType.ROLE:
            candidates = await self._users_by_role(
                node.role_code or "",
                applicant_id=applicant_id,
                applicant_dept=applicant_dept,
                require_scope=True,
            )
        else:
            candidates = []

        if candidates:
            return candidates, False
        if node.fallback_type == FallbackType.SKIP:
            return [], True
        fallback = await self._fallback_candidates(
            node.fallback_type,
            applicant_id=applicant_id,
            applicant_dept=applicant_dept,
        )
        if not fallback:
            raise BizError(
                f"审批节点「{node.name}」未匹配到审批人，请检查部门负责人设置或流程兜底配置"
            )
        for item in fallback:
            item.is_fallback = True
        return fallback, False

    @staticmethod
    def _dedupe(candidates: list[_Candidate]) -> list[_Candidate]:
        seen: set[int] = set()
        result: list[_Candidate] = []
        for item in candidates:
            if item.user_id in seen:
                continue
            seen.add(item.user_id)
            result.append(item)
        return result

    async def start_flow(
        self,
        request: AssetRequest,
        flow: ApprovalFlow,
        *,
        applicant_id: int,
        applicant_dept_id: int | None,
    ) -> FlowStartResult:
        chain = await self._dept_chain(applicant_dept_id)
        applicant_dept = chain[0] if chain else None
        now = now_cst()
        tasks: list[ApprovalTask] = []
        for node in sorted(flow.nodes, key=lambda item: item.step_no):
            candidates, auto_skip = await self._node_candidates(
                node,
                chain,
                applicant_id=applicant_id,
                applicant_dept=applicant_dept,
            )
            if auto_skip:
                tasks.append(
                    ApprovalTask(
                        request_id=request.id,
                        flow_id=flow.id,
                        flow_name=flow.name,
                        node_id=node.id,
                        step_no=node.step_no,
                        step_code=node.step_code,
                        step_name=node.name,
                        approver_type=node.approver_type,
                        approver_id=None,
                        approver_name="系统自动跳过",
                        approve_mode=node.approve_mode,
                        is_fallback=False,
                        status=ApprovalTaskStatus.SKIPPED,
                        acted_at=now,
                        comment="未匹配到审批人，按配置自动跳过",
                    )
                )
                continue
            for candidate in self._dedupe(candidates):
                tasks.append(
                    ApprovalTask(
                        request_id=request.id,
                        flow_id=flow.id,
                        flow_name=flow.name,
                        node_id=node.id,
                        step_no=node.step_no,
                        step_code=node.step_code,
                        step_name=node.name,
                        approver_type=node.approver_type,
                        approver_id=candidate.user_id,
                        approver_name=candidate.name,
                        approve_mode=node.approve_mode,
                        is_fallback=candidate.is_fallback,
                        status=ApprovalTaskStatus.WAITING,
                    )
                )

        active_step_no: int | None = None
        waiting_steps = sorted(
            {task.step_no for task in tasks if task.status == ApprovalTaskStatus.WAITING}
        )
        if waiting_steps:
            active_step_no = waiting_steps[0]
            for task in tasks:
                if (
                    task.step_no == active_step_no
                    and task.status == ApprovalTaskStatus.WAITING
                ):
                    task.status = ApprovalTaskStatus.PENDING
                    task.activated_at = now

        request.flow_id = flow.id
        request.flow_name = flow.name
        request.current_step_no = active_step_no
        request.approval_stage = None
        self.session.add_all(tasks)
        set_committed_value(request, "tasks", tasks)

        current_name = None
        approvers: list[str] = []
        if active_step_no is not None:
            for task in tasks:
                if task.step_no != active_step_no:
                    continue
                current_name = task.step_name
                if task.status == ApprovalTaskStatus.PENDING and task.approver_name:
                    approvers.append(task.approver_name)
        return FlowStartResult(
            flow_id=flow.id,
            flow_name=flow.name,
            total_steps=len(flow.nodes),
            current_step_no=active_step_no,
            current_step_name=current_name,
            current_approvers=list(dict.fromkeys(approvers)),
            auto_skipped=active_step_no is None,
        )

    # ---------- 运行时审批 ----------

    async def _step_tasks(self, request_id: int, step_no: int) -> list[ApprovalTask]:
        rows = list(
            (
                await self.session.execute(
                    select(ApprovalTask)
                    .where(
                        ApprovalTask.request_id == request_id,
                        ApprovalTask.step_no == step_no,
                    )
                    .order_by(ApprovalTask.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            raise ConflictError("审批任务不存在或已被处理，请刷新后重试", code=40922)
        return rows

    @staticmethod
    def _actor_task(
        tasks: list[ApprovalTask],
        context: AuthContext,
    ) -> tuple[ApprovalTask | None, bool]:
        pending = [
            task for task in tasks if task.status == ApprovalTaskStatus.PENDING
        ]
        if not pending:
            raise ConflictError("当前审批任务已处理，请刷新后重试", code=40922)
        own = next(
            (task for task in pending if task.approver_id == context.user.id), None
        )
        if own is not None:
            return own, False
        if context.is_superuser:
            return None, True
        raise PermissionDenied("当前审批节点未分配给该用户审批")

    async def approve(
        self,
        request: AssetRequest,
        comment: str | None,
        context: AuthContext,
    ) -> FlowActionResult:
        step_no = request.current_step_no
        if step_no is None:
            raise ConflictError("当前单据没有待审批节点，请刷新后重试", code=40922)
        tasks = await self._step_tasks(request.id, step_no)
        own, admin_override = self._actor_task(tasks, context)
        now = now_cst()
        if own is not None:
            own.status = ApprovalTaskStatus.APPROVED
            own.acted_at = now
            own.comment = comment
        else:
            for task in tasks:
                if task.status == ApprovalTaskStatus.PENDING:
                    task.status = ApprovalTaskStatus.SKIPPED
                    task.acted_at = now
                    task.comment = comment or "超级管理员代为审批"

        mode = tasks[0].approve_mode
        if admin_override:
            step_finished = True
        elif mode == ApproveMode.ALL:
            step_finished = all(
                task.status == ApprovalTaskStatus.APPROVED for task in tasks
            )
        else:
            step_finished = True
            for task in tasks:
                if task.status == ApprovalTaskStatus.PENDING:
                    task.status = ApprovalTaskStatus.SKIPPED
                    task.acted_at = now
                    task.comment = "或签已由其他审批人处理"

        request.approvals.append(
            AssetRequestApproval(
                request_id=request.id,
                task_id=own.id if own is not None else None,
                step_no=step_no,
                step_code=tasks[0].step_code,
                step_name=tasks[0].step_name,
                action=ApprovalAction.APPROVE,
                approver_id=context.user.id,
                approver_name=context.user.real_name,
                comment=comment,
                operated_at=now,
            )
        )

        if not step_finished:
            return FlowActionResult(
                step_no=step_no,
                step_code=tasks[0].step_code,
                step_name=tasks[0].step_name,
                finished=False,
                admin_override=admin_override,
            )

        next_task = (
            await self.session.execute(
                select(ApprovalTask)
                .where(
                    ApprovalTask.request_id == request.id,
                    ApprovalTask.status == ApprovalTaskStatus.WAITING,
                )
                .order_by(ApprovalTask.step_no, ApprovalTask.id)
                .limit(1)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if next_task is None:
            request.current_step_no = None
            return FlowActionResult(
                step_no=step_no,
                step_code=tasks[0].step_code,
                step_name=tasks[0].step_name,
                finished=True,
                admin_override=admin_override,
            )

        next_step_no = next_task.step_no
        waiting = list(
            (
                await self.session.execute(
                    select(ApprovalTask)
                    .where(
                        ApprovalTask.request_id == request.id,
                        ApprovalTask.step_no == next_step_no,
                        ApprovalTask.status == ApprovalTaskStatus.WAITING,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        for task in waiting:
            task.status = ApprovalTaskStatus.PENDING
            task.activated_at = now
        request.current_step_no = next_step_no
        return FlowActionResult(
            step_no=step_no,
            step_code=tasks[0].step_code,
            step_name=tasks[0].step_name,
            finished=False,
            next_step_no=next_step_no,
            next_step_name=next_task.step_name,
            admin_override=admin_override,
        )

    async def reject(
        self,
        request: AssetRequest,
        comment: str,
        context: AuthContext,
    ) -> FlowActionResult:
        step_no = request.current_step_no
        if step_no is None:
            raise ConflictError("当前单据没有待审批节点，请刷新后重试", code=40922)
        tasks = await self._step_tasks(request.id, step_no)
        own, admin_override = self._actor_task(tasks, context)
        target = own or next(
            task
            for task in tasks
            if task.status == ApprovalTaskStatus.PENDING
        )
        now = now_cst()
        target.status = ApprovalTaskStatus.REJECTED
        target.acted_at = now
        target.comment = comment

        open_tasks = list(
            (
                await self.session.execute(
                    select(ApprovalTask)
                    .where(
                        ApprovalTask.request_id == request.id,
                        ApprovalTask.status.in_(
                            (
                                ApprovalTaskStatus.PENDING,
                                ApprovalTaskStatus.WAITING,
                            )
                        ),
                        ApprovalTask.id != target.id,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        for task in open_tasks:
            task.status = ApprovalTaskStatus.SKIPPED
            task.acted_at = now
            task.comment = "申请已驳回"

        request.approvals.append(
            AssetRequestApproval(
                request_id=request.id,
                task_id=target.id,
                step_no=step_no,
                step_code=target.step_code,
                step_name=target.step_name,
                action=ApprovalAction.REJECT,
                approver_id=context.user.id,
                approver_name=context.user.real_name,
                comment=comment,
                operated_at=now,
            )
        )
        return FlowActionResult(
            step_no=step_no,
            step_code=target.step_code,
            step_name=target.step_name,
            finished=True,
            rejected=True,
            admin_override=admin_override,
        )

    async def skip_open_tasks(
        self, request: AssetRequest, *, comment: str
    ) -> None:
        tasks = list(
            (
                await self.session.execute(
                    select(ApprovalTask)
                    .where(
                        ApprovalTask.request_id == request.id,
                        ApprovalTask.status.in_(
                            (
                                ApprovalTaskStatus.PENDING,
                                ApprovalTaskStatus.WAITING,
                            )
                        ),
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        now = now_cst()
        for task in tasks:
            task.status = ApprovalTaskStatus.SKIPPED
            task.acted_at = now
            task.comment = comment

    # ---------- 展示与鉴权辅助 ----------

    @staticmethod
    def user_can_act(request: AssetRequest, context: AuthContext) -> bool:
        if request.status != RequestStatus.PENDING_APPROVAL or not request.flow_id:
            return False
        tasks = list(request.__dict__.get("tasks") or [])
        if not any(task.status == ApprovalTaskStatus.PENDING for task in tasks):
            return False
        if context.is_superuser:
            return True
        return any(
            task.status == ApprovalTaskStatus.PENDING
            and task.approver_id == context.user.id
            for task in tasks
        )

    @staticmethod
    def has_task_for_user(request: AssetRequest, user_id: int) -> bool:
        return any(
            task.approver_id == user_id
            for task in (request.__dict__.get("tasks") or [])
        )

    @staticmethod
    def _step_status(tasks: list[ApprovalTask]) -> str:
        statuses = {task.status for task in tasks}
        if ApprovalTaskStatus.REJECTED in statuses:
            return ApprovalTaskStatus.REJECTED
        if ApprovalTaskStatus.PENDING in statuses:
            return ApprovalTaskStatus.PENDING
        if ApprovalTaskStatus.WAITING in statuses:
            return ApprovalTaskStatus.WAITING
        if ApprovalTaskStatus.APPROVED in statuses:
            return ApprovalTaskStatus.APPROVED
        return ApprovalTaskStatus.SKIPPED

    @classmethod
    def build_steps(cls, request: AssetRequest) -> list[ApprovalStepOut]:
        grouped: dict[int, list[ApprovalTask]] = {}
        for task in sorted(
            request.__dict__.get("tasks") or [],
            key=lambda item: (item.step_no, item.id),
        ):
            grouped.setdefault(task.step_no, []).append(task)

        steps: list[ApprovalStepOut] = []
        for step_no in sorted(grouped):
            tasks = grouped[step_no]
            status = cls._step_status(tasks)
            approvers = list(
                dict.fromkeys(
                    task.approver_name
                    for task in tasks
                    if task.approver_id is not None and task.approver_name
                )
            )
            pending = list(
                dict.fromkeys(
                    task.approver_name
                    for task in tasks
                    if task.status == ApprovalTaskStatus.PENDING
                    and task.approver_name
                )
            )
            acted = [task for task in tasks if task.acted_at is not None]
            latest = max(acted, key=lambda item: (item.acted_at, item.id)) if acted else None
            steps.append(
                ApprovalStepOut(
                    step_no=step_no,
                    step_code=tasks[0].step_code,
                    step_name=tasks[0].step_name,
                    approve_mode=tasks[0].approve_mode,
                    status=status,
                    status_label=STEP_STATUS_LABELS.get(status, status),
                    approvers=approvers,
                    pending_approvers=pending,
                    acted_at=latest.acted_at if latest else None,
                    comment=latest.comment if latest else None,
                )
            )
        return steps

    @classmethod
    def describe(cls, request: AssetRequest) -> FlowDescription:
        steps = cls.build_steps(request)
        current_step_no = request.current_step_no
        current = next(
            (step for step in steps if step.step_no == current_step_no), None
        )
        return FlowDescription(
            total_steps=len(steps),
            current_step_no=current_step_no,
            current_step_name=current.step_name if current else None,
            current_approvers=current.pending_approvers if current else [],
            steps=steps,
        )

    @staticmethod
    def approval_action_label(action: str) -> str:
        return APPROVAL_ACTION_LABELS.get(action, action)
