import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env.local")
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to DB...")
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE candidate_submissions ADD COLUMN normalized_score FLOAT;'))
        print('Added normalized_score')
    except Exception as e:
        print(f"Error adding normalized_score: {e}")
        
    try:
        conn.execute(text('CREATE INDEX ix_candidate_submissions_normalized_score ON candidate_submissions (normalized_score);'))
        print('Added index for normalized_score')
    except Exception as e:
        print(f"Error adding index: {e}")
        
    conn.commit()
print("Done!")
