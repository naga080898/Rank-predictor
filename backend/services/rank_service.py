import json
import math
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.models import CandidateSubmission
from backend.config import DEFAULT_TOTAL_EXAM_TAKERS

logger = logging.getLogger(__name__)

def calculate_normalized_score(db: Session, submission: CandidateSubmission) -> float:
    """
    Calculates the normalized score using the provided formula:
    M_hat_ij = ((M_t_g - M_q_g) / (M_ti - M_iq)) * (M_ij - M_iq) + M_q_gm
    """
    subj = submission.subject
    
    # Base query for the specific subject
    subj_query = db.query(CandidateSubmission).filter(CandidateSubmission.subject == subj)
    
    total_candidates = subj_query.count()
    if total_candidates == 0:
        return submission.final_score
        
    m_ij = submission.final_score
    
    # Calculate M_q_g (overall mean + overall stddev)
    # Note: SQLite stddev might not be available out-of-box, but PostgreSQL has stddev_samp
    try:
        overall_stats = subj_query.with_entities(
            func.avg(CandidateSubmission.final_score),
            func.stddev_samp(CandidateSubmission.final_score)
        ).first()
        overall_mean = float(overall_stats[0]) if overall_stats and overall_stats[0] is not None else 0.0
        overall_std = float(overall_stats[1]) if overall_stats and overall_stats[1] is not None else 0.0
    except Exception as e:
        logger.warning(f"stddev_samp failed for overall stats, falling back to 0. {e}")
        overall_mean = float(subj_query.with_entities(func.avg(CandidateSubmission.final_score)).scalar() or 0.0)
        overall_std = 0.0
        
    m_q_g = overall_mean + overall_std
    
    # Calculate M_t_g (average marks of the top 0.1% candidates considering all shifts)
    top_0_1_percent_count = max(1, math.ceil(total_candidates * 0.001))
    top_overall_query = subj_query.order_by(CandidateSubmission.final_score.desc()).limit(top_0_1_percent_count)
    top_overall_avg = db.query(func.avg(top_overall_query.subquery().c.final_score)).scalar()
    m_t_g = float(top_overall_avg) if top_overall_avg is not None else overall_mean
    
    # Calculate shift specific stats
    shift_query = subj_query.filter(
        CandidateSubmission.test_date == submission.test_date,
        CandidateSubmission.test_time == submission.test_time
    )
    shift_candidates = shift_query.count()
    
    if shift_candidates == 0:
        return m_ij
        
    try:
        shift_stats = shift_query.with_entities(
            func.avg(CandidateSubmission.final_score),
            func.stddev_samp(CandidateSubmission.final_score)
        ).first()
        shift_mean = float(shift_stats[0]) if shift_stats and shift_stats[0] is not None else 0.0
        shift_std = float(shift_stats[1]) if shift_stats and shift_stats[1] is not None else 0.0
    except Exception as e:
        logger.warning(f"stddev_samp failed for shift stats, falling back to 0. {e}")
        shift_mean = float(shift_query.with_entities(func.avg(CandidateSubmission.final_score)).scalar() or 0.0)
        shift_std = 0.0
        
    m_iq = shift_mean + shift_std
    
    # M_ti = average marks of top 0.1% of the candidates in the ith shift
    top_0_1_percent_shift_count = max(1, math.ceil(shift_candidates * 0.001))
    top_shift_query = shift_query.order_by(CandidateSubmission.final_score.desc()).limit(top_0_1_percent_shift_count)
    top_shift_avg = db.query(func.avg(top_shift_query.subquery().c.final_score)).scalar()
    m_ti = float(top_shift_avg) if top_shift_avg is not None else shift_mean
    
    # M_q_gm = sum of mean marks and standard deviation of candidates in the shift having maximum mean + stddev
    try:
        shift_groups = subj_query.with_entities(
            CandidateSubmission.test_date,
            CandidateSubmission.test_time,
            func.avg(CandidateSubmission.final_score).label('s_mean'),
            func.stddev_samp(CandidateSubmission.final_score).label('s_std')
        ).group_by(CandidateSubmission.test_date, CandidateSubmission.test_time).all()
        
        max_shift_sum = 0.0
        for sg in shift_groups:
            s_m = float(sg.s_mean) if sg.s_mean is not None else 0.0
            s_s = float(sg.s_std) if sg.s_std is not None else 0.0
            if (s_m + s_s) > max_shift_sum:
                max_shift_sum = s_m + s_s
                
        m_q_gm = max_shift_sum if max_shift_sum > 0 else m_q_g
    except Exception as e:
        logger.warning(f"Failed to calculate max shift sum, falling back to overall m_q_g. {e}")
        m_q_gm = m_q_g
        
    denominator = m_ti - m_iq
    if denominator == 0:
        denominator = 1.0 # fallback
        
    normalized_score = ((m_t_g - m_q_g) / denominator) * (m_ij - m_iq) + m_q_gm
    
    return round(normalized_score, 5)

