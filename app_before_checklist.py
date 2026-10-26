import re
from io import BytesIO

import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="AICTE SmartVerify", page_icon="📄", layout="wide")
st.title("AICTE SmartVerify")
st.caption("Evidence-based application validation and compliance assistance")
st.info(
    "Prototype only. This version extracts selectable PDF text and uses transparent "
    "pattern-matching rules. It does not use an AI model, authenticate documents, or "
    "access official AICTE records."
)

ALIASES = {
    "institution": [
        "BIET",
        "Bapuji Institute of Engineering and Technology",
        "Bapuji Institute of Engineering and Technology, Davangere",
    ],
    "course": ["AIML", "AI ML", "Artificial Intelligence and Machine Learning"],
}
FIELDS = ["Institution", "Student name", "USN", "Course", "Academic year", "Document date"]
REFERENCE_FIELDS = ["Institution", "Student name", "USN", "Course", "Academic year"]

CHECKLISTS = {
    "Change in institution details": [
        "Application or change request",
        "Supporting institution records",
        "Applicable NOC or permission, if required",
    ],
    "Change in programme/course/intake": [
        "Application or change request",
        "Programme/course details",
        "Supporting approval or permission, if required",
    ],
    "Change in faculty details": [
        "Application or change request",
        "Faculty details and supporting records",
        "Applicable qualification or appointment evidence",
    ],
    "Other approval-related change": [
        "Application or change request",
        "Supporting evidence for the requested change",
        "Applicable permission or approval, if required",
    ],
}
KEYWORDS = {
    "Application or change request": ["application", "change request", "request for change"],
    "Supporting institution records": ["institution", "college", "institute"],
    "Applicable NOC or permission, if required": ["noc", "no objection certificate", "permission"],
    "Programme/course details": ["programme", "program", "course", "intake"],
    "Supporting approval or permission, if required": ["approval", "permission", "sanction"],
    "Faculty details and supporting records": ["faculty", "staff", "teacher"],
    "Applicable qualification or appointment evidence": ["qualification", "appointment", "degree"],
    "Supporting evidence for the requested change": ["supporting document", "change", "evidence"],
}


def clean(value):
    value = str(value or "").casefold().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def canonical(field, value):
    value_clean = clean(value)
    aliases = ALIASES.get(field, [])
    if any(value_clean == clean(alias) for alias in aliases):
        return clean(aliases[1] if field == "institution" else aliases[-1])
    return value_clean


def excerpt(text, start=None, end=None, radius=100):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    if start is None:
        return text[:radius * 2]
    left, right = max(0, start - radius), min(len(text), (end or start) + radius)
    return ("…" if left else "") + text[left:right] + ("…" if right < len(text) else "")


def read_pdf(file):
    reader = PdfReader(BytesIO(file.getvalue()))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append({"page": number, "text": text})
    return pages


def find_field(patterns, pages):
    for page in pages:
        for pattern in patterns:
            match = re.search(pattern, page["text"] or "", re.IGNORECASE | re.MULTILINE)
            if match:
                value = re.sub(r"\s+", " ", match.group(1)).strip(" \t\r\n,;:")
                if value:
                    return {
                        "value": value,
                        "page": page["page"],
                        "excerpt": excerpt(page["text"], match.start(1), match.end(1)),
                        "method": "Pattern match",
                    }
    return {"value": "", "page": None, "excerpt": "", "method": "Not detected"}


PATTERNS = {
    "Institution": [
        r"\b(Bapuji Institute of Engineering and Technology(?:,?\s*Davangere)?)\b",
        r"\b(BIET)\b",
    ],
    "Student name": [
        r"(?:student name|name of the student|submitted by)\s*[:\-]?\s*([A-Z][A-Z .'-]{2,50}?)(?=\s+(?:USN|ROLL NO|REGISTRATION NO)\b|[\r\n]|$)",
        r"\bName\s*[:\-]\s*([A-Z][A-Z .'-]{2,50}?)(?=\s+(?:USN|ROLL NO)\b|[\r\n]|$)",
    ],
    "USN": [
        r"\bUSN(?:\s*(?:NO\.?|NUMBER))?\s*[:\-]?\s*([A-Z0-9]{8,15})\b",
        r"\b([1-4][A-Z]{2,4}\d{2}[A-Z]{2,4}\d{2,4})\b",
    ],
    "Course": [
        r"\b(Artificial Intelligence and Machine Learning)\b",
        r"\b(AIML)\b",
        r"\b(AI\s*ML)\b",
    ],
    "Academic year": [r"\b(20\d{2}\s*[-–/]\s*20\d{2})\b"],
    "Document date": [
        r"(?:date of issue|issued on|date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
    ],
}


