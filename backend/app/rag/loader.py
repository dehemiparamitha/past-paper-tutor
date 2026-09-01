import os
import base64
import re
import requests
import pymupdf
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini model used for diagram descriptions.
# gemini-1.5-flash is fast and cost-effective for this offline extraction step.
# ---------------------------------------------------------------------------
DIAGRAM_DESCRIPTION_MODEL = "gemini-1.5-flash"


def is_metadata_or_footer(text: str, min_x: float, page_width: float) -> bool:
    text_clean = text.strip()
    if not text_clean:
        return True

    # 1. Filter out vertical margin footers/headers on the far right (usually Department of Examinations, Sri Lanka)
    if page_width > 0 and min_x > page_width * 0.90:
        return True

    text_lower = text_clean.lower()

    # 2. Check for page numbers / serial numbers / markers
    # e.g., "- 5 -", "15", "**", "19923"
    if re.match(r"^[\d\s\-\*]+$", text_clean):
        if len(text_clean) > 4 or re.match(r"^\s*\d+\s*$", text_clean) or re.match(r"^\s*-\s*\d+\s*-\s*$", text_clean) or re.match(r"^\s*\d+\s*\*\*?\s*$", text_clean) or re.match(r"^\s*\*+\s*$", text_clean):
            return True

    # 3. Check for exam code, e.g., "OL / 2015 / 34 - E - I"
    if re.search(r"OL\s*/\s*\d{4}", text_clean, re.IGNORECASE) or re.search(r"\d{4}\s*/\s*\d+\s*-\s*[E|S]", text_clean):
        return True

    # 4. Check for "See page..." instructions
    if re.search(r"See\s+page\s+\w+", text_clean, re.IGNORECASE):
        return True

    # 5. Check for Department of Examinations / Sri Lanka (including common OCR errors)
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


# ---------------------------------------------------------------------------
# Diagram detection
# ---------------------------------------------------------------------------

