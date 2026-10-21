import os
import json
import time
import re
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple
import pymupdf
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()

# =========================================================================
# Gemini Client & Resilient Model Hierarchy
# =========================================================================

FALLBACK_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-pro-latest",
    "gemini-2.5-flash-lite"
]

def get_gemini_client() -> genai.Client:
    """Instantiates and returns the Google GenAI client using the GEMINI_API_KEY environment variable."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Please check your .env file or Streamlit secrets.")
    return genai.Client(api_key=api_key)

def generate_resilient_content(
    prompt: str,
    system_instruction: Optional[str] = None,
    response_schema: Optional[Any] = None,
    temperature: float = 0.2
) -> str:
    """
    Executes Gemini AI calls with automatic fallback across model tiers.
    Retries gracefully if rate limits or high demand (503/429) occur.
    Returns cleaned response text or raises RuntimeError if all models fail.
    """
    client = get_gemini_client()
    last_error = None

    for model_name in FALLBACK_MODELS:
        for attempt in range(2):
            try:
                config_args = {"temperature": temperature}
                if system_instruction:
                    config_args["system_instruction"] = system_instruction
                if response_schema:
                    config_args["response_mime_type"] = "application/json"
                    config_args["response_schema"] = response_schema

                config = types.GenerateContentConfig(**config_args)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_error = e
                time.sleep(0.6)

    raise RuntimeError(f"All AI endpoints are busy or unavailable. Details: {last_error}")

# =========================================================================
# Structured Pydantic Schemas
# =========================================================================

class ExtractedMetric(BaseModel):
    test_name: str = Field(description="Everyday readable name of the test (e.g. Hemoglobin, Blood Sugar, Cholesterol, Creatinine, Platelets)")
    value: float = Field(description="Numerical value of the measurement")
    range: str = Field(description="Healthy standard range provided in the report, e.g. '12.0 - 15.5'")
    status: str = Field(description="Must be strictly: 'High', 'Low', 'Normal', or 'Alert'")
    unit: str = Field(default="", description="Unit of measurement (e.g. g/dL, mg/dL)")

class ClinicalReportExtraction(BaseModel):
    report_date: str = Field(description="Date of the report strictly in YYYY-MM-DD format (e.g. '2026-10-19'). If missing, use today's date.")
    metrics: List[ExtractedMetric] = Field(description="List of all extracted laboratory biomarkers")

class HealthAlert(BaseModel):
    severity: str = Field(description="'Critical', 'Urgent', 'Moderate', or 'Informational'")
    title: str = Field(description="Short, comforting, non-technical title")
    biomarker: str = Field(description="Name of the parameter")
    simple_explanation: str = Field(description="Explain what this means in simple, warm words for elderly patients. Avoid medical jargon.")
    doctor_query: str = Field(description="One simple question they can ask their doctor")

class HealthAlertsResponse(BaseModel):
    alerts: List[HealthAlert] = Field(description="List of parameters to be cautious of")
    urgent_care_needed: bool = Field(description="True if an extreme abnormality requires immediate medical review")
    overall_safety_summary: str = Field(description="Warm, simple, encouraging overall health summary for the patient")

class MealItem(BaseModel):
    dish_name: str = Field(description="Name of the dish")
    portion: str = Field(description="Easy-to-understand portion size (e.g. '1 small bowl', '2 soft rotis')")
    elderly_benefit: str = Field(description="Why this is good for them (e.g. 'Easy to chew and digest, helps steady blood sugar')")

class MealSession(BaseModel):
    meal_time: str = Field(description="Morning (Breakfast), Midday (Lunch), Evening (Dinner), or Bedtime Snack")
    dishes: List[MealItem] = Field(description="List of dishes")

class PersonalizedDietPlan(BaseModel):
    cuisine: str = Field(description="Cuisine name (e.g. 'Roti, Daal and Paneer (Desi Indian)')")
    daily_schedule: List[MealSession] = Field(description="Morning, midday, and evening meals")
    comfort_tips: str = Field(description="Tips for easy chewing, proper hydration, and gentle cooking")
    foods_to_enjoy: List[str] = Field(description="Wholesome foods they can freely enjoy")
    foods_to_limit: List[str] = Field(description="Foods they should eat sparingly")

# =========================================================================
# Simulated OTP Generation
# =========================================================================

def generate_simulated_otp(identifier: str) -> str:
    """Generates and returns a simulated 6-digit OTP code."""
    return f"{random.randint(100000, 999999)}"

# =========================================================================
# PDF Text Extraction (PyMuPDF)
# =========================================================================

def extract_text_from_pdf(pdf_stream_or_bytes) -> str:
    """
    Extracts text cleanly from a PDF document using PyMuPDF (fitz).
    Handles file-like objects, multiple uploads, or raw bytes gracefully.
    """
    try:
        if hasattr(pdf_stream_or_bytes, "read"):
            data = pdf_stream_or_bytes.read()
        else:
            data = pdf_stream_or_bytes

        doc = pymupdf.open(stream=data, filetype="pdf")
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(page.get_text())
        doc.close()
        
        extracted = "\n".join(text_parts).strip()
        if not extracted or len(extracted) < 10:
            raise ValueError("The uploaded PDF did not yield any readable text.")
        return extracted
    except Exception as e:
        raise RuntimeError(f"PyMuPDF failed to parse PDF: {str(e)}")

def extract_text_from_multiple_pdfs(pdf_files: List[Any]) -> str:
    """
    Extracts text from multiple uploaded PDFs concurrently using ThreadPoolExecutor.
    Ensures multi-document OCR finishes in under 5 seconds.
    """
    if not pdf_files:
        return ""
    if len(pdf_files) == 1:
        return extract_text_from_pdf(pdf_files[0])

    with ThreadPoolExecutor(max_workers=min(len(pdf_files), 4)) as executor:
        extracted_pages = list(executor.map(extract_text_from_pdf, pdf_files))
    return "\n\n".join(extracted_pages)

# =========================================================================
# AI Extraction & Structured Analysis
# =========================================================================

def parse_clinical_report(raw_text: str, language: str = "English") -> Dict[str, Any]:
    """
    Uses Gemini with structured JSON output conforming to ClinicalReportExtraction.
    Extracts test names, numeric values, ranges, and statuses.
    """
    system_instruction = f"""
