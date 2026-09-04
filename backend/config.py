import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database URL - SQLite default, easily overridden by Neon/PostgreSQL DATABASE_URL env var
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/rank_predictor.db")

# Fix for some hosted PostgreSQL providers using postgres:// instead of postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Default Exam Scoring Rules
DEFAULT_POSITIVE_MARKS = float(os.getenv("DEFAULT_POSITIVE_MARKS", "1.0"))
DEFAULT_NEGATIVE_MARKS = float(os.getenv("DEFAULT_NEGATIVE_MARKS", "0.25"))

# Estimated Total Candidates (for exam AIR extrapolation)
DEFAULT_TOTAL_EXAM_TAKERS = int(os.getenv("DEFAULT_TOTAL_EXAM_TAKERS", "15000"))

# CORS Allowed Origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
