import json
import re
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    temperature=0
)

TOPIC_PROMPT = ChatPromptTemplate.from_template(
    """
You are an expert Sri Lankan G.C.E. Ordinary Level (O/L) Science teacher and syllabus examiner.
Analyze the following O/L Science content/questions and classify each item strictly into the official Sri Lankan G.C.E. O/L Science textbook chapters grouped by Grade (10 or 11) and Subject Area (Physics, Chemistry, Biology).

Select the `grade`, `subject_area`, and `topic` strictly from this official syllabus taxonomy:

=== GRADE 10 SCIENCE ===
[PHYSICS]
- motion_in_a_straight_line (Chapter 2: Motion in a straight line)
- newtons_laws_of_motion (Chapter 4: Newton's laws of motion)
- friction (Chapter 5: Friction)
- resultant_force (Chapter 9: Resultant force)
- turning_effect_of_a_force (Chapter 11: Turning effect of a force)
- equilibrium_of_forces (Chapter 12: Equilibrium of forces)
- hydrostatic_pressure_and_its_applications (Chapter 15: Hydrostatic pressure and its applications)
- work_energy_and_power (Chapter 18: Work, energy and power)
- current_electricity (Chapter 19: Current electricity)

[CHEMISTRY]
- structure_of_matter (Chapter 3: Structure of matter)
- quantification_of_elements_and_compounds (Chapter 7: Quantification of elements and compounds)
- chemical_bonds (Chapter 10: Chemical bonds)
- change_in_matter (Chapter 16: Changes in Matter)
- rate_of_reaction (Chapter 17: Rate of reaction)

[BIOLOGY]
- chemical_basis_of_life (Chapter 1: Chemical basis of life)
- structure_and_functions_of_cells (Chapter 6: Structure and functions of the plant and animal cell)
- characteristics_of_organisms (Chapter 8: Characteristics of organisms)
- the_world_of_life (Chapter 13: The world of life)
- continuity_of_life(Chapter 14: Continuity of life)
- inheritance (Chapter 20: Inheritance)

=== GRADE 11 SCIENCE ===
[PHYSICS]
- waves_and_their_applications (Chapter 4: Waves and their applications)
- geometrical_optics (Chapter 5: Geometrical Optics)
- heat (Chapter 9: Heat)
- power_and_energy_of_electric_appliances (Chapter 10: Power and Energy of Electric Appliances)
- electronics (Chapter 11: Electronics)
- electromagnetism_and_electromagnetic_induction (Chapter 13 : Electromagnetism and electromagnetic induction)

[CHEMISTRY]
- mixtures (Chapter 3: Mixtures)
- acids_bases_and_salts (Chapter 7: Acids, bases and salts)
- heat_changes_associated_with_chemical_reactions (Chapter 8: Heat changes associated with chemical reactions)
- electrochemistry (Chapter 12: Electrochemistry)
- hydrocarbons_and_their_derivatives (Chapter 14: Hydrocarbons and Their Derivatives)

[BIOLOGY]
- living_tissues (Chapter 1: Living tissues)
- photosynthesis (Chapter 2: Photosynthesis)
- biological_processes_in_human_body (Chapter 6: Biological processes in human body)
- biosphere (Chapter 15: Biosphere)

Also determine:
- `grade`: 10 or 11 (integer)
- `subject_area`: strictly "physics", "chemistry", or "biology"
- `subtopic`: specific concept in lower_snake_case (e.g. "convex_lenses", "ohms_law", "neutralization", "heart_circulation")
- `keywords`: 2-4 key scientific terms comma-separated

Content to classify:
{questions_payload}

Return ONLY a valid JSON array of objects with the exact structure:
[
  {{
    "index": 0,
    "grade": 11,
    "subject_area": "physics",
    "topic": "geometrical_optics",
    "subtopic": "convex_lenses",
    "keywords": "convex lens, focal point, refraction, ray diagram"
  }}
]
"""
)

def _normalize_llm_content(content: Any) -> str:
    """Safely converts LangChain response content (str, list of strings/dicts) to a single string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])
            elif hasattr(item, "text"):
                text_parts.append(str(item.text))
            else:
                text_parts.append(str(item))
        return "".join(text_parts)
    return str(content)


def classify_questions_batch(questions: List[str]) -> List[Dict[str, Any]]:
    """Classifies a batch of question texts into grade, subject_area, topic, subtopic, and keywords."""
    payload = "\n\n".join([f"[{i}] {q[:300]}" for i, q in enumerate(questions)])

    try:
        response = (TOPIC_PROMPT | llm).invoke({"questions_payload": payload})
        raw_text = _normalize_llm_content(response.content).strip()

        # Extract JSON array [ ... ] using regex to handle markdown fences or extra wrappers
        json_match = re.search(r"\[\s*\{.*\}\s*\]", raw_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
        else:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
            cleaned = re.sub(r"```$", "", cleaned).strip()
            parsed = json.loads(cleaned)

        if isinstance(parsed, list):
            return parsed
        return [
            {"index": i, "grade": 10, "topic": "general_science", "subtopic": "general", "subject_area": "general", "keywords": ""}
            for i in range(len(questions))
        ]
    except Exception as e:
        print(f"Warning: Topic extraction failed for batch ({e}). Using defaults.")
        return [
            {"index": i, "grade": 10, "topic": "general_science", "subtopic": "general", "subject_area": "general", "keywords": ""}
            for i in range(len(questions))
        ]

def enrich_chunks_with_topics(chunks: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """Enriches chunk metadata with LLM-extracted grade, subject_area, topic, subtopic, and keywords."""
    print(f"Classifying topics for {len(chunks)} questions according to O/L Science syllabus (batch size: {batch_size})...")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        stems = [c.get("stem", c.get("full_text", "")) for c in batch]
        
        classifications = classify_questions_batch(stems)
        
        for item in classifications:
            idx = item.get("index", 0)
            if idx < len(batch):
                batch_chunk = batch[idx]
                grade_val = item.get("grade", 10)
                try:
                    grade_int = int(grade_val)
                except (ValueError, TypeError):
                    grade_int = 10
                batch_chunk["metadata"]["grade"] = grade_int
                batch_chunk["metadata"]["subject_area"] = item.get("subject_area", "general")
                batch_chunk["metadata"]["topic"] = item.get("topic", "general_science")
                batch_chunk["metadata"]["subtopic"] = item.get("subtopic", "general")
                batch_chunk["metadata"]["keywords"] = item.get("keywords", "")
                
    return chunks

        