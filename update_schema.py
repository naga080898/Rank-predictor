import os
from sqlalchemy import create_engine, text
from backend.config import DATABASE_URL

print(f"Connecting to: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    try:
        conn.execute(text('ALTER TABLE candidate_submissions ADD COLUMN gender VARCHAR(50);'))
        print('Added gender')
    except Exception as e:
        print(f"Error adding gender: {e}")
        
    try:
        conn.execute(text('ALTER TABLE candidate_submissions ADD COLUMN category VARCHAR(50);'))
        print('Added category')
    except Exception as e:
        print(f"Error adding category: {e}")
        
    try:
        conn.execute(text('ALTER TABLE candidate_submissions ADD COLUMN zone VARCHAR(150);'))
        print('Added zone')
    except Exception as e:
        print(f"Error adding zone: {e}")
        
    conn.commit()
print("Done!")
