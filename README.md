# 🔬 MedLens — Multimodal AI Clinical Assistant

[![Live Demo](https://img.shields.io/badge/🤗%20Live%20Demo-HuggingFace-blue)](https://huggingface.co/spaces/Vi-bha/MedLens)

> AI system for prostate cancer MRI analysis combining computer vision and LLMs.

## 🚀 Features
- DICOM MRI preprocessing (T2W + ADC multiparametric sequences)
- PI-RADS scoring (1–5 scale) with lesion mask overlay
- LLM-generated clinical reports via Groq LLaMA 3.1
- Automated PDF export with ReportLab
- Gradio web interface

## 📊 Dataset
- PROSTATEx (TCIA) — 346 patients, 5.93GB
- 70 cancer positive, 130 benign cases
- T2W + ADC MRI sequences with PI-RADS annotations

## 🛠️ Tech Stack
| Component | Technology |
|-----------|------------|
| MRI Loading | PyDICOM, SimpleITK |
| Visualization | Matplotlib |
| LLM Reports | Groq LLaMA 3.1 |
| UI | Gradio |
| PDF Export | ReportLab |

## ⚙️ How to Run
```bash
pip install pydicom simpleitk gradio groq reportlab matplotlib
# Add your GROQ_API_KEY
# Run in Google Colab with PROSTATEx dataset
```

## 📄 Sample Output
- Patient: ProstateX-0000 | PI-RADS: 4 | CANCER DETECTED
- Patient: ProstateX-0009 | PI-RADS: 2 | BENIGN

---
*Built by Vibhavari Tummewar | MTech Advanced Computing, MANIT Bhopal*