def mask_identifier(val: Optional[str]) -> str:
    """Masks hall ticket or identifier for public display (e.g. APVR0048215 -> APVR***8215)."""
    if not val:
        return "N/A"
    s = str(val).strip()
    if len(s) <= 4:
        return s
    return f"{s[:4]}***{s[-4:]}"

def mask_name(val: Optional[str]) -> str:
    """Masks name for public display if needed, or keeps first name."""
    if not val:
        return "Anonymous Candidate"
    parts = val.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."

def calculate_rank_estimate(
    db: Session,
    submission: CandidateSubmission,
    total_exam_estimate: Optional[int] = None
) -> Dict[str, Any]:
    """
    Computes candidate's platform rank, shift rank, percentiles,
    and projected All India Rank (AIR) based on current database distribution.
    """
    subj = submission.subject
    total_pool_estimate = total_exam_estimate or DEFAULT_TOTAL_EXAM_TAKERS

    # Base query for same subject (or all if subject not set)
    subj_query = db.query(CandidateSubmission)
    if subj:
        subj_query = subj_query.filter(CandidateSubmission.subject == subj)

    total_submissions = subj_query.count()

    # Overall Rank (Number of candidates with strictly higher marks + 1)
    better_overall = subj_query.filter(CandidateSubmission.final_score > submission.final_score).count()
    platform_rank = better_overall + 1

    # Overall Percentile
    if total_submissions > 0:
        percentile = round(((total_submissions - platform_rank + 1) / total_submissions) * 100, 2)
    else:
        percentile = 100.0

    # Shift-specific calculation
    shift_query = subj_query.filter(
        CandidateSubmission.test_date == submission.test_date,
        CandidateSubmission.test_time == submission.test_time
    )
    total_shift_submissions = shift_query.count()

    better_in_shift = shift_query.filter(CandidateSubmission.final_score > submission.final_score).count()
    shift_rank = better_in_shift + 1

    if total_shift_submissions > 0:
        shift_percentile = round(((total_shift_submissions - shift_rank + 1) / total_shift_submissions) * 100, 2)
    else:
        shift_percentile = 100.0

    # Shift Difficulty Analysis
    overall_avg_tuple = subj_query.with_entities(func.avg(CandidateSubmission.final_score)).first()
    shift_avg_tuple = shift_query.with_entities(func.avg(CandidateSubmission.final_score)).first()

    overall_avg = float(overall_avg_tuple[0]) if overall_avg_tuple and overall_avg_tuple[0] is not None else submission.final_score
    shift_avg = float(shift_avg_tuple[0]) if shift_avg_tuple and shift_avg_tuple[0] is not None else submission.final_score

    diff = shift_avg - overall_avg
    if total_shift_submissions >= 3:
        if diff < -2.0:
            difficulty_tier = "Tough Shift (Normalization Advantage)"
        elif diff > 2.0:
            difficulty_tier = "Moderate / High Scoring Shift"
        else:
            difficulty_tier = "Balanced Shift"
    else:
        difficulty_tier = "Standard Baseline"

    # Projected AIR calculation
    # Project based on percentile rank over total exam takers
    est_unnormalized_rank = max(1, int(((100.0 - percentile) / 100.0) * total_pool_estimate))
    low_bound = max(1, int(est_unnormalized_rank * 0.80))
    high_bound = max(low_bound + 5, int(est_unnormalized_rank * 1.25) + 5)
    predicted_air_range = f"{low_bound:,} - {high_bound:,}"

    return {
        "platform_rank": platform_rank,
        "total_submissions": total_submissions,
        "percentile": percentile,
        "shift_rank": shift_rank,
        "total_shift_submissions": total_shift_submissions,
        "shift_percentile": shift_percentile,
        "predicted_air_range": predicted_air_range,
        "shift_difficulty_tier": difficulty_tier
    }

