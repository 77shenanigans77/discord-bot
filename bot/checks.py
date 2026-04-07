from bot.constants import (
    CHANGELOG_CREATE_ROLES,
    FAQ_ROLES,
    FEATURE_ROLES,
    SCRIPT_CREATE_ROLES,
    SCRIPT_STATUS_ROLES,
    SCRIPT_STYLE_ROLES,
    SCRIPT_UPDATE_ROLES,
)


def get_member_role_names(member):
    return [role.name.lower() for role in member.roles]


def has_any_role(member, allowed):
    role_names = get_member_role_names(member)
    return any(role.lower() in role_names for role in allowed)


def can_use_script_create(member):
    return has_any_role(member, SCRIPT_CREATE_ROLES)


def can_use_script_update(member):
    return has_any_role(member, SCRIPT_UPDATE_ROLES)


def can_use_script_status(member):
    return has_any_role(member, SCRIPT_STATUS_ROLES)


def can_use_changelog_create(member):
    return has_any_role(member, CHANGELOG_CREATE_ROLES)


def can_use_faq(member):
    return has_any_role(member, FAQ_ROLES)


def can_use_features(member):
    return has_any_role(member, FEATURE_ROLES)


def can_use_script_style(member):
    return has_any_role(member, SCRIPT_STYLE_ROLES)


def build_denied_message():
    return "You do not have permission to use this command."
