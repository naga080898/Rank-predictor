import json
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CandidateSubmission, UnidentifiedCandidate
from backend.schemas import EvaluationResponseSchema
from backend.parser_engine import parse_pdf_bytes_or_file
from backend.services.rank_service import calculate_rank_estimate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Evaluation"])

SAMPLE_PDF_MAP = {
    1: "sample_pdfs/digialm.com____per_g26_pub_33174_touchstone_AssessmentQPHTMLMode1____33174O261_33174O261S11D2010_17878965798832895_APVR0048215_33174O261S11D2010E1_260830083936 12.28.26 PM.pdf",
    2: "sample_pdfs/aee response sheet  12.28.26 PM.pdf"
}

def _process_and_save_result(
    parsed_result: dict,
    file_name: str,
    client_ip: Optional[str],
    estimated_total_candidates: Optional[int],
    db: Session
) -> dict:
    """Helper to upsert candidate submission record and calculate rank."""
    candidate_info = parsed_result["candidate"]
    summary = parsed_result["summary"]
    sections = parsed_result["sections"]
    questions = parsed_result["questions"]
    unidentified_text = parsed_result.get("unidentified_page_text")

    if unidentified_text:
        logger.info(f"Saving unidentified page text for {file_name}")
        unidentified_record = UnidentifiedCandidate(
            file_name=file_name,
            page_text=unidentified_text
        )
        db.add(unidentified_record)

    hall_ticket = candidate_info.get("hall_ticket", "").strip()
    subject = candidate_info.get("subject", "").strip()

    submission = None
    participant_name = candidate_info.get("participant_name", "").strip()
    final_score = summary.get("final_score", 0.0)

    is_valid_score = (final_score != 0)

    if is_valid_score:
        if hall_ticket:
            submission = (
                db.query(CandidateSubmission)
                .filter(
                    CandidateSubmission.hall_ticket == hall_ticket,
                    CandidateSubmission.subject == subject
                )
                .first()
            )

        # Fallback dedup: match by name + subject + score when no hall ticket or no match found
        if not submission and participant_name:
            submission = (
                db.query(CandidateSubmission)
                .filter(
                    CandidateSubmission.participant_name == participant_name,
                    CandidateSubmission.subject == subject,
                    CandidateSubmission.final_score == final_score
                )
                .order_by(CandidateSubmission.id.desc())
                .first()
            )

        if submission:
            logger.info(f"Updating existing submission for Hall Ticket: {hall_ticket}")
            submission.participant_name = candidate_info.get("participant_name") or submission.participant_name
            submission.test_center = candidate_info.get("test_center") or submission.test_center
            submission.test_date = candidate_info.get("test_date") or submission.test_date
            submission.test_time = candidate_info.get("test_time") or submission.test_time
            submission.gender = candidate_info.get("gender") or submission.gender
            submission.category = candidate_info.get("category") or submission.category
            submission.zone = candidate_info.get("zone") or submission.zone
            submission.total_questions = summary["total_questions"]
            submission.attempted = summary["attempted"]
            submission.unattempted = summary["unattempted"]
            submission.correct = summary["correct"]
            submission.incorrect = summary["incorrect"]
            submission.accuracy_percent = summary["accuracy_percent"]
            submission.positive_marking = summary["positive_marking"]
            submission.negative_marking = summary["negative_marking"]
            submission.final_score = summary["final_score"]
            submission.sections_json = json.dumps(sections)
            submission.file_name = file_name
            submission.ip_address = client_ip
        else:
            logger.info(f"Creating new submission record for Hall Ticket: {hall_ticket or 'Anonymous'}")
            submission = CandidateSubmission(
                hall_ticket=hall_ticket,
                participant_name=candidate_info.get("participant_name"),
                test_center=candidate_info.get("test_center"),
                test_date=candidate_info.get("test_date"),
                test_time=candidate_info.get("test_time"),
                subject=subject,
                total_questions=summary["total_questions"],
                attempted=summary["attempted"],
                unattempted=summary["unattempted"],
                correct=summary["correct"],
                incorrect=summary["incorrect"],
                accuracy_percent=summary["accuracy_percent"],
                positive_marking=summary["positive_marking"],
                negative_marking=summary["negative_marking"],
                final_score=summary["final_score"],
                sections_json=json.dumps(sections),
                file_name=file_name,
                ip_address=client_ip,
                gender=candidate_info.get("gender"),
                category=candidate_info.get("category"),
                zone=candidate_info.get("zone")
            )
            db.add(submission)

        db.commit()
        db.refresh(submission)
        
        submission_id = submission.id
        submitted_at = submission.submitted_at
    else:
        logger.info(f"Not saving submission to DB because final_score is 0 for {hall_ticket}")
        submission = CandidateSubmission(
            hall_ticket=hall_ticket,
            subject=subject,
            final_score=final_score
        )
        submission_id = -1
        import datetime
        submitted_at = datetime.datetime.utcnow()

    # Compute dynamic rank & percentile estimates
    rank_estimate = calculate_rank_estimate(
        db=db,
        submission=submission,
        total_exam_estimate=estimated_total_candidates
    )

    return {
        "submission_id": submission_id,
        "candidate": candidate_info,
        "summary": summary,
        "rank_estimate": rank_estimate,
        "sections": sections,
        "questions": questions,
        "submitted_at": submitted_at
    }