def get_comprehensive_stats(db: Session, subject: Optional[str] = None) -> Dict[str, Any]:
    """Generates rich statistical metrics, shift comparisons, and histogram distributions."""
    query = db.query(CandidateSubmission)
    if subject:
        query = query.filter(CandidateSubmission.subject == subject)

    total_submissions = query.count()
    if total_submissions == 0:
        return {
            "total_submissions": 0,
            "subject": subject,
            "overall": {
                "avg_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "median_score": 0.0,
                "std_dev": 0.0,
                "avg_accuracy": 0.0,
                "avg_attempted": 0.0
            },
            "shifts": [],
            "score_distribution": [],
            "sections_average": {}
        }

    scores = [s[0] for s in query.with_entities(CandidateSubmission.final_score).all()]
    scores_sorted = sorted(scores)

    # Statistical values
    avg_score = round(sum(scores) / len(scores), 2)
    max_score = round(max(scores), 2)
    min_score = round(min(scores), 2)

    # Median
    n = len(scores_sorted)
    if n % 2 == 1:
        median_score = round(scores_sorted[n // 2], 2)
    else:
        median_score = round((scores_sorted[n // 2 - 1] + scores_sorted[n // 2]) / 2.0, 2)

    # Standard deviation
    variance = sum((x - avg_score) ** 2 for x in scores) / n
    std_dev = round(math.sqrt(variance), 2)

    # Overall Averages for accuracy and attempts
    avg_acc_tuple = query.with_entities(func.avg(CandidateSubmission.accuracy_percent)).first()
    avg_att_tuple = query.with_entities(func.avg(CandidateSubmission.attempted)).first()
    avg_accuracy = round(float(avg_acc_tuple[0]), 2) if avg_acc_tuple and avg_acc_tuple[0] is not None else 0.0
    avg_attempted = round(float(avg_att_tuple[0]), 1) if avg_att_tuple and avg_att_tuple[0] is not None else 0.0

    # Shift-wise breakdown
    shifts_data = []
    shift_groups = (
        query.with_entities(
            CandidateSubmission.test_date,
            CandidateSubmission.test_time,
            func.count(CandidateSubmission.id),
            func.avg(CandidateSubmission.final_score),
            func.max(CandidateSubmission.final_score),
            func.min(CandidateSubmission.final_score)
        )
        .group_by(CandidateSubmission.test_date, CandidateSubmission.test_time)
        .all()
    )

    for date_val, time_val, count, shift_avg, s_max, s_min in shift_groups:
        d_str = date_val or "Unknown Date"
        t_str = time_val or "Unknown Time"
        shifts_data.append({
            "shift_key": f"{d_str} | {t_str}",
            "test_date": d_str,
            "test_time": t_str,
            "candidate_count": count,
            "avg_score": round(float(shift_avg), 2) if shift_avg is not None else 0.0,
            "max_score": round(float(s_max), 2) if s_max is not None else 0.0,
            "min_score": round(float(s_min), 2) if s_min is not None else 0.0
        })

    # Score Distribution Buckets (10-point intervals)
    buckets_def = [
        ("< 0", float("-inf"), 0.0),
        ("0 - 10", 0.0, 10.0),
        ("10 - 20", 10.0, 20.0),
        ("20 - 30", 20.0, 30.0),
        ("30 - 40", 30.0, 40.0),
        ("40 - 50", 40.0, 50.0),
        ("50 - 60", 50.0, 60.0),
        ("60 - 70", 60.0, 70.0),
        ("70 - 80", 70.0, 80.0),
        ("80 - 90", 80.0, 90.0),
        ("90 - 100", 90.0, 100.0),
        ("> 100", 100.0, float("inf")),
    ]

    distribution = []
    for label, b_min, b_max in buckets_def:
        if b_min == float("-inf"):
            cnt = sum(1 for s in scores if s < b_max)
        elif b_max == float("inf"):
            cnt = sum(1 for s in scores if s > b_min)
        else:
            cnt = sum(1 for s in scores if b_min <= s < b_max or (b_max == 100.0 and s == 100.0))
        
        pct = round((cnt / total_submissions * 100), 2) if total_submissions > 0 else 0.0
        distribution.append({
            "range_label": label,
            "min_score": -999.0 if b_min == float("-inf") else b_min,
            "max_score": 999.0 if b_max == float("inf") else b_max,
            "count": cnt,
            "percentage": pct
        })

    # Sections average breakdown
    sections_totals = {}
    sections_counts = {}
    all_submissions = query.all()
    for sub in all_submissions:
        if sub.sections_json:
            try:
                sec_dict = json.loads(sub.sections_json)
                for sec_name, sec_info in sec_dict.items():
                    sec_score = sec_info.get("score", 0.0)
                    sections_totals[sec_name] = sections_totals.get(sec_name, 0.0) + sec_score
                    sections_counts[sec_name] = sections_counts.get(sec_name, 0) + 1
            except Exception as err:
                logger.warning(f"Error parsing sections_json for sub {sub.id}: {err}")

    sections_avg = {}
    for sec_name, total_val in sections_totals.items():
        c = sections_counts.get(sec_name, 1)
        sections_avg[sec_name] = round(total_val / c, 2)

    return {
        "total_submissions": total_submissions,
        "subject": subject,
        "overall": {
            "avg_score": avg_score,
            "max_score": max_score,
            "min_score": min_score,
            "median_score": median_score,
            "std_dev": std_dev,
            "avg_accuracy": avg_accuracy,
            "avg_attempted": avg_attempted
        },
        "shifts": shifts_data,
        "score_distribution": distribution,
        "sections_average": sections_avg
    }

def get_leaderboard_data(
    db: Session,
    subject: Optional[str] = None,
    test_date: Optional[str] = None,
    test_time: Optional[str] = None,
    gender: Optional[str] = None,
    category: Optional[str] = None,
    zone: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Returns top ranked candidates with filters and percentiles.
    Deduplicates by (participant_name, subject, final_score), keeping only the
    latest submission per unique candidate+score combination.
    """
    from sqlalchemy import func as sqlfunc

    # Build a subquery: for each (participant_name, subject, final_score) group,
    # pick the MAX (latest) submission id to deduplicate re-uploads of the same candidate.
    dedup_subq = (
        db.query(sqlfunc.max(CandidateSubmission.id).label("max_id"))
        .group_by(
            CandidateSubmission.participant_name,
            CandidateSubmission.subject,
            CandidateSubmission.final_score
        )
        .subquery()
    )

    # Main query restricted to the deduplicated set
    query = db.query(CandidateSubmission).filter(
        CandidateSubmission.id.in_(db.query(dedup_subq.c.max_id))
    )

    if subject:
        query = query.filter(CandidateSubmission.subject == subject)
    if test_date:
        query = query.filter(CandidateSubmission.test_date == test_date)
    if test_time:
        query = query.filter(CandidateSubmission.test_time == test_time)
    if gender:
        query = query.filter(CandidateSubmission.gender == gender)
    if category:
        query = query.filter(CandidateSubmission.category == category)
    if zone:
        query = query.filter(CandidateSubmission.zone == zone)

    total_in_pool = query.count()

    results = (
        query.order_by(
            desc(CandidateSubmission.final_score),
            desc(CandidateSubmission.accuracy_percent),
            desc(CandidateSubmission.correct)
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    leaderboard = []
    for idx, cand in enumerate(results):
        rank_num = offset + idx + 1
        pct = round(((total_in_pool - rank_num + 1) / total_in_pool) * 100, 2) if total_in_pool > 0 else 100.0
        
        leaderboard.append({
            "rank": rank_num,
            "submission_id": cand.id,
            "hall_ticket_masked": mask_identifier(cand.hall_ticket),
            "participant_name": cand.participant_name or "Candidate",
            "subject": cand.subject,
            "test_date": cand.test_date,
            "test_time": cand.test_time,
            "gender": cand.gender,
            "category": cand.category,
            "zone": cand.zone,
            "correct": cand.correct,
            "incorrect": cand.incorrect,
            "unattempted": cand.unattempted,
            "accuracy_percent": cand.accuracy_percent,
            "final_score": cand.final_score,
            "percentile": pct,
            "submitted_at": cand.submitted_at
        })

    return leaderboard
