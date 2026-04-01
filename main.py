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


# Maps filenames to their structured parser functions.
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
    # Lock files (transitive deps)
    "composer.lock":     parse_composer_lock,
    "yarn.lock":         parse_yarn_lock,
    "package-lock.json": parse_package_json,   # npm lock is also JSON
    "Cargo.lock":        parse_cargo_lock,
    "Gemfile.lock":      parse_gemfile_lock,
    "go.sum":            parse_go_mod,          # go.sum follows similar patterns
}

LOCK_FILES = frozenset({
    "composer.lock", "yarn.lock", "package-lock.json",
    "Cargo.lock", "Gemfile.lock", "go.sum",
})

LOCK_IN_WEIGHTS = {
    # --- AWS ---
    "dynamodb": 5,
    "rds": 5,
    "lambda": 4,
    "secretsmanager": 3,
    "amplify": 3,
    "eks": 3,
    "ecs": 3,
    "fargate": 3,
    "sqs": 2,
    "sns": 2,
    "s3": 2,
    "route53": 2,
    "iam": 2,
    "ec2": 1,
    "vpcs": 1,
    # --- Firebase / GCP ---
    "firestore": 5,
    "bigquery": 5,
    "firebase-auth": 4,
    "cloud-functions": 4,
    "pubsub": 3,
    "gke": 3,
    "gcs": 2,
    "appengine": 3,
    # --- Azure ---
    "cosmosdb": 5,
    "active-directory": 4,
    "azure-functions": 4,
    "blob-storage": 2,
    "aks": 3,
    # --- Vercel ---
    "vercel-postgres": 5,
    "vercel-kv": 4,
    "vercel-edge": 3,
    # --- IaC & Docker ---
    "kubernetes": 4,
    "terraform": 3,
    "pulumi": 3,
    "ansible": 2,
    "docker-compose": 2,
}

REPLACEABILITY = {
    # EASY
    "s3": "easy", "gcs": "easy", "blob-storage": "easy", "firebase-storage": "easy",
    "ec2": "easy", "rds": "easy", "vpcs": "easy", "route53": "easy",
    "docker": "easy", "dockerfile": "easy", "docker-compose": "easy",
    "containerd": "easy", "moby": "easy", "alpine": "easy",
    "slim-image": "easy", "buildkit": "easy",
    "sqs": "easy", "sns": "easy", "pubsub": "easy",
    "secretsmanager": "easy", "vercel-env": "easy",
    "terraform": "easy", "pulumi": "easy", "ansible": "easy", "hcl": "easy",
    # MEDIUM
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
    # HARD
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
    "go": [
        r'["\']([^"\'.\/][^"\']+\/[^"\']+)["\']',
    ],
    "jvm": [
        r'^import\s+([a-zA-Z0-9._]+)\s*;',
    ],
    "php": [
        r'^use\s+([a-zA-Z0-9\\]+)(?:\s+as\s+\w+)?\s*;',
    ],
    "ruby": [
        r'require\s+["\']([^"\']+)["\']',
    ],
    "csharp": [
        r'^using\s+([a-zA-Z0-9.]+)\s*;',
    ],
    "hcl": [
        r'source\s*=\s*["\']([^"\'.\/][^"\']+)["\']',
    ],
}


def clean_extracted_dep(raw_dep: str) -> str:
    if not raw_dep:
        return ""
    raw_dep = raw_dep.lower().replace("@", "")
    parts = re.split(r'[\/\\.]', raw_dep)
    noise = {"com", "google", "github", "org", "net", "www", "src"}
    parts = [p for p in parts if p and p not in noise]
    return "-".join(parts)


def build_keyword_index(rules: dict) -> dict:
    """Build a flat {keyword: (vendor, service)} lookup for O(1) matching."""
    index = {}
    for vendor, meta in rules.items():
        target = meta.get("maps_to", vendor)
        for service, keywords in meta.get("services", {}).items():
            for kw in keywords:
                index[kw] = (target, service)
    return index


def match_dependency(dep: str, keyword: str) -> bool:
    dep = dep.lower()
    keyword = keyword.lower()
    return (
        dep == keyword
        or dep.startswith(keyword + "-")
        or dep.startswith("@" + keyword)
        or keyword in dep.split("/")[-1]
    )


def detect_imports(content: str, rules: dict) -> dict:
    """
    Scan raw source code for import statements and map them to (vendor, service) pairs.

    Returns:
        {(vendor, service): hit_count}
    """
    found: dict[tuple, int] = {}
    keyword_index = build_keyword_index(rules)

    for patterns in IMPORT_PATTERNS.values():
        for pattern in patterns:
            for m in re.findall(pattern, content, re.MULTILINE):
                dep_key = clean_extracted_dep(normalize(m))
                for kw, (vendor, service) in keyword_index.items():
                    if match_dependency(dep_key, kw):
                        key = (vendor, service)
                        found[key] = found.get(key, 0) + 1

    return found


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

            # --- 1. STRUCTURED PARSING ---
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
                                dep_lower == kw
                                or dep_lower.startswith(kw + "-")
                                or kw in dep_lower
                                for kw in keywords
                            ):
                                _register_service(repo_results, target_vendor, service_key)
                                weight = LOCK_IN_WEIGHTS.get(service_key, 1)
                                raw_vendor_scores[target_vendor] = (
                                    raw_vendor_scores.get(target_vendor, 0) + weight * multiplier
                                )

            # --- 2. CODE-LEVEL IMPORT DETECTION ---
            for (vendor, service_key), count in detect_imports(content, rules).items():
                _register_service(repo_results, vendor, service_key, count)
                weight = LOCK_IN_WEIGHTS.get(service_key, 1)
                raw_vendor_scores[vendor] = (
                    raw_vendor_scores.get(vendor, 0) + weight * count
                )

            # --- 3. FUZZY FALLBACK ---
            for v_name, f_score in detect_vendors(content, rules, get_weight(file)).items():
                v_mapped = rules.get(v_name, {}).get("maps_to", v_name)
                raw_vendor_scores[v_mapped] = raw_vendor_scores.get(v_mapped, 0) + f_score

        # --- 4. AGGREGATION ---
        total = sum(raw_vendor_scores.values()) or 1

        for vendor_services in repo_results["services"].values():
            for svc in vendor_services:
                diff = REPLACEABILITY.get(svc, "medium")
                repo_results["migration_difficulty"][diff] += 1

        return {
            "vendors": [v for v, s in raw_vendor_scores.items() if s / total >= 0.2],
            "scores": raw_vendor_scores,
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
    """Increment the service hit counter in repo_results."""
    repo_results["services"].setdefault(vendor, {})
    repo_results["services"][vendor][service_key] = (
        repo_results["services"][vendor].get(service_key, 0) + count
    )