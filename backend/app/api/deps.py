from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.clock import Clock, SystemClock
from app.database.session import get_db


def get_clock() -> Clock:
    return SystemClock()


DB = Depends(get_db)
CLOCK = Depends(get_clock)
__all__ = ["get_db", "get_clock", "DB", "CLOCK", "Session"]
