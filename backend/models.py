import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from backend.database import Base

class CandidateSubmission(Base):
    __tablename__ = "candidate_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Candidate Metadata
    hall_ticket = Column(String(100), index=True, nullable=True)
    participant_name = Column(String(200), nullable=True)
    test_center = Column(String(300), nullable=True)
    test_date = Column(String(50), index=True, nullable=True)
    test_time = Column(String(100), index=True, nullable=True)  # Shift/Session
    subject = Column(String(150), index=True, nullable=True)

    # Scoring & Evaluation Metrics
    total_questions = Column(Integer, default=0)
    attempted = Column(Integer, default=0)
    unattempted = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    incorrect = Column(Integer, default=0)
    accuracy_percent = Column(Float, default=0.0)
    positive_marking = Column(Float, default=1.0)
    negative_marking = Column(Float, default=0.25)
    final_score = Column(Float, index=True, nullable=False)

    # Detailed Structured JSON payloads
    sections_json = Column(Text, nullable=True)   # JSON string for per-section stats

    # System & Audit info
    ip_address = Column(String(50), nullable=True)
    file_name = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Compound Indexes for faster ranking & statistical queries
    __table_args__ = (
        Index("idx_subj_score", "subject", "final_score"),
        Index("idx_subj_date_time_score", "subject", "test_date", "test_time", "final_score"),
    )
