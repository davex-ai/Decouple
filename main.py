from fastapi import FastAPI
from scanner.repo_loader import clone_repo, safe_rmtree
from scanner.file_finder import find_relevant_files
from scanner.parser import read_file, parse_package_json, parse_requirements, parse_composer_json, parse_gemfile, \
    parse_go_mod, parse_pom_xml, parse_pubspec_yaml, parse_pyproject_toml, parse_cargo_toml, parse_csproj, parse_gradle, \
    parse_composer_lock, parse_yarn_lock, parse_cargo_lock, parse_gemfile_lock
from scanner.vendor_detector import load_rules, detect_vendors, IMPORTANT_FILES


app = FastAPI()

def get_weight(file):
    for key, val in IMPORTANT_FILES.items():
        if file.endswith(key) or key in file:
            return val
    return 1

parser_map = {
        "package.json": parse_package_json,
        "composer.json": parse_composer_json,
        "Gemfile": parse_gemfile,
        "Cargo.toml": parse_cargo_toml,
        "go.mod": parse_go_mod,
        "pom.xml": parse_pom_xml,
        "build.gradle": parse_gradle,
        "pubspec.yaml": parse_pubspec_yaml,
        "pyproject.toml": parse_pyproject_toml,
        "requirements.txt": parse_requirements,

"""Lock files"""
    "composer.lock": parse_composer_lock,
    "yarn.lock": parse_yarn_lock,
    "package-lock.json": parse_package_json,  # npm lock is also JSON
    "Cargo.lock": parse_cargo_lock,
    "Gemfile.lock": parse_gemfile_lock,
    "go.sum": parse_go_mod  # go.sum often follows similar pathing patterns
    }

@app.get("/decouple/scan")
def scan_repo(repo_url: str):
    repo_path = None
    try:
        repo_path = clone_repo(repo_url)

        files = find_relevant_files(repo_path)
        rules = load_rules()

        vendor_scores = {}
        lockfiles = {
            "composer.lock", "yarn.lock", "package-lock.json",
            "Cargo.lock", "Gemfile.lock", "go.sum"
        }
        MAX_TOTAL_SCORE = 50
        for file in files:
            filename = file.split("/")[-1]
            parser = parser_map.get(filename)
            if not parser and file.endswith((".csproj", "packages.config")):
                parser = parse_csproj
            if parser:
                deps = parser(file)
                is_lockfile = filename in lockfiles
                for dep in deps:
                    for vendor, levels in rules.items():
                        for level, value in [("strong", 5), ("medium", 3)]:
                            current_score = 1 if is_lockfile else value
                            for kw in levels.get(level, []):
                                if kw in dep:
                                    if vendor_type == "platform":
                                        vendor_scores[vendor] += score
                                        vendor_scores[maps_to] += score * 0.5
                                    vendor_scores[vendor] = vendor_scores.get(vendor, 0) + current_score
                continue
            content = read_file(file)
            weight = get_weight(file)
            scores = detect_vendors(content, rules, weight)
            for vendor, count in scores.items():
                vendor_scores[vendor] = vendor_scores.get(vendor, 0) + count

            if sum(vendor_scores.values()) > MAX_TOTAL_SCORE:
                break

        total_score = sum(vendor_scores.values()) or 1

        final_vendors = [
        v for v, score in vendor_scores.items()
        if score / total_score >= 0.3
        ]
        # score = compute_risk(list(all_vendors))
        # report = generate_report(list(all_vendors), score)

        return {
            "vendors": final_vendors,
            "scores": vendor_scores,
            "confidence": {
                v: round(score / total_score, 2)
                for v, score in vendor_scores.items()
            }
        }
    finally:
        safe_rmtree(repo_path)
