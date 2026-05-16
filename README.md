# &#x20;Autonomous Insurance Claims Processing Agent

An intelligent agent that processes **First Notice of Loss (FNOL)** documents to extract structured data, detect missing fields, classify claims, and route them to the correct workflow — automatically.

\---

## &#x20;Approach

The agent uses **rule-based NLP with regex pattern matching** to:

1. **Extract** key fields from unstructured FNOL text
2. **Detect** missing mandatory fields
3. **Classify \& Route** claims using deterministic business rules
4. **Return** a structured JSON result with reasoning

### Routing Logic

|Condition|Route|
|-|-|
|Description contains fraud/inconsistent/suspicious| Specialist Queue|
|Any mandatory field is missing| Manual Review|
|Estimated damage < ₹25,000 (all fields present)| Fast-track|
|All fields present, damage ≥ ₹25,000| Standard Processing|



&#x20;Project Structure
```
fnol-agent/
├── agent.py          # Core extraction + routing logic
├── app.py            # Streamlit web UI
├── requirements.txt  # Dependencies
├── sample_docs/      # 5 sample FNOL documents
│   ├── fnol_001_fast_track.txt
│   ├── fnol_002_missing_fields.txt
│   ├── fnol_003_specialist_queue.txt
│   ├── fnol_004_standard.txt
│   └── fnol_005_health.txt
└── outputs/          # JSON results saved here
```

\---

## &#x20;Fields Extracted

**Policy Information**

* Policy Number, Policyholder Name, Effective Dates

**Incident Information**

* Date, Time, Location, Description

**Involved Parties**

* Claimant, Third Parties, Contact Details

**Asset Details**

* Asset Type, Asset ID, Estimated Damage

**Other Mandatory**

* Claim Type, Attachments, Initial Estimate

\---

## &#x20;Steps to Run

### 1\. Clone the repository


git clone https://github.com/bharathtl2002-hash/fnol-agent.git
cd fnol-agent


### 2\. Install dependencies

bash
pip install -r requirements.txt


### 3\. Run the CLI agent

```bash
# Process a single file
python agent.py sample\_docs/fnol\_001\_fast\_track.txt

# Process all sample docs
python agent.py sample\_docs/\*.txt
```

### 4\. Run the Web UI

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

\---

## &#x20;Output Format

```json
{
  "filename": "fnol\_001\_fast\_track.txt",
  "extractedFields": {
    "policy\_number": "POL-2024-78432",
    "policyholder\_name": "Rajesh Kumar",
    "estimated\_damage": 18000,
    ...
  },
  "missingFields": \[],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage ₹18,000 is below the ₹25,000 threshold. All mandatory fields are present. Routed to fast-track processing."
}
```

\---

## Live Demo

**Deployed on Streamlit Cloud:** https://fnol-agent-h4ggez4tdafp4dn5eb2oxv.streamlit.app

## &#x20;Tech Stack

* **Python 3.10+** — Core language
* **Streamlit** — Web UI
* **pdfplumber** — PDF text extraction
* **re (regex)** — Field extraction from unstructured text
* **AI tools** — Used to accelerate development

## 

