from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class CandidateInfoSchema(BaseModel):
    hall_ticket: Optional[str] = ""
    participant_name: Optional[str] = ""
    test_center: Optional[str] = ""
    test_date: Optional[str] = ""
    test_time: Optional[str] = ""
    subject: Optional[str] = ""
    gender: Optional[str] = None
    category: Optional[str] = None
    zone: Optional[str] = None

class QuestionDetailSchema(BaseModel):
    question_number: int
    question_id: Optional[str] = None
    section: Optional[str] = "General"
    question_text: Optional[str] = ""
    options: Dict[int, str] = Field(default_factory=dict)
    chosen_option: Optional[int] = None
    correct_option: Optional[int] = None
    status: str
    marks_awarded: float

class SectionSummarySchema(BaseModel):
    total: int = 0
    correct: int = 0
    incorrect: int = 0
    unattempted: int = 0
    score: float = 0.0

class EvaluationSummarySchema(BaseModel):
    total_questions: int
    attempted: int
    unattempted: int
    correct: int
    incorrect: int
    accuracy_percent: float
    positive_marking: float
    negative_marking: float
    final_score: float

class RankEstimateSchema(BaseModel):
    platform_rank: int
    total_submissions: int
    percentile: float
    shift_rank: int
    total_shift_submissions: int
    shift_percentile: float
    predicted_air_range: str
    shift_difficulty_tier: str

class EvaluationResponseSchema(BaseModel):
    submission_id: int
    candidate: CandidateInfoSchema
    summary: EvaluationSummarySchema
    rank_estimate: RankEstimateSchema
    sections: Dict[str, SectionSummarySchema]
    questions: Optional[List[QuestionDetailSchema]] = None
    submitted_at: datetime

class LeaderboardEntrySchema(BaseModel):
    rank: int
    submission_id: int
    hall_ticket_masked: str
    participant_name: str
    subject: Optional[str] = ""
    test_date: Optional[str] = ""
    test_time: Optional[str] = ""
    gender: Optional[str] = None
    category: Optional[str] = None
    zone: Optional[str] = None
    correct: int
    incorrect: int
    unattempted: int
    accuracy_percent: float
    final_score: float
    percentile: float
    submitted_at: datetime

class ShiftStatSchema(BaseModel):
    shift_key: str
    test_date: str
    test_time: str
    candidate_count: int
    avg_score: float
    max_score: float
    min_score: float

class ScoreBucketSchema(BaseModel):
    range_label: str
    min_score: float
    max_score: float
    count: int
    percentage: float

class StatsResponseSchema(BaseModel):
    total_submissions: int
    subject: Optional[str] = None
    overall: Dict[str, Any]
    shifts: List[ShiftStatSchema]
    score_distribution: List[ScoreBucketSchema]
    sections_average: Dict[str, float]
