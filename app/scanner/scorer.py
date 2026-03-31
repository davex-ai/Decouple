def compute_risk(vendors):
    score = 0

    if len(vendors) == 1:
        score += 40

    if "aws" in vendors:
        score += 20
    if "gcp" in vendors:
        score += 15
    if "azure" in vendors:
        score += 18

    if "firebase" in vendors:
        score += 25
    if "vercel" in vendors:
        score += 15
    if "docker" in vendors:
        score -= 10
    if "iac" in vendors:
        score -= 15

    return max(0, min(score, 100))
