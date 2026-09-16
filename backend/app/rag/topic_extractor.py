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
Analyze the following O/L Science past paper questions and classify each question into the official G.C.E. O/L Science syllabus.

Select the primary `topic` strictly from this official syllabus list:

[PHYSICS]
- motion_in_a_straight_line (velocity, acceleration, motion graphs, equations)
- newtons_laws_and_force (forces, momentum, friction, inertia)
- work_energy_and_power (work done, potential/kinetic energy, power)
- pressure_and_turning_effect (liquid pressure, hydraulic systems, moments, equilibrium)
- heat_and_thermal_physics (temperature, heat transfer, heat capacity, expansion)
- light_and_optics (reflection, refraction, convex/concave lenses, human eye, dispersion)
- sound_and_waves (frequency, wavelength, wave speed, echoes, pitch)
- current_electricity (Ohm's law, circuits, resistance, electric power/energy)
- electromagnetism (magnetic fields, electromagnetic induction, motors, generators, transformers)
- electronics (diodes, rectification, transistors, logic gates, sensors)

[CHEMISTRY]
- structure_of_matter (atomic structure, isotopes, periodic table, chemical bonding)
- chemical_calculations (mole concept, molar mass, concentration, Avogadro constant)
- chemical_reactions_and_rates (rate of reaction, factors affecting rate, energy changes)
- acids_bases_and_salts (pH, indicators, neutralization, properties of acids/bases/salts)
- metals_and_reactivity_series (reactivity series, extraction of metals, corrosion, prevention)
- carbon_and_hydrocarbons (alkanes, alkenes, functional groups, polymers, biogas)

[BIOLOGY]
- biological_processes_in_human_body (digestive, respiratory, circulatory, excretory systems)
- photosynthesis_and_plant_physiology (photosynthesis, transpiration, plant transport)
- microorganisms_and_biotechnology (microorganisms, infectious diseases, industrial applications)
- heredity_and_genetics (DNA, chromosomes, inheritance, monohybrid cross, mutations)
- biosphere_and_ecosystems (ecosystems, food webs, nutrient cycles, pollution, conservation)

Also determine:
- `subject_area`: strictly "physics", "chemistry", or "biology"
- `subtopic`: specific concept in lower_snake_case (e.g. "convex_lenses", "ohms_law", "neutralization", "heart_circulation")
- `keywords`: 2-4 key scientific terms comma-separated

Questions to classify:
{questions_payload}

Return ONLY a valid JSON array of objects with the exact structure:
[
  {{
    "index": 0,
    "topic": "light_and_optics",
    "subtopic": "convex_lenses",
    "subject_area": "physics",
    "keywords": "convex lens, focal point, virtual image, magnification"
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


def classify_questions_batch(questions: List[str]) -> List[Dict[str, str]]:
    """Classifies a batch of question texts into topic, subtopic, subject_area, and keywords."""
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
            {"index": i, "topic": "general_science", "subtopic": "general", "subject_area": "general", "keywords": ""}
            for i in range(len(questions))
        ]
    except Exception as e:
        print(f"Warning: Topic extraction failed for batch ({e}). Using defaults.")
        return [
            {"index": i, "topic": "general_science", "subtopic": "general", "subject_area": "general", "keywords": ""}
            for i in range(len(questions))
        ]

def enrich_chunks_with_topics(chunks: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """Enriches chunk metadata with LLM-extracted topic, subtopic, subject_area, and keywords."""
    print(f"Classifying topics for {len(chunks)} questions according to O/L Science syllabus (batch size: {batch_size})...")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        stems = [c.get("stem", c.get("full_text", "")) for c in batch]
        
        classifications = classify_questions_batch(stems)
        
        for item in classifications:
            idx = item.get("index", 0)
            if idx < len(batch):
                batch_chunk = batch[idx]
                batch_chunk["metadata"]["topic"] = item.get("topic", "general_science")
                batch_chunk["metadata"]["subtopic"] = item.get("subtopic", "general")
                batch_chunk["metadata"]["subject_area"] = item.get("subject_area", "general")
                batch_chunk["metadata"]["keywords"] = item.get("keywords", "")
                
    return chunks

        