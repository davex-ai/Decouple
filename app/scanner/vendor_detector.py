import json

def load_rules(path="data/vendor_rules.json"):
    with open(path) as f:
        return json.load(f)

def detect_vendors(file_contents, rules):
    detected = set()

    content_lower = file_contents.lower()

    for vendor, keywords in rules.items():
        for keyword in keywords:
            if keyword in content_lower:
                detected.add(vendor)

    return list(detected)