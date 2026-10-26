
import re
import hashlib
from io import BytesIO
from datetime import datetime, date

import pandas as pd
import streamlit as st
from pypdf import PdfReader


# --------------------------------------------------
# 1. APP CONFIGURATION AND DESIGN
# --------------------------------------------------

st.set_page_config(
    page_title="SmartVerify | Application Validation",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {
    background: #F4F7FB;
    color: #25364A;
}
.block-container {
    max-width: 1500px;
    padding: 1.8rem 2rem 3rem;
}
[data-testid="stHeader"] {
    background: #FFFFFF;
}
[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #DCE5EF;
}
h1, h2, h3 {
    color: #17365D !important;
    font-weight: 750 !important;
}
p, label {
    font-size: 16px;
}
.sv-banner {
    background: linear-gradient(120deg, #143454, #087F8C);
    padding: 30px 32px;
    border-radius: 17px;
    margin-bottom: 20px;
}
.sv-banner h1 {
    color: white !important;
    font-size: 2.35rem !important;
    margin: 0;
}
.sv-banner p {
    color: #E3FAFA !important;
    font-size: 17px;
    margin: 10px 0 0;
}
.sv-section {
    background: white;
    border: 1px solid #DCE5EF;
    border-left: 5px solid #078B97;
    border-radius: 13px;
    padding: 18px 22px;
    margin: 22px 0 15px;
    box-shadow: 0 3px 12px rgba(20, 50, 80, .04);
}
.sv-section h3 {
    font-size: 1.35rem !important;
    margin: 0;
}
.sv-section p {
    color: #61758D;
    margin: 7px 0 0;
}
div.stButton > button,
div.stDownloadButton > button {
    background: #087F8C;
    color: white !important;
    border: 1px solid #087F8C;
    border-radius: 9px;
    font-weight: 650;
    min-height: 44px;
}
div.stButton > button:hover,
div.stDownloadButton > button:hover {
    background: #066773;
    border-color: #066773;
}
div[data-testid="stFileUploader"],
div[data-testid="stExpander"] {
    background: white;
    border: 1px solid #DCE5EF;
    border-radius: 12px;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #DCE5EF;
    border-top: 4px solid #078B97;
    border-radius: 12px;
    padding: 15px;
}
div[data-testid="stMetricLabel"] {
    color: #61758D;
}
div[data-testid="stMetricValue"] {
    color: #17365D;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #DCE5EF;
    border-radius: 10px;
}
hr {
    border-color: #DCE5EF;
}
</style>
""", unsafe_allow_html=True)


def heading(number, title, description=""):
    desc = f"<p>{description}</p>" if description else ""
    st.markdown(
        f'<div class="sv-section"><h3>{number} &nbsp; {title}</h3>'
        f'{desc}</div>',
        unsafe_allow_html=True,
    )


st.markdown("""
<div class="sv-banner">
    <h1>🛡️ SmartVerify</h1>
    <p>AICTE application validation and regulatory compliance
    decision-support prototype</p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# 2. CONFIGURABLE PROTOTYPE CHECKLISTS
# These are illustrative, NOT official AICTE rules.
# --------------------------------------------------

CHECKLISTS = {
    "Extension of Approval (EoA)": [
        {
            "item": "Application and institution identification",
            "keywords": ["application", "institution", "college", "institute"],
            "why": "Look for application and institution-identification evidence.",
        },
        {
            "item": "Affidavit or undertaking",
            "keywords": ["affidavit", "undertaking", "declaration"],
            "why": "Look for an affidavit, undertaking, or declaration.",
        },
        {
            "item": "Accreditation or certification evidence",
            "keywords": ["accreditation", "accredited", "certification", "certificate"],
            "why": "Look for accreditation or certification references where applicable.",
        },
        {
            "item": "NOC or permission evidence",
            "keywords": ["noc", "no objection certificate", "permission"],
            "why": "Look for NOC or permission evidence where applicable.",
        },
        {
            "item": "Faculty and programme information",
            "keywords": ["faculty", "programme", "program", "course", "intake"],
            "why": "Look for faculty or programme-related information.",
        },
        {
            "item": "Approval or compliance history",
            "keywords": ["approval", "extension of approval", "compliance", "deficiency"],
            "why": "Look for references to approval or compliance records.",
        },
    ],
    "Change in institution details": [
        {
            "item": "Application or change request",
            "keywords": ["application", "change request", "request for change"],
            "why": "Look for evidence of the requested change.",
        },
        {
            "item": "Institution identity and updated details",
            "keywords": ["institution", "college", "institute", "address", "name"],
            "why": "Look for institution identity and updated details.",
        },
        {
            "item": "Supporting permission or NOC",
            "keywords": ["noc", "permission", "no objection certificate", "approval"],
            "why": "Look for supporting permission where applicable.",
        },
    ],
    "Change in programme/course/intake": [
        {
            "item": "Application or change request",
            "keywords": ["application", "change request", "request for change"],
            "why": "Look for evidence of the requested change.",
        },
        {
            "item": "Programme, course or intake details",
            "keywords": ["programme", "program", "course", "intake", "seats"],
            "why": "Look for the programme and intake information.",
        },
        {
            "item": "Supporting approval or permission",
            "keywords": ["approval", "permission", "sanction", "noc"],
            "why": "Look for supporting approval where applicable.",
        },
    ],
    "Change in faculty details": [
        {
            "item": "Application or change request",
            "keywords": ["application", "change request"],
            "why": "Look for evidence of the requested change.",
        },
        {
            "item": "Faculty and appointment details",
            "keywords": ["faculty", "staff", "teacher", "appointment"],
            "why": "Look for faculty and appointment information.",
        },
        {
            "item": "Qualification evidence",
            "keywords": ["qualification", "degree", "certificate", "education"],
            "why": "Look for qualification evidence.",
        },
    ],
    "Other approval-related change": [
        {
            "item": "Application or change request",
            "keywords": ["application", "change request", "request"],
            "why": "Look for evidence of the requested change.",
        },
        {
            "item": "Supporting evidence",
            "keywords": ["supporting document", "evidence", "certificate", "record"],
            "why": "Look for supporting evidence.",
        },
        {
            "item": "Permission or approval evidence",
            "keywords": ["permission", "approval", "sanction", "noc"],
            "why": "Look for approval evidence where applicable.",
        },
    ],
}


FIELDS = [
    "Institution",
    "Student name",
    "USN",
    "Course",
    "Academic year",
    "Document date",
]

REFERENCE_FIELDS = [
    "Institution",
    "Student name",
    "USN",
    "Course",
    "Academic year",
]

ALIASES = {
    "institution": [
        "BIET",
        "Bapuji Institute of Engineering and Technology",
        "Bapuji Institute of Engineering and Technology, Davangere",
    ],
    "course": [
        "AIML",
        "AI ML",
        "Artificial Intelligence and Machine Learning",
    ],
}


# --------------------------------------------------
# 3. EXTRACTION AND COMPARISON HELPERS
# --------------------------------------------------

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
    "Academic year": [
        r"\b(20\d{2}\s*[-–/]\s*20\d{2})\b",
    ],
    "Document date": [
        r"(?:date of issue|issued on|date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    ],
}


def clean(value):
    value = str(value or "").casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonical(field, value):
    normalized = clean(value)
    aliases = ALIASES.get(field, [])

    if any(normalized == clean(alias) for alias in aliases):
        return clean(aliases[1] if field == "institution" else aliases[-1])

    return normalized


def make_excerpt(text, start=None, end=None, radius=100):
    text = re.sub(r"\s+", " ", text or "").strip()

    if not text:
        return ""

    if start is None:
        return text[:radius * 2]

    left = max(0, start - radius)
    right = min(len(text), (end or start) + radius)

    return (
        ("…" if left else "")
        + text[left:right]
        + ("…" if right < len(text) else "")
    )


def read_pdf(uploaded_file):
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
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
            match = re.search(
                pattern,
                page["text"],
                re.IGNORECASE | re.MULTILINE,
            )

            if match:
                value = re.sub(
                    r"\s+", " ", match.group(1)
                ).strip(" \t\r\n,;:")

                if value:
                    return {
                        "value": value,
                        "page": page["page"],
                        "excerpt": make_excerpt(
                            page["text"],
                            match.start(1),
                            match.end(1),
                        ),
                        "method": "Pattern match",
                    }

    return {
        "value": "",
        "page": None,
        "excerpt": "",
        "method": "Not detected",
    }


def extract_fields(pages):
    return {
        field: find_field(PATTERNS[field], pages)
        for field in FIELDS
    }


def compare_values(field, reference, extracted):
    if not str(reference or "").strip():
        return "Not checked", "No reference value was provided."

    if not str(extracted or "").strip():
        return "Manual review", "No value was extracted from the document."

    alias_key = {
        "Institution": "institution",
        "Course": "course",
    }.get(field)

    if alias_key:
        same = canonical(alias_key, reference) == canonical(alias_key, extracted)
    else:
        same = clean(reference) == clean(extracted)

    if same:
        return "Matched", "Values match after configured normalization."

    return "Mismatch", "Reference and extracted values differ."


def expiry_check(text):
    patterns = [
        r"(?:valid\s+until|valid\s+through|expiry\s+date|expiration\s+date|expires\s+on)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)

        if match:
            raw_date = match.group(1)

            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y"):
                try:
                    parsed = datetime.strptime(raw_date, fmt).date()
                    if parsed < date.today():
                        return raw_date, "Potentially expired"
                    return raw_date, "Date is not past"
                except ValueError:
                    continue

            return raw_date, "Date found; manual review required"

    return "", "No explicit expiry date detected"


def analyze_documents(uploaded_files, category, reference):
    records = []
    errors = []

    for uploaded_file in uploaded_files:
        try:
            content = uploaded_file.getvalue()
            pages = read_pdf(uploaded_file)
            full_text = "\n".join(page["text"] for page in pages)
            digest = hashlib.sha256(content).hexdigest()

            records.append({
                "filename": uploaded_file.name,
                "size": len(content),
                "sha256": digest,
                "pages": pages,
                "text": full_text,
                "readable": bool(full_text.strip()),
                "fields": extract_fields(pages) if full_text.strip() else {
                    field: {
                        "value": "",
                        "page": None,
                        "excerpt": "",
                        "method": "No selectable text",
                    }
                    for field in FIELDS
                },
                "expiry": expiry_check(full_text),
            })

        except Exception as exc:
            errors.append(f"{uploaded_file.name}: {exc}")

    if not records:
        return None, errors

    evidence_rows = []
    comparison_rows = []
    cross_rows = []
    checklist_rows = []
    duplicate_rows = []

    # Field extraction evidence
    for record in records:
        for field in FIELDS:
            item = record["fields"][field]

            evidence_rows.append({
                "Document": record["filename"],
                "Field": field,
                "Extracted value": item["value"] or "Not detected",
                "Page": item["page"] or "—",
                "Method": item["method"],
                "Evidence": item["excerpt"] or "No matching excerpt",
            })

    # Compare only against the reference values explicitly supplied
    for record in records:
        for field in REFERENCE_FIELDS:
            reference_value = reference.get(field, "").strip()
            extracted = record["fields"][field]
            status, reason = compare_values(
                field,
                reference_value,
                extracted["value"],
            )

            comparison_rows.append({
                "Document": record["filename"],
                "Field": field,
                "Reference source": "User-entered reference record",
                "Reference value": reference_value or "Not provided",
                "Extracted value": extracted["value"] or "Not detected",
                "Status": status,
                "Reason": reason,
                "Page": extracted["page"] or "—",
                "Evidence": extracted["excerpt"] or "No matching excerpt",
            })

    # Cross-document comparison
    for field in REFERENCE_FIELDS + ["Document date"]:
        values = []

        for record in records:
            item = record["fields"][field]

            if item["value"]:
                alias_key = {
                    "Institution": "institution",
                    "Course": "course",
                }.get(field)

                normalized = (
                    canonical(alias_key, item["value"])
                    if alias_key
                    else clean(item["value"])
                )

                values.append({
                    "document": record["filename"],
                    "value": item["value"],
                    "normalized": normalized,
                    "page": item["page"],
                    "excerpt": item["excerpt"],
                })

        if len(records) < 2:
            status = "Not applicable"
            reason = "Upload at least two documents for cross-document comparison."
        elif len(values) < 2:
            status = "Manual review"
            reason = "Fewer than two documents contain this detected field."
        elif len({value["normalized"] for value in values}) == 1:
            status = "Consistent"
            reason = "Detected values agree after configured normalization."
        else:
            status = "Mismatch"
            reason = "Values differ between documents; check the evidence."

        cross_rows.append({
            "Field": field,
            "Documents with value": len(values),
            "Status": status,
            "Reason": reason,
            "Values and evidence": " | ".join(
                f"{v['document']} (page {v['page']}): {v['value']} — {v['excerpt']}"
                for v in values
            ) or "No values detected",
        })

    # Checklist evidence: keyword indicators only
    combined_text = clean("\n".join(r["text"] for r in records))

    for item in CHECKLISTS[category]:
        found = [
            keyword
            for keyword in item["keywords"]
            if clean(keyword) in combined_text
        ]

        checklist_rows.append({
            "Checklist item": item["item"],
            "Purpose": item["why"],
            "Indicator": "Keyword found" if found else "Not detected",
            "Matched keywords": ", ".join(found) or "None",
            "Interpretation": (
                "Inspect the cited source to confirm the requirement."
                if found
                else "Evidence was not detected by this keyword check; manual review is needed."
            ),
            "Rule source": "Illustrative prototype rule; not an official AICTE rule",
        })

    # Duplicate-file indicators
    hash_groups = {}
    for record in records:
        hash_groups.setdefault(record["sha256"], []).append(record["filename"])

    for filenames in hash_groups.values():
        if len(filenames) > 1:
            duplicate_rows.append({
                "Documents": ", ".join(filenames),
                "Indicator": "Identical file contents",
                "Reason": "These files have the same SHA-256 content hash.",
                "Interpretation": "Possible duplicate upload; review whether duplication is intentional.",
            })

    # Expiry evidence
    expiry_rows = []
    for record in records:
        raw_date, status = record["expiry"]
        expiry_rows.append({
            "Document": record["filename"],
            "Detected expiry date": raw_date or "Not detected",
            "Status": status,
            "Interpretation": (
                "Confirm document type and applicable validity rules manually."
            ),
        })

    return {
        "records": records,
        "evidence": pd.DataFrame(evidence_rows),
        "comparison": pd.DataFrame(comparison_rows),
        "cross": pd.DataFrame(cross_rows),
        "checklist": pd.DataFrame(checklist_rows),
        "duplicates": pd.DataFrame(duplicate_rows, columns=[
            "Documents", "Indicator", "Reason", "Interpretation"
        ]),
        "expiry": pd.DataFrame(expiry_rows),
        "category": category,
    }, errors


# --------------------------------------------------
# 4. SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🛡️ SmartVerify")
    st.caption("Validation workspace")
    st.divider()
    st.markdown("### Workflow")
    st.markdown(
        "1. Application details\n\n"
        "2. Upload documents\n\n"
        "3. Extract evidence\n\n"
        "4. Compare reference records\n\n"
        "5. Review checklist\n\n"
        "6. Export report"
    )
    st.divider()
    st.markdown("### System capabilities")
    st.success("Selectable PDF text extraction")
    st.success("Evidence-linked field results")
    st.success("Configurable keyword checklist")
    st.warning("OCR not implemented")
    st.warning("Official source verification not connected")
    st.warning("No official AICTE record access")


# --------------------------------------------------
# 5. APPLICATION DETAILS
# --------------------------------------------------

heading(
    "01",
    "Application Details",
    "Provide the application category and reference information.",
)

col1, col2 = st.columns([2, 1])

with col1:
    category = st.selectbox(
        "Application category",
        list(CHECKLISTS.keys()),
    )

with col2:
    application_id = st.text_input(
        "Application ID",
        placeholder="DEMO-2026-001",
    )

institution_reference = st.text_input(
    "Institution name for comparison",
    placeholder="Bapuji Institute of Engineering and Technology, Davangere",
)

with st.expander("Optional reference record for comparison"):
    st.caption(
        "Enter values from a trusted reference record you are authorized to use. "
        "These are not fetched from AICTE."
    )

    ref_col1, ref_col2 = st.columns(2)

    with ref_col1:
        reference_student = st.text_input("Reference student name")
        reference_usn = st.text_input("Reference USN")
        reference_course = st.text_input("Reference course")

    with ref_col2:
        reference_year = st.text_input("Reference academic year")
        reference_note = st.text_input(
            "Reference source label",
            placeholder="Example: Synthetic institution record",
        )

reference = {
    "Institution": institution_reference,
    "Student name": reference_student,
    "USN": reference_usn,
    "Course": reference_course,
    "Academic year": reference_year,
}


# --------------------------------------------------
# 6. DOCUMENT UPLOAD
# --------------------------------------------------

heading(
    "02",
    "Supporting Documents",
    "Upload the PDFs to be checked. Scanned PDFs may not contain extractable text.",
)

uploaded_files = st.file_uploader(
    "Choose supporting PDF files",
    type=["pdf"],
    accept_multiple_files=True,
    help="Only PDFs with selectable text can be analyzed by this prototype.",
)

if uploaded_files:
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Files uploaded", len(uploaded_files))
    col_b.metric(
        "Total size",
        f"{sum(f.size for f in uploaded_files) / 1024:.1f} KB",
    )
    col_c.metric(
        "Category",
        category,
    )

    with st.expander("View uploaded file list"):
        for uploaded_file in uploaded_files:
            st.write(f"📄 {uploaded_file.name} — {uploaded_file.size / 1024:.1f} KB")


# --------------------------------------------------
# 7. RUN VALIDATION AND SAVE RESULTS
# --------------------------------------------------

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

if st.button("🔍 Run Validation", type="primary", width="stretch"):
    if not uploaded_files:
        st.error("Upload at least one PDF before running validation.")
    else:
        with st.spinner("Extracting text and running configured checks..."):
            result, errors = analyze_documents(
                uploaded_files,
                category,
                reference,
            )

        for error in errors:
            st.error(error)

        if result:
            st.session_state.analysis_result = result
            st.session_state.audit_log.append({
                "Timestamp": datetime.now().isoformat(timespec="seconds"),
                "Application ID": application_id or "Not provided",
                "Category": category,
                "Uploaded files": len(uploaded_files),
                "Reference source label": reference_note or "User-entered values",
                "Action": "Validation run",
                "Result": "Analysis completed; findings require review",
            })


# --------------------------------------------------
# 8. DISPLAY THE VALIDATION REPORT
# --------------------------------------------------

result = st.session_state.analysis_result

if result:
    records = result["records"]
    evidence_df = result["evidence"]
    comparison_df = result["comparison"]
    cross_df = result["cross"]
    checklist_df = result["checklist"]
    duplicates_df = result["duplicates"]
    expiry_df = result["expiry"]

    st.divider()

    heading(
        "03",
        "Validation Dashboard",
        "A summary of the checks performed on this submission.",
    )

    reference_checks = comparison_df[
        comparison_df["Status"] != "Not checked"
    ]
    mismatches = int(
        (reference_checks["Status"] == "Mismatch").sum()
    )
    not_checked = int(
        (comparison_df["Status"] == "Not checked").sum()
    )
    unreadable = sum(not r["readable"] for r in records)
    expired = int(
        (expiry_df["Status"] == "Potentially expired").sum()
    )

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Documents processed", len(records))
    metric2.metric("Reference mismatches", mismatches)
    metric3.metric("Potentially expired", expired)
    metric4.metric("Unreadable PDFs", unreadable)

    if mismatches or expired or not duplicates_df.empty:
        st.warning(
            "Potential issues were identified. Review the individual evidence "
            "before deciding what action is appropriate."
        )
    elif unreadable:
        st.warning(
            "Some PDFs contain no selectable text. OCR or manual review is needed."
        )
    else:
        st.info(
            "Checks completed. A lack of detected issues does not establish "
            "authenticity or regulatory compliance."
        )

    heading(
        "04",
        "Document Extraction and Evidence",
        "Each detected value includes its source document, page, method and text excerpt.",
    )
    st.dataframe(evidence_df, width="stretch", hide_index=True)

    heading(
        "05",
        "Reference Record Comparison",
        "Only values entered in the reference-record section are used here.",
    )

    if not reference_checks.empty:
        st.dataframe(
            reference_checks,
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(
            "No reference values were supplied. No reference-record comparison "
            "was performed. Enter trusted values and run validation again."
        )

    if not_checked:
        st.caption(
            f"{not_checked} field comparisons were not performed because no "
            "reference value was provided."
        )

    heading(
        "06",
        "Cross-Document Consistency",
        "This checks whether the same detected fields agree across uploaded PDFs.",
    )

    if len(records) < 2:
        st.info(
            "Cross-document comparison requires at least two uploaded documents. "
            "It is not applicable to this single-document submission."
        )
    else:
        st.dataframe(cross_df, width="stretch", hide_index=True)

    heading(
        "07",
        "Application Checklist",
        "These illustrative keyword checks are not official AICTE regulatory rules.",
    )

    st.caption(f"Selected application category: {result['category']}")
    st.dataframe(checklist_df, width="stretch", hide_index=True)

    heading(
        "08",
        "Expiry and Duplicate Indicators",
        "Date and duplicate indicators are preliminary checks, not authentication.",
    )

    st.markdown("**Expiry-date indicators**")
    st.dataframe(expiry_df, width="stretch", hide_index=True)

    st.markdown("**Identical uploaded-file indicators**")
    if duplicates_df.empty:
        st.info("No identical file contents were detected among these uploads.")
    else:
        st.dataframe(
            duplicates_df,
            width="stretch",
            hide_index=True,
        )

    heading(
        "09",
        "Recommended Next Actions",
        "Use these prompts to guide manual review; they are not regulatory decisions.",
    )

    if mismatches:
        st.error(
            "Compare each mismatched field with the original record and supporting evidence."
        )

    if expired:
        st.warning(
            "Review the document type, detected expiry date, and applicable validity requirements."
        )

    if unreadable:
        st.warning(
            "Obtain a text-readable copy or perform manual review for PDFs with no extractable text."
        )

    if not duplicates_df.empty:
        st.warning(
            "Review identical files to determine whether duplicate uploads are intentional."
        )

    if not_checked:
        st.info(
            "Add trusted reference values for fields that need comparison."
        )

    st.info(
        "If a document requires issuer verification, use the issuer's authorized "
        "verification service or route the case for manual confirmation. "
        "This prototype does not contact issuing authorities."
    )

    heading(
        "10",
        "Download Reports",
        "Export the evidence and results for review.",
    )

    report1, report2 = st.columns(2)

    with report1:
        st.download_button(
            "📥 Download extraction evidence",
            evidence_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_evidence.csv",
            "text/csv",
            width="stretch",
        )

        st.download_button(
            "📥 Download reference comparison",
            comparison_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_reference_comparison.csv",
            "text/csv",
            width="stretch",
        )

        st.download_button(
            "📥 Download checklist results",
            checklist_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_checklist.csv",
            "text/csv",
            width="stretch",
        )

    with report2:
        st.download_button(
            "📥 Download cross-document results",
            cross_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_cross_document.csv",
            "text/csv",
            width="stretch",
        )

        st.download_button(
            "📥 Download expiry indicators",
            expiry_df.to_csv(index=False).encode("utf-8-sig"),
            "smartverify_expiry_indicators.csv",
            "text/csv",
            width="stretch",
        )

        st.download_button(
            "📥 Download audit log",
            pd.DataFrame(
                st.session_state.audit_log
            ).to_csv(index=False).encode("utf-8-sig"),
            "smartverify_audit_log.csv",
            "text/csv",
            width="stretch",
        )

    heading(
        "11",
        "Audit Trail",
        "Prototype session log of validation runs. This is not a persistent production audit system.",
    )

    if st.session_state.audit_log:
        st.dataframe(
            pd.DataFrame(st.session_state.audit_log),
            width="stretch",
            hide_index=True,
        )

    heading(
        "12",
        "Original Extracted Text",
        "Open each page to inspect the source text behind the findings.",
    )

    for record in records:
        with st.expander(f"📄 {record['filename']}"):
            st.caption(
                f"SHA-256 content hash: {record['sha256']}"
            )

            if not record["readable"]:
                st.warning(
                    "No selectable text was extracted. The file may be scanned or image-only."
                )
            else:
                for page in record["pages"]:
                    with st.expander(f"Page {page['page']}"):
                        st.text(
                            page["text"]
                            or "[No text extracted from this page]"
                        )


# --------------------------------------------------
# 9. FOOTER AND TRANSPARENCY
# --------------------------------------------------

st.divider()

st.caption(
    "SmartVerify | Hackathon prototype | PDF pattern matching and illustrative "
    "keyword rules only. OCR, AI inference, official AICTE integration, "
    "issuer authentication, regulatory-rule validation, infrastructure analysis, "
    "production role-based access and persistent audit logging are not implemented."
)
