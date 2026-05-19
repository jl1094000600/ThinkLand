from datetime import date
from math import ceil

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DailyPointAccount, PointTransaction

DAILY_POINTS = 100
TOKENS_PER_POINT = 1000


def today() -> date:
    return date.today()


def ensure_daily_points(db: Session, user_id: int) -> DailyPointAccount:
    usage_date = today()
    account = db.scalar(
        select(DailyPointAccount).where(
            DailyPointAccount.user_id == user_id,
            DailyPointAccount.usage_date == usage_date,
        )
    )
    if account is not None:
        return account
    account = DailyPointAccount(user_id=user_id, usage_date=usage_date, granted_points=DAILY_POINTS, used_points=0)
    db.add(account)
    db.flush()
    return account


def points_out(account: DailyPointAccount) -> dict:
    remaining = max(account.granted_points - account.used_points, 0)
    return {
        "date": account.usage_date.isoformat(),
        "granted_points": account.granted_points,
        "used_points": account.used_points,
        "remaining_points": remaining,
    }


def estimate_tokens(text: str) -> int:
    return max(1, ceil(len(text) / 4)) + 350


def points_for_tokens(total_tokens: int) -> int:
    return max(1, ceil(total_tokens / TOKENS_PER_POINT))


def spend_points(db: Session, account: DailyPointAccount, user_id: int, generation_id: int, total_tokens: int) -> int:
    points = points_for_tokens(total_tokens)
    account.used_points += points
    db.add(
        PointTransaction(
            user_id=user_id,
            usage_date=account.usage_date,
            generation_id=generation_id,
            delta_points=-points,
            token_count=total_tokens,
            reason="generation",
        )
    )
    return points

