from __future__ import annotations


class MaintenanceStatus:
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PENDING_REPAIR = "PENDING_REPAIR"
    REPAIRING = "REPAIRING"
    PENDING_ACCEPTANCE = "PENDING_ACCEPTANCE"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


MAINTENANCE_STATUS_LABELS = {
    MaintenanceStatus.PENDING_APPROVAL: "待审批",
    MaintenanceStatus.PENDING_REPAIR: "待维修",
    MaintenanceStatus.REPAIRING: "维修中",
    MaintenanceStatus.PENDING_ACCEPTANCE: "待验收",
    MaintenanceStatus.COMPLETED: "已完成",
    MaintenanceStatus.REJECTED: "已驳回",
    MaintenanceStatus.CANCELLED: "已取消",
}

MAINTENANCE_STATUS_TAG_TYPES = {
    MaintenanceStatus.PENDING_APPROVAL: "warning",
    MaintenanceStatus.PENDING_REPAIR: "primary",
    MaintenanceStatus.REPAIRING: "primary",
    MaintenanceStatus.PENDING_ACCEPTANCE: "warning",
    MaintenanceStatus.COMPLETED: "success",
    MaintenanceStatus.REJECTED: "danger",
    MaintenanceStatus.CANCELLED: "info",
}

MAINTENANCE_ACTIVE_STATUSES = (
    MaintenanceStatus.PENDING_APPROVAL,
    MaintenanceStatus.PENDING_REPAIR,
    MaintenanceStatus.REPAIRING,
    MaintenanceStatus.PENDING_ACCEPTANCE,
)

MAINTENANCE_ALLOWED_TRANSITIONS = {
    MaintenanceStatus.PENDING_APPROVAL: {
        MaintenanceStatus.PENDING_REPAIR,
        MaintenanceStatus.REJECTED,
        MaintenanceStatus.CANCELLED,
    },
    MaintenanceStatus.PENDING_REPAIR: {
        MaintenanceStatus.REPAIRING,
        MaintenanceStatus.CANCELLED,
    },
    MaintenanceStatus.REPAIRING: {MaintenanceStatus.PENDING_ACCEPTANCE},
    MaintenanceStatus.PENDING_ACCEPTANCE: {MaintenanceStatus.COMPLETED},
}


class MaintenancePriority:
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


MAINTENANCE_PRIORITY_LABELS = {
    MaintenancePriority.LOW: "低",
    MaintenancePriority.NORMAL: "普通",
    MaintenancePriority.HIGH: "高",
    MaintenancePriority.URGENT: "紧急",
}

MAINTENANCE_PRIORITY_TAG_TYPES = {
    MaintenancePriority.LOW: "info",
    MaintenancePriority.NORMAL: "primary",
    MaintenancePriority.HIGH: "warning",
    MaintenancePriority.URGENT: "danger",
}


class MaintenanceRecordType:
    PROGRESS = "PROGRESS"
    EXPENSE = "EXPENSE"


MAINTENANCE_RECORD_TYPE_LABELS = {
    MaintenanceRecordType.PROGRESS: "维修记录",
    MaintenanceRecordType.EXPENSE: "费用记录",
}


MAINTENANCE_NO_PREFIX = "WX"


def assert_maintenance_transition(current: str, target: str) -> None:
    if target not in MAINTENANCE_ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"非法的维修工单状态迁移：{current} → {target}")