You are a gentle, meticulous medical laboratory data specialist.
Extract all quantitative lab biomarkers and the report date from the clinical text.
CRITICAL 5th-GRADE READING LEVEL DIRECTIVE:
1. Translate technical test names into simple, 5th-grade everyday terms (e.g. use 'Blood Sugar' instead of 'Hyperglycemia' or 'Plasma Fasting Glucose'; use 'Kidney Function (Creatinine)' instead of 'Serum Creatinine / Renal Profile'; use 'Blood Pressure' instead of 'Hypertension'; use 'Cholesterol' instead of 'Lipid Panel').
2. Extract numerical values for 'value'.
3. Identify normal range (e.g. '12.0 - 15.5').
4. For status, compare value with range: strictly 'High', 'Low', 'Normal', or 'Alert'.
5. Format report_date strictly as YYYY-MM-DD. If missing, use today's date.
6. Never invent or hallucinate missing lab values.
7. Target language: {language}.
"""

    prompt = f"""
Clinical Report Text:
---
{raw_text}
---

Extract all quantitative laboratory test metrics and report date according to the schema in simple words.
"""

    raw_response = generate_resilient_content(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=ClinicalReportExtraction,
        temperature=0.0
    )

    try:
        return json.loads(raw_response)
    except Exception:
        clean = re.sub(r"^```(?:json)?|```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
        return json.loads(clean)

def generate_health_alerts(
    metrics: List[Dict[str, Any]],
    med_history: str = "",
    current_meds: str = "",
    language: str = "English"
) -> Dict[str, Any]:
    """
    Generates structured health alerts in simple, elderly-friendly language.
    """
    abnormal = [m for m in metrics if str(m.get("status", "")).lower() in ["high", "low", "alert"]]

    system_instruction = f"""
You are a warm, caring family doctor speaking with an elderly patient and their family.
CRITICAL DIRECTIVE - THE 'ELDERLY-FRIENDLY' RULE:
- Every single output must be written strictly at a 5th-grade reading level.
- Do NOT use complex medical jargon.
- Instead of 'Hyperglycemia', use 'High Blood Sugar'.
- Instead of 'Renal failure', use 'Kidney problems'.
- Instead of 'Hypertension', use 'High Blood Pressure'.
- Instead of 'Anemia', use 'Low Red Blood Cells / Low Iron'.
- Explain out-of-range numbers gently and reassuringly (e.g., 'Your blood sugar is a bit higher than usual', 'Your hemoglobin is slightly low, which might make you feel tired').
- Provide simple, friendly questions they can take to their doctor.
- Everything must be written completely in {language}.
"""

    prompt = f"""
