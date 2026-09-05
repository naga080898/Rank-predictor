import re
from bs4 import BeautifulSoup

html = """
<table cellspacing="0" cellpadding="0" class="menu-tbl"  style="float: right;margin-bottom: 5px;margin-top: 5px;width: 29%"><tr><td align="right">Question ID :</td><td class="bold">441009774085</td></tr><td align="right">Chosen Option :</td><td class="bold">1</td></table>
"""
status_table = BeautifulSoup(html, 'html.parser').find('table')
text = status_table.get_text(separator=" ", strip=True)
print(text)

q_id = None
chosen_opt = None
if "Question ID" in text:
    m = re.search(r'Question ID\s*:?\s*(\d+)', text)
    if m: q_id = m.group(1)
if "Chosen Option" in text:
    m = re.search(r'Chosen Option\s*:?\s*([1-4]|--|Not Answered)', text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        chosen_opt = int(val) if val.isdigit() else None
        
print("QID:", q_id)
print("OPT:", chosen_opt)

