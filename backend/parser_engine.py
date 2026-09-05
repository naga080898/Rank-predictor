import io
import re
import logging
from pathlib import Path
from typing import Union, Dict, Any, Optional
import pymupdf

logger = logging.getLogger(__name__)

# Known DigiALM / TCS iON color signatures
CORRECT_GREEN_HEX = ["#40c64b", "#008000", "#28a745", "#2e7d32"]
INCORRECT_RED_HEX = ["#f61818", "#ff0000", "#dc3545", "#e53935"]

def color_to_hex(color_int: int) -> str:
    """Converts PyMuPDF integer color to #rrggbb hex string."""
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    return f"#{r:02x}{g:02x}{b:02x}"

def is_green_option(color_int: int) -> bool:
    """
    Identifies if a text color is the Green color used for correct answers.
    Specifically matches #40c64b (Int: 4245067) and any green-dominant shade.
    """
    hex_code = color_to_hex(color_int).lower()
    if hex_code in CORRECT_GREEN_HEX or color_int == 4245067:
        return True
    
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    return (g > 120 and g > (r + 40) and g > (b + 40))

def is_red_option(color_int: int) -> bool:
    """
    Identifies if a text color is the Red color used for wrong options (#f61818).
    """
    hex_code = color_to_hex(color_int).lower()
    if hex_code in INCORRECT_RED_HEX or color_int == 16128024:
        return True
    
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    return (r > 160 and r > (g + 50) and r > (b + 50))

def extract_candidate_info(doc: pymupdf.Document) -> Dict[str, str]:
    """Extracts candidate exam details from the PDF header pages."""
    info = {
        "hall_ticket": "",
        "participant_name": "",
        "test_center": "",
        "test_date": "",
        "test_time": "",
        "subject": ""
    }

    raw_pages_text = []
    for page_idx in range(min(4, len(doc))):
        text = doc[page_idx].get_text("text")
        raw_pages_text.append(f"--- Page {page_idx + 1} ---\n{text}")

        if not info["hall_ticket"]:
            ht_m = re.search(r'Hall Ticket Number\s*\n\s*([^\n]+)', text)
            if ht_m: info["hall_ticket"] = ht_m.group(1).strip()

        if not info["participant_name"]:
            name_m = re.search(r'Participant Name\s*\n\s*([^\n]+)', text)
            if name_m: info["participant_name"] = name_m.group(1).strip()

        if not info["test_center"]:
            center_m = re.search(r'Test Center Name\s*\n\s*([^\n]+)', text)
            if center_m: info["test_center"] = center_m.group(1).strip()

        if not info["test_date"]:
            date_m = re.search(r'Test Date\s*\n\s*([^\n]+)', text)
            if date_m: info["test_date"] = date_m.group(1).strip()

        if not info["test_time"]:
            time_m = re.search(r'Test Time\s*\n\s*([^\n]+)', text)
            if time_m: info["test_time"] = time_m.group(1).strip()

        if not info["subject"]:
            subj_m = re.search(r'Subject\s*\n\s*([^\n]+)', text)
            if subj_m: info["subject"] = subj_m.group(1).strip()

    info["raw_header_text"] = "\n".join(raw_pages_text)
    return info

