import io
import os
import re
import shutil
from typing import List

import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract
from pdfminer.layout import LAParams
from pdf2image import convert_from_bytes
from PIL import Image, ImageOps, ImageFilter
import pytesseract


# =========================================================
# POPPLER CONFIGURATION
# =========================================================

POPPLER_PATH = (
    os.getenv("POPPLER_PATH")
    or os.getenv("POPPLER_BIN")
)

if not POPPLER_PATH or not os.path.isdir(POPPLER_PATH):

    for _cand in [
        r"C:\Poppler\poppler-25.07.0\Library\bin",
        r"C:\Program Files\poppler\bin",
    ]:

        if os.path.isdir(_cand):

            POPPLER_PATH = _cand
            break


if POPPLER_PATH and not os.path.isdir(
    POPPLER_PATH
):

    POPPLER_PATH = None


# =========================================================
# TESSERACT CONFIGURATION
# =========================================================

TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD"
)


if (
    TESSERACT_CMD
    and os.path.isfile(TESSERACT_CMD)
):

    pytesseract.pytesseract.tesseract_cmd = (
        TESSERACT_CMD
    )

else:

    detected_tesseract = (
        shutil.which("tesseract")
    )

    if detected_tesseract:

        pytesseract.pytesseract.tesseract_cmd = (
            detected_tesseract
        )

    elif os.path.isfile(
        "/opt/homebrew/bin/tesseract"
    ):

        pytesseract.pytesseract.tesseract_cmd = (
            "/opt/homebrew/bin/tesseract"
        )

    elif os.path.isfile(
        "/usr/local/bin/tesseract"
    ):

        pytesseract.pytesseract.tesseract_cmd = (
            "/usr/local/bin/tesseract"
        )


# =========================================================
# GENERAL SETTINGS
# =========================================================

PRESERVE_FORMATTING = (
    os.getenv(
        "PRESERVE_FORMATTING",
        "1"
    ).lower()
    not in {
        "0",
        "false",
        "no"
    }
)


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def _normalize_hyphenation_and_spaces(
    text: str
) -> str:

    if not text:
        return ""

    text = re.sub(
        r"(\w)-\s*\n\s*(\w)",
        r"\1\2",
        text
    )

    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text
    )

    text = re.sub(
        r"\n[ \t]+",
        "\n",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def _join_soft_linebreaks_keep_paragraphs(
    text: str
) -> str:

    if not text:
        return ""

    t = (
        text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    t = t.replace(
        "\n\n",
        "<<<P>>>"
    )

    t = t.replace(
        "\n",
        " "
    )

    t = t.replace(
        "<<<P>>>",
        "\n\n"
    )

    t = re.sub(
        r"[ \t]+",
        " ",
        t
    )

    t = re.sub(
        r"\n{3,}",
        "\n\n",
        t
    )

    return t.strip()


def _postprocess_text(
    text: str,
    preserve: bool
) -> str:

    if not text:
        return ""

    text = (
        text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    if preserve:

        text = re.sub(
            r"[ \t]+\n",
            "\n",
            text
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    return _join_soft_linebreaks_keep_paragraphs(
        _normalize_hyphenation_and_spaces(
            text
        )
    )


# =========================================================
# SOCIAL MEDIA OCR CLEANUP
# =========================================================

def _looks_like_ocr_garbage(
    line: str
) -> bool:

    line = line.strip()

    if not line:
        return True


    lower = line.lower()


    # -----------------------------------------------------
    # Common Instagram / social media UI
    # -----------------------------------------------------

    ui_phrases = [

        "liked by",
        "likes",
        "see original",
        "view all comments",
        "view comments",
        "add a comment",
        "follow",
        "following",
        "suggested for you",
        "share",
        "send",
        "save",
        "repost",
        "translate",
        "more",
        "hours ago",
        "hour ago",
        "minutes ago",
        "minute ago",
        "days ago",
        "day ago",
        "weeks ago",
        "week ago"
    ]


    if any(
        phrase in lower
        for phrase in ui_phrases
    ):

        return True


    # -----------------------------------------------------
    # Device status bar
    # -----------------------------------------------------

    device_terms = {

        "lte",
        "5g",
        "4g",
        "wifi",
        "wi-fi",
        "volte",
        "bluetooth",
        "airplane",
        "airplane mode"
    }


    if lower in device_terms:

        return True


    # -----------------------------------------------------
    # Very short OCR fragments containing mostly
    # symbols/numbers
    # -----------------------------------------------------

    alphanumeric = re.sub(
        r"[^A-Za-z0-9]",
        "",
        line
    )


    if len(alphanumeric) <= 2:

        return True


    digit_count = sum(
        c.isdigit()
        for c in line
    )


    alpha_count = sum(
        c.isalpha()
        for c in line
    )


    # Example:
    # 948 ©
    # 4A O FZ Q MH =
    # 123 456 789
    if (
        digit_count > alpha_count
        and len(line) < 40
    ):

        return True


    # Mostly symbols
    symbols = re.sub(
        r"[A-Za-z0-9\s]",
        "",
        line
    )


    if (
        len(symbols) > 0
        and len(symbols)
        >= len(line) * 0.45
    ):

        return True


    # -----------------------------------------------------
    # OCR fragments that look like status indicators
    # -----------------------------------------------------

    if re.fullmatch(
        r"[\d\s©®™°:;.,|/\\_=+\-*]+",
        line
    ):

        return True


    return False


def _clean_ocr_line(
    line: str
) -> str:

    line = line.strip()


    if not line:
        return ""


    # Remove repeated whitespace
    line = re.sub(
        r"[ \t]+",
        " ",
        line
    )


    # Remove obvious leading/trailing OCR symbols
    line = re.sub(
        r"^[|_=~©®™•·]+",
        "",
        line
    )

    line = re.sub(
        r"[|_=~©®™•·]+$",
        "",
        line
    )


    return line.strip()


def _remove_social_media_ui(
    text: str
) -> str:

    if not text:
        return ""


    lines = text.splitlines()

    cleaned_lines = []


    for raw_line in lines:

        line = _clean_ocr_line(
            raw_line
        )


        if not line:
            continue


        if _looks_like_ocr_garbage(
            line
        ):

            continue


        cleaned_lines.append(
            line
        )


    cleaned = "\n".join(
        cleaned_lines
    )


    # -----------------------------------------------------
    # Remove common inline Instagram UI fragments
    # -----------------------------------------------------

    cleaned = re.sub(
        r"\bLiked by\b.*?\band others\b",
        "",
        cleaned,
        flags=re.IGNORECASE
    )


    cleaned = re.sub(
        r"\b\d+\s*(hours?|minutes?|days?|weeks?)\s*ago\b",
        "",
        cleaned,
        flags=re.IGNORECASE
    )


    cleaned = re.sub(
        r"\bSee Original\b",
        "",
        cleaned,
        flags=re.IGNORECASE
    )


    cleaned = re.sub(
        r"\bView all comments\b",
        "",
        cleaned,
        flags=re.IGNORECASE
    )


    # -----------------------------------------------------
    # Remove excessive whitespace
    # -----------------------------------------------------

    cleaned = re.sub(
        r"[ \t]+",
        " ",
        cleaned
    )


    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned
    )


    return cleaned.strip()


# =========================================================
# OCR CHARACTER CLEANUP
# =========================================================

def _fix_common_ocr_errors(
    text: str
) -> str:

    if not text:
        return ""


    replacements = {

        # Common OCR apostrophe/accent issues
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',

        # OCR line artifacts
        "\u00a0": " ",

        # Common mojibake-like OCR characters
        "©": "",
        "®": "",
        "™": ""
    }


    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )


    # Fix multiple spaces
    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text
    )


    # Fix spaces before punctuation
    text = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        text
    )


    return text.strip()


