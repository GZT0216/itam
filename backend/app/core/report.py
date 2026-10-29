REPORT_TYPE_LABELS = {
    "OVERVIEW": "资产分析概览",
    "ASSETS": "资产清单",
    "IDLE": "闲置资产",
    "COMPLIANCE": "合规检查",
}

REPORT_EXPORT_LABELS = {
    "XLSX": "Excel",
    "PDF": "PDF",
}

COMPLIANCE_ISSUES = {
    "MISSING_CUSTODIAN": {
        "label": "缺少责任人",
        "severity": "warning",
        "suggestion": "为在用或借出的资产补充责任人，确保账实对应。",
    },
    "MISSING_LOCATION": {
        "label": "缺少存放位置",
        "severity": "info",
        "suggestion": "补充资产存放位置，便于盘点与调拨。",
    },
    "MISSING_PRICE": {
        "label": "缺少采购金额",
        "severity": "info",
        "suggestion": "补录采购金额，保证资产价值统计准确。",
    },
    "MISSING_PURCHASE_DATE": {
        "label": "缺少采购日期",
        "severity": "info",
        "suggestion": "补录采购日期，用于折旧与账龄分析。",
    },
    "MISSING_SERIAL": {
        "label": "缺少序列号",
        "severity": "warning",
        "suggestion": "硬件资产应登记序列号，便于维保与追溯。",
    },
    "EXPIRED_WARRANTY": {
        "label": "保修已到期",
        "severity": "warning",
        "suggestion": "确认是否续保；临近或已到期资产建议安排更换。",
    },
    "MISSING_DEPT": {
        "label": "未归属部门",
        "severity": "info",
        "suggestion": "为资产指定归属部门，纳入部门数据范围管理。",
    },
}
