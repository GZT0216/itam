from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    DATA_SCOPE_LABELS,
    FIELD_CATALOG,
    SCOPE_PRIORITY,
    SUPER_ADMIN_ROLE,
    DataScope,
)
from app.models import Menu, Role, RoleFieldPermission, User
from app.repositories.menu_repo import MenuRepository
from app.schemas.auth import (
    CurrentUserOut,
    FieldPermissionOut,
    MenuNode,
    RoleBrief,
    UserProfile,
)


@dataclass(slots=True)
class AuthContext:
    user: User
    roles: list[Role]
    permissions: set[str]
    is_superuser: bool
    data_scope: str
    custom_dept_ids: list[int]
    field_permissions: dict[str, dict[str, FieldPermissionOut]]
    menus: list[MenuNode]
    access_jti: str
    access_exp: int

    def has_permission(self, code: str) -> bool:
        return self.is_superuser or code in self.permissions

    def can_view_field(self, resource: str, field_name: str) -> bool:
        if self.is_superuser:
            return True
        permission = self.field_permissions.get(resource, {}).get(field_name)
        return permission.can_view if permission else True

    def can_edit_field(self, resource: str, field_name: str) -> bool:
        if self.is_superuser:
            return True
        permission = self.field_permissions.get(resource, {}).get(field_name)
        return permission.can_edit if permission else True

    def to_profile(self) -> CurrentUserOut:
        user = self.user
        return CurrentUserOut(
            user=UserProfile(
                id=user.id,
                username=user.username,
                real_name=user.real_name,
                employee_no=user.employee_no,
                email=user.email,
                phone=user.phone,
                avatar=user.avatar,
                dept_id=user.dept_id,
                dept_name=user.dept.name if user.dept else None,
                position=user.position,
                status=user.status,
                source=user.source,
                must_change_password=user.must_change_password,
                last_login_at=user.last_login_at,
            ),
            roles=[RoleBrief.model_validate(role) for role in self.roles],
            permissions=sorted(self.permissions),
            data_scope=self.data_scope,
            data_scope_label=DATA_SCOPE_LABELS.get(self.data_scope, self.data_scope),
            custom_dept_ids=self.custom_dept_ids,
            menus=self.menus,
            field_permissions=self.field_permissions,
        )


class PermissionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build_context(
        self,
        user: User,
        *,
        access_jti: str,
        access_exp: int,
    ) -> AuthContext:
        roles = [role for role in user.roles if role.status == 1]
        is_superuser = any(role.code == SUPER_ADMIN_ROLE for role in roles)
        menu_repo = MenuRepository(self.session)
        all_menus = await menu_repo.list_all_enabled()

        if is_superuser:
            allowed_menu_ids: set[int] | None = None
            permissions = {
                menu.permission_code for menu in all_menus if menu.permission_code
            }
        else:
            allowed_menu_ids = {menu.id for role in roles for menu in role.menus}
            permissions = {
                menu.permission_code
                for role in roles
                for menu in role.menus
                if menu.status == 1 and menu.permission_code
            }

        menus = self._build_menu_tree(all_menus, allowed_menu_ids)
        data_scope = self._resolve_data_scope(roles, is_superuser)
        custom_dept_ids = sorted(
            {
                dept.id
                for role in roles
                if role.data_scope == DataScope.CUSTOM
                for dept in role.depts
            }
        )
        field_permissions = await self._build_field_permissions(roles, is_superuser)

        return AuthContext(
            user=user,
            roles=roles,
            permissions=permissions,
            is_superuser=is_superuser,
            data_scope=data_scope,
            custom_dept_ids=custom_dept_ids,
            field_permissions=field_permissions,
            menus=menus,
            access_jti=access_jti,
            access_exp=access_exp,
        )

    @staticmethod
    def _resolve_data_scope(roles: list[Role], is_superuser: bool) -> str:
        if is_superuser:
            return DataScope.ALL
        scope_set = {role.data_scope for role in roles}
        for scope in SCOPE_PRIORITY:
            if scope in scope_set:
                return scope
        return DataScope.SELF

    @staticmethod
    def _build_menu_tree(
        all_menus: list[Menu],
        allowed_menu_ids: set[int] | None,
    ) -> list[MenuNode]:
        if not all_menus:
            return []

        menu_map = {menu.id: menu for menu in all_menus}
        if allowed_menu_ids is None:
            included_ids = set(menu_map)
        else:
            included_ids: set[int] = set()
            for menu_id in allowed_menu_ids:
                current = menu_map.get(menu_id)
                while current is not None:
                    included_ids.add(current.id)
                    current = menu_map.get(current.parent_id) if current.parent_id else None

        visible_menus = [
            menu
            for menu in all_menus
            if menu.visible and menu.type in ("DIR", "MENU") and menu.id in included_ids
        ]
        visible_menus.sort(key=lambda menu: (menu.sort, menu.id))

        node_map: dict[int, MenuNode] = {}
        for menu in visible_menus:
            node_map[menu.id] = MenuNode(
                id=menu.id,
                parent_id=menu.parent_id,
                name=menu.name,
                type=menu.type,
                path=menu.path,
                component=menu.component,
                icon=menu.icon,
                sort=menu.sort,
                permission_code=menu.permission_code,
            )

        roots: list[MenuNode] = []
        for menu in visible_menus:
            node = node_map[menu.id]
            if menu.parent_id and menu.parent_id in node_map:
                node_map[menu.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    async def _build_field_permissions(
        self,
        roles: list[Role],
        is_superuser: bool,
    ) -> dict[str, dict[str, FieldPermissionOut]]:
        if is_superuser:
            return {}

        role_ids = [role.id for role in roles]
        rows: list[RoleFieldPermission] = []
        if role_ids:
            stmt = select(RoleFieldPermission).where(RoleFieldPermission.role_id.in_(role_ids))
            rows = list((await self.session.execute(stmt)).scalars().all())

        configured = {
            (row.role_id, row.resource, row.field): row
            for row in rows
        }

        result: dict[str, dict[str, FieldPermissionOut]] = {}
        for resource, catalog in FIELD_CATALOG.items():
            resource_permissions: dict[str, FieldPermissionOut] = {}
            for field_def in catalog:
                field_name = field_def["field"]
                can_view = False
                can_edit = False
                for role_id in role_ids:
                    row = configured.get((role_id, resource, field_name))
                    if row is None:
                        # 未配置的角色不施加字段限制
                        can_view = True
                        can_edit = True
                    else:
                        can_view = can_view or row.can_view
                        can_edit = can_edit or row.can_edit
                resource_permissions[field_name] = FieldPermissionOut(
                    can_view=can_view,
                    can_edit=can_edit,
                )
            result[resource] = resource_permissions
        return result
