import json
import re

IMPORTANT_FILES = {
    "package.json": 3,
    "requirements.txt": 3,
    "docker-compose.yml": 4,
    "Dockerfile": 4,
    ".tf": 5
}

def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())

def load_rules(path="data/vendor_rules.json"):
    with open(path) as f:
        return json.load(f)

def detect_vendors(file_contents, rules, weight=1):
    scores = {}

    content = normalize(file_contents)

    for vendor, levels in rules.items():
        score = 0

        for level, value in [("strong", 3), ("medium", 2), ("weak", 0.5)]:
            for kw in levels.get(level, []):
                if normalize(kw) in content:
                    score += value

        if score > 0:
            scores[vendor] = score * weight

    return scores