# =========================================================
# FINAL SOCIAL POST CLEANUP
# =========================================================

def _clean_social_media_text(
    text: str
) -> str:

    if not text:
        return ""


    text = _fix_common_ocr_errors(
        text
    )


    text = _remove_social_media_ui(
        text
    )


    text = _normalize_hyphenation_and_spaces(
        text
    )


    # -----------------------------------------------------
    # Remove obvious OCR-only fragments
    # -----------------------------------------------------

    lines = []


    for line in text.splitlines():

        line = line.strip()


        if not line:
            continue


        if _looks_like_ocr_garbage(
            line
        ):

            continue


        lines.append(
            line
        )


    text = "\n".join(
        lines
    )


    # -----------------------------------------------------
    # Normalize spaces
    # -----------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )


    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )


    return text.strip()


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================

def _extract_with_pdfplumber(
    pdf_bytes: bytes
) -> str:

    out_lines: List[str] = []


    with pdfplumber.open(
        io.BytesIO(pdf_bytes)
    ) as pdf:

        for page in pdf.pages:

            text = (
                page.extract_text(
                    x_tolerance=2,
                    y_tolerance=2
                )
                or ""
            )


            if text.strip():

                out_lines.append(
                    text.strip()
                )


    return _postprocess_text(
        "\n\n".join(
            out_lines
        ),
        PRESERVE_FORMATTING
    )


# =========================================================
# PDFMINER FALLBACK
# =========================================================

def _extract_with_pdfminer(
    pdf_bytes: bytes
) -> str:

    laparams = LAParams(

        line_overlap=0.5,

        char_margin=2.0,

        word_margin=0.1,

        line_margin=0.15,

        boxes_flow=0.5,

        all_texts=True
    )


    text = (
        pdfminer_extract(
            io.BytesIO(pdf_bytes),
            laparams=laparams
        )
        or ""
    )


    return _postprocess_text(
        text,
        PRESERVE_FORMATTING
    )


