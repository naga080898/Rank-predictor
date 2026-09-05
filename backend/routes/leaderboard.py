import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import LeaderboardEntrySchema
from backend.services.rank_service import get_leaderboard_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Leaderboard"])

@router.get("/leaderboard", response_model=List[LeaderboardEntrySchema])
def get_leaderboard(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    test_date: Optional[str] = Query(None, description="Filter by exam date"),
    test_time: Optional[str] = Query(None, description="Filter by shift/time"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    category: Optional[str] = Query(None, description="Filter by category"),
    zone: Optional[str] = Query(None, description="Filter by zone"),
    limit: int = Query(50, ge=1, le=200, description="Max candidates to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    Returns ranked leaderboard of candidates ordered by score, accuracy, and correct count.
    """
    logger.info(f"Fetching leaderboard with filters: subject='{subject}', date='{test_date}', time='{test_time}', limit={limit}, offset={offset}")
    return get_leaderboard_data(
        db=db,
        subject=subject,
        test_date=test_date,
        test_time=test_time,
        gender=gender,
        category=category,
        zone=zone,
        limit=limit,
        offset=offset
    )
