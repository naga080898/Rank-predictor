from backend.html_parser_engine import parse_html_response_sheet
with open("/Users/naganarasimharao/.gemini/antigravity-ide/brain/8269dc55-3899-4ce6-a622-61bc739830e2/.system_generated/steps/5/content.md", "r") as f:
    html = f.read()

res = parse_html_response_sheet(html)
print(res["candidate"])