@router.post("/evaluate", response_model=EvaluationResponseSchema)
async def evaluate_response_sheet(
    request: Request,
    file: UploadFile = File(..., description="The DigiALM / TCS iON Response Sheet PDF file"),
    positive_marks: float = Form(1.0, description="Marks awarded for each correct answer"),
    negative_marks: float = Form(0.0, description="Marks deducted for each incorrect answer"),
    estimated_total_candidates: Optional[int] = Form(None, description="Optional custom estimate of total exam candidates"),
    gender: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    zone: Optional[str] = Form(None),
    hall_ticket: str = Form(..., description="The candidate's hall ticket number"),
    db: Session = Depends(get_db)
):
    """
    Parses candidate response sheet PDF, evaluates score, records submission in the database,
    and returns comprehensive candidate performance and rank estimate.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload a valid .pdf response sheet."
        )

    logger.info(f"Received file upload: '{file.filename}', positive={positive_marks}, negative={negative_marks}")

    try:
        pdf_bytes = await file.read()
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        parsed_result = parse_pdf_bytes_or_file(
            source=pdf_bytes,
            positive_marks=positive_marks,
            negative_marks=negative_marks,
            filename=file.filename
        )
        
        parsed_result["candidate"]["gender"] = gender
        parsed_result["candidate"]["category"] = category
        parsed_result["candidate"]["zone"] = zone
        if hall_ticket and not parsed_result["candidate"].get("hall_ticket"):
            parsed_result["candidate"]["hall_ticket"] = hall_ticket

        client_ip = request.client.host if request.client else None
        return _process_and_save_result(
            parsed_result=parsed_result,
            file_name=file.filename,
            client_ip=client_ip,
            estimated_total_candidates=estimated_total_candidates,
            db=db
        )

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"Validation error during PDF parsing: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error evaluating PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process response sheet: {str(e)}")


@router.post("/evaluate/url", response_model=EvaluationResponseSchema)
async def evaluate_response_sheet_url(
    request: Request,
    url: str = Form(..., description="The DigiALM / TCS iON Response Sheet URL"),
    positive_marks: float = Form(1.0, description="Marks awarded for each correct answer"),
    negative_marks: float = Form(0.0, description="Marks deducted for each incorrect answer"),
    estimated_total_candidates: Optional[int] = Form(None, description="Optional custom estimate of total exam candidates"),
    gender: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    zone: Optional[str] = Form(None),
    hall_ticket: str = Form(..., description="The candidate's hall ticket number"),
    db: Session = Depends(get_db)
):
    """
    Downloads HTML from a DigiALM response sheet URL, parses it, evaluates score,
    records submission in the database, and returns candidate performance and rank estimate.
    """
    logger.info(f"Received URL evaluate request: {url}")
    
    import httpx
    from backend.html_parser_engine import parse_html_response_sheet

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html_content = resp.text

        if "rightAns" not in html_content and "questionRowTbl" not in html_content and "question-pnl" not in html_content:
            raise ValueError("The downloaded URL does not appear to be a valid DigiALM response sheet.")

        parsed_result = parse_html_response_sheet(
            html_content=html_content,
            positive_marks=positive_marks,
            negative_marks=negative_marks
        )
        
        parsed_result["candidate"]["gender"] = gender
        parsed_result["candidate"]["category"] = category
        parsed_result["candidate"]["zone"] = zone
        if hall_ticket and not parsed_result["candidate"].get("hall_ticket"):
            parsed_result["candidate"]["hall_ticket"] = hall_ticket

        client_ip = request.client.host if request.client else None
        return _process_and_save_result(
            parsed_result=parsed_result,
            file_name=url,
            client_ip=client_ip,
            estimated_total_candidates=estimated_total_candidates,
            db=db
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error fetching URL: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download response sheet from URL. HTTP Status: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Network error fetching URL: {e}")
        raise HTTPException(status_code=400, detail="Failed to connect to the provided URL.")
    except ValueError as ve:
        logger.warning(f"Validation error during HTML parsing: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error evaluating URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process response sheet URL: {str(e)}")



@router.post("/evaluate-sample/{sample_id}", response_model=EvaluationResponseSchema)
def evaluate_sample_sheet(
    sample_id: int,
    request: Request,
    positive_marks: float = Query(1.0),
    negative_marks: float = Query(0.0),
    estimated_total_candidates: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Fast 1-click evaluation demo using built-in sample response sheets.
    """
    if sample_id not in SAMPLE_PDF_MAP:
        raise HTTPException(status_code=404, detail="Sample PDF index not found.")

    pdf_path = Path(SAMPLE_PDF_MAP[sample_id])
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample file '{pdf_path.name}' not found on server.")

    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        parsed_result = parse_pdf_bytes_or_file(
            source=pdf_bytes,
            positive_marks=positive_marks,
            negative_marks=negative_marks,
            filename=pdf_path.name
        )

        client_ip = request.client.host if request.client else None
        return _process_and_save_result(
            parsed_result=parsed_result,
            file_name=pdf_path.name,
            client_ip=client_ip,
            estimated_total_candidates=estimated_total_candidates,
            db=db
        )
    except Exception as e:
        logger.exception(f"Error evaluating sample PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candidate/{identifier}", response_model=EvaluationResponseSchema)
