import os
from flask import Flask, render_template, request, jsonify

from utils.extract import (
    extract_text_from_pdf,
    extract_text_from_image,
)

from utils.analyze import analyze_text


app = Flask(__name__)

# Keep uploads reasonably controlled.
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
}


def allowed_file(filename):
    """Check whether the uploaded filename has a supported extension."""

    if not filename:
        return False

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def extract_file_text(file):
    """
    Extract text from either a PDF or an image.

    The existing extraction module handles:
    - normal PDFs
    - scanned PDFs
    - PNG
    - JPG/JPEG
    - OCR fallback
    """

    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file)

    return extract_text_from_image(file)


@app.route("/", methods=["GET", "POST"])
def index():

    # =========================================================
    # GET
    # =========================================================

    if request.method == "GET":

        return render_template(
            "index.html",
            results=[],
            errors=[],
            analysis=None,
            combined_text="",
            platform="LinkedIn",
            goal="Engagement",
        )

    # =========================================================
    # POST
    # =========================================================

    uploaded_files = request.files.getlist("files")

    platform = (
        request.form.get("platform")
        or "LinkedIn"
    )

    goal = (
        request.form.get("goal")
        or "Engagement"
    )

    # Validate platform
    allowed_platforms = {
        "LinkedIn",
        "Instagram",
        "X",
    }

    if platform not in allowed_platforms:
        platform = "LinkedIn"

    # Validate goal
    allowed_goals = {
        "Engagement",
        "Shares",
        "Conversions",
        "Awareness",
    }

    if goal not in allowed_goals:
        goal = "Engagement"

    errors = []
    results = []

    # =========================================================
    # NO FILE
    # =========================================================

    if not uploaded_files:

        errors.append(
            "Please upload at least one PDF or image."
        )

        return render_template(
            "index.html",
            results=results,
            errors=errors,
            analysis=None,
            combined_text="",
            platform=platform,
            goal=goal,
        )

    # =========================================================
    # PROCESS FILES
    # =========================================================

    extracted_texts = []

    for file in uploaded_files:

        filename = file.filename or ""

        # Empty filename
        if not filename.strip():
            continue

        # Unsupported type
        if not allowed_file(filename):

            errors.append(
                f"{filename}: unsupported file type. "
                "Use PDF, PNG, JPG or JPEG."
            )

            continue

        try:

            text = extract_file_text(file)

            if not text:
                text = ""

            # Handle extractor error strings
            if text.startswith(
                "Error extracting"
            ):

                errors.append(
                    f"{filename}: {text}"
                )

                continue

            if (
                not text.strip()
                or text.strip()
                in {
                    "No text found.",
                    "No text found (even with OCR).",
                }
            ):

                errors.append(
                    f"{filename}: no readable text was found."
                )

                continue

            results.append({
                "filename": filename,
                "text": text,
                "characters": len(text),
                "words": len(text.split()),
            })

            extracted_texts.append(text)

        except Exception as exc:

            errors.append(
                f"{filename}: unable to process file. "
                f"{str(exc)}"
            )

    # =========================================================
    # NOTHING COULD BE EXTRACTED
    # =========================================================

    if not extracted_texts:

        return render_template(
            "index.html",
            results=results,
            errors=errors or [
                "No readable content was found."
            ],
            analysis=None,
            combined_text="",
            platform=platform,
            goal=goal,
        )

    # =========================================================
    # COMBINE EXTRACTED CONTENT
    # =========================================================

    combined_text = "\n\n".join(
        extracted_texts
    ).strip()

    # =========================================================
    # AI + LOCAL ANALYSIS
    # =========================================================

    try:

        analysis = analyze_text(
            combined_text,
            platform=platform,
            goal=goal,
        )

    except Exception as exc:

        analysis = {
            "summary": {},
            "engagement": [],
            "ai_generated": {},
            "scores": {},
            "content_dna": {},
            "top_issue": {},
            "platform_advice": [],
        }

        errors.append(
            "Content extraction succeeded, but "
            f"analysis encountered an error: {exc}"
        )

    # =========================================================
    # RENDER
    # =========================================================

    return render_template(
        "index.html",
        results=results,
        errors=errors,
        analysis=analysis,
        combined_text=combined_text,
        platform=platform,
        goal=goal,
    )


# =============================================================
# OPTIONAL JSON API
# =============================================================

@app.route("/api/analyze", methods=["POST"])
def api_analyze():

    uploaded_files = request.files.getlist("files")

    platform = (
        request.form.get("platform")
        or "LinkedIn"
    )

    goal = (
        request.form.get("goal")
        or "Engagement"
    )

    allowed_platforms = {
        "LinkedIn",
        "Instagram",
        "X",
    }

    allowed_goals = {
        "Engagement",
        "Shares",
        "Conversions",
        "Awareness",
    }

    if platform not in allowed_platforms:
        platform = "LinkedIn"

    if goal not in allowed_goals:
        goal = "Engagement"

    if not uploaded_files:

        return jsonify({
            "success": False,
            "error": "No files uploaded.",
        }), 400

    results = []
    errors = []
    extracted_texts = []

    for file in uploaded_files:

        filename = file.filename or ""

        if not filename.strip():
            continue

        if not allowed_file(filename):

            errors.append(
                f"{filename}: unsupported file type."
            )

            continue

        try:

            text = extract_file_text(file)

            if (
                not text
                or text.strip()
                in {
                    "No text found.",
                    "No text found (even with OCR).",
                }
            ):

                errors.append(
                    f"{filename}: no readable text found."
                )

                continue

            if text.startswith(
                "Error extracting"
            ):

                errors.append(
                    f"{filename}: {text}"
                )

                continue

            results.append({
                "filename": filename,
                "text": text,
                "characters": len(text),
                "words": len(text.split()),
            })

            extracted_texts.append(text)

        except Exception as exc:

            errors.append(
                f"{filename}: {str(exc)}"
            )

    if not extracted_texts:

        return jsonify({
            "success": False,
            "errors": errors,
        }), 400

    combined_text = "\n\n".join(
        extracted_texts
    ).strip()

    analysis = analyze_text(
        combined_text,
        platform=platform,
        goal=goal,
    )

    return jsonify({
        "success": True,
        "platform": platform,
        "goal": goal,
        "results": results,
        "errors": errors,
        "combined_text": combined_text,
        "analysis": analysis,
    })


# =============================================================
# ERROR HANDLERS
# =============================================================

@app.errorhandler(413)
def request_too_large(error):

    message = (
        "The uploaded files are too large. "
        "Please keep the total upload size under 10 MB."
    )

    return render_template(
        "index.html",
        results=[],
        errors=[message],
        analysis=None,
        combined_text="",
        platform="LinkedIn",
        goal="Engagement",
    ), 413


@app.errorhandler(500)
def internal_server_error(error):

    return render_template(
        "index.html",
        results=[],
        errors=[
            "Something went wrong while processing "
            "your request. Please try again."
        ],
        analysis=None,
        combined_text="",
        platform="LinkedIn",
        goal="Engagement",
    ), 500


# =============================================================
# RUN
# =============================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True,
    )