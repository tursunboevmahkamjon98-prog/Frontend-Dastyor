from fastapi import APIRouter, Depends

from app.models import User
from app.schemas import BalanceOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])

# What is left of billing: reading a balance.
#
# There was a Dushanbe City card-payment flow here — create a payment,
# send the teacher to the bank, credit on a signature-verified webhook.
# It was removed by an explicit decision: a teacher tops up by contacting
# an administrator, paying outside the app, and the administrator credits
# the balance from the admin panel (routers/admin.py's add_balance).
#
# Deleted rather than left disabled on purpose. A dormant webhook that
# credits balances is still an endpoint on the internet, and dead code
# around money is the kind that gets re-enabled by accident.


@router.get("/balance", response_model=BalanceOut)
async def get_balance(user: User = Depends(get_current_user)):
    return BalanceOut(balance_somoni=user.balance_somoni)
