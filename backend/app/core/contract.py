from __future__ import annotations


class ContractType:
    PURCHASE = "PURCHASE"
    MAINTENANCE = "MAINTENANCE"
    LEASE = "LEASE"


CONTRACT_TYPE_LABELS = {
    ContractType.PURCHASE: "采购合同",
    ContractType.MAINTENANCE: "维保合同",
    ContractType.LEASE: "租赁合同",
}

CONTRACT_TYPE_TAG_TYPES = {
    ContractType.PURCHASE: "primary",
    ContractType.MAINTENANCE: "success",
    ContractType.LEASE: "warning",
}


class ContractStatus:
    ACTIVE = "ACTIVE"
    EXPIRING = "EXPIRING"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"


CONTRACT_STATUS_LABELS = {
    ContractStatus.ACTIVE: "生效中",
    ContractStatus.EXPIRING: "即将到期",
    ContractStatus.EXPIRED: "已到期",
    ContractStatus.TERMINATED: "已终止",
}

CONTRACT_STATUS_TAG_TYPES = {
    ContractStatus.ACTIVE: "success",
    ContractStatus.EXPIRING: "warning",
    ContractStatus.EXPIRED: "danger",
    ContractStatus.TERMINATED: "info",
}

CONTRACT_STORED_STATUSES = (ContractStatus.ACTIVE, ContractStatus.TERMINATED)

CONTRACT_NO_PREFIX = "HT"

CONTRACT_EXPIRING_DAYS = 30


def contract_effective_status(
    stored_status: str, end_date, today
) -> str:
    if stored_status == ContractStatus.TERMINATED:
        return ContractStatus.TERMINATED
    days = (end_date - today).days
    if days < 0:
        return ContractStatus.EXPIRED
    if days <= CONTRACT_EXPIRING_DAYS:
        return ContractStatus.EXPIRING
    return ContractStatus.ACTIVE
