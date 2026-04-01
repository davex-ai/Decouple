from fastapi import FastAPI
from scanner.repo_loader import clone_repo, safe_rmtree
from scanner.file_finder import find_relevant_files
from scanner.parser import (
    read_file, parse_package_json, parse_requirements, parse_composer_json,
    parse_gemfile, parse_go_mod, parse_pom_xml, parse_pubspec_yaml,
    parse_pyproject_toml, parse_cargo_toml, parse_csproj, parse_gradle,
    parse_composer_lock, parse_yarn_lock, parse_cargo_lock, parse_gemfile_lock,
)
from scanner.vendor_detector import load_rules, detect_vendors, normalize, IMPORTANT_FILES
import os
import re

app = FastAPI()


def get_weight(file):
    filename = os.path.basename(file)
    for key, val in IMPORTANT_FILES.items():
        if filename == key or filename.endswith(key):
            return val
    return 1


parser_map = {
    "package.json":      parse_package_json,
    "composer.json":     parse_composer_json,
    "Gemfile":           parse_gemfile,
    "Cargo.toml":        parse_cargo_toml,
    "go.mod":            parse_go_mod,
    "pom.xml":           parse_pom_xml,
    "build.gradle":      parse_gradle,
    "pubspec.yaml":      parse_pubspec_yaml,
    "pyproject.toml":    parse_pyproject_toml,
    "requirements.txt":  parse_requirements,
    "composer.lock":     parse_composer_lock,
    "yarn.lock":         parse_yarn_lock,
    "package-lock.json": parse_package_json,
    "Cargo.lock":        parse_cargo_lock,
    "Gemfile.lock":      parse_gemfile_lock,
    "go.sum":            parse_go_mod,
}

LOCK_FILES = frozenset({
    "composer.lock", "yarn.lock", "package-lock.json",
    "Cargo.lock", "Gemfile.lock", "go.sum",
})

LOCK_IN_WEIGHTS = {
    "dynamodb": 5, "rds": 5, "lambda": 4, "secretsmanager": 3,
    "amplify": 3, "eks": 3, "ecs": 3, "fargate": 3, "sqs": 2,
    "sns": 2, "s3": 2, "route53": 2, "iam": 2, "ec2": 1, "vpcs": 1,
    "firestore": 5, "bigquery": 5, "firebase-auth": 4, "cloud-functions": 4,
    "pubsub": 3, "gke": 3, "gcs": 2, "appengine": 3,
    "cosmosdb": 5, "active-directory": 4, "azure-functions": 4,
    "blob-storage": 2, "aks": 3,
    "vercel-postgres": 5, "vercel-kv": 4, "vercel-edge": 3,
    "kubernetes": 4, "terraform": 3, "pulumi": 3, "ansible": 2, "docker-compose": 2,
}

REPLACEABILITY = {
    "s3": "easy", "gcs": "easy", "blob-storage": "easy", "firebase-storage": "easy",
    "ec2": "easy", "rds": "easy", "vpcs": "easy", "route53": "easy",
    "docker": "easy", "dockerfile": "easy", "docker-compose": "easy",
    "containerd": "easy", "moby": "easy", "alpine": "easy",
    "slim-image": "easy", "buildkit": "easy",
    "sqs": "easy", "sns": "easy", "pubsub": "easy",
    "secretsmanager": "easy", "vercel-env": "easy",
    "terraform": "easy", "pulumi": "easy", "ansible": "easy", "hcl": "easy",
    "lambda": "medium", "cloud-functions": "medium", "firebase-functions": "medium",
    "azure-functions": "medium", "cloud-run": "medium", "appengine": "medium",
    "app-service": "medium", "eks": "medium", "ecs": "medium", "fargate": "medium",
    "gke": "medium", "aks": "medium", "kubernetes": "medium", "k8s": "medium",
    "helm": "medium", "kustomize": "medium", "amplify": "medium",
    "firebase-hosting": "medium", "firebase-config": "medium",
    "vercel-analytics": "medium", "vercel-kv": "medium", "vercel-postgres": "medium",
    "iam": "medium", "active-directory": "medium", "cloud-messaging": "medium",
    "aws": "medium", "vercel": "medium", "gcp": "medium", "azure": "medium",
    "iac": "easy",
    "dynamodb": "hard", "firestore": "hard", "cosmosdb": "hard", "bigquery": "hard",
    "firebase-auth": "hard", "firebase-admin": "hard",
    "aws-sdk": "hard", "azure-sdk": "hard", "google-cloud": "hard",
    "cdk": "hard", "cloudformation": "hard", "azure-pipelines": "hard",
    "nextjs": "hard", "vercel-edge": "hard", "firebase": "hard",
}

