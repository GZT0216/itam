SUPER_ADMIN_ROLE = "SUPER_ADMIN"


class DataScope:
    ALL = "ALL"
    DEPT_AND_CHILD = "DEPT_AND_CHILD"
    DEPT = "DEPT"
    CUSTOM = "CUSTOM"
    SELF = "SELF"


DATA_SCOPE_LABELS = {
    DataScope.ALL: "全部数据",
    DataScope.DEPT_AND_CHILD: "本部门及下级部门",
    DataScope.DEPT: "本部门",
    DataScope.CUSTOM: "自定义部门",
    DataScope.SELF: "仅本人",
}

SCOPE_PRIORITY = [
    DataScope.ALL,
    DataScope.DEPT_AND_CHILD,
    DataScope.DEPT,
    DataScope.CUSTOM,
    DataScope.SELF,
]

# 字段级权限目录：前端角色授权界面与后端序列化/更新校验共用
ASSET_FIELD_CATALOG = [
    {"field": "name", "label": "资产名称"},
    {"field": "serial_no", "label": "序列号"},
    {"field": "mac_address", "label": "MAC 地址"},
    {"field": "purchase_date", "label": "购置日期"},
    {"field": "supplier", "label": "供应商"},
    {"field": "purchase_price", "label": "采购价格"},
    {"field": "warranty_end", "label": "保修到期"},
    {"field": "location", "label": "存放位置"},
    {"field": "custodian_id", "label": "当前责任人"},
    {"field": "remark", "label": "备注"},
]

FIELD_CATALOG: dict[str, list[dict[str, str]]] = {
    "asset": ASSET_FIELD_CATALOG,
}