def extract_fields(pages):
    return {field: find_field(PATTERNS[field], pages) for field in FIELDS}


def field_alias_key(field):
    return {"Institution": "institution", "Course": "course"}.get(field)


def compare(field, expected, actual):
    if not str(expected or "").strip():
        return "Manual Review", "No reference value provided"
    if not str(actual or "").strip():
        return "Manual Review", "Field was not detected; check the source document manually"
    key = field_alias_key(field)
    same = (
        canonical(key, expected) == canonical(key, actual)
        if key else clean(expected) == clean(actual)
    )
    return (
        ("Matched", "Values match after configured normalisation")
        if same else
        ("Mismatch Found", "Reference and extracted values differ; verify both sources")
    )


st.subheader("1. Application details")
col1, col2 = st.columns([2, 1])
with col1:
    change_type = st.selectbox("Application category", list(CHECKLISTS))
with col2:
    application_id = st.text_input("Application ID (optional)", placeholder="DEMO-2026-001")

files = st.file_uploader(
    "Upload supporting PDF documents",
    type=["pdf"],
    accept_multiple_files=True,
    help="PDFs must contain selectable text. Scanned-document OCR is not implemented.",
)

with st.expander("Optional: enter reference details for comparison"):
    st.caption("These values are user-provided and are not verified against official records.")
    expected = {
        "Institution": st.text_input("Expected institution name", placeholder="BIET"),
        "Student name": st.text_input("Expected student name"),
        "USN": st.text_input("Expected USN"),
        "Course": st.text_input("Expected course", placeholder="AIML"),
        "Academic year": st.text_input("Expected academic year", placeholder="2025-2026"),
    }

