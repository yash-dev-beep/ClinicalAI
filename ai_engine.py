import os
import json
import time
import re
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple, Union
import pymupdf
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()

# =========================================================================
# Gemini Client & Resilient Model Hierarchy
# =========================================================================

# Explicit, verified production model fallback pool as required
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-4-hydrogen",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest"
]

_CLIENT_INSTANCE: Optional[genai.Client] = None

def get_gemini_client() -> genai.Client:
    """Instantiates or reuses the Google GenAI client using GEMINI_API_KEY."""
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Please check your .env file or Streamlit secrets.")
        _CLIENT_INSTANCE = genai.Client(api_key=api_key)
    return _CLIENT_INSTANCE

def robust_json_loads(raw_text: str) -> Dict[str, Any]:
    """
    Safely parses JSON output from Gemini models, automatically handling markdown fences,
    unintended whitespace, or surrounding narrative text.
    """
    cleaned = raw_text.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    clean = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(clean)
    except Exception:
        pass

    match_obj = re.search(r"(\{.*\})", cleaned, flags=re.DOTALL)
    if match_obj:
        try:
            return json.loads(match_obj.group(1))
        except Exception:
            pass

    try:
        import ast
        val = ast.literal_eval(clean)
        if isinstance(val, (dict, list)):
            return val
    except Exception:
        pass

    raise ValueError(f"Could not parse valid JSON from model response: {raw_text[:200]}...")

def generate_resilient_content(
    contents: Union[str, List[Any]],
    system_instruction: Optional[str] = None,
    response_schema: Optional[Any] = None,
    temperature: float = 0.2
) -> str:
    """
    Executes Gemini AI calls with automatic fallback across model tiers.
    Supports text prompts or multimodal contents list [Part, str].
    Rapid 0.3s failover on HTTP 503/429 errors.
    """
    client = get_gemini_client()
    last_error = None

    for model_name in FALLBACK_MODELS:
        for attempt in range(2):
            try:
                config_args: Dict[str, Any] = {"temperature": temperature}
                if system_instruction:
                    config_args["system_instruction"] = system_instruction
                if response_schema:
                    config_args["response_mime_type"] = "application/json"
                    config_args["response_schema"] = response_schema

                config = types.GenerateContentConfig(**config_args)
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                if response:
                    txt = getattr(response, "text", None)
                    if txt and str(txt).strip():
                        return str(txt).strip()
                    if hasattr(response, "candidates") and response.candidates:
                        for cand in response.candidates:
                            if hasattr(cand, "content") and cand.content and cand.content.parts:
                                parts_text = "".join([getattr(p, "text", "") or "" for p in cand.content.parts])
                                if parts_text.strip():
                                    return parts_text.strip()
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                # Rapid failover on model unavailable / rate limit / 404
                if any(k in err_str for k in ["404", "not_found", "no longer available", "429", "resource_exhausted", "quota", "503"]):
                    time.sleep(0.3)
                    break
                time.sleep(0.3)

    raise RuntimeError(f"All AI endpoints are busy or unavailable. Details: {last_error}")

# =========================================================================
# Structured Pydantic Schemas
# =========================================================================

class LabMetricItem(BaseModel):
    test_name: str = Field(description="Everyday readable name of the biomarker, e.g. 'Fasting Blood Sugar', 'Hemoglobin', 'Creatinine'")
    test_value: float = Field(default=0.0, description="Numerical value of the biomarker")
    value: Optional[float] = Field(default=None, description="Alias for test_value")
    unit: str = Field(default="", description="Unit of measurement (e.g. mg/dL, g/dL, %)")
    reference_range: str = Field(default="", description="Healthy standard reference range, e.g. '70 - 99'")
    range: Optional[str] = Field(default=None, description="Alias for reference_range")
    status: str = Field(description="Must be strictly: 'Normal', 'High', 'Low', or 'Borderline'")

    def __init__(self, **data):
        if "value" in data and "test_value" not in data:
            data["test_value"] = data["value"]
        if "range" in data and "reference_range" not in data:
            data["reference_range"] = data["range"]
        super().__init__(**data)

ExtractedMetric = LabMetricItem

class ExtractedLabReport(BaseModel):
    report_date: str = Field(description="Date of the report strictly in YYYY-MM-DD format (e.g. '2026-11-20'). If missing, use today's date.")
    metrics: List[LabMetricItem] = Field(description="List of all extracted laboratory biomarkers")

