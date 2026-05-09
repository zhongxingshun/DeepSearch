"""角色和文件可见范围控制。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_INTERNAL_EMPLOYEE = "internal_employee"
ROLE_EXTERNAL_CUSTOMER = "external_customer"

LEGACY_ROLE_USER = "user"

ADMIN_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN}
END_USER_ROLES = {ROLE_INTERNAL_EMPLOYEE, ROLE_EXTERNAL_CUSTOMER}
ALLOWED_ROLES = ADMIN_ROLES | END_USER_ROLES

VISIBILITY_PUBLIC = "public"
VISIBILITY_INTERNAL = "internal"
VISIBILITY_MARKETING = "marketing"

ALLOWED_VISIBILITY_SCOPES = {
    VISIBILITY_PUBLIC,
    VISIBILITY_INTERNAL,
    VISIBILITY_MARKETING,
}


def normalize_role(role: str | None) -> str:
    """兼容历史普通用户角色。"""
    if role == LEGACY_ROLE_USER or not role:
        return ROLE_INTERNAL_EMPLOYEE
    return role


def is_admin_role(role: str | None) -> bool:
    return normalize_role(role) in ADMIN_ROLES


def is_super_admin_role(role: str | None) -> bool:
    return normalize_role(role) == ROLE_SUPER_ADMIN


def can_manage_user_role(current_role: str | None, target_role: str | None) -> bool:
    """超管可管理所有账号；管理员只管理非管理员账号。"""
    normalized_current = normalize_role(current_role)
    normalized_target = normalize_role(target_role)

    if normalized_current == ROLE_SUPER_ADMIN:
        return True

    if normalized_current == ROLE_ADMIN:
        return normalized_target in END_USER_ROLES

    return False


def visible_file_scopes_for_role(role: str | None) -> list[str]:
    """返回该角色允许查看/检索的文件可见范围。"""
    normalized_role = normalize_role(role)

    if normalized_role in ADMIN_ROLES:
        return [VISIBILITY_PUBLIC, VISIBILITY_INTERNAL, VISIBILITY_MARKETING]

    if normalized_role == ROLE_INTERNAL_EMPLOYEE:
        return [VISIBILITY_PUBLIC, VISIBILITY_INTERNAL]

    return [VISIBILITY_PUBLIC]


def visible_file_scopes_for_user(user: "User") -> list[str]:
    return visible_file_scopes_for_role(user.role)


def can_access_file_scope(user: "User", visibility_scope: str | None) -> bool:
    return (visibility_scope or VISIBILITY_PUBLIC) in visible_file_scopes_for_user(user)


def validate_role_value(role: str) -> str:
    normalized = normalize_role(role)
    if normalized not in ALLOWED_ROLES:
        raise ValueError("角色必须是 super_admin、admin、internal_employee 或 external_customer")
    return normalized


def validate_visibility_scope(value: str | None) -> str:
    if value is None or not value.strip():
        raise ValueError("文件开放范围为必选项")

    normalized = value.strip()
    if normalized not in ALLOWED_VISIBILITY_SCOPES:
        raise ValueError("文件开放范围必须是 public、internal 或 marketing")
    return normalized