if st.button("Analyse documents", type="primary", width="stretch"):
    if not files:
        st.error("Upload at least one PDF to begin.")
        st.stop()

    records, errors = [], []
    for file in files:
        try:
            pages = read_pdf(file)
            text = "\n".join(p["text"] for p in pages)
            records.append({
                "filename": file.name,
                "pages": pages,
                "text": text,
                "readable": bool(text.strip()),
                "fields": extract_fields(pages) if text.strip() else {
                    field: {"value": "", "page": None, "excerpt": "", "method": "No selectable text"}
                    for field in FIELDS
                },
            })
        except Exception as exc:
            errors.append(f"{file.name}: {exc}")

    for error in errors:
        st.error(error)
    if not records:
        st.error("No documents could be read.")
        st.stop()

    for record in records:
        if not record["readable"]:
            st.warning(
                f"{record['filename']}: no selectable text was found. It may be scanned/image-only; "
                "this prototype cannot OCR it yet."
            )

    st.subheader("2. Extracted information with evidence")
    evidence_rows = []
    for record in records:
        for field in FIELDS:
            item = record["fields"][field]
            evidence_rows.append({
                "Document": record["filename"],
                "Field": field,
                "Extracted value": item["value"] or "Not detected",
                "Page": item["page"] or "—",
                "Extraction method": item["method"],
                "Evidence excerpt": item["excerpt"] or "No matching text excerpt",
            })
    evidence_df = pd.DataFrame(evidence_rows)
    st.dataframe(evidence_df, width="stretch", hide_index=True)

    st.subheader("3. Reference comparison")
    comparison_rows = []
    for record in records:
        for field in REFERENCE_FIELDS:
            item = record["fields"][field]
            status, reason = compare(field, expected[field], item["value"])
            comparison_rows.append({
                "Document": record["filename"],
                "Field": field,
                "Reference value": expected[field].strip() or "Not provided",
                "Extracted value": item["value"] or "Not detected",
                "Status": status,
                "Reason": reason,
                "Page": item["page"] or "—",
                "Evidence excerpt": item["excerpt"] or "No matching text excerpt",
            })
    comparison_df = pd.DataFrame(comparison_rows)
    st.dataframe(comparison_df, width="stretch", hide_index=True)

    st.subheader("4. Cross-document consistency")
    cross_rows = []
    for field in REFERENCE_FIELDS + ["Document date"]:
        values = []
        for record in records:
            item = record["fields"][field]
            if item["value"]:
                key = field_alias_key(field)
                norm = canonical(key, item["value"]) if key else clean(item["value"])
                values.append((record["filename"], item["value"], norm, item["page"], item["excerpt"]))
        if len(values) < 2:
            status, reason = "Manual Review", "Fewer than two documents contain a detected value"
        elif len({v[2] for v in values}) == 1:
            status, reason = "Consistent", "Detected values agree after configured normalisation"
        else:
            status, reason = "Mismatch Found", "Different values were extracted; confirm whether the difference is legitimate"
        cross_rows.append({
            "Field": field,
            "Documents with value": len(values),
            "Status": status,
            "Reason": reason,
            "Values and evidence": " | ".join(
                f"{name} (page {page}): {value} — {source}"
                for name, value, _, page, source in values
            ) or "No values detected",
        })
    cross_df = pd.DataFrame(cross_rows)
    st.dataframe(cross_df, width="stretch", hide_index=True)

    st.subheader("5. Configurable checklist")
    combined = clean("\n".join(r["text"] for r in records))
    checklist_rows = []
    for item in CHECKLISTS[change_type]:
        matches = [word for word in KEYWORDS.get(item, []) if clean(word) in combined]
        checklist_rows.append({
            "Checklist item": item,
            "Keyword indicator": "Keyword found" if matches else "Not detected",
            "Matched keywords": ", ".join(matches) or "None",
            "Interpretation": "Inspect source evidence to confirm" if matches else
                "Manual review: item may be absent or worded differently",
        })
    checklist_df = pd.DataFrame(checklist_rows)
    st.dataframe(checklist_df, width="stretch", hide_index=True)
    st.caption(
        "These checklist items and keywords are illustrative, not an official AICTE checklist. "
        "Keyword presence does not prove a requirement is satisfied."
    )

    st.subheader("6. Overall result")
    ref_mismatches = int((comparison_df["Status"] == "Mismatch Found").sum())
    ref_reviews = int((comparison_df["Status"] == "Manual Review").sum())
    cross_mismatches = int((cross_df["Status"] == "Mismatch Found").sum())
    unreadable = sum(not r["readable"] for r in records)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reference mismatches", ref_mismatches)
    m2.metric("Manual review fields", ref_reviews)
    m3.metric("Cross-document mismatches", cross_mismatches)
    m4.metric("Unreadable PDFs", unreadable)

    if ref_mismatches or cross_mismatches:
        st.error("Potential discrepancies detected. Review the evidence above. A discrepancy is not proof of fraud.")
    elif ref_reviews or unreadable or any(row["Status"] == "Manual Review" for row in cross_rows):
        st.warning("Manual review is required. No-mismatch results do not establish authenticity or compliance.")
    else:
        st.success("No discrepancy was detected by the checks performed. This is not official verification.")

    st.subheader("7. Download reports")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Evidence report (CSV)", evidence_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_evidence_report.csv", "text/csv", width="stretch"
        )
    with c2:
        st.download_button(
            "Comparison report (CSV)", comparison_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_comparison_report.csv", "text/csv", width="stretch"
        )
    with c3:
        st.download_button(
            "Consistency report (CSV)", cross_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_consistency_report.csv", "text/csv", width="stretch"
        )

    st.subheader("8. Source text")
    for record in records:
        with st.expander(f"View extracted text: {record['filename']}"):
            if not record["readable"]:
                st.warning("No selectable text found.")
            else:
                for page in record["pages"]:
                    with st.expander(f"Page {page['page']}"):
                        st.text(page["text"] or "[No text extracted from this page]")

st.divider()
st.caption(
    "Implemented: selectable-text PDF extraction, pattern-based field extraction, page/excerpt evidence, "
    "configured alias normalisation, reference comparison, cross-document consistency checks and CSV reports. "
    "Not implemented: OCR, machine-learning inference, official AICTE rule integration, issuer/API verification, "
    "forgery detection, user accounts, role-based access control or persistent audit logging."
)
