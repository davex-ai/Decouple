from fastapi import FastAPI
from scanner.repo_loader import clone_repo, safe_rmtree
from scanner.file_finder import find_relevant_files
from scanner.parser import read_file, parse_package_json, parse_requirements, parse_composer_json, parse_gemfile, \
    parse_go_mod, parse_pom_xml, parse_pubspec_yaml, parse_pyproject_toml, parse_cargo_toml, parse_csproj, parse_gradle, \
    parse_composer_lock, parse_yarn_lock, parse_cargo_lock, parse_gemfile_lock
from scanner.vendor_detector import load_rules, detect_vendors, IMPORTANT_FILES
import os

app = FastAPI()

def get_weight(file):
    filename = os.path.basename(file)
    for key, val in IMPORTANT_FILES.items():
        if filename == key or filename.endswith(key):
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

LOCK_IN_WEIGHTS = {
    # --- AWS ---
    "dynamodb": 5,        # Data lock-in
    "rds": 5,             # Managed DB
    "lambda": 4,          # Serverless logic
    "secretsmanager": 3,  # Secret orchestration
    "amplify": 3,         # High-level framework
    "eks": 3,             # K8s flavor
    "ecs": 3,
    "fargate": 3,
    "sqs": 2,             # Queueing logic
    "sns": 2,
    "s3": 2,              # Blob storage
    "route53": 2,         # DNS
    "iam": 2,             # Policy logic
    "ec2": 1,             # Standard VM
    "vpcs": 1,

    # --- Firebase / GCP ---
    "firestore": 5,       # Hard data lock-in
    "bigquery": 5,        # Warehouse lock-in
    "firebase-auth": 4,   # User identity
    "cloud-functions": 4, # Serverless logic
    "pubsub": 3,          # Messaging
    "gke": 3,             # K8s flavor
    "gcs": 2,             # Storage
    "appengine": 3,

    # --- Azure ---
    "cosmosdb": 5,        # Database
    "active-directory": 4,# Identity
    "azure-functions": 4, # Serverless
    "blob-storage": 2,
    "aks": 3,

    # --- Vercel ---
    "vercel-postgres": 5, # DB
    "vercel-kv": 4,       # Data
    "vercel-edge": 3,     # Logic

    # --- IaC & Docker ---
    "kubernetes": 4,      # Heavy infra orchestration
    "terraform": 3,       # Logic in HCL
    "pulumi": 3,
    "ansible": 2,
    "docker-compose": 2
}

REPLACEABILITY = {
    # EASY: Infrastructure standards or easily swappable storage
    "s3": "easy", "gcs": "easy", "blob-storage": "easy", "firebase-storage": "easy",
    "ec2": "easy", "rds": "easy", "vpcs": "easy", "route53": "easy",
    "docker": "easy", "dockerfile": "easy", "docker-compose": "easy", "containerd": "easy", "moby": "easy",
    "alpine": "easy", "slim-image": "easy", "buildkit": "easy",
    "sqs": "easy", "sns": "easy", "pubsub": "easy",
    "secretsmanager": "easy", "vercel-env": "easy",
    "terraform": "easy", "pulumi": "easy", "ansible": "easy", "hcl": "easy",

    # MEDIUM: Serverless logic or specialized managed services
    "lambda": "medium", "cloud-functions": "medium", "firebase-functions": "medium",
    "azure-functions": "medium", "cloud-run": "medium", "appengine": "medium", "app-service": "medium",
    "eks": "medium", "ecs": "medium", "fargate": "medium", "gke": "medium", "aks": "medium",
    "kubernetes": "medium", "k8s": "medium", "helm": "medium", "kustomize": "medium",
    "amplify": "medium", "firebase-hosting": "medium", "firebase-config": "medium",
    "vercel-analytics": "medium", "vercel-kv": "medium", "vercel-postgres": "medium",
    "iam": "medium", "active-directory": "medium", "cloud-messaging": "medium",

    # HARD: Proprietary SDKs, non-relational DBs, and Frameworks
    "dynamodb": "hard", "firestore": "hard", "cosmosdb": "hard", "bigquery": "hard",
    "firebase-auth": "hard", "firebase-admin": "hard",
    "aws-sdk": "hard", "azure-sdk": "hard", "google-cloud": "hard",
    "cdk": "hard", "cloudformation": "hard", "azure-pipelines": "hard",
    "nextjs": "hard", "vercel-edge": "hard",

    # WEAK: General platform mentions
    "aws": "medium", "firebase": "hard", "vercel": "medium",
    "gcp": "medium", "azure": "medium", "iac": "easy"
}


def match_dependency(dep, keyword):
    dep = dep.lower()
    keyword = keyword.lower()

    return (
        dep == keyword or
        dep.startswith(keyword + "-") or
        dep.startswith("@" + keyword) or
        keyword in dep.split("/")[-1]
    )

@app.get("/decouple/scan")
def scan_repo(repo_url: str):
    repo_path = None
    try:
        repo_path = clone_repo(repo_url)
        files = find_relevant_files(repo_path)
        rules = load_rules()

        # Data structures for the final output
        repo_results = {
            "services": {},
            "lock_in_score": 0,
            "migration_difficulty": {"easy": 0, "medium": 0, "hard": 0}
        }

        raw_vendor_scores = {}
        lockfiles = {"composer.lock", "yarn.lock", "package-lock.json", "Cargo.lock", "Gemfile.lock", "go.sum"}

        for file in files:
            filename = os.path.basename(file)
            parser = parser_map.get(filename)
            if not parser and file.endswith((".csproj", "packages.config")):
                parser = parse_csproj

            if parser:
                deps = parser(file)
                is_lock = filename in lockfiles

                for dep in deps.keys():
                    dep_lower = dep.lower()

                    for vendor, meta in rules.items():
                        target_vendor = meta.get("maps_to", vendor)

                        if target_vendor not in repo_results["services"]:
                            repo_results["services"][target_vendor] = {}
                        if target_vendor not in raw_vendor_scores:
                            raw_vendor_scores[target_vendor] = 0

                        for service_key, weight in LOCK_IN_WEIGHTS.items():
                            if match_dependency(dep_lower, service_key) :
                                repo_results["services"][target_vendor][service_key] = \
                                    repo_results["services"][target_vendor].get(service_key, 0) + 1

                                points = weight * (0.2 if is_lock else 1.0)
                                raw_vendor_scores[target_vendor] += points
                continue

            content = read_file(file)
            weight = get_weight(file)
            scores = detect_vendors(content, rules, weight)
            for vendor, count in scores.items():
                v = rules.get(vendor, {}).get("maps_to", vendor)
                raw_vendor_scores[v] = raw_vendor_scores.get(v, 0) + count

        total_raw_points = sum(raw_vendor_scores.values())

        repo_results["lock_in_score"] = min(int(total_raw_points * 2), 100)

        for vendor_services in repo_results["services"].values():
            for service in vendor_services.keys():
                diff_level = REPLACEABILITY.get(service, "medium")
                repo_results["migration_difficulty"][diff_level] += 1

        return repo_results

    finally:
        if repo_path:
            safe_rmtree(repo_path)

