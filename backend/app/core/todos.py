from __future__ import annotations


class TodoCategory:
    APPROVAL = "APPROVAL"
    CONFIRM = "CONFIRM"
    HANDLE = "HANDLE"
    MINE = "MINE"
    DUE = "DUE"


TODO_CATEGORY_LABELS = {
    TodoCategory.APPROVAL: "待我审批",
    TodoCategory.CONFIRM: "待我确认",
    TodoCategory.HANDLE: "待我处理",
    TodoCategory.MINE: "我发起的",
    TodoCategory.DUE: "即将到期",
}

TODO_CATEGORY_ORDER = (
    TodoCategory.APPROVAL,
    TodoCategory.CONFIRM,
    TodoCategory.HANDLE,
    TodoCategory.MINE,
    TodoCategory.DUE,
)


class TodoType:
    REQUEST_APPROVAL = "request_approval"
    TRANSFER_APPROVAL = "transfer_approval"
    SCRAP_APPROVAL = "scrap_approval"
    MAINTENANCE_APPROVAL = "maintenance_approval"
    INVENTORY_APPROVAL = "inventory_approval"
    REQUEST_OUTBOUND = "request_outbound"
    REQUEST_RETURN = "request_return"
    TRANSFER_CONFIRM = "transfer_confirm"
    SCRAP_CONFIRM = "scrap_confirm"
    INBOUND_CONFIRM = "inbound_confirm"
    MAINTENANCE_REPAIR = "maintenance_repair"
    MAINTENANCE_ACCEPT = "maintenance_accept"
    INVENTORY = "inventory"
    MY_BUSINESS = "my_business"
    BORROW_DUE = "borrow_due"


TODO_TYPE_LABELS = {
    TodoType.REQUEST_APPROVAL: "业务申请审批",
    TodoType.TRANSFER_APPROVAL: "调拨审批",
    TodoType.SCRAP_APPROVAL: "报废审批",
    TodoType.MAINTENANCE_APPROVAL: "维修审批",
    TodoType.INVENTORY_APPROVAL: "盘点盈亏审批",
    TodoType.REQUEST_OUTBOUND: "出库确认",
    TodoType.REQUEST_RETURN: "归还确认",
    TodoType.TRANSFER_CONFIRM: "调拨确认",
    TodoType.SCRAP_CONFIRM: "报废处置确认",
    TodoType.INBOUND_CONFIRM: "入库确认",
    TodoType.MAINTENANCE_REPAIR: "维修处理",
    TodoType.MAINTENANCE_ACCEPT: "维修验收",
    TodoType.INVENTORY: "盘点执行",
    TodoType.MY_BUSINESS: "进行中的我的单据",
    TodoType.BORROW_DUE: "借用到期提醒",
}

TODO_TYPE_CATEGORY = {
    TodoType.REQUEST_APPROVAL: TodoCategory.APPROVAL,
    TodoType.TRANSFER_APPROVAL: TodoCategory.APPROVAL,
    TodoType.SCRAP_APPROVAL: TodoCategory.APPROVAL,
    TodoType.MAINTENANCE_APPROVAL: TodoCategory.APPROVAL,
    TodoType.INVENTORY_APPROVAL: TodoCategory.APPROVAL,
    TodoType.REQUEST_OUTBOUND: TodoCategory.CONFIRM,
    TodoType.REQUEST_RETURN: TodoCategory.CONFIRM,
    TodoType.TRANSFER_CONFIRM: TodoCategory.CONFIRM,
    TodoType.SCRAP_CONFIRM: TodoCategory.CONFIRM,
    TodoType.INBOUND_CONFIRM: TodoCategory.CONFIRM,
    TodoType.MAINTENANCE_REPAIR: TodoCategory.HANDLE,
    TodoType.MAINTENANCE_ACCEPT: TodoCategory.HANDLE,
    TodoType.INVENTORY: TodoCategory.HANDLE,
    TodoType.MY_BUSINESS: TodoCategory.MINE,
    TodoType.BORROW_DUE: TodoCategory.DUE,
}

TODO_TYPE_ORDER = (
    TodoType.REQUEST_APPROVAL,
    TodoType.TRANSFER_APPROVAL,
    TodoType.SCRAP_APPROVAL,
    TodoType.MAINTENANCE_APPROVAL,
    TodoType.INVENTORY_APPROVAL,
    TodoType.REQUEST_OUTBOUND,
    TodoType.REQUEST_RETURN,
    TodoType.TRANSFER_CONFIRM,
    TodoType.SCRAP_CONFIRM,
    TodoType.INBOUND_CONFIRM,
    TodoType.MAINTENANCE_REPAIR,
    TodoType.MAINTENANCE_ACCEPT,
    TodoType.INVENTORY,
    TodoType.MY_BUSINESS,
    TodoType.BORROW_DUE,
)

TODO_TYPE_PATHS = {
    TodoType.REQUEST_APPROVAL: "/assets/review",
    TodoType.TRANSFER_APPROVAL: "/assets/transfers",
    TodoType.SCRAP_APPROVAL: "/assets/scraps",
    TodoType.MAINTENANCE_APPROVAL: "/assets/maintenance",
    TodoType.INVENTORY_APPROVAL: "/assets/inventory",
    TodoType.REQUEST_OUTBOUND: "/assets/outbound",
    TodoType.REQUEST_RETURN: "/assets/returns",
    TodoType.TRANSFER_CONFIRM: "/assets/transfers",
    TodoType.SCRAP_CONFIRM: "/assets/scraps",
    TodoType.INBOUND_CONFIRM: "/assets/inbounds",
    TodoType.MAINTENANCE_REPAIR: "/assets/maintenance",
    TodoType.MAINTENANCE_ACCEPT: "/assets/maintenance",
    TodoType.INVENTORY: "/assets/inventory",
    TodoType.MY_BUSINESS: "/assets/requisitions",
    TodoType.BORROW_DUE: "/assets/mine",
}

MY_BUSINESS_PATHS = {
    "REQUISITION": "/assets/requisitions",
    "BORROW": "/assets/requisitions",
    "RETURN": "/assets/requisitions",
    "TRANSFER": "/assets/transfers",
    "SCRAP": "/assets/scraps",
    "MAINTENANCE": "/assets/maintenance",
    "INVENTORY": "/assets/inventory",
    "INVENTORY_ADJUSTMENT": "/assets/inventory",
    "PURCHASE": "/assets/inbounds",
    "OTHER": "/assets/inbounds",
}
