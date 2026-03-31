from fastapi import FastAPI
from scanner.repo_loader import clone_repo
from scanner.file_finder import find_relevant_files
from scanner.parser import read_file
from scanner.vendor_detector import load_rules, detect_vendors
from scanner.scorer import compute_risk
from scanner.report import generate_report

app = FastAPI()

@app.get("/decouple/scan")
def scan_repo(repo_url: str):
    repo_path = clone_repo(repo_url)

    files = find_relevant_files(repo_path)
    rules = load_rules()

    all_vendors = set()

    for file in files:
        content = read_file(file)
        vendors = detect_vendors(content, rules)
        all_vendors.update(vendors)

    score = compute_risk(list(all_vendors))
    report = generate_report(list(all_vendors), score)

    return report