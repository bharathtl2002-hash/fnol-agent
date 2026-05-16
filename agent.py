"""
Autonomous Insurance Claims Processing Agent
Extracts fields from FNOL documents, identifies missing fields,
classifies claims, and routes to the correct workflow.
"""

import json
import re
import os
import sys
from pathlib import Path


# ── Routing Rules ────────────────────────────────────────────────────────────

FRAUD_KEYWORDS = ["fraud", "inconsistent", "suspicious", "fabricated", "false"]
FAST_TRACK_THRESHOLD = 25000  # ₹25,000

MANDATORY_FIELDS = [
    "policy_number", "policyholder_name", "effective_dates",
    "incident_date", "incident_time", "incident_location", "incident_description",
    "claimant", "asset_type", "asset_id", "estimated_damage",
    "claim_type", "initial_estimate"
]


# ── Field Extraction ──────────────────────────────────────────────────────────

def extract_fields(text: str) -> dict:
    """Extract structured fields from raw FNOL text using pattern matching."""
    fields = {}
    t = text.lower()

    # Policy Information
    m = re.search(r"policy\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9\-]+)", text, re.I)
    if m: fields["policy_number"] = m.group(1).strip()

    m = re.search(r"policyholder\s*(?:name)?\s*[:\-]?\s*([A-Za-z\s]+?)(?:\n|,|\.)", text, re.I)
    if m: fields["policyholder_name"] = m.group(1).strip()

    m = re.search(r"effective\s*date[s]?\s*[:\-]?\s*([\d\/\-\s\w]+?)(?:\n|,)", text, re.I)
    if m: fields["effective_dates"] = m.group(1).strip()

    # Incident Information
    m = re.search(r"(?:incident|accident|loss)\s*date\s*[:\-]?\s*([\d\/\-\w\s,]+?)(?:\n|at|time)", text, re.I)
    if m: fields["incident_date"] = m.group(1).strip()

    m = re.search(r"(?:incident|accident)?\s*time\s*[:\-]?\s*([\d:\s]+(?:AM|PM)?)", text, re.I)
    if m: fields["incident_time"] = m.group(1).strip()

    m = re.search(r"(?:location|place|address)\s*[:\-]?\s*(.+?)(?:\n|incident|date)", text, re.I)
    if m: fields["incident_location"] = m.group(1).strip()

    m = re.search(r"(?:description|details?|narrative)\s*[:\-]?\s*(.+?)(?:\n\n|\Z)", text, re.I | re.DOTALL)
    if m: fields["incident_description"] = m.group(1).strip()[:300]

    # Involved Parties
    m = re.search(r"claimant\s*[:\-]?\s*([A-Za-z\s]+?)(?:\n|,|\.)", text, re.I)
    if m: fields["claimant"] = m.group(1).strip()

    m = re.search(r"third\s*part(?:y|ies)\s*[:\-]?\s*(.+?)(?:\n|,)", text, re.I)
    if m: fields["third_parties"] = m.group(1).strip()

    m = re.search(r"contact\s*(?:details?|info|number)?\s*[:\-]?\s*(.+?)(?:\n|,)", text, re.I)
    if m: fields["contact_details"] = m.group(1).strip()

    # Asset Details
    m = re.search(r"asset\s*type\s*[:\-]?\s*(.+?)(?:\n|,|\.)", text, re.I)
    if m: fields["asset_type"] = m.group(1).strip()

    # Also try vehicle/property as asset type
    if "asset_type" not in fields:
        m = re.search(r"(?:vehicle|car|bike|property|equipment)\s*type\s*[:\-]?\s*(.+?)(?:\n|,)", text, re.I)
        if m: fields["asset_type"] = m.group(1).strip()

    m = re.search(r"asset\s*(?:id|identifier|number)\s*[:\-]?\s*([A-Z0-9\-]+)", text, re.I)
    if m: fields["asset_id"] = m.group(1).strip()

    # Also try vehicle registration / VIN
    if "asset_id" not in fields:
        m = re.search(r"(?:registration|reg\.?|vin|vehicle\s*no\.?)\s*[:\-]?\s*([A-Z0-9\-]+)", text, re.I)
        if m: fields["asset_id"] = m.group(1).strip()

    m = re.search(r"estimated\s*damage\s*[:\-]?\s*[₹$]?\s*([\d,]+)", text, re.I)
    if m: fields["estimated_damage"] = int(m.group(1).replace(",", ""))

    # Other Mandatory Fields
    m = re.search(r"claim\s*type\s*[:\-]?\s*(.+?)(?:\n|,|\.)", text, re.I)
    if m: fields["claim_type"] = m.group(1).strip()

    m = re.search(r"attachments?\s*[:\-]?\s*(.+?)(?:\n|,|\Z)", text, re.I)
    if m: fields["attachments"] = m.group(1).strip()

    m = re.search(r"initial\s*estimate\s*[:\-]?\s*[₹$]?\s*([\d,]+)", text, re.I)
    if m: fields["initial_estimate"] = int(m.group(1).replace(",", ""))

    return fields


