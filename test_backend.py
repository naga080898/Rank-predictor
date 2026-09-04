import sys
import logging
from pathlib import Path
from fastapi.testclient import TestClient

# Setup test logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend_test")

from backend.main import app
from backend.database import init_db

def test_api():
    logger.info("Initializing DB for test...")
    init_db()

    client = TestClient(app)

    # 1. Test Health Check
    logger.info("Testing GET /health...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    logger.info(f"Health response: {resp.json()}")

    # 2. Test PDF Evaluation Upload with sample PDF 1
    sample_pdf_1 = Path("sample_pdfs/aee response sheet  12.28.26 PM.pdf")
    logger.info(f"Testing POST /api/evaluate with: {sample_pdf_1.name}...")
    with open(sample_pdf_1, "rb") as f:
        files = {"file": (sample_pdf_1.name, f, "application/pdf")}
        data = {"positive_marks": 1.0, "negative_marks": 0.25}
        resp = client.post("/api/evaluate", files=files, data=data)

    assert resp.status_code == 200, f"Evaluate failed: {resp.status_code} {resp.text}"
    eval1 = resp.json()
    logger.info(f"Candidate 1 evaluated: {eval1['candidate']['participant_name']} (Hall Ticket: {eval1['candidate']['hall_ticket']})")
    logger.info(f"Score: {eval1['summary']['final_score']}, Platform Rank: {eval1['rank_estimate']['platform_rank']}/{eval1['rank_estimate']['total_submissions']}")

    # 3. Test PDF Evaluation Upload with sample PDF 2
    sample_pdf_2 = Path("sample_pdfs/digialm.com____per_g26_pub_33174_touchstone_AssessmentQPHTMLMode1____33174O261_33174O261S11D2010_17878965798832895_APVR0048215_33174O261S11D2010E1_260830083936 12.28.26 PM.pdf")
    logger.info(f"Testing POST /api/evaluate with: {sample_pdf_2.name}...")
    with open(sample_pdf_2, "rb") as f:
        files = {"file": (sample_pdf_2.name, f, "application/pdf")}
        data = {"positive_marks": 1.0, "negative_marks": 0.25}
        resp = client.post("/api/evaluate", files=files, data=data)

    assert resp.status_code == 200, f"Evaluate failed: {resp.status_code} {resp.text}"
    eval2 = resp.json()
    logger.info(f"Candidate 2 evaluated: {eval2['candidate']['participant_name']} (Hall Ticket: {eval2['candidate']['hall_ticket']})")
    logger.info(f"Score: {eval2['summary']['final_score']}, Platform Rank: {eval2['rank_estimate']['platform_rank']}/{eval2['rank_estimate']['total_submissions']}")

    # 4. Test GET /api/candidate/{hall_ticket}
    ht = eval1['candidate']['hall_ticket']
    logger.info(f"Testing GET /api/candidate/{ht}...")
    resp = client.get(f"/api/candidate/{ht}")
    assert resp.status_code == 200, f"Candidate lookup failed: {resp.text}"
    cand_data = resp.json()
    logger.info(f"Candidate lookup success: Score={cand_data['summary']['final_score']}, Updated Rank={cand_data['rank_estimate']['platform_rank']}/{cand_data['rank_estimate']['total_submissions']}")

    # 5. Test GET /api/leaderboard
    logger.info("Testing GET /api/leaderboard...")
    resp = client.get("/api/leaderboard")
    assert resp.status_code == 200, f"Leaderboard failed: {resp.text}"
    leaderboard = resp.json()
    logger.info(f"Leaderboard entries returned: {len(leaderboard)}")
    for item in leaderboard:
        logger.info(f"  Rank #{item['rank']}: {item['participant_name']} ({item['hall_ticket_masked']}) - Score: {item['final_score']} (Percentile: {item['percentile']}%)")

    # 6. Test GET /api/stats
    logger.info("Testing GET /api/stats...")
    resp = client.get("/api/stats")
    assert resp.status_code == 200, f"Stats failed: {resp.text}"
    stats = resp.json()
    logger.info(f"Total recorded submissions: {stats['total_submissions']}")
    logger.info(f"Overall metrics: {stats['overall']}")
    logger.info(f"Shift stats count: {len(stats['shifts'])}")
    for sh in stats['shifts']:
        logger.info(f"  Shift: {sh['shift_key']} | Count: {sh['candidate_count']} | Avg Score: {sh['avg_score']}")

    logger.info("ALL BACKEND FASTAPI TESTS PASSED SUCCESSFULLY! ✅")

if __name__ == "__main__":
    test_api()