IMPORT_PATTERNS = {
    "js_ts": [
        r'(?:import|export)\s+(?:[\w*\s{},]*\s+from\s+)?["\']([^"\'.\/][^"\']+)["\']',
        r'(?:import|require)\s*\(\s*["\']([^"\'.\/][^"\']+)["\']\s*\)',
    ],
    "python": [
        r'^\s*import\s+([a-zA-Z0-9_]+)',
        r'^\s*from\s+([a-zA-Z0-9_]+)\s+import',
    ],
    "go": [r'["\']([^"\'.\/][^"\']+\/[^"\']+)["\']'],
    "jvm": [r'^import\s+([a-zA-Z0-9._]+)\s*;'],
    "php": [r'^use\s+([a-zA-Z0-9\\]+)(?:\s+as\s+\w+)?\s*;'],
    "ruby": [r'require\s+["\']([^"\']+)["\']'],
    "csharp": [r'^using\s+([a-zA-Z0-9.]+)\s*;'],
    "hcl": [r'source\s*=\s*["\']([^"\'.\/][^"\']+)["\']'],
}


def clean_extracted_dep(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.lower()
    if raw.startswith("@"):
        raw = raw[1:]
    parts = re.split(r'[\/\\]', raw)
    noise = {"com", "google", "github", "org", "net", "www", "src"}
    parts = [p for p in parts if p and p not in noise]
    return "-".join(parts)


def build_keyword_index(rules: dict) -> dict:
    index = {}
    for vendor, meta in rules.items():
        target = meta.get("maps_to", vendor)
        for service, keywords in meta.get("services", {}).items():
            for kw in keywords:
                index[kw.lower()] = (target, service)
    return index


def match_dependency(dep: str, keyword: str) -> bool:
    return (
        dep == keyword
        or dep.startswith(keyword + "-")
        or dep.endswith("-" + keyword)
        or keyword in dep.split("-")
    )


def detect_imports(content: str, rules: dict) -> dict:
    found: dict[tuple, int] = {}
    keyword_index = build_keyword_index(rules)
    for patterns in IMPORT_PATTERNS.values():
        for pattern in patterns:
            for m in re.findall(pattern, content, re.MULTILINE):
                dep_key = clean_extracted_dep(m)
                for kw, (vendor, service) in keyword_index.items():
                    if match_dependency(dep_key, kw):
                        key = (vendor, service)
                        found[key] = found.get(key, 0) + 1
    return found


# ─────────────────────────────────────────────────────────────────────────────
# DEBUG ENDPOINT
# Use this to diagnose why a repo returns empty results.
# GET /decouple/debug?repo_url=<url>
#
# Returns:
#   files_found       — every file the scanner picked up (relative paths)
#   per_file          — for each file: parsed deps, matched services, import hits, fuzzy hits
#   rules_loaded      — whether vendor_rules.json loaded OK
#   keyword_index_size— how many keywords are in the index
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/decouple/debug")
def debug_scan(repo_url: str):
    repo_path = None
    trace = {
        "repo_url": repo_url,
        "clone_error": None,
        "file_count": 0,
        "files_found": [],
        "rules_loaded": False,
        "rules_vendors": [],
        "keyword_index_size": 0,
        "per_file": [],
    }
    try:
        repo_path = clone_repo(repo_url)

        files = find_relevant_files(repo_path)
        trace["files_found"] = sorted(os.path.relpath(f, repo_path) for f in files)
        trace["file_count"] = len(files)

        rules = load_rules()
        trace["rules_loaded"] = True
        trace["rules_vendors"] = list(rules.keys())
        trace["keyword_index_size"] = len(build_keyword_index(rules))

        for file in files:
            filename = os.path.basename(file)
            content = read_file(file)
            entry = {
                "file": os.path.relpath(file, repo_path),
                "bytes": len(content) if content else 0,
                "has_parser": filename in parser_map,
                "structured_deps": [],
                "structured_matches": [],
                "import_hits": [],
                "fuzzy_hits": {},
            }

            if not content:
                entry["note"] = "empty/unreadable"
                trace["per_file"].append(entry)
                continue

            # Structured parsing
            parser = parser_map.get(filename)
            if not parser and file.endswith((".csproj", "packages.config")):
                parser = parse_csproj
            if parser:
                deps = parser(file)
                entry["structured_deps"] = list(deps.keys())[:40]
                for dep in deps:
                    dep_lower = dep.lower()
                    for vendor, meta in rules.items():
                        target_vendor = meta.get("maps_to", vendor)
                        for service_key, keywords in meta.get("services", {}).items():
                            if any(
                                dep_lower == kw.lower()
                                or dep_lower.startswith(kw.lower() + "-")
                                or kw.lower() in dep_lower.split("/")[-1]
                                for kw in keywords
                            ):
                                entry["structured_matches"].append(
                                    {"dep": dep, "vendor": target_vendor, "service": service_key}
                                )

            # Import detection
            import_hits = detect_imports(content, rules)
            entry["import_hits"] = [
                {"vendor": v, "service": s, "count": c}
                for (v, s), c in import_hits.items()
            ]

            # Fuzzy
            entry["fuzzy_hits"] = detect_vendors(content, rules, get_weight(file))

            trace["per_file"].append(entry)

        return trace

    except Exception as e:
        import traceback
        trace["error"] = str(e)
        trace["traceback"] = traceback.format_exc()
        return trace
    finally:
        if repo_path and isinstance(repo_path, str) and os.path.exists(repo_path):
            safe_rmtree(repo_path)


@app.get("/decouple/scan")
def scan_repo(repo_url: str):
    repo_path = None
    try:
        repo_path = clone_repo(repo_url)
        files = find_relevant_files(repo_path)
        rules = load_rules()

        repo_results = {
            "services": {},
            "lock_in_score": 0,
            "migration_difficulty": {"easy": 0, "medium": 0, "hard": 0},
        }
        raw_vendor_scores: dict[str, float] = {}

        for file in files:
            filename = os.path.basename(file)
            content = read_file(file)
            if not content:
                continue

            parser = parser_map.get(filename)
            if not parser and file.endswith((".csproj", "packages.config")):
                parser = parse_csproj

            if parser:
                deps = parser(file)
                is_lock = filename in LOCK_FILES
                multiplier = 0.2 if is_lock else 1.0
                for dep in deps:
                    dep_lower = dep.lower()
                    for vendor, meta in rules.items():
                        target_vendor = meta.get("maps_to", vendor)
                        for service_key, keywords in meta.get("services", {}).items():
                            if any(
                                dep_lower == kw.lower()
                                or dep_lower.startswith(kw.lower() + "-")
                                or kw.lower() in dep_lower.split("/")[-1]
                                for kw in keywords
                            ):
                                _register_service(repo_results, target_vendor, service_key)
                                weight = LOCK_IN_WEIGHTS.get(service_key, 1)
                                raw_vendor_scores[target_vendor] = (
                                    raw_vendor_scores.get(target_vendor, 0) + weight * multiplier
                                )

            for (vendor, service_key), count in detect_imports(content, rules).items():
                _register_service(repo_results, vendor, service_key, count)
                weight = LOCK_IN_WEIGHTS.get(service_key, 1)
                raw_vendor_scores[vendor] = (
                    raw_vendor_scores.get(vendor, 0) + weight * count
                )

            for v_name, f_score in detect_vendors(content, rules, get_weight(file)).items():
                v_mapped = rules.get(v_name, {}).get("maps_to", v_name)
                raw_vendor_scores[v_mapped] = raw_vendor_scores.get(v_mapped, 0) + f_score

        total = sum(raw_vendor_scores.values()) or 1

        for vendor_services in repo_results["services"].values():
            for svc in vendor_services:
                diff = REPLACEABILITY.get(svc, "medium")
                repo_results["migration_difficulty"][diff] += 1

        return {
            "vendors": [v for v, s in raw_vendor_scores.items() if s / total >= 0.2],
            "scores": {k: round(v, 2) for k, v in raw_vendor_scores.items()},
            "confidence": {v: round(s / total, 2) for v, s in raw_vendor_scores.items()},
            "lock_in_score": min(int(total * 1.5), 100),
            **repo_results,
        }

    finally:
        if repo_path and isinstance(repo_path, str) and os.path.exists(repo_path):
            safe_rmtree(repo_path)


def _register_service(
    repo_results: dict, vendor: str, service_key: str, count: int = 1
) -> None:
    repo_results["services"].setdefault(vendor, {})
    repo_results["services"][vendor][service_key] = (
        repo_results["services"][vendor].get(service_key, 0) + count
    )