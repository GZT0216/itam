from __future__ import annotations


class TransferStatus:
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PENDING_TRANSFER = "PENDING_TRANSFER"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


TRANSFER_STATUS_LABELS = {
    TransferStatus.PENDING_APPROVAL: "待审批",
    TransferStatus.PENDING_TRANSFER: "待确认调拨",
    TransferStatus.COMPLETED: "已完成",
    TransferStatus.REJECTED: "已驳回",
    TransferStatus.CANCELLED: "已取消",
}

TRANSFER_STATUS_TAG_TYPES = {
    TransferStatus.PENDING_APPROVAL: "warning",
    TransferStatus.PENDING_TRANSFER: "primary",
    TransferStatus.COMPLETED: "success",
    TransferStatus.REJECTED: "danger",
    TransferStatus.CANCELLED: "info",
}

TRANSFER_ACTIVE_STATUSES = (TransferStatus.PENDING_APPROVAL, TransferStatus.PENDING_TRANSFER)

TRANSFER_ALLOWED_TRANSITIONS = {
    TransferStatus.PENDING_APPROVAL: {
        TransferStatus.PENDING_TRANSFER,
        TransferStatus.REJECTED,
        TransferStatus.CANCELLED,
    },
    TransferStatus.PENDING_TRANSFER: {
        TransferStatus.COMPLETED,
        TransferStatus.CANCELLED,
    },
}


class ScrapStatus:
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PENDING_DISPOSAL = "PENDING_DISPOSAL"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


SCRAP_STATUS_LABELS = {
    ScrapStatus.PENDING_APPROVAL: "待审批",
    ScrapStatus.PENDING_DISPOSAL: "待报废处置",
    ScrapStatus.COMPLETED: "已完成",
    ScrapStatus.REJECTED: "已驳回",
    ScrapStatus.CANCELLED: "已取消",
}

SCRAP_STATUS_TAG_TYPES = {
    ScrapStatus.PENDING_APPROVAL: "warning",
    ScrapStatus.PENDING_DISPOSAL: "danger",
    ScrapStatus.COMPLETED: "info",
    ScrapStatus.REJECTED: "danger",
    ScrapStatus.CANCELLED: "info",
}

SCRAP_ACTIVE_STATUSES = (ScrapStatus.PENDING_APPROVAL, ScrapStatus.PENDING_DISPOSAL)

SCRAP_ALLOWED_TRANSITIONS = {
    ScrapStatus.PENDING_APPROVAL: {
        ScrapStatus.PENDING_DISPOSAL,
        ScrapStatus.REJECTED,
        ScrapStatus.CANCELLED,
    },
    ScrapStatus.PENDING_DISPOSAL: {
        ScrapStatus.COMPLETED,
        ScrapStatus.CANCELLED,
    },
}


class InventoryStatus:
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


INVENTORY_STATUS_LABELS = {
    InventoryStatus.IN_PROGRESS: "盘点中",
    InventoryStatus.COMPLETED: "已完成",
    InventoryStatus.CANCELLED: "已取消",
}

INVENTORY_STATUS_TAG_TYPES = {
    InventoryStatus.IN_PROGRESS: "primary",
    InventoryStatus.COMPLETED: "success",
    InventoryStatus.CANCELLED: "info",
}


class InventoryResult:
    PENDING = "PENDING"
    NORMAL = "NORMAL"
    ABNORMAL = "ABNORMAL"
    MISSING = "MISSING"


INVENTORY_RESULT_LABELS = {
    InventoryResult.PENDING: "待核对",
    InventoryResult.NORMAL: "正常",
    InventoryResult.ABNORMAL: "异常",
    InventoryResult.MISSING: "盘亏",
}

INVENTORY_RESULT_TAG_TYPES = {
    InventoryResult.PENDING: "info",
    InventoryResult.NORMAL: "success",
    InventoryResult.ABNORMAL: "warning",
    InventoryResult.MISSING: "danger",
}


class InventoryAdjustmentStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


INVENTORY_ADJUSTMENT_STATUS_LABELS = {
    InventoryAdjustmentStatus.PENDING: "待审批",
    InventoryAdjustmentStatus.APPROVED: "已通过",
    InventoryAdjustmentStatus.REJECTED: "已驳回",
}

INVENTORY_ADJUSTMENT_STATUS_TAG_TYPES = {
    InventoryAdjustmentStatus.PENDING: "warning",
    InventoryAdjustmentStatus.APPROVED: "success",
    InventoryAdjustmentStatus.REJECTED: "danger",
}


class InboundStatus:
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


INBOUND_STATUS_LABELS = {
    InboundStatus.PENDING: "待确认入库",
    InboundStatus.COMPLETED: "已入库",
    InboundStatus.CANCELLED: "已取消",
}

INBOUND_STATUS_TAG_TYPES = {
    InboundStatus.PENDING: "warning",
    InboundStatus.COMPLETED: "success",
    InboundStatus.CANCELLED: "info",
}


class InboundType:
    PURCHASE = "PURCHASE"
    OTHER = "OTHER"


INBOUND_TYPE_LABELS = {
    InboundType.PURCHASE: "采购入库",
    InboundType.OTHER: "其他入库",
}


TRANSFER_NO_PREFIX = "DB"
SCRAP_NO_PREFIX = "BF"
INVENTORY_NO_PREFIX = "PD"
INVENTORY_ADJUSTMENT_NO_PREFIX = "TZ"
INBOUND_NO_PREFIX = "RK"


def assert_transfer_transition(current: str, target: str) -> None:
    if target not in TRANSFER_ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"非法的调拨单状态迁移：{current} → {target}")


def assert_scrap_transition(current: str, target: str) -> None:
    if target not in SCRAP_ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"非法的报废单状态迁移：{current} → {target}")