def get_candidate_evaluation(
    identifier: str,
    subject: Optional[str] = Query(None, description="Subject filter if searching by hall ticket"),
    db: Session = Depends(get_db)
):
    """
    Retrieves previous scorecard and updated live rank for a given Hall Ticket or Submission ID.
    """
    query = db.query(CandidateSubmission)
    if identifier.isdigit():
        sub = query.filter(CandidateSubmission.id == int(identifier)).first()
    else:
        q = query.filter(CandidateSubmission.hall_ticket == identifier)
        if subject:
            q = q.filter(CandidateSubmission.subject == subject)
        sub = q.order_by(CandidateSubmission.id.desc()).first()

    if not sub:
        raise HTTPException(status_code=404, detail="Candidate submission not found.")

    sections = json.loads(sub.sections_json) if sub.sections_json else {}
    questions = []

    rank_estimate = calculate_rank_estimate(db=db, submission=sub)

    return {
        "submission_id": sub.id,
        "candidate": {
            "hall_ticket": sub.hall_ticket or "",
            "participant_name": sub.participant_name or "",
            "test_center": sub.test_center or "",
            "test_date": sub.test_date or "",
            "test_time": sub.test_time or "",
            "subject": sub.subject or "",
            "gender": sub.gender,
            "category": sub.category,
            "zone": sub.zone
        },
        "summary": {
            "total_questions": sub.total_questions,
            "attempted": sub.attempted,
            "unattempted": sub.unattempted,
            "correct": sub.correct,
            "incorrect": sub.incorrect,
            "accuracy_percent": sub.accuracy_percent,
            "positive_marking": sub.positive_marking,
            "negative_marking": sub.negative_marking,
            "final_score": sub.final_score
        },
        "rank_estimate": rank_estimate,
        "sections": sections,
        "questions": questions,
        "submitted_at": sub.submitted_at
    }