def detect_diagram_boxes(response_data: dict, page_width: int, page_height: int,
                          vision_width: int, vision_height: int) -> list[dict]:
    """
    Detect diagram bounding boxes from the Vision API response.

    Tries two strategies:
    1. Primary: Look for blocks whose blockType == "PICTURE".
    2. Fallback: Find large rectangular regions of the page that have sparse
       OCR coverage — these are likely diagram areas.

    Returns a list of dicts with keys:
        x0, y0, x1, y1  — pixel coordinates in the *pixmap* space
        mid_y            — vertical midpoint in Vision coordinate space (for ordering)
    """
    scale_x = page_width / vision_width if vision_width > 0 else 1.0
    scale_y = page_height / vision_height if vision_height > 0 else 1.0

    diagram_boxes = []

    pages = response_data.get("fullTextAnnotation", {}).get("pages", [])
    for page in pages:
        for block in page.get("blocks", []):
            block_type = block.get("blockType", "TEXT")
            if block_type == "PICTURE":
                vertices = block.get("boundingBox", {}).get("vertices", [])
                if len(vertices) < 4:
                    continue
                xs = [v.get("x", 0) for v in vertices]
                ys = [v.get("y", 0) for v in vertices]
                v_x0, v_y0 = min(xs), min(ys)
                v_x1, v_y1 = max(xs), max(ys)
                diagram_boxes.append({
                    "x0": int(v_x0 * scale_x),
                    "y0": int(v_y0 * scale_y),
                    "x1": int(v_x1 * scale_x),
                    "y1": int(v_y1 * scale_y),
                    "mid_y": (v_y0 + v_y1) / 2,   # Vision-space y for ordering
                    "vision_mid_y": (v_y0 + v_y1) / 2,
                })

    if diagram_boxes:
        return diagram_boxes

    # -------------------------------------------------------------------
    # Fallback heuristic: scan for regions with sparse text density.
    # Build a rough "text coverage" map by marking bounding boxes of all
    # text words, then look for large gaps that span ≥15% of page height
    # and ≥30% of page width.
    # -------------------------------------------------------------------
    all_word_boxes = []
    for page in pages:
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    vertices = word.get("boundingBox", {}).get("vertices", [])
                    if len(vertices) >= 4:
                        xs = [v.get("x", 0) for v in vertices]
                        ys = [v.get("y", 0) for v in vertices]
                        all_word_boxes.append((min(xs), min(ys), max(xs), max(ys)))

    if not all_word_boxes or vision_height == 0:
        return []

    # Divide the page into horizontal bands of ~20px and check text density per band
    band_size = max(1, vision_height // 50)
    num_bands = vision_height // band_size + 1
    band_has_text = [False] * num_bands

    for (wx0, wy0, wx1, wy1) in all_word_boxes:
        b_start = wy0 // band_size
        b_end = wy1 // band_size
        for b in range(b_start, min(b_end + 1, num_bands)):
            band_has_text[b] = True

    # Find contiguous empty-band runs that span ≥15% of the page height
    min_empty_bands = max(1, int(0.15 * num_bands))
    min_width_fraction = 0.30

    i = 0
    while i < num_bands:
        if not band_has_text[i]:
            j = i
            while j < num_bands and not band_has_text[j]:
                j += 1
            span = j - i
            if span >= min_empty_bands:
                v_y0 = i * band_size
                v_y1 = min(j * band_size, vision_height)
                # Only treat as a diagram if wide enough
                # Check whether any word box overlaps this y-range with x coverage > threshold
                # If there is very little text in this y-strip, it is likely a diagram
                strip_words = [b for b in all_word_boxes if b[3] >= v_y0 and b[1] <= v_y1]
                if len(strip_words) <= 5:
                    v_x0 = int(vision_width * 0.05)
                    v_x1 = int(vision_width * 0.95)
                    # Only flag if the strip is wide enough
                    if (v_x1 - v_x0) >= vision_width * min_width_fraction:
                        diagram_boxes.append({
                            "x0": int(v_x0 * scale_x),
                            "y0": int(v_y0 * scale_y),
                            "x1": int(v_x1 * scale_x),
                            "y1": int(v_y1 * scale_y),
                            "mid_y": (v_y0 + v_y1) / 2,
                            "vision_mid_y": (v_y0 + v_y1) / 2,
                        })
            i = j if j > i else i + 1
        else:
            i += 1

    return diagram_boxes


# ---------------------------------------------------------------------------
# Gemini Vision — diagram description
# ---------------------------------------------------------------------------

def describe_diagram_with_gemini(cropped_image_bytes: bytes) -> str:
    """
    Send a cropped diagram image to Gemini Vision and return a natural-language
    description suitable for embedding alongside the question text in a RAG pipeline.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")

    image_base64 = base64.b64encode(cropped_image_bytes).decode("utf-8")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{DIAGRAM_DESCRIPTION_MODEL}:generateContent?key={api_key}"
    )

    prompt_text = (
        "This is a cropped diagram from a Sri Lankan O/L (Ordinary Level) science exam question paper. "
        "Describe exactly what is shown in this diagram. Include all labels, numerical values, units, "
        "directions (left/right/up/down), arrows, component names, and spatial relationships. "
        "If it is a physics diagram (forces, circuits, optics, mechanics), describe the physical setup clearly. "
        "If it is a biology diagram (cell, tissue, organ), describe the structure and any labels. "
        "If it is a chemistry diagram (apparatus, molecules), describe the components and their arrangement. "
        "Be concise but complete. Do not speculate beyond what is visible."
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
            "maxOutputTokens": 300,
        }
    }

    import time
    max_retries = 4
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                description = "".join(p.get("text", "") for p in parts).strip()
                if description:
                    return description
            return ""
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  [WARN] Gemini diagram description failed after {max_retries} attempts: {e}")
                return ""
            print(f"  [WARN] Gemini request failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 2

    return ""


# ---------------------------------------------------------------------------
# Crop a region from a pymupdf Pixmap
# ---------------------------------------------------------------------------

def crop_pixmap(pixmap: pymupdf.Pixmap, x0: int, y0: int, x1: int, y1: int) -> bytes:
    """
    Crop a rectangle from a pymupdf Pixmap and return it as PNG bytes.
    Clamps coordinates to valid pixmap bounds.
    """
    x0 = max(0, min(x0, pixmap.width - 1))
    y0 = max(0, min(y0, pixmap.height - 1))
    x1 = max(x0 + 1, min(x1, pixmap.width))
    y1 = max(y0 + 1, min(y1, pixmap.height))

    clip_rect = pymupdf.IRect(x0, y0, x1, y1)
    cropped = pymupdf.Pixmap(pixmap, clip_rect)
    return cropped.tobytes("png")


# ---------------------------------------------------------------------------
# Main OCR + diagram-description function
# ---------------------------------------------------------------------------

def extract_text_with_vision(image_bytes: bytes, pixmap: pymupdf.Pixmap) -> str:

    api_key = os.getenv("CLOUD_VISION_API_KEY")

    if not api_key:
        raise ValueError("CLOUD_VISION_API_KEY is not set")

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

    # -----------------------------------------------------------------------
    # Step 1: Detect diagram bounding boxes
    # -----------------------------------------------------------------------
    vision_width = pages[0].get("width", 0) if pages else 0
    vision_height = pages[0].get("height", 0) if pages else 0

    diagram_boxes = []
    if vision_width > 0 and vision_height > 0:
        diagram_boxes = detect_diagram_boxes(
            response_data,
            page_width=pixmap.width,
            page_height=pixmap.height,
            vision_width=vision_width,
            vision_height=vision_height,
        )
        if diagram_boxes:
            print(f"  Found {len(diagram_boxes)} diagram region(s) on this page.")

    # -----------------------------------------------------------------------
    # Step 2: Generate Gemini descriptions for each diagram
    # -----------------------------------------------------------------------
    # Each entry: { "vision_mid_y": float, "description": str }
    diagram_descriptions = []
    for i, box in enumerate(diagram_boxes):
        print(f"  Describing diagram {i+1}/{len(diagram_boxes)} with Gemini...")
        try:
            cropped_bytes = crop_pixmap(pixmap, box["x0"], box["y0"], box["x1"], box["y1"])
            description = describe_diagram_with_gemini(cropped_bytes)
            if description:
                diagram_descriptions.append({
                    "vision_mid_y": box["vision_mid_y"],
                    "description": description,
                })
                print(f"  Diagram {i+1} described ({len(description)} chars).")
            else:
                print(f"  Diagram {i+1}: no description returned, skipping.")
        except Exception as e:
            print(f"  [WARN] Could not describe diagram {i+1}: {e}")

    # -----------------------------------------------------------------------
    # Step 3: Build text paragraphs (existing spatial reconstruction logic)
    # -----------------------------------------------------------------------
    paragraphs_list = []
    for page in pages:
        page_width = page.get("width", 0)
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                # Extract word objects with their text and bounding box vertices
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
                
                # Split paragraph on question numbers, instructions, or option markers mid-paragraph
                split_indices = []
                for idx, w in enumerate(words_data):
                    if idx == 0:
                        continue
                    
                    is_split_point = False

                    # Check for question numbers like "17."
                    if re.match(r"^\d+\.$", w["text"]):
                        is_split_point = True
                    # Check for "17" followed by "."
                    elif re.match(r"^\d+$", w["text"]) and idx + 1 < len(words_data) and words_data[idx+1]["text"] == ".":
                        is_split_point = True
                    # Check for instruction keywords followed by question references
                    elif w["text"] in {"Use", "Consider", "Read", "Based", "Refer", "Study", "Answer"}:
                        rest_text = " ".join(item["text"] for item in words_data[idx:])
                        if re.search(r"questions?\s+(?:No\.\s+)?\d+", rest_text, re.IGNORECASE) or re.search(r"\d+\s*(?:and|to)\s*\d+", rest_text):
                            is_split_point = True
                    # Split on MCQ option markers mid-paragraph, e.g. "(" followed by "1"-"4" then ")"
                    # Pattern: word is "(" AND next word is a digit 1-4 AND word after is ")"
                    elif w["text"] == "(" and idx + 2 < len(words_data):
                        next_w = words_data[idx + 1]["text"]
                        after_w = words_data[idx + 2]["text"]
                        if re.match(r"^[1-4]$", next_w) and after_w == ")":
                            is_split_point = True
                    # Also handle combined token like "(2)" or "( 2 )" as single word mid-paragraph
                    elif re.match(r"^\([1-4]\)$", w["text"]):
                        is_split_point = True

                    if is_split_point:
                        split_indices.append(idx)
                
                # Split words_data into parts
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
                    
                    # Filter out metadata, page numbers, or vertical margins
                    if is_metadata_or_footer(text, min_x, page_width):
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
                    
    # Group paragraphs into vertical bands
    paragraphs_list.sort(key=lambda p: p["mid_y"])
    
    question_starts = []
    other_paragraphs = []
    matched_paragraphs = set()
    
    for p in paragraphs_list:
        text_stripped = p["text"].strip()
        
        # 1. Check if it starts with a question number like "12."
        match = re.match(r"^(\d+)\s*\.\s", text_stripped)
        if match:
            question_starts.append({
                "number": int(match.group(1)),
                "min_y": p["min_y"],
                "paragraph": p
            })
            matched_paragraphs.add(id(p))
            continue
            
        # 2. Check if it is an instruction block referencing a question number
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
            
    # Group by question number to find min_y
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
    
    # If no questions found on the page, return standard sorted text
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

        # -----------------------------------------------------------------------
        # Inject diagram descriptions at their vertical positions (no-question page)
        # -----------------------------------------------------------------------
        result_lines = _inject_diagram_descriptions(
            [p["text"] for p in sorted_paragraphs],
            [(p["mid_y"], p["text"]) for p in sorted_paragraphs],
            diagram_descriptions,
            vision_height,
        )
        return "\n".join(result_lines)
        
    reconstructed_lines = []
    # Track (line_text, vision_mid_y) pairs for diagram injection
    line_positions = []   # list of (vision_mid_y, line_text) in output order

    # -----------------------------------------------------------------------
    # Step 4: Reconstruct question text (existing logic)
    # -----------------------------------------------------------------------

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
            for p in row:
                reconstructed_lines.append(p["text"])
                line_positions.append((p["mid_y"], p["text"]))
            
    # Process each question band
    for i, num in enumerate(sorted_q_nums):
        start_y = q_min_ys[num]
        end_y = q_min_ys[sorted_q_nums[i+1]] if i + 1 < len(sorted_q_nums) else float("inf")

        # Collect the question start paragraphs (stems/instructions) - these ALWAYS go first
        q_stems = list(q_start_paragraphs[num])
        # Sort stems by their vertical position (e.g. instruction block above question stem)
        q_stems.sort(key=lambda p: p["min_y"])

        # Collect remaining paragraphs (options, sub-questions) within this band's range
        band_others = []
        for p in other_paragraphs:
            if start_y <= p["mid_y"] < end_y:
                band_others.append(p)

        # Sort band_others spatially: group into rows, sort rows left-to-right
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

        # Separate option paragraphs from non-option paragraphs
        option_pattern = re.compile(r"^\(\s*([1-4])\s*\)")

        options_map = {}   # option_num (int) -> paragraph
        non_options = []   # paragraphs that are not MCQ options, in positional order

        for p in sorted_others:
            m = option_pattern.match(p["text"].strip())
            if m:
                opt_num = int(m.group(1))
                if opt_num not in options_map:
                    options_map[opt_num] = p
            else:
                non_options.append(p)

        first_option_y = min(
            (p["min_y"] for p in options_map.values()), default=float("inf")
        )

        pre_option_non_opts = [p for p in non_options if p["mid_y"] < first_option_y]
        post_option_non_opts = [p for p in non_options if p["mid_y"] >= first_option_y]

        # Output: stems → pre-option non-opts → options (1)→(4) → post-option non-opts
        for p in q_stems:
            reconstructed_lines.append(p["text"])
            line_positions.append((p["mid_y"], p["text"]))
        for p in pre_option_non_opts:
            reconstructed_lines.append(p["text"])
            line_positions.append((p["mid_y"], p["text"]))
        for opt_num in sorted(options_map.keys()):
            p = options_map[opt_num]
            reconstructed_lines.append(p["text"])
            line_positions.append((p["mid_y"], p["text"]))
        for p in post_option_non_opts:
            reconstructed_lines.append(p["text"])
            line_positions.append((p["mid_y"], p["text"]))

    # -----------------------------------------------------------------------
    # Step 5: Inject diagram descriptions at the right positions
    # -----------------------------------------------------------------------
    final_lines = _inject_diagram_descriptions(
        reconstructed_lines,
        line_positions,
        diagram_descriptions,
        vision_height,
    )

    return "\n".join(final_lines)


def _inject_diagram_descriptions(
    lines: list[str],
    line_positions: list[tuple],   # list of (vision_mid_y, line_text) parallel to lines
    diagram_descriptions: list[dict],
    vision_height: int,
) -> list[str]:
    """
    Insert [DIAGRAM: ...] tags into `lines` at the position where each diagram
    appears vertically on the page.

    Strategy:
    - For each diagram description, find the line whose vision_mid_y is closest
      to the diagram's vision_mid_y, then insert the [DIAGRAM: ...] tag
      *after* that line (i.e. between the question stem and the options).
    - If no line positions are available, append at the end.

    Already-injected positions are tracked so multiple diagrams on the same
    page don't collide.
    """
    if not diagram_descriptions:
        return list(lines)

    result = list(lines)
    # We'll build insertion offsets as we go (insert from bottom to top to keep indices stable)
    # Map: insertion_index -> list of [DIAGRAM: ...] strings to insert after that index
    insertions: dict[int, list[str]] = {}

    for diag in sorted(diagram_descriptions, key=lambda d: d["vision_mid_y"]):
        tag = f"[DIAGRAM: {diag['description']}]"
        mid_y = diag["vision_mid_y"]

        if not line_positions:
            # Append at end
            idx = len(result) - 1
        else:
            # Find the line whose y position is just *above* the diagram midpoint
            best_idx = 0
            best_dist = float("inf")
            for i, (ly, _) in enumerate(line_positions):
                dist = abs(ly - mid_y)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
            idx = best_idx

        insertions.setdefault(idx, []).append(tag)

    # Apply insertions from bottom to top (to preserve indices)
    for idx in sorted(insertions.keys(), reverse=True):
        tags = insertions[idx]
        insert_pos = idx + 1  # insert AFTER the found line
        for tag in reversed(tags):
            result.insert(insert_pos, tag)

    return result


def load_pdf(file_path: str) -> str:

    document = pymupdf.open(file_path)

    text_parts = []

    for page_number, page in enumerate(document, start=1):

        print(f"Processing page {page_number}...")

        # Convert page to image
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(2, 2)
        )

        image_bytes = pixmap.tobytes("png")

        # OCR using Google Vision + Gemini diagram descriptions
        page_text = extract_text_with_vision(image_bytes, pixmap)

        text_parts.append(
            f"\n--- Page {page_number} ---\n"
            f"{page_text}"
        )

    document.close()

    return "\n".join(text_parts)