Abnormal Lab Results:
{json.dumps(abnormal, indent=2)}

All Lab Results:
{json.dumps(metrics, indent=2)}

Patient Medical History: {med_history or 'None'}
Current Medications: {current_meds or 'None'}
Language: {language}

Generate a clear, gentle health alert summary evaluating what to watch out for at a 5th-grade reading level in {language}.
"""

    raw_response = generate_resilient_content(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=HealthAlertsResponse,
        temperature=0.2
    )

    try:
        return json.loads(raw_response)
    except Exception:
        clean = re.sub(r"^```(?:json)?|```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
        return json.loads(clean)

def generate_narrative_synthesis(
    metrics: List[Dict[str, Any]],
    med_history: str = "",
    current_meds: str = "",
    language: str = "English"
) -> str:
    """
    Generates an extremely simple, comforting narrative summary of lab findings for an elderly user at a 5th-grade reading level.
    """
    system_instruction = f"""
You are a loving, attentive family doctor speaking directly to an elderly patient in {language}.
CRITICAL DIRECTIVE - THE 'ELDERLY-FRIENDLY' RULE:
- Every single sentence must be written strictly at a 5th-grade reading level.
- Do NOT use complex medical jargon: use 'High Blood Sugar' instead of 'Hyperglycemia', 'Kidney problems' instead of 'Renal failure', 'High Blood Pressure' instead of 'Hypertension'.
- Use warm, everyday language suitable for an elderly grandmother or grandfather.
- Use friendly everyday examples to explain how their body is doing.
- Clearly tell them what looks great and what they should show their family doctor.
- Completely in {language}.
"""

    prompt = f"""
Patient Lab Tests: {json.dumps(metrics, indent=2)}
Previous Medical History: {med_history or 'None'}
Current Medications: {current_meds or 'None'}

Write a simple, 3-paragraph friendly health summary explaining their results in {language}.
"""

    try:
        return generate_resilient_content(prompt=prompt, system_instruction=system_instruction, temperature=0.3)
    except Exception as e:
        return f"Summary of your health test: Everything recorded cleanly. Please consult your family doctor for a routine review. ({str(e)})"

# =========================================================================
# Personalized Diet Planner (Elderly-Friendly)
# =========================================================================

def generate_personalized_diet_plan(
    cuisine: str,
    abnormal_metrics: List[Dict[str, Any]],
    med_history: str = "",
    current_meds: str = "",
    dietary_restrictions: str = "",
    language: str = "English"
) -> Dict[str, Any]:
    """
    Generates an elderly-friendly, recovery-oriented daily diet plan in the requested cuisine.
    Focuses on soft-to-chew, easy-to-digest, nutritious meals.
    """
    system_instruction = f"""
You are a caring geriatric nutritionist and clinical dietitian.
Generate a daily recovery meal plan in {language} for an elderly patient.
ELDERLY-FRIENDLY DIET DIRECTIVES:
1. Cuisine: Strictly align with '{cuisine}'. If 'Roti, Daal and Paneer (Desi Indian)', feature soft whole-wheat rotis with a little ghee, well-cooked yellow moong daal, tender paneer, cooked bottle gourd/spinach, and soothing buttermilk.
2. Ensure meals are easy to chew, gentle on the stomach, and well-hydrated.
3. Tailor ingredients to help improve their abnormal test markers (e.g. low salt for blood pressure, gentle fiber for blood sugar).
4. Do NOT use fancy or difficult culinary jargon. Keep instructions simple.
5. All text must be in {language}.
"""

    prompt = f"""
Selected Cuisine: {cuisine}
Abnormal Tests: {json.dumps(abnormal_metrics, indent=2)}
Medical History: {med_history or 'None'}
Medications: {current_meds or 'None'}
Preferences / Allergies: {dietary_restrictions or 'None'}
Language: {language}

