"""
MedLens — Gradio UI
Run: python app.py

Requires:
  - GROQ_API_KEY environment variable
  - patient_index.pkl and patient_pirads.pkl in ./data/
  - lesion_index.pkl in ./data/
  - PROSTATEx DICOM data accessible at paths stored in patient_index.pkl

See README.md for full setup instructions.
"""

import os
import pickle
import tempfile

import gradio as gr

from imaging import visualize_patient
from report import generate_pdf_report

# ─────────────────────────────────────────────────────
# Load pre-built indexes
# ─────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def _load_pickle(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. "
            "Run the data preparation notebook first — see README.md."
        )
    with open(path, "rb") as f:
        return pickle.load(f)

patient_index  = _load_pickle("patient_index.pkl")
patient_pirads = _load_pickle("patient_pirads.pkl")
lesion_index   = _load_pickle("lesion_index.pkl")

SAMPLE_PATIENTS = {
    "ProstateX-0000": "🔴 Cancer",
    "ProstateX-0001": "🟢 Benign",
    "ProstateX-0005": "🔴 Cancer",
    "ProstateX-0009": "🟢 Benign",
    "ProstateX-0010": "🟢 Benign",
}


# ─────────────────────────────────────────────────────
# Core analysis function
# ─────────────────────────────────────────────────────

def run_medlens(patient_id: str):
    patient_id = patient_id.strip()
    if not patient_id:
        return "❌ Please enter a patient ID.", None, None

    if patient_id not in patient_index:
        return (
            f"❌ Patient `{patient_id}` not found. "
            "Try one of the sample patients listed below.",
            None, None,
        )

    try:
        findings  = lesion_index.get(patient_id, [])
        pirads    = patient_pirads.get(patient_id, "N/A")
        sig_count = sum(1 for f in findings if f["significant"])

        # MRI visualization
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            viz_path = tmp_img.name

        fig = visualize_patient(
            patient_id, patient_index, lesion_index,
            patient_pirads, output_path=viz_path,
        )

        # PDF report
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False,
            prefix=f"{patient_id}_",
        ) as tmp_pdf:
            pdf_path = tmp_pdf.name

        generate_pdf_report(
            patient_id=patient_id,
            findings=findings,
            pirads=pirads,
            viz_path=viz_path,
            output_path=pdf_path,
        )

        # Markdown summary
        findings_md = ""
        for f in findings:
            label = "🔴 SIGNIFICANT" if f["significant"] else "🟢 Benign"
            findings_md += (
                f"- **Finding {f['finding']}**: {label} "
                f"— Gleason: {f.get('gleason', 'N/A')}\n"
            )
        if not findings_md:
            findings_md = "- No lesions detected\n"

        if sig_count > 0:
            rec = "⚠️ Urological consultation and biopsy confirmation recommended."
        elif isinstance(pirads, int) and pirads >= 3:
            rec = "📅 Repeat MRI in 6–12 months or targeted biopsy if PSA rising."
        else:
            rec = "✅ Routine surveillance. Annual PSA monitoring."

        report_md = f"""## 📊 Patient Summary

| Metric | Value |
|--------|-------|
| **Patient ID** | {patient_id} |
| **PI-RADS Score** | {pirads} / 5 |
| **Total Findings** | {len(findings)} |
| **Cancer Status** | {'🔴 Clinically Significant' if sig_count > 0 else '🟢 Benign'} |

---

## 🔬 Clinical Findings
{findings_md}

---

## 💊 Recommendation
{rec}

---
*AI-assisted analysis. Requires radiologist confirmation. Not for clinical use.*
"""
        return report_md, fig, pdf_path

    except Exception as e:
        return f"❌ Error: {e}", None, None


# ─────────────────────────────────────────────────────
# Gradio UI
# ─────────────────────────────────────────────────────

sample_table = "\n".join(
    f"| {pid} | {status} |"
    for pid, status in SAMPLE_PATIENTS.items()
)

with gr.Blocks(
    title="MedLens — Prostate MRI AI",
    theme=gr.themes.Soft(),
) as demo:

    gr.Markdown(f"""
    # 🔬 MedLens — AI Clinical Assistant for Prostate Cancer
    *PROSTATEx Dataset · 346 Patients · T2W + ADC MRI · PI-RADS Scoring*

    ### 🧪 Sample patients
    | Patient ID | Status |
    |------------|--------|
    {sample_table}
    """)

    with gr.Row():
        with gr.Column(scale=1):
            patient_input = gr.Textbox(
                label="Patient ID",
                placeholder="e.g. ProstateX-0000",
                value="ProstateX-0000",
            )
            analyze_btn = gr.Button(
                "🔍 Analyze Patient", variant="primary", size="lg"
            )

        with gr.Column(scale=2):
            report_output = gr.Markdown(label="Clinical Report")

    mri_output = gr.Plot(label="MRI Visualization")
    pdf_output = gr.File(label="📄 Download PDF Report")

    analyze_btn.click(
        fn=run_medlens,
        inputs=patient_input,
        outputs=[report_output, mri_output, pdf_output],
    )

if __name__ == "__main__":
    demo.launch()
