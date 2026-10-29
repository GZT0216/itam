class RequestType:
    REQUISITION = "REQUISITION"
    BORROW = "BORROW"
    RETURN = "RETURN"


REQUEST_TYPE_LABELS = {
    RequestType.REQUISITION: "领用",
    RequestType.BORROW: "借用",
    RequestType.RETURN: "归还",
}

REQUEST_NO_PREFIXES = {
    RequestType.REQUISITION: "LY",
    RequestType.BORROW: "JY",
    RequestType.RETURN: "GH",
}


class RequestStatus:
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PENDING_OUTBOUND = "PENDING_OUTBOUND"
    BORROWED = "BORROWED"
    PENDING_RETURN = "PENDING_RETURN"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalStage:
    DEPT = "DEPT"
    ASSET = "ASSET"


APPROVAL_STAGE_LABELS = {
    ApprovalStage.DEPT: "部门管理员审批",
    ApprovalStage.ASSET: "资产管理员审批",
}

APPROVAL_STAGE_ROLES = {
    ApprovalStage.DEPT: "DEPT_ADMIN",
    ApprovalStage.ASSET: "ASSET_ADMIN",
}


class ApprovalAction:
    APPROVE = "APPROVE"
    REJECT = "REJECT"


APPROVAL_ACTION_LABELS = {
    ApprovalAction.APPROVE: "通过",
    ApprovalAction.REJECT: "驳回",
}


REQUEST_STATUS_LABELS = {
    RequestStatus.PENDING_APPROVAL: "待审批",
    RequestStatus.PENDING_OUTBOUND: "待出库",
    RequestStatus.BORROWED: "借用中",
    RequestStatus.PENDING_RETURN: "待归还确认",
    RequestStatus.COMPLETED: "已完成",
    RequestStatus.REJECTED: "已驳回",
    RequestStatus.CANCELLED: "已取消",
}

REQUEST_STATUS_TAG_TYPES = {
    RequestStatus.PENDING_APPROVAL: "warning",
    RequestStatus.PENDING_OUTBOUND: "primary",
    RequestStatus.BORROWED: "warning",
    RequestStatus.PENDING_RETURN: "warning",
    RequestStatus.COMPLETED: "success",
    RequestStatus.REJECTED: "danger",
    RequestStatus.CANCELLED: "info",
}

# 资产存在以下状态的单据时，不允许再创建新的业务申请
ACTIVE_REQUEST_STATUSES = (
    RequestStatus.PENDING_APPROVAL,
    RequestStatus.PENDING_OUTBOUND,
    RequestStatus.BORROWED,
    RequestStatus.PENDING_RETURN,
)

# 状态机：每种单据仅允许下列迁移，禁止跨状态直接跳转
ALLOWED_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    RequestType.REQUISITION: {
        RequestStatus.PENDING_APPROVAL: {
            RequestStatus.PENDING_OUTBOUND,
            RequestStatus.REJECTED,
            RequestStatus.CANCELLED,
        },
        RequestStatus.PENDING_OUTBOUND: {
            RequestStatus.COMPLETED,
            RequestStatus.CANCELLED,
        },
    },
    RequestType.BORROW: {
        RequestStatus.PENDING_APPROVAL: {
            RequestStatus.PENDING_OUTBOUND,
            RequestStatus.REJECTED,
            RequestStatus.CANCELLED,
        },
        RequestStatus.PENDING_OUTBOUND: {
            RequestStatus.BORROWED,
            RequestStatus.CANCELLED,
        },
        RequestStatus.BORROWED: {RequestStatus.COMPLETED},
    },
    RequestType.RETURN: {
        RequestStatus.PENDING_RETURN: {
            RequestStatus.COMPLETED,
            RequestStatus.CANCELLED,
        },
    },
}


class AssetHistoryAction:
    OUTBOUND = "OUTBOUND"
    RETURN = "RETURN"


ASSET_HISTORY_ACTION_LABELS = {
    AssetHistoryAction.OUTBOUND: "确认出库",
    AssetHistoryAction.RETURN: "确认归还",
}


def assert_transition(request_type: str, current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(request_type, {}).get(current, set())
    if target not in allowed:
        raise ValueError(f"非法的单据状态迁移：{current} → {target}")
