import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import StatsResponseSchema
from backend.services.rank_service import get_comprehensive_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Statistics"])

@router.get("/stats", response_model=StatsResponseSchema)
def get_exam_statistics(
    subject: Optional[str] = Query(None, description="Filter stats by subject (e.g. Electrical Engineering)"),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated statistical analysis:
    - Overall marks metrics (Average, Median, Max, Min, Std Dev, Accuracy)
    - Shift-wise comparative stats (Shift normalization insights)
    - Score distribution histograms
    - Section-wise average score breakdown
    """
    logger.info(f"Fetching statistics for subject: '{subject or 'All'}'")
    stats = get_comprehensive_stats(db=db, subject=subject)
    return stats
