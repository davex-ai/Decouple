import json

IMPORTANT_FILES = {
    "package.json": 3,
    "requirements.txt": 3,
    "docker-compose.yml": 4,
    "Dockerfile": 4,
    ".tf": 5
}

def load_rules(path="data/vendor_rules.json"):
    with open(path) as f:
        return json.load(f)

def detect_vendors(file_contents, rules, weight=1):
    scores = {}

    content = file_contents.lower()

    for vendor, levels in rules.items():
        score = 0

        for kw in levels.get("strong", []):
            if kw in content:
                score += 3

        for kw in levels.get("medium", []):
            if kw in content:
                score += 2

        for kw in levels.get("weak", []):
            if kw in content:
                score += 0.5

        if score > 0:
            scores[vendor] = score * weight

    return scores