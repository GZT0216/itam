class ApproverType:
    DEPT_MANAGER = "DEPT_MANAGER"
    USER = "USER"
    ROLE = "ROLE"


APPROVER_TYPE_LABELS = {
    ApproverType.DEPT_MANAGER: "部门负责人",
    ApproverType.USER: "指定用户",
    ApproverType.ROLE: "指定角色",
}


class ApproveMode:
    OR = "OR"
    ALL = "ALL"


APPROVE_MODE_LABELS = {
    ApproveMode.OR: "或签",
    ApproveMode.ALL: "会签",
}


class FallbackType:
    ASSET_ADMIN = "ASSET_ADMIN"
    DEPT_ADMIN = "DEPT_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"
    SKIP = "SKIP"


FALLBACK_TYPE_LABELS = {
    FallbackType.ASSET_ADMIN: "转资产管理员",
    FallbackType.DEPT_ADMIN: "转部门管理员",
    FallbackType.SUPER_ADMIN: "转超级管理员",
    FallbackType.SKIP: "自动跳过",
}


class ApprovalTaskStatus:
    PENDING = "PENDING"
    WAITING = "WAITING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


TASK_STATUS_LABELS = {
    ApprovalTaskStatus.PENDING: "待审批",
    ApprovalTaskStatus.WAITING: "待流转",
    ApprovalTaskStatus.APPROVED: "已通过",
    ApprovalTaskStatus.REJECTED: "已驳回",
    ApprovalTaskStatus.SKIPPED: "已跳过",
}

TASK_STATUS_TAG_TYPES = {
    ApprovalTaskStatus.PENDING: "warning",
    ApprovalTaskStatus.WAITING: "info",
    ApprovalTaskStatus.APPROVED: "success",
    ApprovalTaskStatus.REJECTED: "danger",
    ApprovalTaskStatus.SKIPPED: "info",
}

STEP_STATUS_LABELS = {
    ApprovalTaskStatus.PENDING: "审批中",
    ApprovalTaskStatus.WAITING: "待流转",
    ApprovalTaskStatus.APPROVED: "已通过",
    ApprovalTaskStatus.REJECTED: "已驳回",
    ApprovalTaskStatus.SKIPPED: "已跳过",
}

APPROVAL_FLOW_STATUS_LABELS = {
    1: "启用",
    0: "停用",
}

MAX_FLOW_STEPS = 10
