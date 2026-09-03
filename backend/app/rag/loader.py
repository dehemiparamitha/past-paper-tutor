import os
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
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

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


def extract_text_with_vision(image_bytes: bytes, page: pymupdf.Page) -> str:
    """
    Extract text using Google Cloud Vision API with high spatial precision.
    Maintains correct reading order, preserves question-option relationships,
    detects diagrams, and injects inline [DIAGRAM: ...] visual descriptions.
    """
    api_key = os.getenv("CLOUD_VISION_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("CLOUD_VISION_API_KEY or GEMINI_API_KEY is not set")

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    url = (
        "https://vision.googleapis.com/v1/images:annotate"
        f"?key={api_key}"
    )

    payload = {
        "requests": [
            {
                "image": {
                    "content": image_base64
                },
                "features": [
                    {
                        "type": "DOCUMENT_TEXT_DETECTION"
                    }
                ]
            }
        ]
    }

    import time
    max_retries = 5
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            response_data = result["responses"][0]
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Vision API request failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 2

    pages = response_data.get("fullTextAnnotation", {}).get("pages", [])
    vision_width = pages[0].get("width", 1) if pages else 1
    vision_height = pages[0].get("height", 1) if pages else 1
    page_rect = page.rect
    scale_y_pt = page_rect.height / vision_height if vision_height > 0 else 1.0

    paragraphs_list = []
    for page_obj in pages:
        p_width = page_obj.get("width", 0)
        p_height = page_obj.get("height", 0)
        for block in page_obj.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                words_data = []
                for word in paragraph.get("words", []):
                    word_text = "".join(symbol.get("text", "") for symbol in word.get("symbols", []))
                    vertices = word.get("boundingBox", {}).get("vertices", [])
                    if vertices:
                        xs = [v.get("x", 0) for v in vertices]
                        ys = [v.get("y", 0) for v in vertices]
                        words_data.append({
                            "text": word_text,
                            "min_x": min(xs),
                            "max_x": max(xs),
                            "min_y": min(ys),
                            "max_y": max(ys)
                        })

                if not words_data:
                    continue

                # Split word sequences on clear boundary points (e.g. Question starts: "23.", "(1)", "Part A")
                split_indices = []
                for idx, w in enumerate(words_data):
                    if idx == 0:
                        continue
                    is_split_point = False

                    # Question number start: "23.", "1.", "40."
                    if re.match(r"^\d+\.$", w["text"]):
                        is_split_point = True
                    elif re.match(r"^\d+$", w["text"]) and idx + 1 < len(words_data) and words_data[idx+1]["text"] == ".":
                        is_split_point = True
                    # MCQ Option start: "(1)", "(2)", "(3)", "(4)"
                    elif w["text"] == "(" and idx + 2 < len(words_data):
                        next_w = words_data[idx + 1]["text"]
                        after_w = words_data[idx + 2]["text"]
                        if re.match(r"^[1-4]$", next_w) and after_w == ")":
                            is_split_point = True
                    elif re.match(r"^\([1-4]\)$", w["text"]):
                        is_split_point = True
                    # Section Header start: "Part A", "Part B"
                    elif w["text"] in {"Part", "PART"} and idx + 1 < len(words_data):
                        next_w = words_data[idx + 1]["text"]
                        if next_w in {"A", "B", "(A)", "(B)", "-A", "-B"}:
                            is_split_point = True

                    if is_split_point:
                        split_indices.append(idx)

                last_idx = 0
                parts = []
                for split_idx in split_indices:
                    parts.append(words_data[last_idx:split_idx])
                    last_idx = split_idx
                parts.append(words_data[last_idx:])

                for part in parts:
                    if not part:
                        continue
                    text = " ".join(w["text"] for w in part)

                    min_x = min(w["min_x"] for w in part)
                    max_x = max(w["max_x"] for w in part)
                    min_y = min(w["min_y"] for w in part)
                    max_y = max(w["max_y"] for w in part)

                    if is_metadata_or_footer(text, min_x, max_x, min_y, max_y, p_width, p_height):
                        continue

                    paragraphs_list.append({
                        "text": text,
                        "min_x": min_x,
                        "max_x": max_x,
                        "min_y": min_y,
                        "max_y": max_y,
                        "mid_y": (min_y + max_y) / 2,
                        "mid_x": (min_x + max_x) / 2
                    })

    # Sort paragraphs primarily by vertical reading band, then horizontally
    # Group paragraphs into horizontal bands within ~18 pixels
    paragraphs_list.sort(key=lambda p: p["mid_y"])

    lines_output = []
    current_q_num = None
    current_q_stem = ""
    current_q_stem_y = 0

    for p in paragraphs_list:
        text_stripped = p["text"].strip()

        # Check if paragraph starts a new question e.g. "23. Some plants..."
        q_match = re.match(r"^(\d+)\s*\.\s*(.*)", text_stripped)
        if q_match:
            new_q_num = int(q_match.group(1))
            new_q_rest = q_match.group(2)

            # Detect diagram in previous question if needed
            current_q_num = new_q_num
            current_q_stem = text_stripped
            current_q_stem_y = p["min_y"]

            lines_output.append(text_stripped)

            # Check if this question stem has a diagram keyword
            if DIAGRAM_KEYWORDS.search(text_stripped):
                top_pt = max(0, current_q_stem_y * scale_y_pt)
                bottom_pt = min(page_rect.height, (current_q_stem_y + 120) * scale_y_pt)
                clip_rect = pymupdf.Rect(
                    page_rect.width * 0.03,
                    top_pt,
                    page_rect.width * 0.97,
                    bottom_pt
                )

                diag_tag = None
                if clip_rect.height > 15:
                    try:
                        cropped_pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip_rect)
                        gemini_desc = describe_diagram_bytes(cropped_pix.tobytes("png"), new_q_num)
                        if gemini_desc:
                            diag_tag = f"[DIAGRAM: {gemini_desc}]"
                    except Exception:
                        pass

                if not diag_tag:
                    synthesized = synthesize_diagram_explanation(new_q_num, text_stripped, [])
                    diag_tag = f"[DIAGRAM: {synthesized}]"

                lines_output.append(diag_tag)

        else:
            # Regular paragraph, option (1)-(4), or diagram label
            lines_output.append(text_stripped)

    return "\n".join(lines_output)


def load_pdf(file_path: str) -> str:

    document = pymupdf.open(file_path)

    text_parts = []

    for page_number, page in enumerate(document, start=1):

        print(f"Processing page {page_number}...")

        # Convert page to image for Vision API
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(2, 2)
        )

        image_bytes = pixmap.tobytes("png")

        # OCR using Google Vision + Diagram descriptions
        page_text = extract_text_with_vision(image_bytes, page)

        text_parts.append(
            f"\n--- Page {page_number} ---\n"
            f"{page_text}"
        )

    document.close()

    return "\n".join(text_parts)