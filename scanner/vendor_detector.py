import json
import re

IMPORTANT_FILES = {
    "package.json": 3,
    "requirements.txt": 3,
    "docker-compose.yml": 4,
    "Dockerfile": 4,
    ".tf": 5,
}


def normalize(text: str) -> str:
    """Strip everything except lowercase alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def load_rules(path: str = "data/vendor_rules.json") -> dict:
    with open(path) as f:
        return json.load(f)


def detect_vendors(file_contents: str, rules: dict, weight: float = 1) -> dict:
    """
    Fuzzy detection for non-structured files.
    Scans raw text for any keywords defined in the services rules.
    Each matched service contributes once per file (no double-counting).
    """
    scores: dict[str, float] = {}
    content = normalize(file_contents)

    for vendor, meta in rules.items():
        vendor_score = 0.0
        for keywords in meta.get("services", {}).values():
            for kw in keywords:
                if normalize(kw) in content:
                    vendor_score += 2 * weight
                    break  # one hit per service per file

        if vendor_score > 0:
            scores[vendor] = vendor_score

    return scores