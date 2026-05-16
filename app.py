"""
Streamlit Web UI for the Autonomous Insurance Claims Processing Agent
Run: streamlit run app.py
"""

import streamlit as st
import json
from agent import process_fnol

st.set_page_config(
    page_title="Insurance Claims Agent",
    page_icon="🛡️",
    layout="wide"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .route-badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 8px;
    }
    .fast-track    { background: #00c853; color: #000; }
    .manual        { background: #ff6d00; color: #fff; }
    .specialist    { background: #d50000; color: #fff; }
    .standard      { background: #2979ff; color: #fff; }
    .stTextArea textarea { font-family: monospace; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

ROUTE_CLASS = {
    "Fast-track": "fast-track",
    "Manual Review": "manual",
    "Specialist Queue": "specialist",
    "Standard Processing": "standard"
}

ROUTE_EMOJI = {
    "Fast-track": "⚡",
    "Manual Review": "🔍",
    "Specialist Queue": "🚨",
    "Standard Processing": "✅"
}

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🛡️ Autonomous Insurance Claims Processing Agent")
st.markdown("*Upload or paste FNOL documents to extract fields, detect gaps, and route claims automatically.*")
st.divider()

# ── Input Section ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📄 Input FNOL Document")

    input_mode = st.radio("Input Mode", ["Paste Text", "Upload File"], horizontal=True)

    fnol_text = ""
    if input_mode == "Paste Text":
        fnol_text = st.text_area(
            "Paste FNOL document text here:",
            height=400,
            placeholder="Policy Number: POL-2024-XXXXX\nPolicyholder Name: ...\n..."
        )
    else:
        uploaded = st.file_uploader("Upload FNOL (.txt or .pdf)", type=["txt", "pdf"])
        if uploaded:
            if uploaded.type == "application/pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(uploaded) as pdf:
                        fnol_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                except Exception:
                    st.error("PDF parsing requires pdfplumber. Install it or paste text instead.")
            else:
                fnol_text = uploaded.read().decode("utf-8", errors="ignore")

            if fnol_text:
                st.text_area("Document Preview", fnol_text, height=300, disabled=True)

    process_btn = st.button("🚀 Process Claim", type="primary", use_container_width=True)

# ── Results Section ───────────────────────────────────────────────────────────
with col2:
    st.subheader("📊 Claim Analysis Results")

    if process_btn and fnol_text.strip():
        with st.spinner("Analyzing FNOL document..."):
            result = process_fnol(fnol_text, filename="input_document")

        route = result["recommendedRoute"]
        route_class = ROUTE_CLASS.get(route, "standard")
        route_emoji = ROUTE_EMOJI.get(route, "✅")

        # Route Banner
        st.markdown(
            f'<div class="route-badge {route_class}">{route_emoji} {route}</div>',
            unsafe_allow_html=True
        )
        st.markdown(f"**Reasoning:** {result['reasoning']}")
        st.divider()

        # Extracted Fields
        with st.expander("✅ Extracted Fields", expanded=True):
            ef = result["extractedFields"]
            if ef:
                for k, v in ef.items():
                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
            else:
                st.warning("No fields could be extracted.")

        # Missing Fields
        with st.expander(f"⚠️ Missing Fields ({len(result['missingFields'])})", expanded=True):
            mf = result["missingFields"]
            if mf:
                for f in mf:
                    st.markdown(f"- ❌ `{f}`")
            else:
                st.success("All mandatory fields are present!")

        # JSON Output
        with st.expander("📋 Raw JSON Output"):
            st.json(result)

        # Download
        st.download_button(
            "⬇️ Download JSON Result",
            data=json.dumps(result, indent=2),
            file_name="claim_result.json",
            mime="application/json",
            use_container_width=True
        )

    elif process_btn:
        st.warning("Please provide FNOL document text or upload a file.")
    else:
        st.info("👈 Paste or upload an FNOL document and click **Process Claim**")

# ── Demo Section ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("🧪 Demo: Batch Process Sample Documents")

if st.button("Run All 5 Sample FNOL Documents", use_container_width=True):
    import os
    from pathlib import Path

    sample_dir = Path("sample_docs")
    files = sorted(sample_dir.glob("*.txt"))

    if not files:
        st.error("No sample files found in sample_docs/")
    else:
        cols = st.columns(len(files))
        for i, (col, f) in enumerate(zip(cols, files)):
            with col:
                text = f.read_text(encoding="utf-8")
                res = process_fnol(text, filename=f.name)
                route = res["recommendedRoute"]
                emoji = ROUTE_EMOJI.get(route, "✅")
                rc = ROUTE_CLASS.get(route, "standard")
                st.markdown(f"**{f.stem}**")
                st.markdown(
                    f'<div class="route-badge {rc}" style="font-size:0.8rem;padding:4px 10px;">'
                    f'{emoji} {route}</div>', unsafe_allow_html=True
                )
                st.markdown(f"Fields: {len(res['extractedFields'])}/13")
                st.markdown(f"Missing: {len(res['missingFields'])}")
