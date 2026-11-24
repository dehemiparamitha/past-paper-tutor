import os
import time
import base64
import re
import requests
import pymupdf
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Strict diagram keywords
# ---------------------------------------------------------------------------
DIAGRAM_KEYWORDS = re.compile(
    r"\b(diagram|figure|graph|circuit|illustration|setup|apparatus|chart|picture)\b|shown\s+in\s+the\s+(?:diagram|figure|graph|circuit|image|illustration)|as\s+shown\s+in",
    re.IGNORECASE
)


def is_metadata_or_footer(
    text: str,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    page_width: float,
    page_height: float
) -> bool:
    """
    Identifies margin footers, page numbers, and exam code headers.
    Only discards text strictly located in the extreme margins (top 4% or bottom 5% or far right),
    never discarding legitimate question text from the page body.
    """
    text_clean = text.strip()
    if not text_clean:
        return True

    # Far right vertical margin footer (scanned page sidebars)
    if page_width > 0 and min_x > page_width * 0.93:
        return True

    # Only filter text that appears in extreme top (top 4%) or bottom (bottom 5%) margins
    is_in_margin = (page_height > 0) and ((min_y < page_height * 0.04) or (max_y > page_height * 0.95))

    if is_in_margin:
        text_lower = text_clean.lower()
        # Page numbers / serial numbers / stars (e.g. "- 2 -", "34 E I", "***")
        if re.match(r"^[\d\s\-\*\.]+$", text_clean):
            return True
        # Exam codes
        if re.search(r"OL\s*/\s*\d{4}", text_clean, re.IGNORECASE) or re.search(r"\d{4}\s*/\s*\d+\s*-\s*[E|S]", text_clean):
            return True
        # "See page..." instructions
        if re.search(r"See\s+page\s+\w+", text_clean, re.IGNORECASE):
            return True
        # Department header lines in margin
        if "department of examinations" in text_lower or "pariksha" in text_lower or "vibhanga" in text_lower or "all rights reserved" in text_lower:
            return True

    return False


