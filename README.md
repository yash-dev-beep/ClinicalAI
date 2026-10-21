# ClinicalAI: Production-Ready AI Clinical Decision Support System

An enterprise-grade, modular clinical decision-support application built with **Streamlit, SQLite, PyMuPDF, Plotly, and the Google Gemini SDK**.

---

## 🌟 Key Features

1. **Modular 3-Tier Architecture**:
   - [`app.py`](file:///c:/Users/yashc/Downloads/project%20hood/app.py): Responsive Streamlit UI with persistent cookie sessions (`extra-streamlit-components`), native container layouts, and interactive Plotly visualizations.
   - [`database.py`](file:///c:/Users/yashc/Downloads/project%20hood/database.py): Relational SQLite storage with foreign key constraints, hashed security credentials, and transactional integrity enforcing `UNIQUE(user_id, report_date)`.
   - [`ai_engine.py`](file:///c:/Users/yashc/Downloads/project%20hood/ai_engine.py): Multi-model Gemini client (`gemini-flash-latest`, fallback tiers), `ThreadPoolExecutor` concurrent analysis, PyMuPDF parsing, and Pydantic structured JSON schemas.

2. **Multilingual Support (12 Languages)**:
   - Full flag-based selector, dropdown, and in-memory translation dictionary:
     - 🇺🇸 English, 🇮🇳 Hindi, 🇮🇳 Punjabi, 🇮🇳 Bengali, 🇮🇳 Marathi, 🇮🇳 Gujarati, 🇮🇳 Tamil, 🇮🇳 Telugu, 🇪🇸 Spanish, 🇫🇷 French, 🇨🇳 Mandarin, 🇸🇦 Arabic.
   - Selected language translates UI elements, AI clinical analysis, and interactive chatbots dynamically.

3. **Report Upload & Longitudinal Health Trends**:
   - PDF-only upload with PyMuPDF document extraction.
   - Graceful duplicate handling if a report with the same collection date already exists.
   - Color-coded abnormal findings table highlighting high, low, or alert biomarkers.
   - Plotly line charts displaying historical biomarker trajectories with shaded green normal reference range bands (`add_hrect`).

4. **Personalized Recovery Diet Planner**:
   - Interactive cuisine selector including **"Roti, Daal and Paneer"**, Mediterranean, Continental, South Indian, East Asian, Latin American, and Middle Eastern.
   - Generates morning, midday, and evening meals tailored to abnormal lab results and drug-nutrient safety.
   - Dedicated Dietary AI Chatbot for recipe instructions, ingredient substitutions, and portion adjustments.

5. **Context-Aware Clinical AI Chatbot**:
   - Clinically grounded assistant answering patient questions while enforcing safety guardrails and reminding users to consult attending physicians.

---

## 🚀 Quick Setup & Local Execution

### 1. Prerequisites & Environment
Ensure you have Python 3.10+ installed.

```bash
# Clone or navigate to the repository
cd "c:\Users\yashc\Downloads\project hood"

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # On Windows
source venv/bin/activate  # On Linux/macOS
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
Copy `.env.example` to `.env` and insert your Google Gemini API key:
```bash
cp .env.example .env
```
In `.env`:
```env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

### 4. Run the Verification Test Suite
```bash
python test_ui.py
```

### 5. Launch the Streamlit App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.
