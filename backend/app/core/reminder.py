from __future__ import annotations


class ReminderCategory:
    WARRANTY = "WARRANTY"
    CONTRACT = "CONTRACT"
    BORROW = "BORROW"
    INVENTORY = "INVENTORY"


REMINDER_CATEGORY_LABELS = {
    ReminderCategory.WARRANTY: "保修到期",
    ReminderCategory.CONTRACT: "合同到期",
    ReminderCategory.BORROW: "借用到期",
    ReminderCategory.INVENTORY: "盘点任务",
}

REMINDER_CATEGORY_LINKS = {
    ReminderCategory.WARRANTY: "/assets/reminders?category=WARRANTY",
    ReminderCategory.CONTRACT: "/assets/reminders?category=CONTRACT",
    ReminderCategory.BORROW: "/assets/reminders?category=BORROW",
    ReminderCategory.INVENTORY: "/assets/reminders?category=INVENTORY",
}

REMINDER_CATEGORY_ORDER = {
    ReminderCategory.WARRANTY: 0,
    ReminderCategory.CONTRACT: 1,
    ReminderCategory.BORROW: 2,
    ReminderCategory.INVENTORY: 3,
}


class ReminderLevel:
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"


REMINDER_LEVEL_LABELS = {
    ReminderLevel.DANGER: "紧急",
    ReminderLevel.WARNING: "预警",
    ReminderLevel.INFO: "关注",
}

REMINDER_LEVEL_ORDER = {
    ReminderLevel.DANGER: 0,
    ReminderLevel.WARNING: 1,
    ReminderLevel.INFO: 2,
}