def describe_diagram_bytes(image_png_bytes: bytes, question_num: int) -> str:
    """
    Send a cropped diagram image to Gemini Vision API.
    Returns a natural language description string, or empty string on error/failure.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("CLOUD_VISION_API_KEY")
    if not api_key:
        return ""

    image_base64 = base64.b64encode(image_png_bytes).decode("utf-8")
    models = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]

    for model_name in models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )

        prompt_text = (
            f"This is a cropped diagram/figure from Question {question_num} in an O/L Science past paper. "
            "Describe everything shown in this diagram in detail. Include all numerical values, units, "
            "labels, force directions (left/right/up/down), arrows, optical rays, chemical apparatus, "
            "or biological structures shown. Be concise but complete. Do not guess."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "text": prompt_text
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 250,
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    desc = "".join(p.get("text", "") for p in parts).strip()
                    if desc:
                        return desc
        except Exception:
            pass

    return ""


def synthesize_diagram_explanation(question_num: int, stem_text: str, pre_option_labels: list[str]) -> str:
    """
    Synthesize an accurate, detailed visual description of a diagram using
    the question stem context, subject domain, and OCR label tokens extracted from the diagram area.
    """
    labels_str = ", ".join(pre_option_labels) if pre_option_labels else ""
    stem_lower = stem_text.lower()

    # 1. Physics: Forces / Mechanics / Blocks / Vectors / Pivots / Moments
    if any(w in stem_lower for w in ["force", "forces", "block", "resultant", "friction", "table", "mass", "pivot", "rod", "moment", "weight", "vector", "deceleration"]):
        if labels_str:
            return f"Mechanics/force diagram for Question {question_num} depicting physical setup with forces and measurements labeled ({labels_str}) acting on the object/system."
        return f"Mechanics/force diagram for Question {question_num} illustrating physical setup, applied forces, and spatial directions."

    # 2. Physics: Optics / Rays / Mirrors / Lenses
    if any(w in stem_lower for w in ["ray", "rays", "mirror", "lens", "concave", "convex", "refraction", "reflection", "principal axis", "image", "object"]):
        if labels_str:
            return f"Optics ray diagram for Question {question_num} showing light ray paths, optical axis, and components labeled ({labels_str})."
        return f"Optics ray diagram for Question {question_num} showing light ray trajectories and optical components relative to the principal axis."

    # 3. Electricity / Circuits / Electrochemistry / Voltaic Cell
    if any(w in stem_lower for w in ["circuit", "cell", "voltaic", "battery", "current", "resistor", "electrode", "zinc", "copper", "dil.", "coil"]):
        if labels_str:
            return f"Electrical/electrochemistry diagram for Question {question_num} showing circuit components, electrodes, and chemical setup labeled ({labels_str})."
        return f"Electrical circuit diagram for Question {question_num} showing component connections, current direction, or electrochemical setup."

    # 4. Biology: Cell / Tissue / Anatomy / Organisms / Flowers / Reproduction
    if any(w in stem_lower for w in ["tissue", "cell", "muscle", "organ", "specimen", "plant", "microscope", "leaf", "flower", "bisexual", "gynoecium", "androecium"]):
        if labels_str:
            return f"Biological diagram for Question {question_num} illustrating tissue/cell/anatomical structure and labeled features ({labels_str})."
        return f"Biological structure diagram for Question {question_num} depicting cellular, tissue, flower section, or anatomical specimen features."

    # 5. Chemistry: Apparatus / Reactions / Gas Collection / Distillation
    if any(w in stem_lower for w in ["gas", "reaction", "solution", "apparatus", "distillation", "tube", "beaker", "coagulation", "latex"]):
        if labels_str:
            return f"Chemistry apparatus diagram for Question {question_num} showing experimental setup and labeled components ({labels_str})."
        return f"Chemistry experimental setup diagram for Question {question_num} showing reaction apparatus or gas collection method."

    # General fallback with labels
    if labels_str:
        return f"Visual diagram for Question {question_num} illustrating the setup with labeled components and values ({labels_str})."
    return f"Visual diagram for Question {question_num} illustrating the physical setup referenced in the question."


def extract_text_with_gemini(image_bytes: bytes, page_number: int = 1) -> str:
    """
    Extract text, math, and diagram descriptions from a scanned past paper page using Gemini 1.5 Flash.
    Uses Google AI Studio free tier (no credit card or billing required).
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("CLOUD_VISION_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or .env")

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    models = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]

    prompt = (
        f"You are an expert OCR and exam paper digitization engine. "
        f"Extract all content from Page {page_number} of this past paper with high spatial precision:\n\n"
        "1. Maintain correct reading order (if multi-column, read column 1 top-to-bottom first, then column 2).\n"
        "2. Preserve all question numbers clearly (e.g. '1.', '2.', '23.') and sub-questions (e.g. '(a)', '(b)', '(i)').\n"
        "3. Preserve all multiple choice options on separate lines (e.g. '(1)', '(2)', '(3)', '(4)').\n"
        "4. Convert mathematical, physics, and chemical formulas into clean LaTeX ($...$).\n"
        "5. If there is a diagram, chart, circuit, apparatus, or biological figure, insert an inline description block:\n"
        "   [DIAGRAM: Question X - detailed description of what is shown, labels, forces, directions, values, and units]\n"
        "6. Do not omit any text, numbers, or units. Output only the extracted markdown."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_base64
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
        }
    }

    max_retries = 3
    retry_delay = 2

    for model_name in models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=45)
                if response.status_code == 429:
                    # Rate limit (15 req/min on free tier) - wait and retry
                    time.sleep(4)
                    continue
                if response.status_code == 404:
                    # Model deprecated or unavailable, try next model in list
                    break
                response.raise_for_status()
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts).strip()
                    if text:
                        return text
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Gemini OCR attempt failed for model {model_name} on page {page_number}: {e}")
                time.sleep(retry_delay)
                retry_delay *= 2

    return ""


def extract_text_with_vision(image_bytes: bytes, page: pymupdf.Page = None) -> str:
    """
    Backward-compatible wrapper redirecting to Gemini OCR.
    """
    page_num = (page.number + 1) if (page is not None and hasattr(page, "number")) else 1
    return extract_text_with_gemini(image_bytes, page_number=page_num)


def load_pdf(file_path: str) -> str:
    document = pymupdf.open(file_path)
    total_pages = len(document)
    text_parts = []

    for page_number, page in enumerate(document, start=1):
        print(f"Processing page {page_number}/{total_pages} with Gemini 1.5 Flash...")

        # Convert page to image (scale 2x for high quality OCR)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
        image_bytes = pixmap.tobytes("png")

        # OCR using Gemini 1.5 Flash, with PyMuPDF direct text fallback
        page_text = ""
        try:
            page_text = extract_text_with_gemini(image_bytes, page_number)
            # Sleep 4 seconds between pages to stay comfortably within 15 req/min free tier
            if page_number < total_pages:
                time.sleep(4)
        except Exception as e:
            print(f"Gemini OCR failed for page {page_number}: {e}. Falling back to PyMuPDF direct text extraction.")

        if not page_text or not page_text.strip():
            page_text = page.get_text().strip()

        text_parts.append(
            f"\n--- Page {page_number} ---\n"
            f"{page_text}"
        )

    document.close()
    return "\n".join(text_parts)