# =========================================================
# IMAGE PREPROCESSING FOR OCR
# =========================================================

def _prep_for_ocr(
    img: Image.Image
) -> Image.Image:

    # -----------------------------------------------------
    # Upscale image
    # -----------------------------------------------------

    width, height = img.size


    if width < 1600:

        scale = 1600 / width

        img = img.resize(

            (
                int(width * scale),
                int(height * scale)
            ),

            Image.Resampling.LANCZOS
        )


    # -----------------------------------------------------
    # Grayscale
    # -----------------------------------------------------

    g = ImageOps.grayscale(
        img
    )


    # -----------------------------------------------------
    # Contrast
    # -----------------------------------------------------

    g = ImageOps.autocontrast(
        g
    )


    # -----------------------------------------------------
    # Sharpen
    # -----------------------------------------------------

    g = g.filter(
        ImageFilter.SHARPEN
    )


    # -----------------------------------------------------
    # Mild thresholding
    # -----------------------------------------------------

    g = g.point(

        lambda p:
            255
            if p > 210
            else (
                0
                if p < 70
                else p
            )
    )


    return g


# =========================================================
# OCR IMAGE
# =========================================================

def _ocr_image(
    img: Image.Image,
    psm: int = 6
) -> str:

    img = _prep_for_ocr(
        img
    )


    cfg = (
        f"--oem 3 --psm {psm}"
    )


    if PRESERVE_FORMATTING:

        cfg += (
            " -c "
            "preserve_interword_spaces=1"
        )


    try:

        return pytesseract.image_to_string(

            img,

            lang="eng",

            config=cfg
        )

    except Exception as e:

        return (
            f"OCR ERROR: {e}"
        )


# =========================================================
# OCR SCANNED PDF
# =========================================================

def _ocr_scanned_pdf(
    pdf_bytes: bytes
) -> str:

    conversion_args = {

        "dpi":
            300
    }


    if POPPLER_PATH:

        conversion_args[
            "poppler_path"
        ] = POPPLER_PATH


    images = convert_from_bytes(

        pdf_bytes,

        **conversion_args
    )


    page_texts: List[str] = []


    for _, img in enumerate(

        images,

        start=1
    ):

        txt = _ocr_image(

            img,

            psm=6
        ).strip()


        if txt:

            page_texts.append(
                txt
            )


    return _postprocess_text(

        "\n\n".join(
            page_texts
        ),

        PRESERVE_FORMATTING
    )


# =========================================================
# PUBLIC PDF EXTRACTION FUNCTION
# =========================================================

def extract_text_from_pdf(
    file_stream
) -> str:

    try:

        if hasattr(
            file_stream,
            "seek"
        ):

            file_stream.seek(0)


        pdf_bytes = (
            file_stream.read()
        )


        # -------------------------------------------------
        # PDF text layer
        # -------------------------------------------------

        text_plumber = (
            _extract_with_pdfplumber(
                pdf_bytes
            )
        )


        if (
            text_plumber
            and len(text_plumber) > 10
        ):

            return text_plumber


        # -------------------------------------------------
        # PDFMiner
        # -------------------------------------------------

        text_miner = (
            _extract_with_pdfminer(
                pdf_bytes
            )
        )


        if (
            text_miner
            and len(text_miner) > 10
        ):

            return text_miner


        # -------------------------------------------------
        # OCR
        # -------------------------------------------------

        ocr_text = (
            _ocr_scanned_pdf(
                pdf_bytes
            )
        )


        if ocr_text:

            return ocr_text


        return (
            "No text found "
            "(even with OCR)."
        )


    except Exception as e:

        return (
            f"Error extracting "
            f"PDF text: {e}"
        )


# =========================================================
# PUBLIC IMAGE EXTRACTION FUNCTION
# =========================================================

def extract_text_from_image(
    file_stream
) -> str:

    try:

        if hasattr(
            file_stream,
            "seek"
        ):

            file_stream.seek(0)


        image_bytes = (
            file_stream.read()
        )


        img = Image.open(
            io.BytesIO(
                image_bytes
            )
        )


        # -------------------------------------------------
        # First OCR pass
        # -------------------------------------------------

        txt = _ocr_image(

            img,

            psm=6
        )


        # -------------------------------------------------
        # Clean OCR
        # -------------------------------------------------

        cleaned = (
            _clean_social_media_text(
                txt
            )
        )


        # -------------------------------------------------
        # If cleanup removed too much,
        # return the original processed text.
        # -------------------------------------------------

        if (
            len(cleaned.strip())
            < 30
            and len(txt.strip()) > 30
        ):

            return _postprocess_text(

                txt,

                PRESERVE_FORMATTING
            )


        return _postprocess_text(

            cleaned,

            PRESERVE_FORMATTING
        )


    except Exception as e:

        return (
            f"Error extracting "
            f"image text: {e}"
        )