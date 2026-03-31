def generate_report(vendors, score):
    return {
        "vendors_detected": vendors,
        "risk_score": score,
        "risk_level": (
            "Low" if score < 30 else
            "Medium" if score < 70 else
            "High"
        )
    }