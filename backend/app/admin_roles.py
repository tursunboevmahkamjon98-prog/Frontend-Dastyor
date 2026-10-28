"""Fine-grained permissions on top of the plain admin/not-admin gate.

app.auth.get_current_admin answers one question - "is this user an admin
at all" - and every endpoint that existed before this module keeps
asking exactly that question, unchanged. This module answers a second,
narrower question - "which admin actions can THIS admin take" - driven
by User.admin_tier, a column that only ever means something once role
is already "admin" (see models.py's comment and the database CHECK
constraint that enforces it).

Four tiers, confirmed with the product owner:
  super     every permission, including managing other admins' tiers.
  finance   payments, balance, cards, expenses, reports.
  support   users, SMS, viewing payments (not deciding them).
  readonly  view-only, everywhere.

An admin with admin_tier = NULL is one that was made an admin before
this column existed. That is not "no permissions" - it is explicitly
treated as super, so introducing tiers never silently strips capability
from an admin who already had it.
"""

from fastapi import Depends, HTTPException

from app.auth import get_current_admin
from app.models import User

TIER_SUPER = "super"
TIER_FINANCE = "finance"
TIER_SUPPORT = "support"
TIER_READONLY = "readonly"

ADMIN_TIERS = (TIER_SUPER, TIER_FINANCE, TIER_SUPPORT, TIER_READONLY)

TIER_PERMISSIONS: dict[str, frozenset[str]] = {
    TIER_SUPER: frozenset({"*"}),
    TIER_FINANCE: frozenset({
        "payments.view", "payments.review",
        "balance.manage",
        "topups.manage",
        "cards.manage",
        "expenses.manage",
        "reports.view",
        "audit.view",
    }),
    TIER_SUPPORT: frozenset({
        "users.manage",
        "users.sms",
        "payments.view",
    }),
    TIER_READONLY: frozenset({"*.view"}),
}


def _tier_for(admin: User) -> str:
    # NULL admin_tier predates this column entirely - see the module
    # docstring for why that resolves to super rather than to nothing.
    return admin.admin_tier or TIER_SUPER


def has_permission(admin: User, permission: str) -> bool:
    perms = TIER_PERMISSIONS.get(_tier_for(admin), frozenset())
    if "*" in perms or permission in perms:
        return True
    # "*.view" covers every ".view"-suffixed permission for readonly,
    # without readonly having to also get the mutating half of the name.
    return permission.endswith(".view") and "*.view" in perms


def require_permission(permission: str):
    """FastAPI dependency: admin-gated AND tier-gated.

    Always layers on top of get_current_admin, never instead of it - an
    endpoint still 403s a plain "user" exactly as it always did; this
    only adds a second, narrower 403 for an admin whose tier doesn't
    cover `permission`.
    """

    async def _dependency(admin: User = Depends(get_current_admin)) -> User:
        if not has_permission(admin, permission):
            raise HTTPException(status_code=403, detail="Insufficient admin permission")
        return admin

    return _dependency
