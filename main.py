from fastapi import FastAPI
from scanner.repo_loader import clone_repo, safe_rmtree
from scanner.file_finder import find_relevant_files
from scanner.parser import read_file
from scanner.vendor_detector import load_rules, detect_vendors, IMPORTANT_FILES


app = FastAPI()

@app.get("/decouple/scan")
def scan_repo(repo_url: str):
    try:
        repo_path = clone_repo(repo_url)

        files = find_relevant_files(repo_path)
        rules = load_rules()

        vendor_scores = {}

        for file in files:
            content = read_file(file)
            weight = 1
            for key, val in IMPORTANT_FILES.items():
                if file.endswith(key) or file.endswith(f"{key}vars"):
                    weight = val
            scores = detect_vendors(content, rules, weight)
            for vendor, count in scores.items():
                vendor_scores[vendor] = vendor_scores.get(vendor, 0) + count

        max_score = max(vendor_scores.values(), default=1)

        final_vendors = [
        v for v, score in vendor_scores.items()
        if score / max_score >= 0.3
        ]
        # score = compute_risk(list(all_vendors))
        # report = generate_report(list(all_vendors), score)

        return {
            "vendors": final_vendors,
            "scores": vendor_scores,
            "confidence": {
                v: round(score / max_score, 2)
                for v, score in vendor_scores.items()
            }
        }
    finally:
        safe_rmtree(repo_path)