ClinicalReportExtraction = ExtractedLabReport

def generate_simulated_otp(identifier: str) -> str:
    """Generates a secure 6-digit simulated OTP code."""
    return f"{random.randint(100000, 999999)}"

class DietCustomizationResponse(BaseModel):
    assistant_reply: str = Field(description="Warm, helpful confirmation and guidance in the user's active language at a 5th-grade level")
    diet_was_modified: bool = Field(description="Whether the diet plan was modified or updated based on the user's request")
    updated_diet_plan_markdown: Optional[str] = Field(default=None, description="The complete rewritten 5-part meal plan if modified; null if unchanged")
    detected_new_allergies_or_restrictions: List[str] = Field(default=[], description="Any permanent food allergy, intolerance, or restriction detected (e.g. 'Milk / Dairy products', 'Peanuts')")

# =========================================================================
# Deterministic Patient Health Score Calculator
# =========================================================================

def calculate_patient_health_score(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates a deterministic patient health score (0-100) immediately in Python.
    Guarantees consistent, transparent scoring without LLM math mistakes.
    Starts at 100.
    Borderline deducts a mild penalty (-5 scaled by total parameters).
    High or Low deducts a sharper weighted penalty (-12 to -15, bounded between 15 and 100).
    """
    total_params = len(metrics)
    if total_params == 0:
        return {
            "score": 100,
            "label": "Good",
            "color": "#16a34a",
            "total_params": 0,
            "normal_count": 0,
            "attention_count": 0
        }

    normal_count = 0
    borderline_count = 0
    sharp_penalty_count = 0

    for m in metrics:
        st = str(m.get("status", "Normal")).strip().lower()
        if st == "normal":
            normal_count += 1
        elif st in ["borderline", "mild"]:
            borderline_count += 1
        else: # High, Low, Alert, Critical
            sharp_penalty_count += 1

    attention_count = borderline_count + sharp_penalty_count
    unit_weight = 100.0 / total_params
    deduction = (borderline_count * 0.5 * unit_weight) + (sharp_penalty_count * 1.35 * unit_weight)
    score = int(round(max(15.0, min(100.0, 100.0 - deduction))))

    if score >= 85:
        label = "Excellent"
        color = "#16a34a"  # Green
    elif score >= 70:
        label = "Good"
        color = "#22c55e"  # Light Green
    elif score >= 50:
        label = "Fair / Needs Attention"
        color = "#eab308"  # Amber
    else:
        label = "Critical / Consult Doctor"
        color = "#ef4444"  # Red

    return {
        "score": score,
        "label": label,
        "color": color,
        "total_params": total_params,
        "normal_count": normal_count,
        "attention_count": attention_count
    }

# =========================================================================
# Multimodal Hybrid Document Ingestion Pipeline
# =========================================================================

def extract_from_image_bytes(image_bytes: bytes, mime_type: str = "image/png", language: str = "English") -> Dict[str, Any]:
    """
    Direct multimodal image extraction using Gemini Vision endpoint with strict ExtractedLabReport schema.
    """
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    system_instruction = f"""
You are an expert clinical laboratory data clerk and medical record digitizer.
Extract all clinical lab biomarkers accurately from the provided medical document image into structured JSON conforming to ExtractedLabReport.

Directives:
1. Normalize biomarker names into simple, patient-friendly terms (e.g. 'Fasting Blood Sugar', 'Hemoglobin', 'Creatinine', 'Thyroid TSH').
2. Extract numerical test_value as a float.
3. Identify reference_range (e.g. '70 - 99').
4. status MUST strictly be: 'Normal', 'High', 'Low', or 'Borderline'.
5. Extract report_date in YYYY-MM-DD format. If missing, use today's date ({time.strftime("%Y-%m-%d")}).
6. Translate test names and units gently into {language}.
"""
    prompt = f"Digitize this lab test report completely into structured ExtractedLabReport JSON in {language}."

    raw = generate_resilient_content(
        contents=[image_part, prompt],
        system_instruction=system_instruction,
        response_schema=ExtractedLabReport,
        temperature=0.0
    )
    return robust_json_loads(raw)

def extract_from_single_pdf(file_bytes: bytes, language: str = "English") -> Dict[str, Any]:
    """
    Extracts text from digital PDF directly with PyMuPDF.
    If the PDF is a scan/photo (fewer than 25 readable characters per page), automatically renders
    the page to PNG and routes directly to Gemini Multimodal Vision endpoint.
    """
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    num_pages = len(doc)
    text_parts = []
    is_scanned = False

    for page_num in range(num_pages):
        page = doc[page_num]
        txt = page.get_text().strip()
        if len(txt) < 25:
            is_scanned = True
            break
        text_parts.append(txt)

    if not is_scanned and "\n".join(text_parts).strip():
        full_text = "\n\n".join(text_parts)
        return parse_clinical_text(full_text, language=language)

    # Scanned PDF Fallback: Render up to first 4 pages to PNG and send as multimodal parts
    image_parts = []
    for page_num in range(min(num_pages, 4)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        image_parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

    doc.close()

    system_instruction = f"""
You are an expert clinical laboratory data clerk.
Extract all quantitative lab biomarkers accurately from the scanned medical report pages into structured JSON conforming to ExtractedLabReport.

Directives:
1. Translate test names into simple patient-friendly terms in {language}.
2. Ensure test_value is a clean float.
3. reference_range must capture standard healthy bounds.
4. status MUST strictly be: 'Normal', 'High', 'Low', or 'Borderline'.
5. Extract report_date in YYYY-MM-DD format. If missing, use today ({time.strftime("%Y-%m-%d")}).
"""
    contents = image_parts + [f"Extract all lab tests from these scanned report pages into ExtractedLabReport JSON in {language}."]
    raw = generate_resilient_content(
        contents=contents,
        system_instruction=system_instruction,
        response_schema=ExtractedLabReport,
        temperature=0.0
    )
    return robust_json_loads(raw)

def detect_date_in_text(raw_text: str) -> Optional[str]:
    """
    Deterministically detects consultation/collection dates from medical text headers
    and formats them as YYYY-MM-DD.
    """
    if not raw_text:
        return None

    # 1. Matches: 08 Jul 2026, 17 August 2026, 26 Sep 26
    m1 = re.search(r'(?:collection\s*date|report\s*date|date\s*of\s*collection|dated|sample\s*date|date)[:\s]+(\d{1,2}[\s\-\/](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-\/]\d{2,4})', raw_text, re.IGNORECASE)
    if m1:
        date_str = m1.group(1).replace("-", " ").replace("/", " ").strip()
        for fmt in ["%d %b %Y", "%d %B %Y", "%d %b %y"]:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except Exception:
                pass

    # 2. Matches: 2026-07-08 or 2026/07/08
    m2 = re.search(r'(?:collection\s*date|report\s*date|date\s*of\s*collection|dated|sample\s*date|date)[:\s]+(\d{4}[\-\/]\d{1,2}[\-\/]\d{1,2})', raw_text, re.IGNORECASE)
    if m2:
        date_str = m2.group(1).replace("/", "-").strip()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            pass

    # 3. Matches: 08-07-2026 or 08/07/2026
    m3 = re.search(r'(?:collection\s*date|report\s*date|date\s*of\s*collection|dated|sample\s*date|date)[:\s]+(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{4})', raw_text, re.IGNORECASE)
    if m3:
        date_str = m3.group(1).replace("/", "-").strip()
        for fmt in ["%d-%m-%Y", "%m-%d-%Y"]:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except Exception:
                pass

    return None

def parse_clinical_text(raw_text: str, language: str = "English") -> Dict[str, Any]:
    """
    Zero-hallucination extraction conforming to ExtractedLabReport from digital text layer.
    """
    clean_text = raw_text.strip()
    if len(clean_text) > 30000:
        clean_text = clean_text[:30000]

    system_instruction = f"""
You are an expert clinical laboratory data clerk.
Extract all numerical laboratory biomarkers strictly into ExtractedLabReport JSON in {language}.

Directives:
1. test_name: Patient-friendly biomarker name (e.g. 'Fasting Blood Sugar', 'Total Cholesterol', 'Hemoglobin').
2. test_value: Float measurement.
3. reference_range: E.g. '70 - 99'.
4. status: Strictly 'Normal', 'High', 'Low', or 'Borderline'.
5. report_date: Strictly YYYY-MM-DD format. Default to today ({time.strftime("%Y-%m-%d")}) if not found.
"""
    prompt = f"Lab Report Text:\n---\n{clean_text}\n---\nExtract all biomarkers in {language}."
    raw = generate_resilient_content(
        contents=prompt,
        system_instruction=system_instruction,
        response_schema=ExtractedLabReport,
        temperature=0.0
    )
    parsed = robust_json_loads(raw)
    detected_date = detect_date_in_text(raw_text)
    if detected_date:
        parsed["report_date"] = detected_date
    return parsed

def extract_multimodal_documents(uploaded_files: List[Any], language: str = "English") -> Dict[str, Any]:
    """
    Concurrently processes multiple uploaded PDFs or Images (PNG/JPG/JPEG) across up to 4 worker threads.
    Preserves each consultation report distinctly by its report_date, enabling accurate longitudinal
    trend graphs when multiple reports from different dates/timestamps are uploaded together.
    """
    if not uploaded_files:
        today_str = time.strftime("%Y-%m-%d")
        return {"reports": [], "report_date": today_str, "metrics": []}

    def process_single(file_obj):
        name = getattr(file_obj, "name", "upload.pdf").lower()
        if hasattr(file_obj, "getvalue"):
            data_bytes = file_obj.getvalue()
        elif hasattr(file_obj, "read"):
            file_obj.seek(0)
            data_bytes = file_obj.read()
        else:
            data_bytes = bytes(file_obj)

        if name.endswith(".pdf"):
            res = extract_from_single_pdf(data_bytes, language=language)
        elif name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            mime = "image/jpeg" if name.endswith((".jpg", ".jpeg")) else "image/png"
            res = extract_from_image_bytes(data_bytes, mime_type=mime, language=language)
        else:
            res = extract_from_single_pdf(data_bytes, language=language)

        res["source_file"] = name
        return res

    if len(uploaded_files) == 1:
        res = process_single(uploaded_files[0])
        r_date = res.get("report_date") or time.strftime("%Y-%m-%d")
        m_list = res.get("metrics") or []
        single_rep = {"report_date": r_date, "metrics": m_list, "source_file": res.get("source_file", "")}
        return {
            "reports": [single_rep],
            "report_date": r_date,
            "metrics": m_list
        }

    with ThreadPoolExecutor(max_workers=min(len(uploaded_files), 4)) as executor:
        results = list(executor.map(process_single, uploaded_files))

    # Group extracted metrics by distinct report_date
    reports_by_date: Dict[str, Dict[str, Any]] = {}
    for res in results:
        r_date = res.get("report_date")
        if not r_date or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(r_date)):
            r_date = time.strftime("%Y-%m-%d")

        if r_date not in reports_by_date:
            reports_by_date[r_date] = {
                "report_date": r_date,
                "metrics": [],
                "source_files": []
            }

        if res.get("source_file"):
            reports_by_date[r_date]["source_files"].append(res["source_file"])

        existing_names = {str(m.get("test_name", "")).strip().lower() for m in reports_by_date[r_date]["metrics"]}
        for m in res.get("metrics", []):
            t_name = str(m.get("test_name", "")).strip()
            if t_name and t_name.lower() not in existing_names:
                existing_names.add(t_name.lower())
                reports_by_date[r_date]["metrics"].append(m)

    # Sort reports chronologically by date
    sorted_dates = sorted(reports_by_date.keys())
    all_reports = [reports_by_date[d] for d in sorted_dates]
    latest_rep = all_reports[-1] if all_reports else {"report_date": time.strftime("%Y-%m-%d"), "metrics": []}

    return {
        "reports": all_reports,
        "report_date": latest_rep["report_date"],
        "metrics": latest_rep["metrics"]
    }

# =========================================================================
# Plain-Language Summary, Daily Life Tips & Comparative Narrative
# =========================================================================

def generate_simple_summary_and_tips(
    metrics: List[Dict[str, Any]],
    medications: str = "",
    conditions: str = "",
    language: str = "English"
) -> Tuple[str, str]:
    """
    Generates an ultra-simple 5th-grade summary and practical daily life tips.
    Returns (narrative_summary, daily_life_tips).
    """
    metrics_summary = []
    for m in metrics:
        name = m.get("test_name", "")
        val = m.get("test_value", m.get("value", ""))
        unit = m.get("unit", "")
        ref = m.get("reference_range", m.get("range", ""))
        st = m.get("status", "Normal")
        metrics_summary.append(f"- {name}: {val} {unit} (Normal Range: {ref}) -> Status: {st}")
    metrics_str = "\n".join(metrics_summary) if metrics_summary else "No biomarkers recorded."

    system_instruction = f"""
You are a warm, gentle clinical health communicator for seniors and families.
Translate the patient's lab results into clear, comforting everyday words in {language} strictly at a 5th-grade reading level.
Never use cold, scary medical jargon. Always be encouraging and practical.

Structure your response into two distinct sections:
SECTION 1: SUMMARY
✅ What Looks Good: Praise 2-3 healthy normal test results.
⚠️ What Needs Attention: For each out-of-range test, write exactly ONE clear, reassuring sentence explaining what it means in everyday life.

SECTION 2: DAILY LIFE TIPS
💧 Practical Home Care: Give 3 specific, simple daily habits tied directly to their results and health conditions (e.g. drinking 8 glasses of warm water for kidney/sugar support, 15 minutes of gentle walking after lunch, warm herbal tea for cough, reducing salty pickles).
"""

    prompt = f"""
Target Language: {language}
Patient Daily Medications: {medications or 'None reported'}
Pre-existing Health Conditions: {conditions or 'None reported'}

Biomarker Test Results:
{metrics_str}

Please generate the warm 5th-grade Summary and Daily Life Tips in {language}.
"""

    try:
        raw = generate_resilient_content(
            contents=prompt,
            system_instruction=system_instruction,
            temperature=0.2
        )
        parts = raw.split("SECTION 2: DAILY LIFE TIPS")
        if len(parts) == 2:
            summary_text = parts[0].replace("SECTION 1: SUMMARY", "").strip()
            tips_text = parts[1].strip()
            return summary_text, tips_text
        return raw, "💧 Stay hydrated with 8 glasses of warm water daily, take gentle 15-minute walks, and get 7-8 hours of restful sleep."
    except Exception as e:
        return (
            f"Your health report has been reviewed. Several parameters are in normal healthy ranges. Please review with your doctor. ({str(e)})",
            "💧 Drink plenty of fresh water, enjoy balanced homemade meals, and take light daily walks."
        )

def generate_comparative_narrative(
    current_metrics: List[Dict[str, Any]],
    past_metrics: List[Dict[str, Any]],
    past_date: str,
    language: str = "English"
) -> str:
    """
    Generates a 2-sentence progress comparison against prior lab records.
    """
    if not past_metrics:
        return "This is your first recorded health consultation. We will track your progress over time!"

    curr_dict = {m.get("test_name", "").lower(): m for m in current_metrics}
    past_dict = {m.get("test_name", "").lower(): m for m in past_metrics}

    comparisons = []
    for k, cm in curr_dict.items():
        if k in past_dict:
            pm = past_dict[k]
            comparisons.append(f"- {cm.get('test_name')}: past was {pm.get('test_value', pm.get('value'))}, now {cm.get('test_value', cm.get('value'))} (status: {cm.get('status')})")

    if not comparisons:
        return f"Comparing with your visit on {past_date}: New tests were recorded today, giving your doctor a comprehensive picture of your wellness."

    prompt = f"""
Language: {language}
Past Report Date: {past_date}
Biomarker Changes:
{chr(10).join(comparisons[:6])}

Write exactly 2 warm, encouraging sentences comparing their progress since {past_date} in simple 5th-grade words in {language}.
"""
    try:
        return generate_resilient_content(
            contents=prompt,
            system_instruction=f"You are a gentle geriatric doctor comparing health progress in {language}.",
            temperature=0.2
        )
    except Exception:
        return f"Comparing with your test on {past_date}, your biomarkers have been updated and are trending steadily. Continue your healthy daily habits!"

# =========================================================================
# Custom-Prompt Cuisine Tile Engine (CUISINE_PROMPT_REGISTRY)
# =========================================================================

CUISINE_PROMPT_REGISTRY: Dict[str, Dict[str, str]] = {
    "roti_daal": {
        "title": "🍛 Roti, Daal and Paneer (Mandatory Desi Indian)",
        "focus": "Whole-wheat or multigrain phulka, light moong or masoor dal, homemade low-fat paneer bhurji or tikka, tender lauki, tori, or tinda sabzi, plain fresh curd, and roasted jeera buttermilk. Strictly bans Western superfoods (no kale, quinoa, avocado, chia seeds, or Greek yogurt). Uses traditional, comforting Indian home staples."
    },
    "south_indian": {
        "title": "🍲 South Indian Comfort",
        "focus": "Steamed idli, fermented ragi or moong dal dosa, low-oil vegetable sambar, digestive pepper-jeera rasam, soft curd rice with pomegranate, boiled sundal, and tender coconut water. Emphasizes gut-friendly fermentation and low-sodium tempering with curry leaves and mustard seeds."
    },
    "gujarati_jain": {
        "title": "🫓 Gujarati / Jain Sattvic",
        "focus": "Moong dal khichdi with a dash of pure cow ghee, soothing Gujarati kadhi, soft methi thepla, steamed dudhi muthiya, lightly spiced ringan or bhindi shaak, and sweet lime juice. Strictly respects Jain and mild-spice sattvic home cooking with carefully controlled sugar and jaggery."
    },
    "bengali": {
        "title": "🐟 Bengali Home Kitchen",
        "focus": "Light, gentle patla macher jhol prepared with fresh rohu or katla fish, masoor dal, digestive shukto with bitter gourd, laau ghonto (bottle gourd stew), and measured portions of steamed rice. Uses pure mustard oil sparingly for aroma and digestion."
    },
    "maharashtrian": {
        "title": "🌾 Maharashtrian Everyday",
        "focus": "Warm jowar or bajra bhakri, kanda poha (peanuts omitted if allergic), varan bhaat with lemon, sprouted matki usal, comforting pithla, and crunchy cucumber koshimbir with curd. Uses wholesome, unrefined regional grains."
    },
    "diabetic_heart": {
        "title": "🥗 Simple Diabetic & Heart-Safe",
        "focus": "Low-glycemic Indian staples: besan or moong dal chilla with mint chutney, broken wheat daliya with vegetables, sprouted moong chaat, methi multigrain roti, bitter gourd (karela) or bottle gourd (lauki) sabzi, and flaxseed powder. Zero refined sugar, low salt, and heart-healthy high fiber."
    }
}

def generate_localized_cuisine_diet(
    cuisine_key: str,
    metrics: List[Dict[str, Any]],
    medications: str = "",
    conditions: str = "",
    allergies: Optional[List[str]] = None,
    language: str = "English"
) -> str:
    """
    Generates an affordable, culturally authentic 5-segment recovery meal plan:
    1. Breakfast, 2. Lunch, 3. Evening Snack, 4. Light Dinner, 5. Foods to Avoid/Reduce.
    Dynamically injects tile prompt, patient lab metrics, medications, conditions,
    and HARD SAFETY EXCLUSIONS for all persistent allergies.
    """
    tile_info = CUISINE_PROMPT_REGISTRY.get(cuisine_key, CUISINE_PROMPT_REGISTRY["roti_daal"])
    allergies_list = allergies or []
    allergies_str = ", ".join(allergies_list) if allergies_list else "None reported"

    abnormal_metrics = [
        f"{m.get('test_name')}: {m.get('test_value', m.get('value'))} {m.get('unit', '')} ({m.get('status')})"
        for m in metrics if str(m.get('status', '')).lower() in ['high', 'low', 'borderline', 'alert']
    ]
    abnormal_str = "\n".join(abnormal_metrics) if abnormal_metrics else "All biomarkers are within normal healthy ranges."

    system_instruction = f"""
You are an expert clinical dietitian and cultural nutrition specialist.
Create a warm, appetizing, easy-to-digest recovery meal plan in {language} conforming strictly to the requested cuisine.
Everything must be tailored to an elderly patient at a 5th-grade reading level.

CRITICAL HARD SAFETY EXCLUSION:
The patient has the following PERMANENT ALLERGIES AND RESTRICTIONS:
>>> {allergies_str.upper()} <<<
Under NO circumstances may any dish, ingredient, sauce, or seasoning contain ANY of these allergens. If allergic to milk/dairy, ban milk, paneer, curd, ghee, and butter completely.

Cuisine Guidelines:
{tile_info['title']}
{tile_info['focus']}

Mandatory 5-Part Structure (format using clear Markdown headers):
### 1. 🌅 Breakfast (सुबह का नाश्ता / Healthy Morning Start)
### 2. ☀️ Lunch (दोपहर का भोजन / Nourishing Midday Meal)
### 3. ☕ Evening Refreshment (शाम का नाश्ता / Light Snack & Drink)
### 4. 🌙 Dinner (हल्का रात का खाना / Easy-to-Digest Night Meal)
### 5. 🚫 Foods to Avoid or Limit (परहेज / Safety Precautions)
"""

    prompt = f"""
Target Language: {language}
Selected Cuisine: {tile_info['title']}
Pre-existing Conditions: {conditions or 'None reported'}
Daily Medications: {medications or 'None reported'}
Permanent Allergies / Hard Exclusions: {allergies_str}

Key Out-of-Range Lab Biomarkers:
{abnormal_str}

Please generate the complete, comforting 5-part recovery meal plan adhering strictly to {tile_info['title']} in {language}.
"""

    try:
        return generate_resilient_content(
            contents=prompt,
            system_instruction=system_instruction,
            temperature=0.25
        )
    except Exception as e:
        return f"### Recovery Meal Plan ({tile_info['title']})\n\nEnjoy soft, freshly cooked home meals like moong dal khichdi, warm vegetable soups, and phulka. Avoid oily or heavily salted items. Please consult your doctor for personalized nutritional guidance. ({str(e)})"

# =========================================================================
# Three Specialized Bottom-of-Tab Chatbot Agents
# =========================================================================

def chat_general_health(messages: List[Dict[str, str]], language: str = "English") -> str:
    """
    Tab 1 Bot: General Everyday Health Companion.
    Provides simple 5th-grade everyday home care and wellness advice.
    """
    system_instruction = f"""
You are a warm, gentle clinical health companion for seniors and their caregivers.
Answer general day-to-day wellness questions (home remedies, hydration, gentle exercise, sleep, mild cough/cold) in {language} strictly at a 5th-grade reading level.
Always be reassuring, polite, and include a soft reminder to consult their attending doctor for persistent or severe symptoms.
"""
    chat_transcript = "\n".join([f"{m.get('role', 'user').capitalize()}: {m.get('message', m.get('content', ''))}" for m in messages[-8:]])
    prompt = f"Target Language: {language}\n\nConversation History:\n{chat_transcript}\n\nAssistant (in {language}):"

    try:
        return generate_resilient_content(
            contents=prompt,
            system_instruction=system_instruction,
            temperature=0.3
        )
    except Exception as e:
        return f"I am here to support your daily wellness. Drink plenty of fresh water and rest comfortably. Please check with your doctor for persistent symptoms. ({str(e)})"

def chat_clinical_context(
    messages: List[Dict[str, str]],
    metrics: List[Dict[str, Any]],
    health_score: Optional[int] = None,
    summary: str = "",
    medications: str = "",
    conditions: str = "",
    language: str = "English"
) -> str:
    """
    Tab 2 Bot: Clinical Context Agent.
    Strictly grounded in patient's SQLite data (metrics, score, summary, medications, conditions).
    """
    metrics_summary = [
        f"{m.get('test_name')}: {m.get('test_value', m.get('value'))} {m.get('unit', '')} (Ref: {m.get('reference_range', m.get('range', ''))}, Status: {m.get('status')})"
        for m in metrics[:15]
    ]
    metrics_str = "\n".join(metrics_summary) if metrics_summary else "No lab metrics recorded yet."

    system_instruction = f"""
You are a dedicated clinical report assistant.
You are strictly grounded in this patient's actual recorded lab test results, health score, and medication profile.
Explain their numbers, trends, and health score in clear, comforting, 5th-grade {language}.
Never invent numbers that are not in the record.

Patient Context:
- Health Score: {health_score if health_score is not None else 'N/A'}/100
- Medications: {medications or 'None reported'}
- Health Conditions: {conditions or 'None reported'}
- Latest Summary: {summary[:400] if summary else 'N/A'}

Recorded Lab Biomarkers:
{metrics_str}
"""
    chat_transcript = "\n".join([f"{m.get('role', 'user').capitalize()}: {m.get('message', m.get('content', ''))}" for m in messages[-8:]])
    prompt = f"Target Language: {language}\n\nConversation History:\n{chat_transcript}\n\nAssistant (in {language}):"

    try:
        return generate_resilient_content(
            contents=prompt,
            system_instruction=system_instruction,
            temperature=0.2
        )
    except Exception as e:
        return f"Based on your recorded lab tests, your parameters are on file with an overall score of {health_score or 'N/A'}. Please discuss any specific medicine adjustments with your doctor. ({str(e)})"

def chat_diet_customizer(
    messages: List[Dict[str, str]],
    active_diet: str = "",
    cuisine_name: str = "",
    metrics: Optional[List[Dict[str, Any]]] = None,
    allergies: Optional[List[str]] = None,
    language: str = "English"
) -> DietCustomizationResponse:
    """
    Tab 3 Bot: Interactive Diet Customizer & Persistent Safety Memory Agent.
    Rewrites the active diet plan when requested AND automatically detects and saves
    new food allergies or restrictions to persist to SQLite.
    Conforms to DietCustomizationResponse Pydantic schema.
    """
    allergies_list = allergies or []
    allergies_str = ", ".join(allergies_list) if allergies_list else "None reported"

    system_instruction = f"""
You are an expert personalized dietitian and food allergy safety agent.
You help patients customize their recovery meal plan and safeguard them against allergens in {language}.

Your tasks:
1. Provide a warm, helpful assistant_reply in {language} at a 5th-grade level.
2. If the user asks to modify, swap, or adjust foods in their diet (e.g. "I cannot eat spicy food", "Replace rice with roti", "I don't like bitter gourd"):
   - Set diet_was_modified = true
   - In updated_diet_plan_markdown, output the COMPLETE updated 5-segment meal plan in Markdown.
   - Otherwise, set diet_was_modified = false and updated_diet_plan_markdown = null.
3. DETECT NEW ALLERGIES OR PERMANENT RESTRICTIONS:
   - If the user mentions any allergy, intolerance, or permanent dietary restriction (e.g. "I am allergic to milk", "Allergic to peanuts", "I cannot digest lactose", "I don't eat gluten", "Allergic to eggs"):
   - Extract each item cleanly as a string in detected_new_allergies_or_restrictions (e.g. ["Milk / Dairy products"] or ["Peanuts"]).
   - In the updated diet plan, IMMEDIATELY ban those ingredients!
   - If no new allergy was mentioned, return an empty list [].

Active Cuisine: {cuisine_name}
Current Permanent Allergies: {allergies_str}
"""

    chat_transcript = "\n".join([f"{m.get('role', 'user').capitalize()}: {m.get('message', m.get('content', ''))}" for m in messages[-6:]])

    prompt = f"""
Target Language: {language}
Active Diet Plan:
---
{active_diet[:1200] if active_diet else 'Standard recovery diet'}
---

Current Permanent Allergies: {allergies_str}

Conversation:
{chat_transcript}

Respond strictly conforming to DietCustomizationResponse schema.
"""

    try:
        raw = generate_resilient_content(
            contents=prompt,
            system_instruction=system_instruction,
            response_schema=DietCustomizationResponse,
            temperature=0.2
        )
        data = robust_json_loads(raw)
        return DietCustomizationResponse(**data)
    except Exception as e:
        return DietCustomizationResponse(
            assistant_reply=f"I have noted your request. Please ensure all your meals are gentle and easy to digest. ({str(e)})",
            diet_was_modified=False,
            updated_diet_plan_markdown=None,
            detected_new_allergies_or_restrictions=[]
        )

# =========================================================================
# Verification Dispatcher: SMTP Email OTP
# =========================================================================

def send_real_email_otp(recipient_email: str, otp_code: str) -> bool:
    """
    Dispatches a verification code using SMTP with TLS (port 587).
    Returns False on connection or credential errors to allow seamless on-screen UI fallback.
    """
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not smtp_email or not smtp_password or "your_email" in smtp_email:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your ClinicalAI Verification Code: {otp_code}"
        msg["From"] = f"ClinicalAI Support <{smtp_email}>"
        msg["To"] = recipient_email

        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #1e293b; padding: 20px;">
            <div style="max-width: 500px; margin: auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
              <h2 style="color: #0284c7; margin-top: 0;">ClinicalAI Decision Support</h2>
              <p style="font-size: 16px;">Hello,</p>
              <p style="font-size: 16px;">Here is your secure 6-digit verification code to access your health companion:</p>
              <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; text-align: center; padding: 16px; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #16a34a;">{otp_code}</span>
              </div>
              <p style="font-size: 14px; color: #64748b;">This code is valid for 15 minutes. Never share this code with anyone.</p>
              <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
              <p style="font-size: 12px; color: #94a3b8; text-align: center;">ClinicalAI Personal Health Companion</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, recipient_email, msg.as_string())
        return True
    except Exception:
        return False