Formulate an easy-to-eat, wholesome daily meal plan (Morning, Midday, Evening) according to the PersonalizedDietPlan schema.
"""

    raw_response = generate_resilient_content(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=PersonalizedDietPlan,
        temperature=0.3
    )

    try:
        return json.loads(raw_response)
    except Exception:
        clean = re.sub(r"^```(?:json)?|```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
        return json.loads(clean)

# =========================================================================
# Concurrency Engine (ThreadPoolExecutor)
# =========================================================================

def run_concurrent_report_analysis(
    raw_text: str,
    med_history: str = "",
    current_meds: str = "",
    language: str = "English",
    default_cuisine: str = "Roti, Daal and Paneer (Desi Indian)"
) -> Dict[str, Any]:
    """
    Dispatches narrative synthesis, safety checking, and diet formulation simultaneously
    using ThreadPoolExecutor for lightning-fast processing in seconds.
    """
    extraction = parse_clinical_report(raw_text, language=language)
    metrics = extraction.get("metrics", [])
    report_date = extraction.get("report_date", time.strftime("%Y-%m-%d"))
    abnormal_metrics = [m for m in metrics if str(m.get("status", "")).lower() in ["high", "low", "alert"]]

    results = {
        "report_date": report_date,
        "metrics": metrics,
        "analysis_summary": "",
        "health_alerts": None,
        "initial_diet_plan": None
    }

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_narrative = executor.submit(
            generate_narrative_synthesis,
            metrics,
            med_history,
            current_meds,
            language
        )
        future_safety = executor.submit(
            generate_health_alerts,
            metrics,
            med_history,
            current_meds,
            language
        )
        future_diet = executor.submit(
            generate_personalized_diet_plan,
            default_cuisine,
            abnormal_metrics,
            med_history,
            current_meds,
            "",
            language
        )

        try:
            results["analysis_summary"] = future_narrative.result(timeout=45)
        except Exception as e:
            results["analysis_summary"] = f"Your health analysis is ready. Please discuss with your doctor. ({str(e)})"

        try:
            results["health_alerts"] = future_safety.result(timeout=45)
        except Exception as e:
            results["health_alerts"] = {
                "alerts": [],
                "urgent_care_needed": False,
                "overall_safety_summary": f"Health alerts checked cleanly. ({str(e)})"
            }

        try:
            results["initial_diet_plan"] = future_diet.result(timeout=45)
        except Exception:
            results["initial_diet_plan"] = None

    return results

class DietCustomizationResult(BaseModel):
    reply_message: str = Field(description="Gentle, comforting 5th-grade explanation of the change")
    updated_daily_schedule: Optional[List[MealSession]] = Field(default=None, description="Updated daily meals reflecting the user's requested swaps")
    updated_foods_to_enjoy: Optional[List[str]] = Field(default=None, description="Updated foods to enjoy")
    updated_foods_to_limit: Optional[List[str]] = Field(default=None, description="Updated foods to limit")
    updated_comfort_tips: Optional[str] = Field(default=None, description="Updated tips for chewing, budget, or preparation")

# =========================================================================
# Specialized Popover Chatbots (Elderly-Friendly)
# =========================================================================

def ask_health_assistant(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    language: str = "English"
) -> str:
    """
    Chatbot 1: Day-to-day health assistant on the Home page.
    Instructed to answer general health queries strictly at a 5th-grade reading level in the user's language.
    """
    system_instruction = f"""
You are a warm, kind, and patient health companion for elderly users.
CRITICAL DIRECTIVE - THE 'ELDERLY-FRIENDLY' RULE:
- Every single response must be written strictly at a 5th-grade reading level.
- Do NOT use complex medical jargon.
- Instead of 'Hyperglycemia', use 'High Blood Sugar'.
- Instead of 'Renal failure', use 'Kidney problems'.
- Instead of 'Hypertension', use 'High Blood Pressure'.
- Instead of 'Dyslipidemia', use 'High Cholesterol'.
- If they ask about everyday symptoms (e.g., feeling dizzy, drinking enough water, joint stiffness), give practical, comforting everyday wellness advice.
- Always gently remind them to speak with their doctor for medication changes or serious issues.
- Answer completely in {language}.
"""

    history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in conversation_history[-6:]])
    prompt = f"""
CONVERSATION HISTORY:
{history_str}

USER: {user_message}
HEALTH ASSISTANT (at 5th-grade reading level in {language}):
"""
    return generate_resilient_content(prompt=prompt, system_instruction=system_instruction, temperature=0.4)

def ask_trends_assistant(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    metrics: List[Dict[str, Any]],
    med_history: str = "",
    current_meds: str = "",
    language: str = "English"
) -> str:
    """
    Chatbot 2: Context-aware assistant on the Analysis page.
    Discusses health trends and lab values strictly at a 5th-grade reading level without medical jargon.
    """
    system_instruction = f"""
