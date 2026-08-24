# Social Media Content Analyzer

Social Media Content Analyzer is a lightweight, production‑ready web app that turns PDFs and images into social‑ready text and practical insights. Upload one or many files with drag‑and‑drop, and the app extracts text using pdfplumber/pdfminer for digital PDFs and Tesseract OCR for scans through pdf2image. It preserves useful formatting, cleans stray breaks, and merges content so you can work from a single, readable draft. A fast local analysis summarizes word and character counts, hashtags, mentions, links, top keywords, and overall sentiment via VADER. For creative acceleration, optional Gemini integration proposes a concise caption, relevant hashtags, and ten clear engagement ideas you can copy in one click. The interface is simple, responsive, and accessible, built with Flask and Bootstrap, featuring copy buttons, JSON export, and a dark mode toggle. Environment variables control secrets and preferences; Poppler and Tesseract are the only system dependencies. Run locally with Python, or use the included Dockerfile for consistent builds and easy cloud deployment. On Render, the service binds to the provided PORT automatically. This project suits marketers, founders, and teams who want to convert research, case studies, screenshots, or scanned documents into polished social posts quickly and confidently.

Live demo: https://social-media-analyzer-e0fe.onrender.com

## Features
- Upload multiple PDFs and images (drag & drop)
- Text extraction with layout preservation (pdfplumber/pdfminer)
- OCR for scanned PDFs and images (Tesseract via pytesseract/pdf2image)
- Quick metrics: word/char counts, hashtags, mentions, URLs, top keywords
- Sentiment/tone via VADER
- Optional AI suggestions (caption, hashtags, 10 engagement ideas) via Gemini
- Copy buttons, JSON export, and light/dark theme

## Requirements
- Python 3.10+
- Poppler (for `pdf2image`)
- Tesseract OCR (for `pytesseract`)

Install system tools (only if running without Docker):
- Windows: Install Poppler and Tesseract and note their install paths
- macOS: `brew install poppler tesseract`
- Linux (Debian/Ubuntu): `sudo apt-get install poppler-utils tesseract-ocr`

## Run (Docker)
This repo includes a Dockerfile that installs Poppler and Tesseract in the image.

- Build: `docker build -t social-analyzer .`
- Run: `docker run -p 8000:8000 -e SECRET_KEY=devkey social-analyzer`
- Open: `http://localhost:8000`

Environment variables:
- `SECRET_KEY` (required)
- `GEMINI_API_KEY` (optional, enables AI suggestions)
- `PRESERVE_FORMATTING=1` (optional)

## Run (without Docker)
- `python -m venv .venv`
- `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows)
- `pip install -r requirements.txt`
- Add `.env` with: `SECRET_KEY=...`, optional `GEMINI_API_KEY=...`
- Windows optional: `POPPLER_PATH=...`, `TESSERACT_CMD=...`
- Start: `python app.py` → `http://127.0.0.1:5000`

## Deploy on Render
Option A — Docker (recommended):
- Push this repo with `Dockerfile` to GitHub.
- In Render: New → Web Service → Select repo → “Use Docker”.
- Set env vars: `SECRET_KEY`, optional `GEMINI_API_KEY`, optional `PRESERVE_FORMATTING=1`.
- Render builds the image and serves the app (binds to `$PORT` automatically).

Option B — Native Python (no Docker):
- Build command: `apt-get update && apt-get install -y poppler-utils tesseract-ocr && pip install -r requirements.txt`
- Start command: `gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:$PORT app:app`
- Add env vars in the dashboard as above.

## Notes
- AI suggestions are only generated if `GEMINI_API_KEY` is present.
- If OCR yields empty text, verify Tesseract is installed and accessible.
- If PDF images fail for OCR, ensure Poppler is installed and on PATH (or set `POPPLER_PATH`).

## Project Structure
- `app.py` — Flask app (upload, route, render)
- `utils/extract.py` — PDF/image text extraction + OCR
- `utils/analyze.py` — text metrics + VADER + Gemini wiring
- `utils/gemini_client.py` — Gemini client
- `templates/` — HTML (Bootstrap)
- `static/` — CSS/JS

