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

    content_lower = file_contents.lower()

    for vendor, keywords in rules.items():
        for keyword in keywords:
            if keyword in content_lower:
                scores[vendor] = scores.get(vendor, 0) + weight

    return scores