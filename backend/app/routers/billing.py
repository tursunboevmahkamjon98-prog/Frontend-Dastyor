from fastapi import APIRouter, Depends

from app.models import User
from app.schemas import BalanceOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])



@router.get("/balance", response_model=BalanceOut)
async def get_balance(user: User = Depends(get_current_user)):
    return BalanceOut(balance_somoni=user.balance_somoni)
