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
    You are an expert curriculum and exam paper classifier.
Analyze the following exam questions and assign a primary topic, a specific subtopic, and 2-4 keywords to each.
Format each topic and subtopic in lower_snake_case (e.g. topic: "optics", subtopic: "convex_lenses").
Questions to classify:
{questions_payload}
Return ONLY a valid JSON array of objects with the exact structure:
[
  {{
    "index": 0,
    "topic": "optics",
    "subtopic": "convex_lenses",
    "keywords": "focal length, light refraction, magnification"
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
    """Classifies a batch of question texts into topic, subtopic, and keywords."""
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
        return [{"index": i, "topic": "general", "subtopic": "general", "keywords": ""} for i in range(len(questions))]
    except Exception as e:
        print(f"Warning: Topic extraction failed for batch ({e}). Using defaults.")
        return [{"index": i, "topic": "general", "subtopic": "general", "keywords": ""} for i in range(len(questions))]

def enrich_chunks_with_topics(chunks: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """Enriches chunk metadata with LLM-extracted topic, subtopic, and keywords."""
    print(f"Classifying topics for {len(chunks)} questions using LLM (batch size: {batch_size})...")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        stems = [c.get("stem", c.get("full_text", "")) for c in batch]
        
        classifications = classify_questions_batch(stems)
        
        for item in classifications:
            idx = item.get("index", 0)
            if idx < len(batch):
                batch_chunk = batch[idx]
                batch_chunk["metadata"]["topic"] = item.get("topic", "general")
                batch_chunk["metadata"]["subtopic"] = item.get("subtopic", "general")
                batch_chunk["metadata"]["keywords"] = item.get("keywords", "")
                
    return chunks

        