# ── Missing Field Detection ───────────────────────────────────────────────────

def detect_missing_fields(extracted: dict) -> list:
    """Return list of mandatory fields that are missing."""
    return [f for f in MANDATORY_FIELDS if f not in extracted or extracted[f] == ""]


# ── Routing Logic ─────────────────────────────────────────────────────────────

def route_claim(extracted: dict, missing: list, description: str = "") -> tuple[str, str]:
    """
    Returns (route, reasoning) based on the routing rules.
    Routes: Fast-track | Manual Review | Specialist Queue | Standard Processing
    """
    desc = description.lower() if description else str(extracted.get("incident_description", "")).lower()

    # Rule 1: Fraud / inconsistency keywords → Specialist Queue
    if any(kw in desc for kw in FRAUD_KEYWORDS):
        matched = [kw for kw in FRAUD_KEYWORDS if kw in desc]
        return (
            "Specialist Queue",
            f"Description contains suspicious keyword(s): {matched}. "
            "Claim flagged for specialist review due to potential fraud indicators."
        )

    # Rule 2: Missing mandatory fields → Manual Review
    if missing:
        return (
            "Manual Review",
            f"The following mandatory fields are missing: {missing}. "
            "Claim cannot be auto-processed and requires manual intervention."
        )

    # Rule 3: Low damage → Fast-track
    damage = extracted.get("estimated_damage") or extracted.get("initial_estimate")
    if damage is not None and int(damage) < FAST_TRACK_THRESHOLD:
        return (
            "Fast-track",
            f"Estimated damage ₹{damage:,} is below the ₹{FAST_TRACK_THRESHOLD:,} threshold. "
            "All mandatory fields are present. Routed to fast-track processing."
        )

    # Default → Standard Processing
    return (
        "Standard Processing",
        "All mandatory fields are present, no fraud indicators detected, "
        f"and estimated damage exceeds ₹{FAST_TRACK_THRESHOLD:,}. "
        "Routed to standard claims processing workflow."
    )


# ── Main Agent ────────────────────────────────────────────────────────────────

def process_fnol(text: str, filename: str = "unknown") -> dict:
    """Process a single FNOL document and return structured result."""
    extracted = extract_fields(text)
    missing = detect_missing_fields(extracted)
    route, reasoning = route_claim(extracted, missing)

    return {
        "filename": filename,
        "extractedFields": extracted,
        "missingFields": missing,
        "recommendedRoute": route,
        "reasoning": reasoning
    }


def process_file(filepath: str) -> dict:
    """Read a file and process it as FNOL."""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    return process_fnol(text, filename=path.name)


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        # Demo mode: process all sample docs
        sample_dir = Path("sample_docs")
        if not sample_dir.exists():
            print("Usage: python agent.py <fnol_file.txt> [file2.txt ...]")
            print("       or place files in sample_docs/ and run without args")
            return

        files = list(sample_dir.glob("*.txt")) + list(sample_dir.glob("*.pdf"))
        if not files:
            print("No .txt or .pdf files found in sample_docs/")
            return
    else:
        files = [Path(f) for f in sys.argv[1:]]

    results = []
    for f in files:
        print(f"\n{'='*60}")
        print(f"Processing: {f.name}")
        print("="*60)
        result = process_file(str(f))
        results.append(result)
        print(json.dumps(result, indent=2))

    # Save all results
    out_path = Path("outputs/results.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results saved to {out_path}")


if __name__ == "__main__":
    main()