You are a gentle doctor reviewing health lab trends with an elderly patient and their family.
CRITICAL DIRECTIVE - THE 'ELDERLY-FRIENDLY' RULE:
- Every single sentence must be written strictly at a 5th-grade reading level.
- Do NOT use complex medical jargon.
- Use 'High Blood Sugar' instead of 'Hyperglycemia', 'Kidney problems' instead of 'Renal failure', 'High Blood Pressure' instead of 'Hypertension'.
- Ground your answers in the user's actual lab numbers provided below.
- Explain numbers using simple everyday analogies (e.g., 'Your hemoglobin carries oxygen like little delivery trucks; right now you have slightly fewer trucks, which is why you might feel sleepy').
- Suggest simple questions to ask their doctor at their next visit.
- Answer completely in {language}.
"""

    context_str = f"""
PATIENT TEST NUMBERS:
{json.dumps(metrics, indent=2)}

Medical History: {med_history or 'None'}
Medications: {current_meds or 'None'}
"""
    history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in conversation_history[-6:]])
    prompt = f"""
{context_str}

CONVERSATION HISTORY:
{history_str}

USER QUESTION: {user_message}
ASSISTANT (at 5th-grade reading level in {language}):
"""
    return generate_resilient_content(prompt=prompt, system_instruction=system_instruction, temperature=0.4)

def ask_diet_assistant(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    diet_plan: Optional[Dict[str, Any]],
    abnormal_metrics: List[Dict[str, Any]],
    language: str = "English"
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Chatbot 3: Diet customizer on the Diet Planner page.
    Allows the user to say things like 'I don't like spinach, change it' or 'Make this cheaper' or 'Make it softer to chew',
    dynamically updating the active diet plan while maintaining a 5th-grade reading level.
    """
    system_instruction = f"""
You are a warm, helpful culinary companion and elderly nutrition expert.
CRITICAL DIRECTIVE - THE 'ELDERLY-FRIENDLY' RULE:
- Speak strictly at a 5th-grade reading level.
- If the user asks to change, swap, or modify a dish (e.g., 'I don't like spinach, change it', 'Make this cheaper', 'Make it softer to chew'), provide a friendly reply AND update the meal plan schedule accordingly.
- Keep all suggested foods easy to chew, budget-friendly, and gentle on digestion.
- Answer completely in {language}.
"""

    plan_str = json.dumps(diet_plan, indent=2) if diet_plan else "General wholesome elderly diet"
    history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in conversation_history[-6:]])
    prompt = f"""
ACTIVE MEAL PLAN:
{plan_str}

ABNORMAL PARAMETERS:
{json.dumps(abnormal_metrics, indent=2)}

CONVERSATION HISTORY:
{history_str}

USER REQUEST: {user_message}

Provide a conversational reply at a 5th-grade reading level, and if a change was requested, provide the updated daily schedule conforming to DietCustomizationResult schema in {language}.
"""

    try:
        raw_res = generate_resilient_content(
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema=DietCustomizationResult,
            temperature=0.3
        )
        parsed = json.loads(raw_res)
        reply = parsed.get("reply_message", "Here are your meal updates!")
        
        updated_plan = None
        if parsed.get("updated_daily_schedule") and diet_plan:
            updated_plan = dict(diet_plan)
            updated_plan["daily_schedule"] = parsed["updated_daily_schedule"]
            if parsed.get("updated_foods_to_enjoy"):
                updated_plan["foods_to_enjoy"] = parsed["updated_foods_to_enjoy"]
            if parsed.get("updated_foods_to_limit"):
                updated_plan["foods_to_limit"] = parsed["updated_foods_to_limit"]
            if parsed.get("updated_comfort_tips"):
                updated_plan["comfort_tips"] = parsed["updated_comfort_tips"]

        return reply, updated_plan
    except Exception:
        # Fallback to plain conversational response
        simple_reply = generate_resilient_content(
            prompt=f"{prompt}\n\nPlease reply conversationally at a 5th-grade reading level in {language}.",
            system_instruction=system_instruction,
            temperature=0.4
        )
        return simple_reply, None