def parse_pdf_bytes_or_file(
    source: Union[bytes, str, Path],
    positive_marks: float = 1.0,
    negative_marks: float = 0.25,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parses candidate response sheet PDF from raw bytes or file path:
    - Extracts all questions (Q.1, Q.2 ... Q.N)
    - Identifies Correct Answer using Green (#40c64b)
    - Identifies Candidate's Chosen Answer
    - Categorizes sections
    - Computes final score and section breakdown.
    """
    doc = None
    try:
        if isinstance(source, bytes):
            logger.info(f"Opening PDF from in-memory bytes (size: {len(source)} bytes, filename: {filename or 'unknown'})")
            doc = pymupdf.open(stream=source, filetype="pdf")
        else:
            pdf_path = Path(source)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
            logger.info(f"Opening PDF from file path: {pdf_path}")
            doc = pymupdf.open(str(pdf_path))

        num_pages = len(doc)
        logger.info(f"PDF opened successfully with {num_pages} pages.")

        if num_pages == 0:
            raise ValueError("The provided PDF has 0 pages.")

        candidate_info = extract_candidate_info(doc)
        
        unidentified_page_text = None
        if any(not candidate_info.get(k) for k in ["hall_ticket", "participant_name", "test_center", "test_date", "test_time", "subject"]):
            if len(doc) > 0:
                unidentified_page_text = doc[0].get_text("text")
                try:
                    import time
                    out_dir = Path("unidentified_candidates")
                    out_dir.mkdir(exist_ok=True)
                    safe_fname = (filename or "unknown").replace("/", "_").replace("\\", "_")
                    save_path = out_dir / f"unidentified_{int(time.time())}_{safe_fname}.txt"
                    save_path.write_text(unidentified_page_text, encoding="utf-8")
                    logger.warning(f"Candidate info missing. Saved first page text to {save_path}")
                except Exception as e:
                    logger.error(f"Failed to save unidentified candidate info locally: {e}")

        logger.info(
            f"Candidate Info: name='{candidate_info['participant_name']}', "
            f"hall_ticket='{candidate_info['hall_ticket']}', "
            f"date='{candidate_info['test_date']}', "
            f"time='{candidate_info['test_time']}', "
            f"subject='{candidate_info['subject']}'"
        )

        # Step 1: Collect text spans across all pages
        all_pages_spans = []
        for page_idx in range(num_pages):
            page = doc[page_idx]
            page_dict = page.get_text("dict")
            blocks = sorted(page_dict.get("blocks", []), key=lambda b: (b.get("bbox", [0, 0])[1], b.get("bbox", [0, 0])[0]))
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                all_pages_spans.append({
                                    "text": text,
                                    "color_int": span["color"],
                                    "hex": color_to_hex(span["color"]),
                                    "bbox": span["bbox"],
                                    "page": page_idx + 1
                                })

        # if not all_pages_spans:
        #     raise ValueError("No extractable text found in PDF. Scanned or image-only PDFs are not supported directly without OCR.")

        # Step 2: Locate Question Anchors (Q.1, Q.2, ... Q.N)
        q_start_indices = []
        seen_q_nums = set()
        for idx, span in enumerate(all_pages_spans):
            m = re.match(r'^Q\.?\s*(\d+)(?:\s|\.|$)', span["text"])
            if m:
                q_num = int(m.group(1))
                if q_num not in seen_q_nums:
                    q_start_indices.append((idx, q_num))
                    seen_q_nums.add(q_num)

        # if not q_start_indices:
        #     raise ValueError("No valid question identifiers (e.g. Q.1, Q.2) found in the PDF. Please verify this is an official DigiALM / TCS iON response sheet.")

        logger.info(f"Identified {len(q_start_indices)} questions across document.")

        questions_list = []
        current_section = "General"

        for i in range(len(q_start_indices)):
            start_idx, q_num = q_start_indices[i]
            end_idx = q_start_indices[i+1][0] if i + 1 < len(q_start_indices) else len(all_pages_spans)
            q_spans = all_pages_spans[start_idx:end_idx]

            # Update Section if present
            for s in q_spans:
                clean_s = s["text"].replace("\xa0", " ")
                sec_m = re.search(r'Section\s*:\s*(.+)', clean_s)
                if sec_m:
                    current_section = sec_m.group(1).strip()

            # Extract Question ID & Chosen Option
            qid = None
            chosen_opt = None
            for s_idx, s in enumerate(q_spans):
                if "Question ID" in s["text"]:
                    combined = s["text"] + " " + (q_spans[s_idx+1]["text"] if s_idx+1 < len(q_spans) else "")
                    qid_m = re.search(r'Question ID\s*:\s*(\d+)', combined)
                    if qid_m: qid = qid_m.group(1)

                if "Chosen Option" in s["text"]:
                    combined = s["text"] + " " + (q_spans[s_idx+1]["text"] if s_idx+1 < len(q_spans) else "")
                    opt_m = re.search(r'Chosen Option\s*:\s*([1-4]|--|Not Answered)', combined, re.IGNORECASE)
                    if opt_m:
                        val = opt_m.group(1).strip()
                        chosen_opt = int(val) if val.isdigit() else None

            # Extract Options & Detect Green Correct Option
            options_dict = {}
            correct_opt = None
            question_text_parts = []
            is_in_options = False

            for s in q_spans:
                text = s["text"]

                if any(h in text for h in ["AP Vidyut Recruitment", "Hall Ticket Number", "Participant Name", "Test Center", "Test Date", "Test Time"]):
                    continue

                if text == "Ans":
                    is_in_options = True
                    continue

                opt_m = re.match(r'^([1-4])\.\s*(.*)', text)
                if opt_m:
                    opt_num = int(opt_m.group(1))
                    opt_val = opt_m.group(2).strip()
                    options_dict[opt_num] = opt_val
                    
                    if is_green_option(s["color_int"]):
                        correct_opt = opt_num
                elif is_in_options:
                    if is_green_option(s["color_int"]) and correct_opt is None:
                        if options_dict:
                            correct_opt = max(options_dict.keys())
                else:
                    if not any(k in text for k in ["Question ID", "Chosen Option", "Section :", f"Q.{q_num}"]):
                        question_text_parts.append(text)

            # Evaluate Marks
            status = "UNKNOWN"
            marks = 0.0

            if correct_opt is not None:
                if chosen_opt is None:
                    status = "UNATTEMPTED"
                    marks = 0.0
                elif chosen_opt == correct_opt:
                    status = "CORRECT"
                    marks = positive_marks
                else:
                    status = "INCORRECT"
                    marks = -negative_marks
            else:
                if chosen_opt is None:
                    status = "UNATTEMPTED"
                    marks = 0.0
                else:
                    status = "ATTEMPTED"
                    marks = 0.0

            questions_list.append({
                "question_number": q_num,
                "question_id": qid,
                "section": current_section,
                "question_text": " ".join(question_text_parts).strip(),
                "options": options_dict,
                "chosen_option": chosen_opt,
                "correct_option": correct_opt,
                "status": status,
                "marks_awarded": marks
            })

        # Summary calculations
        total_q = len(questions_list)
        correct_cnt = sum(1 for q in questions_list if q["status"] == "CORRECT")
        incorrect_cnt = sum(1 for q in questions_list if q["status"] == "INCORRECT")
        unattempted_cnt = sum(1 for q in questions_list if q["status"] == "UNATTEMPTED")
        final_score = round(sum(q["marks_awarded"] for q in questions_list), 2)
        accuracy = round((correct_cnt / (correct_cnt + incorrect_cnt) * 100), 2) if (correct_cnt + incorrect_cnt) > 0 else 0.0

        sections_summary = {}
        for q in questions_list:
            sec = q["section"]
            if sec not in sections_summary:
                sections_summary[sec] = {"total": 0, "correct": 0, "incorrect": 0, "unattempted": 0, "score": 0.0}
            sections_summary[sec]["total"] += 1
            if q["status"] == "CORRECT": sections_summary[sec]["correct"] += 1
            elif q["status"] == "INCORRECT": sections_summary[sec]["incorrect"] += 1
            elif q["status"] == "UNATTEMPTED": sections_summary[sec]["unattempted"] += 1
            sections_summary[sec]["score"] = round(sections_summary[sec]["score"] + q["marks_awarded"], 2)

        return {
            "candidate": candidate_info,
            "summary": {
                "total_questions": total_q,
                "attempted": correct_cnt + incorrect_cnt,
                "unattempted": unattempted_cnt,
                "correct": correct_cnt,
                "incorrect": incorrect_cnt,
                "accuracy_percent": accuracy,
                "positive_marking": positive_marks,
                "negative_marking": negative_marks,
                "final_score": final_score
            },
            "sections": sections_summary,
            "questions": questions_list,
            "raw_header_text": candidate_info.pop("raw_header_text", ""),
            "unidentified_page_text": unidentified_page_text
        }

    finally:
        if doc is not None:
            doc.close()
