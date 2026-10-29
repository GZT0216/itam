from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _strip(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class LdapConfigPayload(BaseModel):
    enabled: bool = False
    server_host: str = Field(default="", max_length=255)
    server_port: int = Field(default=389, ge=1, le=65535)
    use_ssl: bool = False
    start_tls: bool = False
    base_dn: str = Field(default="", max_length=512)
    bind_dn: str = Field(default="", max_length=512)
    bind_password: str | None = Field(default=None, max_length=256)
    user_filter: str = Field(
        default="(&(objectCategory=person)(objectClass=user))", max_length=500
    )
    dept_filter: str = Field(default="(objectClass=organizationalUnit)", max_length=500)
    username_attribute: str = Field(default="sAMAccountName", min_length=1, max_length=80)
    real_name_attribute: str = Field(default="displayName", min_length=1, max_length=80)
    email_attribute: str = Field(default="mail", min_length=1, max_length=80)
    phone_attribute: str = Field(default="telephoneNumber", min_length=1, max_length=80)
    employee_no_attribute: str = Field(default="employeeID", min_length=1, max_length=80)
    default_role_id: int | None = Field(default=None, gt=0)
    root_dept_id: int | None = Field(default=None, gt=0)
    sync_interval_minutes: int = Field(default=60, ge=5, le=10080)

    @field_validator(
        "server_host",
        "base_dn",
        "bind_dn",
        "bind_password",
        "user_filter",
        "dept_filter",
        "username_attribute",
        "real_name_attribute",
        "email_attribute",
        "phone_attribute",
        "employee_no_attribute",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _strip(value)

    @field_validator("user_filter", "dept_filter")
    @classmethod
    def check_filter(cls, value: str | None) -> str | None:
        if value is not None and not (value.startswith("(") and value.endswith(")")):
            raise ValueError("LDAP 过滤条件需使用括号包裹，例如 (objectClass=organizationalUnit)")
        return value

    @model_validator(mode="after")
    def check_connection(self) -> "LdapConfigPayload":
        if self.use_ssl and self.start_tls:
            raise ValueError("SSL 与 StartTLS 不能同时启用")
        if self.enabled:
            if not self.server_host:
                raise ValueError("启用同步时必须填写域控服务器地址")
            if not self.base_dn:
                raise ValueError("启用同步时必须填写 Base DN")
            if not self.bind_dn:
                raise ValueError("启用同步时必须填写绑定账号")
            if not self.user_filter:
                raise ValueError("启用同步时必须填写用户过滤条件")
        return self


class LdapConfigUpdate(LdapConfigPayload):
    version: int | None = Field(default=None, ge=1)


class LdapConfigOut(BaseModel):
    id: int
    enabled: bool
    server_host: str
    server_port: int
    use_ssl: bool
    start_tls: bool
    base_dn: str
    bind_dn: str
    has_password: bool
    user_filter: str
    dept_filter: str
    username_attribute: str
    real_name_attribute: str
    email_attribute: str
    phone_attribute: str
    employee_no_attribute: str
    default_role_id: int | None = None
    default_role_name: str | None = None
    root_dept_id: int | None = None
    root_dept_name: str | None = None
    sync_interval_minutes: int
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_message: str | None = None
    last_test_at: datetime | None = None
    last_test_status: str | None = None
    last_test_message: str | None = None
    version: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LdapTestResult(BaseModel):
    success: bool
    message: str
    server: str | None = None
    dept_sample: int = 0
    user_sample: int = 0
    elapsed_ms: int = 0
    checked_at: datetime


class LdapSyncLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int
    dept_total: int
    dept_created: int
    dept_updated: int
    user_total: int
    user_created: int
    user_updated: int
    user_disabled: int
    user_skipped: int
    error_count: int
    operator_name: str | None = None
    message: str | None = None
    details: list[dict] | None = None
    error_message: str | None = None


class LdapSyncLogPageOut(BaseModel):
    items: list[LdapSyncLogOut]
    total: int
    page: int
    page_size: int


class LdapRoleOption(BaseModel):
    id: int
    code: str
    name: str


class LdapDeptOption(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    level: int
    status: int


class LdapOptionsOut(BaseModel):
    roles: list[LdapRoleOption]
    depts: list[LdapDeptOption]
    ldap_dept_count: int
    ldap_user_count: int
    local_user_count: int
