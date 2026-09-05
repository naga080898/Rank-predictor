import re
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def parse_html_response_sheet(
    html_content: str,
    positive_marks: float = 1.0,
    negative_marks: float = 0.25
) -> Dict[str, Any]:
    """
    Parses a DigiALM / TCS iON HTML response sheet to extract scores and candidate info.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 1. Extract Candidate Info
    candidate_info = {
        "hall_ticket": "",
        "participant_name": "",
        "test_center": "",
        "test_date": "",
        "test_time": "",
        "subject": ""
    }
    
    # Search for all table rows and match headers
    for tr in soup.find_all('tr'):
        tds = tr.find_all(['td', 'th'])
        if len(tds) >= 2:
            label = tds[0].get_text(strip=True).replace(':', '').strip()
            val = tds[1].get_text(strip=True)
            
            if "Roll Number" in label or "Participant ID" in label or "Hall Ticket" in label:
                candidate_info["hall_ticket"] = val
            elif "Participant Name" in label or "Candidate Name" in label:
                candidate_info["participant_name"] = val
            elif "Test Center Name" in label:
                candidate_info["test_center"] = val
            elif "Test Date" in label:
                candidate_info["test_date"] = val
            elif "Test Time" in label:
                candidate_info["test_time"] = val
            elif "Subject" in label:
                candidate_info["subject"] = val

    # 2. Extract Questions
    questions_list = []
    
    # Typical TCS iON structure uses tables for each question
    question_panels = soup.find_all('div', class_='question-pnl')
    if not question_panels:
        # Fallback to tables with specific classes if div isn't found
        question_panels = soup.find_all('table', class_='questionRowTbl')

    current_section = "General"
    
    # Sometimes sections are in headers
    sections = soup.find_all('div', class_='section-cntnr')
    
    for idx, panel in enumerate(question_panels):
        # Determine section
        # Look backwards for section headers
        sec_header = panel.find_previous('div', class_='section-name')
        if sec_header:
            current_section = sec_header.get_text(strip=True)
        
        q_num = idx + 1
        q_id = None
        chosen_opt = None
        correct_opt = None
        options_dict = {}
        question_text = ""
        
        # Get question ID and Chosen Option from the status table
        status_table = panel.find('table', class_='menu-tbl')
        if status_table:
            text = status_table.get_text(separator=" ", strip=True)
            if "Question ID" in text:
                m = re.search(r'Question ID\s*:?\s*(\d+)', text)
                if m: q_id = m.group(1)
            if "Chosen Option" in text:
                m = re.search(r'Chosen Option\s*:?\s*([1-4]|--|Not Answered)', text, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    chosen_opt = int(val) if val.isdigit() else None
                        
        # Extract question text and options
        # Options usually in a table with class 'questionRowTbl' or similar inside the panel
        options_table = panel.find('table', class_='questionRowTbl')
        if not options_table:
            options_table = panel
            
        if options_table:
            # First row is usually the question text
            tds = options_table.find_all('td')
            if tds:
                # Naive attempt: collect text until we hit option rows
                question_text_parts = []
                for td in tds:
                    txt = td.get_text(strip=True)
                    # Options often start with "1." or "2." or have specific classes
                    if re.match(r'^[1-4]\.', txt) or td.find('img', alt=re.compile(r'tick', re.I)):
                        break
                    question_text_parts.append(txt)
                question_text = " ".join(question_text_parts[:2]).strip() # Just grab a snippet
                
            # Find options
            opt_rows = options_table.find_all('tr')
            opt_counter = 1
            for tr in opt_rows:
                tds = tr.find_all('td')
                if not tds:
                    continue
                    
                # The correct option often has a class 'rightAns' or an image with alt="Tick"
                is_correct = False
                if 'rightAns' in tr.get('class', []) or tr.find(class_='rightAns'):
                    is_correct = True
                elif tr.find('img', src=re.compile(r'tick', re.I)):
                    is_correct = True
                    
                # Get the text from the last TD to avoid prefixing with "Ans" from earlier columns
                opt_td = tds[-1]
                row_text = opt_td.get_text(strip=True)
                
                # Try to extract "1. option text"
                m = re.match(r'^([1-4])\.\s*(.*)', row_text)
                if m:
                    opt_num = int(m.group(1))
                    options_dict[opt_num] = m.group(2)
                    if is_correct:
                        correct_opt = opt_num
                else:
                    # Alternative option structure
                    if len(tds) >= 2 and tds[-2].get_text(strip=True).isdigit():
                        opt_num = int(tds[-2].get_text(strip=True))
                        options_dict[opt_num] = opt_td.get_text(strip=True)
                        if is_correct:
                            correct_opt = opt_num
                            
        # If we couldn't parse options well, fallback guessing
        if not options_dict:
            options_dict = {1: "Option 1", 2: "Option 2", 3: "Option 3", 4: "Option 4"}
            
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
            else:
                status = "ATTEMPTED"

        questions_list.append({
            "question_number": q_num,
            "question_id": q_id,
            "section": current_section,
            "question_text": question_text[:150] + "..." if len(question_text) > 150 else question_text,
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
        "raw_header_text": ""
    }
