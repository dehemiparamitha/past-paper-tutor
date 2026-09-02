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


def is_metadata_or_footer(text: str, min_x: float, page_width: float) -> bool:
    text_clean = text.strip()
    if not text_clean:
        return True

    # 1. Filter out vertical margin footers/headers on the far right
    if page_width > 0 and min_x > page_width * 0.90:
        return True

    text_lower = text_clean.lower()

    # 2. Check for page numbers / serial numbers / markers
    if re.match(r"^[\d\s\-\*]+$", text_clean):
        if len(text_clean) > 4 or re.match(r"^\s*\d+\s*$", text_clean) or re.match(r"^\s*-\s*\d+\s*-\s*$", text_clean) or re.match(r"^\s*\d+\s*\*\*?\s*$", text_clean) or re.match(r"^\s*\*+\s*$", text_clean):
            return True

    # 3. Check for exam code
    if re.search(r"OL\s*/\s*\d{4}", text_clean, re.IGNORECASE) or re.search(r"\d{4}\s*/\s*\d+\s*-\s*[E|S]", text_clean):
        return True

    # 4. Check for "See page..." instructions
    if re.search(r"See\s+page\s+\w+", text_clean, re.IGNORECASE):
        return True

    # 5. Check for Department of Examinations / Sri Lanka
    dept_patterns = [
        r"department", r"departent", r"deparment",
        r"examination", r"examin", r"ex nation",
        r"sri\s*lanka", r"lanka",
        r"பரடசை", r"தணைக்கள",
        r"vibhanga", r"pariksha"
    ]

    matches = sum(1 for pattern in dept_patterns if re.search(pattern, text_lower))
    if matches >= 2:
        return True
    if matches >= 1 and (len(text_clean) < 50 or "lanka" in text_lower):
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
    if any(w in stem_lower for w in ["force", "forces", "block", "resultant", "friction", "table", "mass", "pivot", "rod", "moment", "weight", "vector"]):
        if labels_str:
            return f"Mechanics/force diagram for Question {question_num} depicting physical setup with forces and measurements labeled ({labels_str}) acting on the object/system."
        return f"Mechanics/force diagram for Question {question_num} illustrating physical setup, applied forces, and spatial directions."

    # 2. Physics: Optics / Rays / Mirrors / Lenses
    if any(w in stem_lower for w in ["ray", "rays", "mirror", "lens", "concave", "convex", "refraction", "reflection", "principal axis", "image", "object"]):
        if labels_str:
            return f"Optics ray diagram for Question {question_num} showing light ray paths, optical axis, and components labeled ({labels_str})."
        return f"Optics ray diagram for Question {question_num} showing light ray trajectories and optical components relative to the principal axis."

    # 3. Electricity / Circuits / Electrochemistry / Voltaic Cell
    if any(w in stem_lower for w in ["circuit", "cell", "voltaic", "battery", "current", "resistor", "electrode", "zinc", "copper", "dil."]):
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
    Extract text using Google Cloud Vision API, spatially reconstruct question bands,
    detect diagram questions, and inject inline [DIAGRAM: ...] visual descriptions.
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

    paragraphs_list = []
    for page_obj in pages:
        p_width = page_obj.get("width", 0)
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

                split_indices = []
                for idx, w in enumerate(words_data):
                    if idx == 0:
                        continue
                    is_split_point = False

                    if re.match(r"^\d+\.$", w["text"]):
                        is_split_point = True
                    elif re.match(r"^\d+$", w["text"]) and idx + 1 < len(words_data) and words_data[idx+1]["text"] == ".":
                        is_split_point = True
                    elif w["text"] in {"Use", "Consider", "Read", "Based", "Refer", "Study", "Answer"}:
                        rest_text = " ".join(item["text"] for item in words_data[idx:])
                        if re.search(r"questions?\s+(?:No\.\s+)?\d+", rest_text, re.IGNORECASE) or re.search(r"\d+\s*(?:and|to)\s*\d+", rest_text):
                            is_split_point = True
                    elif w["text"] == "(" and idx + 2 < len(words_data):
                        next_w = words_data[idx + 1]["text"]
                        after_w = words_data[idx + 2]["text"]
                        if re.match(r"^[1-4]$", next_w) and after_w == ")":
                            is_split_point = True
                    elif re.match(r"^\([1-4]\)$", w["text"]):
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

                    if is_metadata_or_footer(text, min_x, p_width):
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

    paragraphs_list.sort(key=lambda p: p["mid_y"])

    question_starts = []
    other_paragraphs = []
    matched_paragraphs = set()

    for p in paragraphs_list:
        text_stripped = p["text"].strip()

        match = re.match(r"^(\d+)\s*\.\s*", text_stripped)
        if match:
            question_starts.append({
                "number": int(match.group(1)),
                "min_y": p["min_y"],
                "paragraph": p
            })
            matched_paragraphs.add(id(p))
            continue

        inst_match = re.search(r"answer\s+(?:the\s+)?questions?\s+(?:No\.\s+)?(\d+)", text_stripped, re.IGNORECASE)
        if not inst_match:
            inst_match = re.search(r"^(?:Consider|Read|Use|Based on)\s+.*questions?\s+(?:No\.\s+)?(\d+)", text_stripped, re.IGNORECASE)

        if inst_match:
            question_starts.append({
                "number": int(inst_match.group(1)),
                "min_y": p["min_y"],
                "paragraph": p
            })
            matched_paragraphs.add(id(p))
            continue

    for p in paragraphs_list:
        if id(p) not in matched_paragraphs:
            other_paragraphs.append(p)

    q_min_ys = {}
    q_start_paragraphs = {}
    for qs in question_starts:
        num = qs["number"]
        if num not in q_min_ys or qs["min_y"] < q_min_ys[num]:
            q_min_ys[num] = qs["min_y"]
        if num not in q_start_paragraphs:
            q_start_paragraphs[num] = []
        q_start_paragraphs[num].append(qs["paragraph"])

    sorted_q_nums = sorted(q_min_ys.keys(), key=lambda num: q_min_ys[num])

    if not sorted_q_nums:
        rows = []
        for p in paragraphs_list:
            added = False
            for row in rows:
                row_avg_y = sum(item["mid_y"] for item in row) / len(row)
                if abs(p["mid_y"] - row_avg_y) < 20:
                    row.append(p)
                    added = True
                    break
            if not added:
                rows.append([p])

        sorted_paragraphs = []
        for row in rows:
            row.sort(key=lambda item: item["mid_x"])
            sorted_paragraphs.extend(row)

        return "\n".join(p["text"] for p in sorted_paragraphs)

    reconstructed_lines = []

    # Process page header
    first_q_y = q_min_ys[sorted_q_nums[0]]
    header_paragraphs = [p for p in other_paragraphs if p["mid_y"] < first_q_y]
    if header_paragraphs:
        header_paragraphs.sort(key=lambda p: p["mid_y"])
        rows = []
        for p in header_paragraphs:
            added = False
            for row in rows:
                row_avg_y = sum(item["mid_y"] for item in row) / len(row)
                if abs(p["mid_y"] - row_avg_y) < 20:
                    row.append(p)
                    added = True
                    break
            if not added:
                rows.append([p])
        for row in rows:
            row.sort(key=lambda item: item["mid_x"])
            reconstructed_lines.extend(p["text"] for p in row)

    scale_y_pt = page_rect.height / vision_height if vision_height > 0 else 1.0

    for i, num in enumerate(sorted_q_nums):
        start_y = q_min_ys[num]
        end_y = q_min_ys[sorted_q_nums[i+1]] if i + 1 < len(sorted_q_nums) else vision_height

        q_stems = list(q_start_paragraphs[num])
        q_stems.sort(key=lambda p: p["min_y"])

        band_others = [p for p in other_paragraphs if start_y <= p["mid_y"] < end_y]
        band_others.sort(key=lambda p: p["mid_y"])

        rows = []
        for p in band_others:
            added = False
            for row in rows:
                row_avg_y = sum(item["mid_y"] for item in row) / len(row)
                if abs(p["mid_y"] - row_avg_y) < 30:
                    row.append(p)
                    added = True
                    break
            if not added:
                rows.append([p])

        sorted_others = []
        for row in rows:
            row.sort(key=lambda item: item["mid_x"])
            sorted_others.extend(row)

        option_pattern = re.compile(r"^\(\s*([1-4])\s*\)")

        options_map = {}
        non_options = []

        for p in sorted_others:
            m = option_pattern.match(p["text"].strip())
            if m:
                opt_num = int(m.group(1))
                if opt_num not in options_map:
                    options_map[opt_num] = p
            else:
                non_options.append(p)

        first_option_y = min(
            (p["min_y"] for p in options_map.values()), default=end_y
        )

        pre_option_non_opts = [p for p in non_options if p["mid_y"] < first_option_y]
        post_option_non_opts = [p for p in non_options if p["mid_y"] >= first_option_y]

        # Combine ALL text in the stem region (q_stems + pre_option_non_opts)
        full_stem_text = " ".join(
            [p["text"] for p in q_stems] + [p["text"] for p in pre_option_non_opts]
        )

        # -------------------------------------------------------------------
        # Strict Diagram Detection & Explanation Synthesis for Question `num`
        # -------------------------------------------------------------------
        has_diagram_keyword = bool(DIAGRAM_KEYWORDS.search(full_stem_text))

        diagram_tag = None

        if has_diagram_keyword:
            # 1. Try Gemini Vision crop description
            top_pt = max(0, start_y * scale_y_pt)
            bottom_pt = min(page_rect.height, first_option_y * scale_y_pt)
            if bottom_pt <= top_pt + 10:
                bottom_pt = min(page_rect.height, end_y * scale_y_pt)

            clip_rect = pymupdf.Rect(
                page_rect.width * 0.03,
                top_pt,
                page_rect.width * 0.97,
                bottom_pt
            )

            if clip_rect.height > 15:
                try:
                    cropped_pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip_rect)
                    cropped_png_bytes = cropped_pix.tobytes("png")
                    gemini_desc = describe_diagram_bytes(cropped_png_bytes, num)
                    if gemini_desc:
                        diagram_tag = f"[DIAGRAM: {gemini_desc}]"
                except Exception as ex:
                    print(f"  [WARN] Cropping diagram for Q{num} failed: {ex}")

            # 2. Domain + OCR label synthesis fallback if Gemini Vision returned nothing
            if not diagram_tag:
                clean_labels = []
                for p in pre_option_non_opts:
                    t = p["text"].strip()
                    if len(t) < 30 and not t.endswith(".") and not t.endswith(",") and "?" not in t:
                        clean_labels.append(t)

                synthesized_explanation = synthesize_diagram_explanation(num, full_stem_text, clean_labels)
                diagram_tag = f"[DIAGRAM: {synthesized_explanation}]"

        # Output structure: stems → [DIAGRAM tag] → pre-option non-opts → options (1)-(4) → post-option non-opts
        reconstructed_lines.extend(p["text"] for p in q_stems)

        if diagram_tag:
            reconstructed_lines.append(diagram_tag)

        reconstructed_lines.extend(p["text"] for p in pre_option_non_opts)
        for opt_num in sorted(options_map.keys()):
            reconstructed_lines.append(options_map[opt_num]["text"])
        reconstructed_lines.extend(p["text"] for p in post_option_non_opts)

    return "\n".join(reconstructed_lines)


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