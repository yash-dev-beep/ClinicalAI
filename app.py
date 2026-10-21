import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import re
import os
import random
from datetime import datetime
import extra_streamlit_components as stx

import database
import ai_engine

# =========================================================================
# Page Setup & Streamlit Configuration
# =========================================================================

st.set_page_config(
    page_title="ClinicalAI - Easy Health Companion",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema and tables
database.init_db()

# =========================================================================
# Module 2: 12-Language Translation Matrix
# =========================================================================

LANG_LIST = [
    {"id": "en", "name": "English 🇺🇸", "flag": "🇺🇸", "label": "English"},
    {"id": "hi", "name": "Hindi (हिंदी) 🇮🇳", "flag": "🇮🇳", "label": "हिंदी"},
    {"id": "pa", "name": "Punjabi (ਪੰਜਾਬੀ)", "flag": "🇮🇳", "label": "ਪੰਜਾਬੀ"},
    {"id": "bn", "name": "Bengali (বাংলা)", "flag": "🇮🇳", "label": "বাংলা"},
    {"id": "mr", "name": "Marathi (मराठी)", "flag": "🇮🇳", "label": "मराठी"},
    {"id": "ta", "name": "Tamil (தமிழ்)", "flag": "🇮🇳", "label": "தமிழ்"},
    {"id": "te", "name": "Telugu (తెలుగు)", "flag": "🇮🇳", "label": "తెలుగు"},
    {"id": "gu", "name": "Gujarati (ગુજરાતી)", "flag": "🇮🇳", "label": "ગુજરાતી"},
    {"id": "es", "name": "Spanish (Español) 🇪🇸", "flag": "🇪🇸", "label": "Español"},
    {"id": "fr", "name": "French (Français) 🇫🇷", "flag": "🇫🇷", "label": "Français"},
    {"id": "zh", "name": "Mandarin (中文) 🇨🇳", "flag": "🇨🇳", "label": "中文"},
    {"id": "ar", "name": "Arabic (العربية) 🇸🇦", "flag": "🇸🇦", "label": "العربية"}
]

TRANSLATIONS = {
    "English 🇺🇸": {
        "app_title": "ClinicalAI — Your Personal Health Companion",
        "app_sub": "Clear, gentle, and easy-to-read health updates for you and your family",
        "choose_lang": "Choose Your Language / अपनी भाषा चुनें:",
        "login_tab": "Sign In",
        "register_tab": "New Patient Register",
        "forgot_tab": "Forgot Password",
        "identifier_lbl": "Mobile Number or Email",
        "identifier_ph": "e.g., 9876543210 or yourname@gmail.com",
        "password_lbl": "Your Password",
        "password_ph": "Enter your password",
        "new_password_lbl": "Create a New Password",
        "send_otp_btn": "📩 Send Verification Code (OTP)",
        "otp_lbl": "Enter the 6-Digit Code",
        "otp_ph": "6-digit code",
        "register_btn": "✓ Verify Code & Create Account",
        "login_btn": "✓ Sign In Securely",
        "reset_btn": "✓ Update Password & Proceed",
        "sign_out": "🚪 Sign Out",
        "welcome": "Welcome back",
        "no_reports_title": "📄 Let's Review Your Lab Report",
        "no_reports_sub": "Upload your test paper or blood report PDF. We'll read it and explain everything in simple, friendly words.",
        "med_history_lbl": "Past Health Conditions (e.g., Blood Pressure, Sugar, None)",
        "med_history_ph": "e.g., High Blood Pressure for 5 years, Mild Sugar, None...",
        "current_meds_lbl": "Daily Medicines You Take",
        "current_meds_ph": "e.g., 1 tablet blood pressure pill in morning, vitamin D...",
        "upload_lbl": "Select Your Lab Report Papers (PDF files)",
        "analyze_btn": "🔍 Analyze My Health Reports",
        "trends_header": "📈 Your Health Trends Over Time",
        "trends_sub": "Here is how your health numbers look over time. Green shaded areas mean healthy normal numbers.",
        "select_marker_lbl": "Select Health Test to View:",
        "alerts_header": "🔔 Important Things to Know From Your Report",
        "alerts_sub": "Carefully color-coded for your comfort. Red means ask your doctor; Green means healthy.",
        "alert_badge": "⚠️ Alert / Check with Doctor",
        "good_badge": "✅ All Good & Healthy",
        "upload_more": "➕ Add Another Test Report (PDF)",
        "diet_tab_btn": "🥗 My Recovery Diet Plan",
        "trends_tab_btn": "📊 Health Trends & Reports",
        "diet_header": "🥗 Nutritious, Easy-to-Digest Recovery Diet",
        "diet_sub": "Click any cuisine below to get delicious, soft, and healthy meals tailored to your test results.",
        "cuisine_roti": "🫓 Roti, Daal and Paneer (Desi Indian)",
        "cuisine_south": "🍲 South Indian (Soft Idli, Sambar & Rasam)",
        "cuisine_med": "🫒 Mediterranean (Heart Healthy)",
        "cuisine_diabetic": "🌾 Diabetic Friendly (Low Sugar & High Fiber)",
        "cuisine_heart": "❤️ Heart Friendly (Low Salt & Tender)",
        "generate_diet_btn": "✨ Create My Personal Meal Plan",
        "diet_chat_popover": "🧑🍳 Customize My Diet",
        "trends_chat_popover": "🤖 Discuss My Health Trends",
        "health_chat_popover": "💬 Ask Health Assistant",
        "popover_ph": "Type your question here in simple words...",
        "safety_disclaimer": "💙 Health Note: This tool provides simple everyday educational support. Always consult your attending doctor before changing medicines."
    },
    "Hindi (हिंदी) 🇮🇳": {
        "app_title": "क्लिनिकल एआई — आपका सरल स्वास्थ्य साथी",
        "app_sub": "आपके और आपके परिवार के लिए सरल, स्पष्ट और आसान भाषा में स्वास्थ्य जानकारी",
        "choose_lang": "अपनी भाषा चुनें:",
        "login_tab": "साइन इन करें",
        "register_tab": "नया खाता बनाएं",
        "forgot_tab": "पासवर्ड भूल गए?",
        "identifier_lbl": "मोबाइल नंबर या ईमेल",
        "identifier_ph": "जैसे: 9876543210 या yourname@gmail.com",
        "password_lbl": "आपका पासवर्ड",
        "password_ph": "अपना पासवर्ड दर्ज करें",
        "new_password_lbl": "नया पासवर्ड बनाएं",
        "send_otp_btn": "📩 ओटीपी (OTP) कोड भेजें",
        "otp_lbl": "6-अंकीय कोड दर्ज करें",
        "otp_ph": "6 अंकों का कोड",
        "register_btn": "✓ कोड सत्यापित करें और खाता बनाएं",
        "login_btn": "✓ सुरक्षित साइन इन करें",
        "reset_btn": "✓ पासवर्ड बदलें और आगे बढ़ें",
        "sign_out": "🚪 लॉग आउट",
        "welcome": "नमस्ते",
        "no_reports_title": "📄 आइए आपकी लैब रिपोर्ट समझें",
        "no_reports_sub": "अपनी खून या लैब जांच की पीडीएफ अपलोड करें। हम इसे सरल भाषा में समझाएंगे।",
        "med_history_lbl": "पुरानी बीमारियां (जैसे: बीपी, शुगर, कुछ नहीं)",
        "med_history_ph": "जैसे: 5 साल से बीपी, थोड़ी शुगर, कोई नहीं...",
        "current_meds_lbl": "रोज ली जाने वाली दवाएं",
        "current_meds_ph": "जैसे: सुबह बीपी की 1 गोली, विटामिन डी...",
        "upload_lbl": "अपनी जांच रिपोर्ट चुनें (PDF फाइल)",
        "analyze_btn": "🔍 मेरी रिपोर्ट का विश्लेषण करें",
        "trends_header": "📈 समय के साथ आपके स्वास्थ्य का हाल",
        "trends_sub": "हरा रंग सामान्य स्वस्थ सीमा दिखाता है। ग्राफ में आपकी रिपोर्ट की प्रगति देखें।",
        "select_marker_lbl": "जांच का नाम चुनें:",
        "alerts_header": "🔔 रिपोर्ट से जुड़ी जरूरी सावधानियां",
        "alerts_sub": "लाल रंग का मतलब है डॉक्टर से पूछें; हरे रंग का मतलब है सब ठीक है।",
        "alert_badge": "⚠️ डॉक्टर से सलाह लें",
        "good_badge": "✅ सब सामान्य और स्वस्थ है",
        "upload_more": "➕ नई जांच रिपोर्ट जोड़ें (PDF)",
        "diet_tab_btn": "🥗 स्वास्थ्य सुधार आहार योजना",
        "trends_tab_btn": "📊 स्वास्थ्य रुझान और रिपोर्ट",
        "diet_header": "🥗 पौष्टिक और सुपाच्य आहार योजना",
        "diet_sub": "अपनी पसंद के भोजन पर क्लिक करें और रिपोर्ट अनुसार हल्का व पौष्टिक आहार पाएं।",
        "cuisine_roti": "🫓 रोटी, दाल और पनीर (देसी भारतीय भोजन)",
        "cuisine_south": "🍲 दक्षिण भारतीय (नरम इडली, सांभर व रसम)",
        "cuisine_med": "🫒 दिल के लिए स्वस्थ (हल्का जैतून व सब्जियां)",
        "cuisine_diabetic": "🌾 शुगर के लिए सुरक्षित (कम मीठा, उच्च फाइबर)",
        "cuisine_heart": "❤️ दिल की सेहत (कम नमक, नरम व हल्का भोजन)",
        "generate_diet_btn": "✨ मेरा भोजन प्लान बनाएं",
        "diet_chat_popover": "🧑🍳 आहार में बदलाव पूछें",
        "trends_chat_popover": "🤖 अपनी रिपोर्ट पर चर्चा करें",
        "health_chat_popover": "💬 स्वास्थ्य सहायक से पूछें",
        "popover_ph": "सरल शब्दों में अपना सवाल यहां लिखें...",
        "safety_disclaimer": "💙 स्वास्थ्य सलाह: यह ऐप केवल सामान्य मार्गदर्शन के लिए है। दवाएं बदलने से पहले डॉक्टर से जरूर पूछें।"
    },
    "Punjabi (ਪੰਜਾਬੀ)": {
        "app_title": "ਕਲੀਨਿਕਲ ਏਆਈ — ਤੁਹਾਡਾ ਸਿਹਤ ਸਾਥੀ",
        "app_sub": "ਤੁਹਾਡੇ ਅਤੇ ਤੁਹਾਡੇ ਪਰਿਵਾਰ ਲਈ ਸਰਲ ਅਤੇ ਆਸਾਨ ਸਿਹਤ ਜਾਣਕਾਰੀ",
        "choose_lang": "ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ:",
        "login_tab": "ਸਾਈਨ ਇਨ",
        "register_tab": "ਨਵਾਂ ਖਾਤਾ ਬਣਾਓ",
        "forgot_tab": "ਪਾਸਵਰਡ ਭੁੱਲ ਗਏ?",
        "identifier_lbl": "ਮੋਬਾਈਲ ਨੰਬਰ ਜਾਂ ਈਮੇਲ",
        "identifier_ph": "ਉਦਾਹਰਨ: 9876543210",
        "password_lbl": "ਪਾਸਵਰਡ",
        "password_ph": "ਪਾਸਵਰਡ ਭਰੋ",
        "new_password_lbl": "ਨਵਾਂ ਪਾਸਵਰਡ ਬਣਾਓ",
        "send_otp_btn": "📩 ਓਟੀਪੀ (OTP) ਭੇਜੋ",
        "otp_lbl": "6-ਅੰਕੀ ਕੋਡ ਭਰੋ",
        "otp_ph": "6 ਅੰਕਾਂ ਦਾ ਕੋਡ",
        "register_btn": "✓ ਖਾਤਾ ਬਣਾਓ",
        "login_btn": "✓ ਸਾਈਨ ਇਨ",
        "reset_btn": "✓ ਪਾਸਵਰਡ ਬਦਲੋ",
        "sign_out": "🚪 ਲਾਗ ਆਉਟ",
        "welcome": "ਜੀ ਆਇਆਂ ਨੂੰ",
        "no_reports_title": "📄 ਆਓ ਤੁਹਾਡੀ ਰਿਪੋਰਟ ਸਮਝੀਏ",
        "no_reports_sub": "ਆਪਣੀ ਲੈਬ ਟੈਸਟ ਰਿਪੋਰਟ ਪੀਡੀਐਫ ਅੱਪਲੋਡ ਕਰੋ।",
        "med_history_lbl": "ਪੁਰਾਣੀਆਂ ਬਿਮਾਰੀਆਂ (ਬੀਪੀ, ਖੰਡ ਆਦਿ)",
        "med_history_ph": "ਉਦਾਹਰਨ: ਬੀਪੀ, ਸ਼ੂਗਰ...",
        "current_meds_lbl": "ਰੋਜ਼ਾਨਾ ਦਵਾਈਆਂ",
        "current_meds_ph": "ਉਦਾਹਰਨ: ਸਵੇਰੇ ਬੀਪੀ ਦੀ ਗੋਲੀ...",
        "upload_lbl": "ਰਿਪੋਰਟ ਚੁਣੋ (PDF ਫਾਈਲਾਂ)",
        "analyze_btn": "🔍 ਰਿਪੋਰਟ ਦੀ ਜਾਂਚ ਕਰੋ",
        "trends_header": "📈 ਤੁਹਾਡੀ ਸਿਹਤ ਦੇ ਰੁਝਾਨ",
        "trends_sub": "ਹਰਾ ਰੰਗ ਨਾਰਮਲ ਸਿਹਤ ਦਰਸਾਉਂਦਾ ਹੈ।",
        "select_marker_lbl": "ਟੈਸਟ ਦਾ ਨਾਂ ਚੁਣੋ:",
        "alerts_header": "🔔 ਜ਼ਰੂਰੀ ਸਾਵਧਾਨੀਆਂ",
        "alerts_sub": "ਲਾਲ ਰੰਗ ਮਤਲਬ ਡਾਕਟਰ ਨਾਲ ਗੱਲ ਕਰੋ; ਹਰਾ ਮਤਲਬ ਸਭ ਠੀਕ ਹੈ।",
        "alert_badge": "⚠️ ਡਾਕਟਰ ਨਾਲ ਸੰਪਰਕ ਕਰੋ",
        "good_badge": "✅ ਸਭ ਨਾਰਮਲ ਹੈ",
        "upload_more": "➕ ਹੋਰ ਰਿਪੋਰਟ ਜੋੜੋ (PDF)",
        "diet_tab_btn": "🥗 ਭੋਜਨ ਯੋਜਨਾ",
        "trends_tab_btn": "📊 ਸਿਹਤ ਰੁਝਾਨ",
        "diet_header": "🥗 ਪੌਸ਼ਟਿਕ ਅਤੇ ਹਲਕਾ ਭੋਜਨ",
        "diet_sub": "ਸੁਆਦੀ ਅਤੇ ਹਲਕਾ ਖਾਣਾ ਪ੍ਰਾਪਤ ਕਰੋ।",
        "cuisine_roti": "🫓 ਰੋਟੀ, ਦਾਲ ਅਤੇ ਪਨੀਰ (ਦੇਸੀ ਖਾਣਾ)",
        "cuisine_south": "🍲 ਦੱਖਣੀ ਭਾਰਤੀ (ਨਰਮ ਇਡਲੀ, ਸਾਂਭਰ)",
        "cuisine_med": "🫒 ਦਿਲ ਲਈ ਚੰਗਾ ਭੋਜਨ",
        "cuisine_diabetic": "🌾 ਸ਼ੂਗਰ ਕੰਟਰੋਲ ਭੋਜਨ",
        "cuisine_heart": "❤️ ਦਿਲ ਦੀ ਸਿਹਤ (ਘੱਟ ਲੂਣ)",
        "generate_diet_btn": "✨ ਡਾਈਟ ਪਲਾਨ ਬਣਾਓ",
        "diet_chat_popover": "🧑🍳 ਡਾਈਟ ਸਲਾਹਕਾਰ",
        "trends_chat_popover": "🤖 ਰਿਪੋਰਟ ਸਲਾਹਕਾਰ",
        "health_chat_popover": "💬 ਸਿਹਤ ਸਾਥੀ",
        "popover_ph": "ਆਪਣਾ ਸਵਾਲ ਇੱਥੇ ਪੁੱਛੋ...",
        "safety_disclaimer": "💙 ਸਿਹਤ ਸਲਾਹ: ਦਵਾਈ ਬਦਲਣ ਤੋਂ ਪਹਿਲਾਂ ਆਪਣੇ ਡਾਕਟਰ ਦੀ ਸਲਾਹ ਜ਼ਰੂਰ ਲਵੋ।"
    },
    "Bengali (বাংলা)": {
        "app_title": "ক্লিনিক্যাল এআই — আপনার স্বাস্থ্য সঙ্গী",
        "app_sub": "সহজ ও স্পষ্ট ভাষায় আপনার স্বাস্থ্য রিপোর্ট বুঝুন",
        "choose_lang": "ভাষা নির্বাচন করুন:",
        "login_tab": "সাইন ইন",
        "register_tab": "নতুন অ্যাকাউন্ট তৈরি করুন",
        "forgot_tab": "পাসওয়ার্ড ভুলে গেছেন?",
        "identifier_lbl": "মোবাইল নম্বর বা ইমেল",
        "identifier_ph": "যেমন: 9876543210",
        "password_lbl": "পাসওয়ার্ড",
        "password_ph": "পাসওয়ার্ড দিন",
        "new_password_lbl": "নতুন পাসওয়ার্ড দিন",
        "send_otp_btn": "📩 ওটিপি (OTP) পাঠান",
        "otp_lbl": "৬ সংখ্যার কোড লিখুন",
        "otp_ph": "৬ সংখ্যার কোড",
        "register_btn": "✓ অ্যাকাউন্ট তৈরি করুন",
        "login_btn": "✓ সাইন ইন করুন",
        "reset_btn": "✓ পাসওয়ার্ড পরিবর্তন করুন",
        "sign_out": "🚪 লগ আউট",
        "welcome": "স্বাগতম",
        "no_reports_title": "📄 আপনার ল্যাব রিপোর্ট দেখুন",
        "no_reports_sub": "আপনার রক্ত পরীক্ষার রিপোর্ট আপলোড করুন। আমরা সহজে বুঝিয়ে দেব।",
        "med_history_lbl": "পুরোনো রোগ (যেমন: রক্তচাপ, সুগার)",
        "med_history_ph": "যেমন: উচ্চ রক্তচাপ, ডায়াবেটিস...",
        "current_meds_lbl": "প্রতিদিনের ওষুধ",
        "current_meds_ph": "ওষুধের নাম লিখুন...",
        "upload_lbl": "রিপোর্ট নির্বাচন করুন (PDF)",
        "analyze_btn": "🔍 রিপোর্ট বিশ্লেষণ করুন",
        "trends_header": "📈 আপনার স্বাস্থ্যের পরিবর্তন",
        "trends_sub": "সবুজ রঙ স্বাভাবিক মাত্রা নির্দেশ করে।",
        "select_marker_lbl": "পরীক্ষার নাম নির্বাচন করুন:",
        "alerts_header": "🔔 প্রয়োজনীয় সতর্কতা",
        "alerts_sub": "লাল মানে ডাক্তারকে জানান; সবুজ মানে স্বাভাবিক।",
        "alert_badge": "⚠️ ডাক্তারের সাথে যোগাযোগ করুন",
        "good_badge": "✅ সবকিছু স্বাভাবিক",
        "upload_more": "➕ আরও রিপোর্ট যোগ করুন (PDF)",
        "diet_tab_btn": "🥗 খাদ্য পরিকল্পনা",
        "trends_tab_btn": "📊 স্বাস্থ্য রিপোর্ট",
        "diet_header": "🥗 পুষ্টিকর ও সহজপাচ্য খাদ্য পরিকল্পনা",
        "diet_sub": "আপনার পছন্দসই খাবার বেছে নিন।",
        "cuisine_roti": "🫓 রুটি, ডাল এবং পনির (দেশি খাবার)",
        "cuisine_south": "🍲 দক্ষিণ ভারতীয় (নরম ইডলি ও সম্বর)",
        "cuisine_med": "🫒 হার্টের জন্য ভালো খাবার",
        "cuisine_diabetic": "🌾 ডায়াবেটিস সহায়ক খাদ্য",
        "cuisine_heart": "❤️ হার্ট ফ্রেন্ডলি (কম নুন)",
        "generate_diet_btn": "✨ ডায়েট প্ল্যান তৈরি করুন",
        "diet_chat_popover": "🧑🍳 ডায়েট সহকারী",
        "trends_chat_popover": "🤖 রিপোর্ট সহকারী",
        "health_chat_popover": "💬 স্বাস্থ্য সহকারী",
        "popover_ph": "সহজ ভাষায় আপনার প্রশ্ন লিখুন...",
        "safety_disclaimer": "💙 স্বাস্থ্য তথ্য: ওষুধ পরিবর্তনের আগে অবশ্যই ডাক্তারের পরামর্শ নিন।"
    },
    "Marathi (मराठी)": {
        "app_title": "क्लिनिकल एआय — तुमचा आरोग्य मित्र",
        "app_tagline": "तुमच्या आरोग्याची सोप्या भाषेतील माहिती",
        "choose_lang": "भाषा निवडा:",
        "login_tab": "साइन इन",
        "register_tab": "नवीन खाते उघडा",
        "forgot_tab": "पासवर्ड विसरलात?",
        "identifier_lbl": "मोबाइल नंबर किंवा ईमेल",
        "identifier_ph": "उदा. 9876543210",
        "password_lbl": "पासवर्ड",
        "password_ph": "पासवर्ड टाका",
        "new_password_lbl": "नवीन पासवर्ड टाका",
        "send_otp_btn": "📩 ओटीपी कोड पाठवा",
        "otp_lbl": "६ अंकी कोड टाका",
        "otp_ph": "६ अंकी कोड",
        "register_btn": "✓ खाते तयार करा",
        "login_btn": "✓ साइन इन",
        "reset_btn": "✓ पासवर्ड बदला",
        "sign_out": "🚪 बाहेर पडा",
        "welcome": "स्वागत आहे",
        "no_reports_title": "📄 तुमचा लॅब रिपोर्ट समजून घेऊया",
        "no_reports_sub": "तुमचा तपासणी अहवाल अपलोड करा. आम्ही तो सोप्या भाषेत समजावून सांगू.",
        "med_history_lbl": "मागील आजार (उदा. बीपी, शुगर)",
        "med_history_ph": "उदा. बीपी, मधुमेह...",
        "current_meds_lbl": "सध्या सुरू असलेली औषधे",
        "current_meds_ph": "सकाळची बीपी गोळी इ...",
        "upload_lbl": "रिपोर्ट निवडा (PDF)",
        "analyze_btn": "🔍 अहवाल तपासा",
        "trends_header": "📈 आरोग्याचा आलेख",
        "trends_sub": "हिरवा रंग सामान्य श्रेणी दर्शवतो.",
        "select_marker_lbl": "तपासणी निवडा:",
        "alerts_header": "🔔 महत्त्वाच्या सूचना",
        "alerts_sub": "लाल रंग म्हणजे डॉक्टरांचा सल्ला घ्या; हिरवा म्हणजे सर्व ठीक आहे.",
        "alert_badge": "⚠️ डॉक्टरांशी बोला",
        "good_badge": "✅ सर्व सामान्य आहे",
        "upload_more": "➕ नवीन रिपोर्ट जोडा (PDF)",
        "diet_tab_btn": "🥗 आहार योजना",
        "trends_tab_btn": "📊 आरोग्य कल",
        "diet_header": "🥗 पौष्टिक व पचायला हलका आहार",
        "diet_sub": "तुमच्या आवडीनुसार आरोग्यदायी जेवण योजना मिळवा.",
        "cuisine_roti": "🫓 पोळी, डाळ आणि पनीर (घरगुती जेवण)",
        "cuisine_south": "🍲 दक्षिण भारतीय (मऊ इडली, सांबार)",
        "cuisine_med": "🫒 हृदयासाठी आरोग्यदायी",
        "cuisine_diabetic": "🌾 मधुमेह नियंत्रण आहार",
        "cuisine_heart": "❤️ कमी मिठाचे जेवण",
        "generate_diet_btn": "✨ आहार योजना तयार करा",
        "diet_chat_popover": "🧑🍳 आहार सहाय्यक",
        "trends_chat_popover": "🤖 रिपोर्ट सहाय्यक",
        "health_chat_popover": "💬 आरोग्य सहाय्यक",
        "popover_ph": "तुमचा प्रश्न येथे विचारा...",
        "safety_disclaimer": "💙 सूचना: औषध बदलण्यापूर्वी डॉक्टरांचा सल्ला नक्की घ्या."
    },
    "Tamil (தமிழ்)": {
        "app_title": "கிளினிக்கல் ஏஐ — உங்கள் நல்வாழ்வு துணை",
        "app_sub": "எளிமையான தமிழில் உங்கள் மருத்துவ அறிக்கை விளக்கம்",
        "choose_lang": "மொழியைத் தேர்ந்தெடுக்கவும்:",
        "login_tab": "உள்நுழைக",
        "register_tab": "பதிவு செய்க",
        "forgot_tab": "கடவுச்சொல் மறந்துவிட்டதா?",
        "identifier_lbl": "தொலைபேசி எண் அல்லது மின்னஞ்சல்",
        "identifier_ph": "எ.கா: 9876543210",
        "password_lbl": "கடவுச்சொல்",
        "password_ph": "கடவுச்சொல்லை உள்ளிடவும்",
        "new_password_lbl": "புதிய கடவுச்சொல்",
        "send_otp_btn": "📩 ஓடிபி பெறுக",
        "otp_lbl": "6 இலக்க குறியீடு",
        "otp_ph": "6 இலக்க குறியீடு",
        "register_btn": "✓ பதிவு செய்க",
        "login_btn": "✓ உள்நுழைக",
        "reset_btn": "✓ கடவுச்சொல் மாற்றுக",
        "sign_out": "🚪 வெளியேறு",
        "welcome": "வணக்கம்",
        "no_reports_title": "📄 மருத்துவ அறிக்கையை பதிவேற்றவும்",
        "no_reports_sub": "உங்கள் இரத்தப் பரிசோதனை அறிக்கையை எளிமையாகப் புரிந்துகொள்ளலாம்.",
        "med_history_lbl": "முந்தைய நோய்கள் (எ.கா: சர்க்கரை, பிரஷர்)",
        "med_history_ph": "சர்க்கரை நோய், இரத்த அழுத்தம்...",
        "current_meds_lbl": "தற்போது உட்கொள்ளும் மருந்துகள்",
        "current_meds_ph": "மருந்துகளின் பெயர்கள்...",
        "upload_lbl": "அறிக்கையைத் தேர்ந்தெடுக்கவும் (PDF)",
        "analyze_btn": "🔍 அறிக்கையை ஆய்வு செய்க",
        "trends_header": "📈 உங்கள் உடல்நல மாற்றங்கள்",
        "trends_sub": "பச்சை நிறம் ஆரோக்கியமான அளவைக் குறிக்கிறது.",
        "select_marker_lbl": "பரிசோதனையைத் தேர்வு செய்க:",
        "alerts_header": "🔔 கவனிக்க வேண்டியவை",
        "alerts_sub": "சிவப்பு நிறம் மருத்துவரை அணுக வேண்டும் என்பதைக் குறிக்கிறது.",
        "alert_badge": "⚠️ மருத்துவரிடம் கேட்கவும்",
        "good_badge": "✅ அனைத்தும் நலம்",
        "upload_more": "➕ புதிய அறிக்கை சேர்க்க (PDF)",
        "diet_tab_btn": "🥗 உணவு முறை",
        "trends_tab_btn": "📊 உடல்நல விவரம்",
        "diet_header": "🥗 ஆரோக்கிய உணவு திட்டம்",
        "diet_sub": "சுவையான மற்றும் ஆரோக்கியமான உணவு முறையைத் தேர்வு செய்க.",
        "cuisine_roti": "🫓 சப்பாத்தி, பருப்பு மற்றும் பனீர்",
        "cuisine_south": "🍲 தென்னிந்திய உணவு (மென்மையான இட்லி, சாம்பார்)",
        "cuisine_med": "🫒 இதயத்திற்கு ஏற்ற உணவு",
        "cuisine_diabetic": "🌾 சர்க்கரை கட்டுப்பாட்டு உணவு",
        "cuisine_heart": "❤️ குறைந்த உப்பு உணவு",
        "generate_diet_btn": "✨ உணவு அட்டவணை உருவாக்குக",
        "diet_chat_popover": "🧑🍳 உணவு ஆலோசகர்",
        "trends_chat_popover": "🤖 அறிக்கை உதவியாளர்",
        "health_chat_popover": "💬 நல்வாழ்வு உதவியாளர்",
        "popover_ph": "உங்கள் கேள்வியை இங்கே கேட்கவும்...",
        "safety_disclaimer": "💙 குறிப்பு: மருந்துகளை மாற்றும் முன் மருத்துவரிடம் ஆலோசிக்கவும்."
    },
    "Telugu (తెలుగు)": {
        "app_title": "క్లినికల్ ఏఐ — మీ ఆరోగ్య నేస్తం",
        "app_sub": "సులభమైన మాటల్లో మీ ఆరోగ్య సమాచారం",
        "choose_lang": "భాషను ఎంచుకోండి:",
        "login_tab": "లాగిన్",
        "register_tab": "కొత్త ఖాతా",
        "forgot_tab": "పాస్‌వర్డ్ మర్చిపోయారా?",
        "identifier_lbl": "ఫోన్ నంబర్ లేదా ఈమెయిల్",
        "identifier_ph": "ఉదా: 9876543210",
        "password_lbl": "పాస్‌వర్డ్",
        "password_ph": "పాస్‌వర్డ్ నమోదు చేయండి",
        "new_password_lbl": "కొత్త పాస్‌వర్డ్",
        "send_otp_btn": "📩 ఓటీపీ పంపండి",
        "otp_lbl": "6 అంకెల కోడ్",
        "otp_ph": "6 అంకెల కోడ్",
        "register_btn": "✓ నమోదు చేసుకోండి",
        "login_btn": "✓ లాగిన్ అవ్వండి",
        "reset_btn": "✓ పాస్‌వర్డ్ మార్చండి",
        "sign_out": "🚪 లాగౌట్",
        "welcome": "స్వాగతం",
        "no_reports_title": "📄 మీ రిపోర్ట్‌ను పరిశీలిద్దాం",
        "no_reports_sub": "మీ రక్త పరీక్ష రిపోర్ట్ అప్‌లోడ్ చేయండి. సులభంగా వివరిస్తాం.",
        "med_history_lbl": "గత ఆరోగ్య సమస్యలు (బీపీ, షుగర్ మొదలైనవి)",
        "med_history_ph": "షుగర్, బీపీ...",
        "current_meds_lbl": "వాడుతున్న మందులు",
        "current_meds_ph": "మందుల వివరాలు...",
        "upload_lbl": "రిపోర్ట్ ఫైల్ ఎంచుకోండి (PDF)",
        "analyze_btn": "🔍 విశ్లేషించండి",
        "trends_header": "📈 మీ ఆరోగ్య ప్రగతి",
        "trends_sub": "ఆకుపచ్చ రంగు ఆరోగ్యకరమైన పరిధిని సూచిస్తుంది.",
        "select_marker_lbl": "పరీక్ష పేరు ఎంచుకోండి:",
        "alerts_header": "🔔 ముఖ్యమైన హెచ్చరికలు",
        "alerts_sub": "ఎరుపు రంగు అంటే డాక్టర్‌ను సంప్రదించాలి; ఆకుపచ్చ అంటే అంతా బాగుంది.",
        "alert_badge": "⚠️ డాక్టర్‌ను సంప్రదించండి",
        "good_badge": "✅ అంతా బాగుంది",
        "upload_more": "➕ మరో రిపోర్ట్ జోడించండి (PDF)",
        "diet_tab_btn": "🥗 ఆహార ప్రణాళిక",
        "trends_tab_btn": "📊 ఆరోగ్య నివేదిక",
        "diet_header": "🥗 ఆరోగ్యకరమైన తేలికపాటి ఆహారం",
        "diet_sub": "మీకు నచ్చిన ఆహార శైలిని ఎంచుకోండి.",
        "cuisine_roti": "🫓 రొట్టె, పప్పు మరియు పన్నీర్",
        "cuisine_south": "🍲 దక్షిణ భారత భోజనం (ఇడ్లీ, సాంబార్)",
        "cuisine_med": "🫒 గుండెకు మంచి ఆహారం",
        "cuisine_diabetic": "🌾 షుగర్ నియంత్రణ ఆహారం",
        "cuisine_heart": "❤️ తక్కువ ఉప్పు ఆహారం",
        "generate_diet_btn": "✨ ఆహార పట్టిక తయారు చేయండి",
        "diet_chat_popover": "🧑🍳 ఆహార సహాయకుడు",
        "trends_chat_popover": "🤖 రిపోర్ట్ సహాయకుడు",
        "health_chat_popover": "💬 ఆరోగ్య సహాయకుడు",
        "popover_ph": "మీ సందేహాన్ని ఇక్కడ అడగండి...",
        "safety_disclaimer": "💙 గమనిక: మందులు మార్చే ముందు మీ డాక్టర్‌ను సంప్రదించండి."
    },
    "Gujarati (ગુજરાતી)": {
        "app_title": "ક્લિનિકલ એઆઈ — તમારો આરોગ્ય સાથી",
        "app_sub": "સરળ ગુજરાતીમાં તમારા લેબ રિપોર્ટની સમજૂતી",
        "choose_lang": "ભાષા પસંદ કરો:",
        "login_tab": "સાઇન ઇન",
        "register_tab": "નવું ખાતું ખોલો",
        "forgot_tab": "પાસવર્ડ ભૂલી ગયા?",
        "identifier_lbl": "મોબાઇલ નંબર અથવા ઇમેઇલ",
        "identifier_ph": "દા.ત. 9876543210",
        "password_lbl": "પાસવર્ડ",
        "password_ph": "પાસવર્ડ દાખલ કરો",
        "new_password_lbl": "નવો પાસવર્ડ બનાવો",
        "send_otp_btn": "📩 ઓટીપી (OTP) મેળવો",
        "otp_lbl": "૬ અંકનો કોડ દાખલ કરો",
        "otp_ph": "૬ અંકનો કોડ",
        "register_btn": "✓ ખાતું બનાવો",
        "login_btn": "✓ સાઇન ઇન કરો",
        "reset_btn": "✓ પાસવર્ડ બદલો",
        "sign_out": "🚪 બહાર નીકળો",
        "welcome": "આવકારો",
        "no_reports_title": "📄 તમારો ટેસ્ટ રિપોર્ટ સમજો",
        "no_reports_sub": "તમારો બ્લડ ટેસ્ટ રિપોર્ટ અપલોડ કરો. સરળ ભાષામાં સમજી શકાશે.",
        "med_history_lbl": "જૂની બીમારીઓ (બીપી, ડાયાબિટીસ વગેરે)",
        "med_history_ph": "બ્લડ પ્રેશર, સુગર...",
        "current_meds_lbl": "રોજિંદી દવાઓ",
        "current_meds_ph": "દવાઓનું નામ...",
        "upload_lbl": "રિપોર્ટ પસંદ કરો (PDF)",
        "analyze_btn": "🔍 રિપોર્ટ તપાસો",
        "trends_header": "📈 સ્વાસ્થ્યના આંકડા",
        "trends_sub": "લીલો રંગ સામાન્ય સ્વાસ્થ્ય દર્શાવે છે.",
        "select_marker_lbl": "ટેસ્ટ પસંદ કરો:",
        "alerts_header": "🔔 જરૂરી સૂચનાઓ",
        "alerts_sub": "લાલ રંગ એટલે ડૉક્ટરની સલાહ લો; લીલો એટલે બધું બરાબર છે.",
        "alert_badge": "⚠️ ડૉક્ટરનો સંપર્ક કરો",
        "good_badge": "✅ બધું સામાન્ય છે",
        "upload_more": "➕ નવો રિપોર્ટ ઉમેરો (PDF)",
        "diet_tab_btn": "🥗 આહાર યોજના",
        "trends_tab_btn": "📊 હેલ્થ ટ્રેન્ડ્સ",
        "diet_header": "🥗 પૌષ્ટિક અને હળવો આહાર",
        "diet_sub": "તમારી પસંદગી અનુસાર આહાર યોજના મેળવો.",
        "cuisine_roti": "🫓 રોટલી, દાળ અને પનીર (દેશી ભોજન)",
        "cuisine_south": "🍲 દક્ષિણ ભારતીય (પોચી ઇડલી, સંભાર)",
        "cuisine_med": "🫒 હૃદય માટે સારું ભોજન",
        "cuisine_diabetic": "🌾 ડાયાબિટીસ નિયંત્રણ આહાર",
        "cuisine_heart": "❤️ ઓછું મીઠું ધરાવતો આહાર",
        "generate_diet_btn": "✨ ડાયેટ પ્લાન બનાવો",
        "diet_chat_popover": "🧑🍳 આહાર સલાહકાર",
        "trends_chat_popover": "🤖 રિપોર્ટ સહાયક",
        "health_chat_popover": "💬 આરોગ્ય સહાયક",
        "popover_ph": "તમારો પ્રશ્ન અહીં પૂછો...",
        "safety_disclaimer": "💙 સલાહ: દવા બદલતા પહેલા તમારા ડૉક્ટરની સલાહ અવશ્ય લો."
    },
    "Spanish (Español) 🇪🇸": {
        "app_title": "ClinicalAI — Tu Compañero de Salud Fácil",
        "app_sub": "Información médica clara, sencilla y sin palabras difíciles para ti y tu familia",
        "choose_lang": "Selecciona tu idioma / Choose Language:",
        "login_tab": "Iniciar Sesión",
        "register_tab": "Crear Cuenta",
        "forgot_tab": "¿Olvidaste tu contraseña?",
        "identifier_lbl": "Teléfono Móvil o Correo",
        "identifier_ph": "ej. 612345678 o nombre@gmail.com",
        "password_lbl": "Tu Contraseña",
        "password_ph": "Ingresa tu contraseña",
        "new_password_lbl": "Crea una Nueva Contraseña",
        "send_otp_btn": "📩 Enviar Código de Verificación (OTP)",
        "otp_lbl": "Ingresa el Código de 6 Dígitos",
        "otp_ph": "Código de 6 dígitos",
        "register_btn": "✓ Verificar y Crear Cuenta",
        "login_btn": "✓ Iniciar Sesión",
        "reset_btn": "✓ Actualizar Contraseña",
        "sign_out": "🚪 Salir",
        "welcome": "Bienvenido",
        "no_reports_title": "📄 Revisemos tu Informe de Laboratorio",
        "no_reports_sub": "Sube tus análisis de sangre en PDF. Te explicaremos todo con palabras sencillas y amables.",
        "med_history_lbl": "Condiciones previas (ej. Presión alta, Azúcar, Ninguna)",
        "med_history_ph": "ej. Presión alta hace 5 años, Azúcar leve, Ninguna...",
        "current_meds_lbl": "Medicamentos que tomas diariamente",
        "current_meds_ph": "ej. Pastilla para la presión por la mañana, Vitamina D...",
        "upload_lbl": "Selecciona tus análisis (Archivos PDF)",
        "analyze_btn": "🔍 Analizar Mis Informes",
        "trends_header": "📈 La Evolución de tu Salud",
        "trends_sub": "Las áreas sombreadas en verde indican los niveles normales y saludables.",
        "select_marker_lbl": "Selecciona el análisis a visualizar:",
        "alerts_header": "🔔 Puntos Importantes a Tener en Cuenta",
        "alerts_sub": "Código de colores sencillo: Rojo significa consultar con tu médico; Verde significa todo bien.",
        "alert_badge": "⚠️ Alerta / Consultar con el Médico",
        "good_badge": "✅ Todo Normal y Saludable",
        "upload_more": "➕ Agregar Otro Análisis (PDF)",
        "diet_tab_btn": "🥗 Mi Plan de Comidas Saludables",
        "trends_tab_btn": "📊 Gráficos e Informes de Salud",
        "diet_header": "🥗 Comidas Nutritivas y Fáciles de Digerir",
        "diet_sub": "Haz clic en una gastronomía para recibir un menú suave y saludable adaptado a tus análisis.",
        "cuisine_roti": "🫓 Roti, Daal y Paneer (Comida India Casera)",
        "cuisine_south": "🍲 Del Sur de la India (Idli suave y lentejas)",
        "cuisine_med": "🫒 Mediterránea (Saludable para el corazón)",
        "cuisine_diabetic": "🌾 Especial para la Diabetes (Bajo en azúcar)",
        "cuisine_heart": "❤️ Salud del Corazón (Bajo en sal y suave)",
        "generate_diet_btn": "✨ Crear Mi Plan de Comidas",
        "diet_chat_popover": "🧑🍳 Personalizar Mi Comida",
        "trends_chat_popover": "🤖 Conversar Sobre Mis Análisis",
        "health_chat_popover": "💬 Preguntar al Asistente de Salud",
        "popover_ph": "Escribe tu pregunta con palabras sencillas...",
        "safety_disclaimer": "💙 Nota: Esta aplicación es solo para orientación educativa. Consulta a tu médico antes de cambiar medicamentos."
    },
    "French (Français) 🇫🇷": {
        "app_title": "ClinicalAI — Votre Compagnon Santé Facile",
        "app_sub": "Des informations médicales simples, claires et réconfortantes pour vous et vos proches",
        "choose_lang": "Choisissez votre langue / Choose Language:",
        "login_tab": "Connexion",
        "register_tab": "Nouveau Compte",
        "forgot_tab": "Mot de passe oublié ?",
        "identifier_lbl": "Numéro de Mobile ou E-mail",
        "identifier_ph": "ex. 0612345678 ou nom@gmail.com",
        "password_lbl": "Votre Mot de Passe",
        "password_ph": "Entrez votre mot de passe",
        "new_password_lbl": "Créez un Nouveau Mot de Passe",
        "send_otp_btn": "📩 Envoyer le Code de Vérification (OTP)",
        "otp_lbl": "Entrez le Code à 6 Chiffres",
        "otp_ph": "Code à 6 chiffres",
        "register_btn": "✓ Vérifier et Créer le Compte",
        "login_btn": "✓ Se Connecter",
        "reset_btn": "✓ Mettre à Jour le Mot de Passe",
        "sign_out": "🚪 Se Déconnecter",
        "welcome": "Bienvenue",
        "no_reports_title": "📄 Analysons Vos Résultats de Bilan",
        "no_reports_sub": "Téléversez vos analyses de sang en PDF. Nous vous expliquerons tout simplement sans jargon.",
        "med_history_lbl": "Problèmes de santé antérieurs (Tension, Diabète, Aucun)",
        "med_history_ph": "ex. Hypertension depuis 5 ans, Aucun...",
        "current_meds_lbl": "Médicaments que vous prenez chaque jour",
        "current_meds_ph": "ex. Comprimé pour la tension le matin, Vitamine D...",
        "upload_lbl": "Sélectionnez vos bilans (Fichiers PDF)",
        "analyze_btn": "🔍 Analyser Mes Résultats",
        "trends_header": "📈 Évolution de Votre Santé au Fil du Temps",
        "trends_sub": "Les zones vertes indiquent les valeurs normales et saines.",
        "select_marker_lbl": "Sélectionnez le test à afficher :",
        "alerts_header": "🔔 Points d'Attention Importants",
        "alerts_sub": "Code couleur simple : Rouge = À vérifier avec votre médecin ; Vert = Tout va bien.",
        "alert_badge": "⚠️ Attention / À vérifier avec le médecin",
        "good_badge": "✅ Tout est Normal et Réconfortant",
        "upload_more": "➕ Ajouter un Autre Bilan (PDF)",
        "diet_tab_btn": "🥗 Mon Menu Réconfortant",
        "trends_tab_btn": "📊 Évolution & Bilans",
        "diet_header": "🥗 Repas Sains, Tendres et Faciles à Digérer",
        "diet_sub": "Choisissez une cuisine pour découvrir des repas adaptés à vos résultats sanguins.",
        "cuisine_roti": "🫓 Roti, Daal et Paneer (Cuisine Indienne Douce)",
        "cuisine_south": "🍲 Sud de l'Inde (Idli moelleux, lentilles)",
        "cuisine_med": "🫒 Méditerranéenne (Bonne pour le cœur)",
        "cuisine_diabetic": "🌾 Équilibrée Diabète (Peu de sucre)",
        "cuisine_heart": "❤️ Santé Cardiaque (Pauvre en sel, tendre)",
        "generate_diet_btn": "✨ Créer Mon Menu Personnalisé",
        "diet_chat_popover": "🧑🍳 Personnaliser Mon Menu",
        "trends_chat_popover": "🤖 Échanger sur Mes Résultats",
        "health_chat_popover": "💬 Parler à l'Assistant Santé",
        "popover_ph": "Posez votre question simplement ici...",
        "safety_disclaimer": "💙 Note Santé : Cette application offre un soutien informatif. Demandez toujours conseil à votre médecin."
    },
    "Mandarin (中文) 🇨🇳": {
        "app_title": "ClinicalAI — 您的贴心健康陪伴助手",
        "app_sub": "为长辈量身打造的简单、温暖、通俗易懂的体检报告解读",
        "choose_lang": "选择您的语言 / Choose Language:",
        "login_tab": "登录账号",
        "register_tab": "新用户注册",
        "forgot_tab": "忘记密码？",
        "identifier_lbl": "手机号或邮箱",
        "identifier_ph": "例如: 13800000000 或 name@gmail.com",
        "password_lbl": "密码",
        "password_ph": "请输入密码",
        "new_password_lbl": "设置新密码",
        "send_otp_btn": "📩 获取6位验证码 (OTP)",
        "otp_lbl": "输入6位验证码",
        "otp_ph": "6位验证码",
        "register_btn": "✓ 验证并完成注册",
        "login_btn": "✓ 安全登录",
        "reset_btn": "✓ 重置密码并登录",
        "sign_out": "🚪 退出登录",
        "welcome": "欢迎您",
        "no_reports_title": "📄 让我们帮您看看化验单",
        "no_reports_sub": "上传您的血液或体检化验单PDF。我们会用最亲切、简单的大白话为您解释清楚。",
        "med_history_lbl": "以往健康情况 (例如: 血压高、血糖稍高、无)",
        "med_history_ph": "例如: 高血压5年、轻度糖尿病、无...",
        "current_meds_lbl": "平时天天服用的药品",
        "current_meds_ph": "例如: 早上一片降压药、维生素D...",
        "upload_lbl": "选择您的化验单文件 (PDF格式)",
        "analyze_btn": "🔍 立即解读我的体检报告",
        "trends_header": "📈 您的长期生理指标变化曲线",
        "trends_sub": "绿色阴影区域代表正常健康的指标区间，一目了然。",
        "select_marker_lbl": "选择要查看的指标项目：",
        "alerts_header": "🔔 报告中需要您多留意的项目",
        "alerts_sub": "红色代表建议复查或请教医生；绿色代表健康达标，请放心。",
        "alert_badge": "⚠️ 请多留意 / 建议咨询医生",
        "good_badge": "✅ 各项达标 / 状态良好",
        "upload_more": "➕ 继续上传新报告 (PDF)",
        "diet_tab_btn": "🥗 营养易嚼康复食谱",
        "trends_tab_btn": "📊 健康趋势与报告",
        "diet_header": "🥗 软烂易消化、控糖降压的营养膳食",
        "diet_sub": "点击您喜欢的菜系，系统会根据您的体检指标生成易嚼、温和的一日三餐。",
        "cuisine_roti": "🫓 Roti, Daal and Paneer (传统印度温和素食)",
        "cuisine_south": "🍲 南印度风味 (松软米糕与温热扁豆汤)",
        "cuisine_med": "🫒 地中海养心膳食 (少盐少油)",
        "cuisine_diabetic": "🌾 控糖稳糖食谱 (低升糖高纤维)",
        "cuisine_heart": "❤️ 护心减盐食谱 (易嚼软食)",
        "generate_diet_btn": "✨ 为我定制每日营养计划",
        "diet_chat_popover": "🧑🍳 调整我的每日食谱",
        "trends_chat_popover": "🤖 聊聊我的化验指标",
        "health_chat_popover": "💬 咨询健康助手",
        "popover_ph": "请用平常的话写下您想问的问题...",
        "safety_disclaimer": "💙 温馨提示: 本应用提供日常生活参考，增减药物请务必遵照主治医生医嘱。"
    },
    "Arabic (العربية) 🇸🇦": {
        "app_title": "كلينيكال إيه آي — رفيقك الصحي البسيط",
        "app_sub": "معلومات صحية سهلة وبسيطة تناسب كبار السن وعائلاتهم",
        "choose_lang": "اختر لغتك المفضلة:",
        "login_tab": "تسجيل الدخول",
        "register_tab": "مستخدم جديد",
        "forgot_tab": "نسيت كلمة المرور؟",
        "identifier_lbl": "رقم الجوال أو البريد الإلكتروني",
        "identifier_ph": "مثال: 0501234567 أو name@gmail.com",
        "password_lbl": "كلمة المرور",
        "password_ph": "أدخل كلمة المرور",
        "new_password_lbl": "إنشاء كلمة مرور جديدة",
        "send_otp_btn": "📩 إرسال رمز التحقق (OTP)",
        "otp_lbl": "أدخل الرمز المكون من 6 أرقام",
        "otp_ph": "رمز التحقق",
        "register_btn": "✓ تأكيد الرمز وإنشاء الحساب",
        "login_btn": "✓ تسجيل الدخول بأمان",
        "reset_btn": "✓ تحديث كلمة المرور",
        "sign_out": "🚪 خروج",
        "welcome": "أهلاً بك",
        "no_reports_title": "📄 لنقرأ نتائج تحاليلك الطبية معاً",
        "no_reports_sub": "ارفع ملف الفحص بصيغة PDF وسنشرح لك الأرقام بكلمات بسيطة ومريحة دون تعقيد.",
        "med_history_lbl": "الحالات الصحية السابقة (مثل الضغط، السكر)",
        "med_history_ph": "مثال: ضغط الدم، سكر خفيف، لا يوجد...",
        "current_meds_lbl": "الأدوية اليومية التي تتناولها",
        "current_meds_ph": "مثال: حبة ضغط صباحاً، فيتامين د...",
        "upload_lbl": "اختر ملفات التحاليل (PDF)",
        "analyze_btn": "🔍 قراءة وتحليل التقرير",
        "trends_header": "📈 مسار صحتك عبر الوقت",
        "trends_sub": "المناطق المظللة بالأخضر تعني المستويات الطبيعية والمطمئنة.",
        "select_marker_lbl": "اختر التحليل المطلوب عرضه:",
        "alerts_header": "🔔 أمور يرجى الانتباه إليها ومناقشتها مع الطبيب",
        "alerts_sub": "اللون الأحمر يعني استشارة الطبيب؛ الأخضر يعني كل شيء سليم ومطمئن.",
        "alert_badge": "⚠️ استشر طبيبك",
        "good_badge": "✅ صحي ومطمئن",
        "upload_more": "➕ إضافة تقرير جديد (PDF)",
        "diet_tab_btn": "🥗 وجبات صحية سهلة الهضم",
        "trends_tab_btn": "📊 الرسوم البيانية والتقارير",
        "diet_header": "🥗 وجبات مغذية، طرية وسهلة المضغ",
        "diet_sub": "اختر نوع الوجبات المناسب لك للحصول على خطة سهلة الأكل.",
        "cuisine_roti": "🫓 خبز الروتي مع العدس والجبن (طعام مريح)",
        "cuisine_south": "🍲 جنوب الهند (إدلي طري وعدس دافئ)",
        "cuisine_med": "🫒 وجبات البحر المتوسط (صديقة للقلب)",
        "cuisine_diabetic": "🌾 وجبات مناسبة لمستوى السكر",
        "cuisine_heart": "❤️ وجبات قليلة الملح وسهلة الهضم",
        "generate_diet_btn": "✨ تجهيز وجباتي اليومية",
        "diet_chat_popover": "🧑🍳 تعديل الوجبات والمكونات",
        "trends_chat_popover": "🤖 مناقشة نتائج الفحوصات",
        "health_chat_popover": "💬 سؤال المساعد الصحي",
        "popover_ph": "اكتب سؤالك هنا بكلمات بسيطة...",
        "safety_disclaimer": "💙 تذكير ودي: هذا التطبيق للإرشاد اليومي فقط. استشر طبيبك دائماً قبل تغيير أي دواء."
    }
}

if "translations" not in st.session_state:
    st.session_state.translations = TRANSLATIONS

def t(key: str) -> str:
    """Returns the translation for the given key based on current language stored in session state."""
    lang = st.session_state.get("lang", "English 🇺🇸")
    trans_dict = st.session_state.get("translations", TRANSLATIONS)
    dict_for_lang = trans_dict.get(lang, trans_dict.get("English 🇺🇸", {}))
    return dict_for_lang.get(key, trans_dict.get("English 🇺🇸", {}).get(key, key))

# =========================================================================
# Session State Initialization
# =========================================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

if "lang" not in st.session_state:
    st.session_state.lang = "English 🇺🇸"

if "active_nav" not in st.session_state:
    st.session_state.active_nav = "trends"

if "active_cuisine" not in st.session_state:
    st.session_state.active_cuisine = "Roti, Daal and Paneer (Desi Indian)"

if "active_diet_plan" not in st.session_state:
    st.session_state.active_diet_plan = None

if "simulated_otp" not in st.session_state:
    st.session_state.simulated_otp = None

if "otp_target" not in st.session_state:
    st.session_state.otp_target = None

if "chat_history_health" not in st.session_state:
    st.session_state.chat_history_health = []

if "chat_history_trends" not in st.session_state:
    st.session_state.chat_history_trends = []

if "chat_history_diet" not in st.session_state:
    st.session_state.chat_history_diet = []

# Persistent Cookie Session
cookie_manager = stx.CookieManager(key="clinical_cookie_store")

if not st.session_state.authenticated:
    cached_uid = cookie_manager.get("clinical_auth_uid")
    if cached_uid:
        try:
            persisted_u = database.get_user_by_id(int(cached_uid))
            if persisted_u:
                st.session_state.user = persisted_u
                st.session_state.authenticated = True
                if persisted_u.get("preferred_language") in TRANSLATIONS:
                    st.session_state.lang = persisted_u["preferred_language"]
        except Exception:
            pass

# =========================================================================
# Elderly-Friendly UI Compaction CSS
# =========================================================================

st.markdown("""
<style>
    /* CRITICAL UI Compaction rule: remove default top whitespace */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    /* Large elderly-friendly fonts */
    h1, h2, h3, h4 {
        color: #1e293b;
        font-weight: 700;
    }
    p, div, label, span {
        font-size: 1.05rem;
    }
    .stButton>button {
        font-size: 1.05rem !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# Module 3: Login & Authentication (Elderly-Friendly UI)
# =========================================================================

def render_login_screen():
    st.markdown(f"## 🩺 {t('app_title')}")
    st.caption(t("app_sub"))
    st.info(t("safety_disclaimer"))
    st.markdown("---")

    # 1. Visual 12-Language Flag Dropdown & Tiles
    st.markdown(f"#### 🌐 {t('choose_lang')}")
    
    # Dropdown selector
    cur_idx = [item["name"] for item in LANG_LIST].index(st.session_state.lang) if st.session_state.lang in [item["name"] for item in LANG_LIST] else 0
    dropdown_lang = st.selectbox(
        "Select Language / भाषा चुनें",
        options=[item["name"] for item in LANG_LIST],
        index=cur_idx,
        key="login_lang_dropdown",
        label_visibility="collapsed"
    )
    if dropdown_lang != st.session_state.lang:
        st.session_state.lang = dropdown_lang
        st.rerun()

    # Clickable Colorful Flag Tiles Grid
    cols_per_row = 4
    for r in range(0, len(LANG_LIST), cols_per_row):
        row_langs = LANG_LIST[r:r+cols_per_row]
        cols = st.columns(len(row_langs))
        for idx, item in enumerate(row_langs):
            with cols[idx]:
                is_selected = (st.session_state.lang == item["name"])
                btn_type = "primary" if is_selected else "secondary"
                if st.button(f"{item['flag']} {item['label']}", key=f"lang_btn_{item['id']}", type=btn_type, use_container_width=True):
                    st.session_state.lang = item["name"]
                    st.rerun()

    st.markdown("---")

    # 2. Compact Authentication Card in a single desktop frame
    auth_left, auth_center, auth_right = st.columns([1, 2, 1])
    with auth_center:
        with st.container(border=True):
            tab_login, tab_register, tab_forgot = st.tabs([t("login_tab"), t("register_tab"), t("forgot_tab")])

            # --- TAB 1: LOGIN ---
            with tab_login:
                with st.form("form_login"):
                    u_id = st.text_input(t("identifier_lbl"), placeholder=t("identifier_ph"), key="login_id_in")
                    u_pw = st.text_input(t("password_lbl"), type="password", placeholder=t("password_ph"), key="login_pw_in")
                    btn_login = st.form_submit_button(t("login_btn"), type="primary", use_container_width=True)

                    if btn_login:
                        if not u_id or not u_pw:
                            st.error("Please enter both your phone/email and password.")
                        else:
                            auth_user = database.authenticate_user(u_id, u_pw)
                            if auth_user:
                                st.session_state.user = auth_user
                                st.session_state.authenticated = True
                                if auth_user.get("preferred_language") in TRANSLATIONS:
                                    st.session_state.lang = auth_user["preferred_language"]
                                cookie_manager.set("clinical_auth_uid", str(auth_user["id"]), expires_at=datetime(2027, 1, 1))
                                st.success(f"{t('welcome')}!")
                                st.rerun()
                            else:
                                st.error("Incorrect details. Please check your phone/email or password.")

            # --- TAB 2: REGISTER WITH SIMULATED OTP ---
            with tab_register:
                reg_id = st.text_input(f"{t('identifier_lbl')} *", placeholder=t("identifier_ph"), key="reg_id_in")
                if st.button(t("send_otp_btn"), key="btn_send_reg_otp", use_container_width=True):
                    if not reg_id or len(reg_id.strip()) < 4:
                        st.warning("Please enter your phone number or email first.")
                    else:
                        existing = database.get_user_by_identifier(reg_id)
                        if existing:
                            st.warning("An account already exists for this number/email. Please sign in.")
                        else:
                            otp_val = f"{random.randint(100000, 999999)}"
                            st.session_state.simulated_otp = otp_val
                            st.session_state.otp_target = reg_id.strip()
                            database.store_otp(reg_id.strip(), otp_val)

                if st.session_state.simulated_otp and st.session_state.otp_target == reg_id.strip():
                    st.success(f"📱 **Simulated OTP Code:** `{st.session_state.simulated_otp}`")
                    with st.form("form_reg_verify"):
                        entered_otp = st.text_input(t("otp_lbl"), placeholder=t("otp_ph"))
                        reg_pw = st.text_input(t("password_lbl"), type="password", placeholder=t("password_ph"))
                        btn_reg_done = st.form_submit_button(t("register_btn"), type="primary", use_container_width=True)

                        if btn_reg_done:
                            if entered_otp.strip() != st.session_state.simulated_otp:
                                st.error("Incorrect code. Please enter the 6-digit code shown above.")
                            elif not reg_pw or len(reg_pw.strip()) < 4:
                                st.error("Please enter a password with at least 4 characters.")
                            else:
                                new_u = database.register_user(reg_id, reg_pw, st.session_state.lang)
                                if new_u:
                                    st.session_state.user = new_u
                                    st.session_state.authenticated = True
                                    st.session_state.simulated_otp = None
                                    cookie_manager.set("clinical_auth_uid", str(new_u["id"]), expires_at=datetime(2027, 1, 1))
                                    st.success("Account created successfully!")
                                    st.rerun()
                                else:
                                    st.error("Could not register. Please try again.")

            # --- TAB 3: FORGOT PASSWORD FLOW ---
            with tab_forgot:
                forgot_id = st.text_input(f"{t('identifier_lbl')} *", placeholder=t("identifier_ph"), key="forgot_id_in")
                if st.button("📩 Send Password Reset Code", key="btn_send_forgot_otp", use_container_width=True):
                    if not forgot_id:
                        st.warning("Please enter your phone or email.")
                    else:
                        u_record = database.get_user_by_identifier(forgot_id)
                        if not u_record:
                            st.error("No account found with this identifier.")
                        else:
                            otp_reset = f"{random.randint(100000, 999999)}"
                            st.session_state.simulated_otp = otp_reset
                            st.session_state.otp_target = forgot_id.strip()
                            database.store_otp(forgot_id.strip(), otp_reset)

                if st.session_state.simulated_otp and st.session_state.otp_target == forgot_id.strip():
                    st.success(f"📱 **Password Reset Code:** `{st.session_state.simulated_otp}`")
                    with st.form("form_reset_pw"):
                        entered_reset_otp = st.text_input(t("otp_lbl"), placeholder=t("otp_ph"))
                        new_pw = st.text_input(t("new_password_lbl"), type="password")
                        btn_reset_submit = st.form_submit_button(t("reset_btn"), type="primary", use_container_width=True)

                        if btn_reset_submit:
                            ok, msg = database.verify_and_reset_password(forgot_id, entered_reset_otp, new_pw)
                            if ok:
                                st.session_state.simulated_otp = None
                                st.success("Password updated! Please sign in using your new password.")
                            else:
                                st.error(msg)

# =========================================================================
# Top Header Bar for Authenticated Users
# =========================================================================

def render_top_header():
    col1, col2, col3 = st.columns([6, 3, 3])
    with col1:
        st.markdown(f"### 🩺 {t('app_title')}")
        st.caption(f"👤 {st.session_state.user['identifier']}")
    with col2:
        # Language Switcher
        current_name = st.session_state.lang
        idx = [item["name"] for item in LANG_LIST].index(current_name) if current_name in [item["name"] for item in LANG_LIST] else 0
        new_lang = st.selectbox(
            "Language",
            options=[item["name"] for item in LANG_LIST],
            index=idx,
            key="top_lang_select",
            label_visibility="collapsed"
        )
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang
            if st.session_state.user:
                database.update_user_language(st.session_state.user["id"], new_lang)
            st.rerun()
    with col3:
        if st.button(t("sign_out"), key="btn_top_signout", use_container_width=True):
            cookie_manager.delete("clinical_auth_uid")
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

# =========================================================================
# Module 4: Home Page (Upload & Context) - When NO Reports Exist
# =========================================================================

def render_first_time_home_page():
    user = st.session_state.user
    st.markdown(f"## {t('no_reports_title')}")
    st.write(t("no_reports_sub"))
    st.markdown("---")

    with st.container(border=True):
        uploaded_files = st.file_uploader(
            t("upload_lbl"),
            type=["pdf"],
            accept_multiple_files=True,
            key="first_time_pdf_uploader"
        )

        col_hist, col_meds = st.columns(2)
        with col_hist:
            med_hist = st.text_area(t("med_history_lbl"), placeholder=t("med_history_ph"), height=110, key="first_med_hist")
        with col_meds:
            curr_meds = st.text_area(t("current_meds_lbl"), placeholder=t("current_meds_ph"), height=110, key="first_curr_meds")

        btn_analyze = st.button(t("analyze_btn"), type="primary", use_container_width=True)

        if btn_analyze:
            if not uploaded_files:
                st.warning("Please select at least one laboratory PDF report first.")
            else:
                with st.spinner("Reading your test papers with PyMuPDF and Google Gemini concurrently..."):
                    try:
                        # Concurrent OCR text extraction using ThreadPoolExecutor
                        full_text = ai_engine.extract_text_from_multiple_pdfs(uploaded_files)

                        # Concurrent analysis with ThreadPoolExecutor
                        analysis_res = ai_engine.run_concurrent_report_analysis(
                            raw_text=full_text,
                            med_history=med_hist,
                            current_meds=curr_meds,
                            language=st.session_state.lang
                        )

                        metrics = analysis_res.get("metrics", [])
                        report_date = analysis_res.get("report_date", datetime.now().strftime("%Y-%m-%d"))
                        summary = analysis_res.get("analysis_summary", "")

                        if not metrics:
                            st.error("No laboratory numbers could be identified in the uploaded PDF. Please make sure it is a clear test report.")
                        else:
                            ok, rep_id, msg = database.save_report_and_metrics(
                                user_id=user["id"],
                                report_date=report_date,
                                med_history=med_hist,
                                current_meds=curr_meds,
                                analysis_summary=summary,
                                metrics=metrics,
                                overwrite=False
                            )
                            if ok:
                                st.success("Your report has been analyzed successfully!")
                                st.session_state.active_nav = "trends"
                                st.rerun()
                            elif msg == "DUPLICATE_REPORT":
                                st.info(f"ℹ️ Report for {report_date} is already saved. Duplicate entry blocked to keep trends accurate.")
                                st.session_state.active_nav = "trends"
                                st.rerun()
                            else:
                                st.error(f"Save error: {msg}")
                    except Exception as e:
                        st.error(f"Analysis error: {str(e)}")

    st.markdown("---")

    # Chatbot 1: st.popover("💬 Ask Health Assistant") at bottom left
    popover_col1, popover_col2 = st.columns([1, 1])
    with popover_col1:
        with st.popover(t("health_chat_popover")):
            st.markdown(f"#### {t('health_chat_popover')}")
            st.caption("Ask any general everyday question about your health, drinking water, or gentle exercise.")
            
            for msg in st.session_state.chat_history_health:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            health_q = st.chat_input(t("popover_ph"), key="chat_health_in")
            if health_q:
                st.session_state.chat_history_health.append({"role": "user", "content": health_q})
                with st.chat_message("user"):
                    st.markdown(health_q)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        reply = ai_engine.ask_health_assistant(
                            health_q,
                            st.session_state.chat_history_health,
                            st.session_state.lang
                        )
                        st.markdown(reply)
                        st.session_state.chat_history_health.append({"role": "assistant", "content": reply})

# =========================================================================
# Module 5: Analysis Page (Health Trends - Default Home Post-Upload)
# =========================================================================

def render_analysis_page():
    user = st.session_state.user
    reports = database.get_user_reports(user["id"])
    all_metrics = database.get_all_user_metrics_history(user["id"])
    latest_report = database.get_latest_report_with_metrics(user["id"])

    if not latest_report:
        render_first_time_home_page()
        return

    # Continuous Upload Option in an Expandable Container
    with st.expander(t("upload_more")):
        st.write("Upload additional test reports anytime to track your health progress.")
        more_files = st.file_uploader("Upload Lab Report PDF", type=["pdf"], accept_multiple_files=True, key="more_pdf_uploader")
        col_h2, col_m2 = st.columns(2)
        with col_h2:
            h2 = st.text_area(t("med_history_lbl"), value=latest_report.get("med_history", ""), height=80, key="more_med_h")
        with col_m2:
            m2 = st.text_area(t("current_meds_lbl"), value=latest_report.get("current_meds", ""), height=80, key="more_curr_m")
        if st.button("🔍 Analyze New Report", key="btn_analyze_more", type="primary"):
            if more_files:
                with st.spinner("Processing new report..."):
                    try:
                        combined = ai_engine.extract_text_from_multiple_pdfs(more_files)
                        res = ai_engine.run_concurrent_report_analysis(
                            raw_text=combined,
                            med_history=h2,
                            current_meds=m2,
                            language=st.session_state.lang
                        )
                        metrics = res.get("metrics", [])
                        r_date = res.get("report_date", datetime.now().strftime("%Y-%m-%d"))
                        database.save_report_and_metrics(
                            user_id=user["id"],
                            report_date=r_date,
                            med_history=h2,
                            current_meds=m2,
                            analysis_summary=res.get("analysis_summary", ""),
                            metrics=metrics,
                            overwrite=True
                        )
                        st.success("New report added to your health history!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    st.markdown("---")

    # 1. Top Section: Glanceable Graphs with Shaded Healthy Ranges
    with st.container(border=True):
        st.markdown(f"### {t('trends_header')}")
        st.caption(t("trends_sub"))

        if all_metrics:
            df_m = pd.DataFrame(all_metrics)
            available_tests = sorted(df_m["test_name"].unique())
            
            selected_test = st.selectbox(
                t("select_marker_lbl"),
                options=available_tests,
                index=0,
                key="trends_metric_select"
            )

            test_records = df_m[df_m["test_name"] == selected_test].sort_values("report_date")
            
            if not test_records.empty:
                fig = go.Figure()
                
                # Extract normal bounds for shaded green rectangle
                range_str = str(test_records["range"].iloc[-1])
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", range_str)
                min_n, max_n = None, None
                if len(nums) >= 2:
                    try:
                        min_n = float(nums[0])
                        max_n = float(nums[1])
                    except ValueError:
                        pass

                if min_n is not None and max_n is not None and min_n < max_n:
                    fig.add_hrect(
                        y0=min_n,
                        y1=max_n,
                        fillcolor="rgba(34, 197, 94, 0.2)",
                        line_width=0,
                        annotation_text=f"Normal Healthy Range ({min_n} - {max_n})",
                        annotation_position="top left",
                        annotation_font_size=14,
                        annotation_font_color="green"
                    )

                unit_txt = test_records["unit"].iloc[-1] or ""
                fig.add_trace(go.Scatter(
                    x=test_records["report_date"],
                    y=test_records["value"],
                    mode="lines+markers",
                    name=selected_test,
                    line=dict(color="#1d4ed8", width=4),
                    marker=dict(size=12, color="#1e40af"),
                    hovertemplate="<b>Date:</b> %{x}<br><b>Your Value:</b> %{y} " + unit_txt + "<extra></extra>"
                ))

                fig.update_layout(
                    title=dict(text=f"<b>{selected_test}</b> ({unit_txt})", font=dict(size=18)),
                    xaxis=dict(title=dict(text="Test Date", font=dict(size=14)), tickfont=dict(size=12)),
                    yaxis=dict(title=dict(text=f"Result ({unit_txt})", font=dict(size=14)), tickfont=dict(size=12)),
                    margin=dict(l=40, r=40, t=50, b=40),
                    height=360,
                    template="plotly_white"
                )

                st.plotly_chart(fig, use_container_width=True)

    # 2. Bottom Section: Color-Coded Alerts
    with st.container(border=True):
        st.markdown(f"### {t('alerts_header')}")
        st.caption(t("alerts_sub"))

        metrics_list = latest_report.get("metrics", [])
        abnormal_list = [m for m in metrics_list if str(m.get("status", "")).lower() in ["high", "low", "alert"]]
        normal_list = [m for m in metrics_list if str(m.get("status", "")).lower() == "normal"]

        if abnormal_list:
            for m in abnormal_list:
                status_txt = m.get("status", "Check with Doctor")
                unit_str = f" {m.get('unit')}" if m.get('unit') else ""
                # Red alert box
                st.error(f"🔴 **{m.get('test_name')}**: Your value is **{m.get('value')}{unit_str}** (Healthy range: {m.get('range', 'N/A')}). Status: **{status_txt}** — *{t('alert_badge')}*")
        else:
            st.success("🎉 Excellent! All laboratory measurements are in normal healthy ranges.")

        if normal_list:
            with st.expander(f"{t('good_badge')} ({len(normal_list)} parameters)"):
                for m in normal_list:
                    unit_str = f" {m.get('unit')}" if m.get('unit') else ""
                    st.success(f"🟢 **{m.get('test_name')}**: {m.get('value')}{unit_str} (Normal range: {m.get('range', 'N/A')})")

    st.markdown("---")

    # Chatbot 2: st.popover("🤖 Discuss My Health Trends") at bottom right
    pop_col1, pop_col2 = st.columns([1, 1])
    with pop_col2:
        with st.popover(t("trends_chat_popover")):
            st.markdown(f"#### {t('trends_chat_popover')}")
            st.caption("Ask questions about your numbers, what a high or low result means, or questions to ask your doctor.")

            for msg in st.session_state.chat_history_trends:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            trend_q = st.chat_input(t("popover_ph"), key="chat_trends_in")
            if trend_q:
                st.session_state.chat_history_trends.append({"role": "user", "content": trend_q})
                with st.chat_message("user"):
                    st.markdown(trend_q)
                with st.chat_message("assistant"):
                    with st.spinner("Reviewing your numbers..."):
                        reply = ai_engine.ask_trends_assistant(
                            user_message=trend_q,
                            conversation_history=st.session_state.chat_history_trends,
                            metrics=metrics_list,
                            med_history=latest_report.get("med_history", ""),
                            current_meds=latest_report.get("current_meds", ""),
                            language=st.session_state.lang
                        )
                        st.markdown(reply)
                        st.session_state.chat_history_trends.append({"role": "assistant", "content": reply})

# =========================================================================
# Module 6: The Diet Planner
# =========================================================================

CUISINES = [
    {"id": "roti_daal", "label": "🫓 Roti, Daal and Paneer", "name": "Roti, Daal and Paneer", "desc": "Classic Desi Indian: soft rotis, yellow moong daal, tender paneer & light vegetables"},
    {"id": "south_indian", "label": "🍲 South Indian", "name": "South Indian", "desc": "Steamed idlis, comforting sambar, gentle rasam & tender greens"},
    {"id": "mediterranean", "label": "🫒 Mediterranean", "name": "Mediterranean", "desc": "Olive oil, soft lentils, stewed vegetables & mild fish"},
    {"id": "diabetic", "label": "🌾 Diabetic Friendly", "name": "Diabetic Friendly", "desc": "Low sugar, high fiber & steady-energy gentle meals"},
    {"id": "heart", "label": "❤️ Heart Friendly", "name": "Heart Friendly", "desc": "Low salt, tender steamed meals & potassium-rich broths"}
]

def render_diet_planner_page():
    user = st.session_state.user
    latest_report = database.get_latest_report_with_metrics(user["id"])
    
    if not latest_report:
        st.info("Please upload a health test report first so we can tailor meals to your body's needs.")
        return

    st.markdown(f"## {t('diet_header')}")
    st.write(t("diet_sub"))

    metrics = latest_report.get("metrics", [])
    abnormal_metrics = [m for m in metrics if str(m.get("status", "")).lower() in ["high", "low", "alert"]]

    # Cuisine Selection Tiles Grid
    with st.container(border=True):
        st.markdown("#### 🍽️ Choose a Cuisine Style:")
        cols = st.columns(len(CUISINES))
        for i, c in enumerate(CUISINES):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{c['label']}**")
                    st.caption(c["desc"])
                    is_selected = (st.session_state.active_cuisine == c["name"])
                    btn_type = "primary" if is_selected else "secondary"
                    btn_text = "✓ Selected" if is_selected else "Select"
                    if st.button(btn_text, key=f"cuisine_tile_{c['id']}", type=btn_type, use_container_width=True):
                        st.session_state.active_cuisine = c["name"]
                        st.rerun()

        st.info(f"Selected: **{st.session_state.active_cuisine}**")

        if st.button(t("generate_diet_btn"), type="primary", use_container_width=True):
            with st.spinner("Preparing gentle, nutritious daily meal suggestions with Gemini..."):
                try:
                    plan = ai_engine.generate_personalized_diet_plan(
                        cuisine=st.session_state.active_cuisine,
                        abnormal_metrics=abnormal_metrics,
                        med_history=latest_report.get("med_history", ""),
                        current_meds=latest_report.get("current_meds", ""),
                        dietary_restrictions="",
                        language=st.session_state.lang
                    )
                    st.session_state.active_diet_plan = plan
                    st.success("Your customized meal plan is ready!")
                except Exception as e:
                    st.error(f"Error creating plan: {str(e)}")

    # Render Active Diet Plan
    if st.session_state.active_diet_plan:
        plan = st.session_state.active_diet_plan
        st.markdown("---")
        with st.container(border=True):
            st.markdown(f"### 📋 Daily Meal Guide ({plan.get('cuisine', st.session_state.active_cuisine)})")
            
            if plan.get("comfort_tips"):
                st.info(f"💡 **Easy Chewing & Digestion Advice:** {plan.get('comfort_tips')}")

            # Meal Sessions (Morning, Midday, Evening)
            schedule = plan.get("daily_schedule", [])
            if schedule:
                s_cols = st.columns(len(schedule))
                for idx, session in enumerate(schedule):
                    with s_cols[idx]:
                        with st.container(border=True):
                            st.markdown(f"#### 🕒 {session.get('meal_time', 'Meal')}")
                            for dish in session.get("dishes", []):
                                st.markdown(f"**{dish.get('dish_name')}** ({dish.get('portion', '')})")
                                st.caption(f"🌿 *{dish.get('elderly_benefit', '')}*")
                                st.markdown("---")

            col_p, col_l = st.columns(2)
            with col_p:
                st.success("##### 🥗 Wholesome Foods to Enjoy Daily")
                for f in plan.get("foods_to_enjoy", []):
                    st.markdown(f"- **{f}**")
            with col_l:
                st.warning("##### 🚫 Foods to Limit")
                for f in plan.get("foods_to_limit", []):
                    st.markdown(f"- **{f}**")

    st.markdown("---")

    # Chatbot 3: st.popover("🧑🍳 Customize My Diet") at the bottom
    pop_col1, pop_col2 = st.columns([1, 1])
    with pop_col1:
        with st.popover(t("diet_chat_popover")):
            st.markdown(f"#### {t('diet_chat_popover')}")
            st.caption("Ask to change ingredients, make food softer, or substitute foods (e.g., 'I don't like spinach, change it' or 'Make this cheaper').")

            for msg in st.session_state.chat_history_diet:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            diet_q = st.chat_input(t("popover_ph"), key="chat_diet_in")
            if diet_q:
                st.session_state.chat_history_diet.append({"role": "user", "content": diet_q})
                with st.chat_message("user"):
                    st.markdown(diet_q)
                with st.chat_message("assistant"):
                    with st.spinner("Finding tasty substitutes & updating your meals..."):
                        reply_res = ai_engine.ask_diet_assistant(
                            user_message=diet_q,
                            conversation_history=st.session_state.chat_history_diet,
                            diet_plan=st.session_state.active_diet_plan,
                            abnormal_metrics=abnormal_metrics,
                            language=st.session_state.lang
                        )
                        if isinstance(reply_res, tuple):
                            reply_txt, updated_plan = reply_res
                            if updated_plan:
                                st.session_state.active_diet_plan = updated_plan
                        else:
                            reply_txt = reply_res
                            updated_plan = None

                        st.markdown(reply_txt)
                        st.session_state.chat_history_diet.append({"role": "assistant", "content": reply_txt})
                        if updated_plan:
                            st.success("✨ Your daily meal plan above was dynamically updated!")
                            st.rerun()

# =========================================================================
# Main Router
# =========================================================================

def main():
    if not st.session_state.authenticated:
        render_login_screen()
    else:
        render_top_header()
        
        user = st.session_state.user
        reports = database.get_user_reports(user["id"])
        
        if not reports:
            # If NO reports exist -> Home Page (Upload & Context) with Chatbot 1
            render_first_time_home_page()
        else:
            # If reports DO exist -> Default Home becomes Analysis Page with tab navigation
            tab_col1, tab_col2 = st.columns(2)
            with tab_col1:
                btn_type1 = "primary" if st.session_state.active_nav == "trends" else "secondary"
                if st.button(t("trends_tab_btn"), type=btn_type1, use_container_width=True):
                    st.session_state.active_nav = "trends"
                    st.rerun()
            with tab_col2:
                btn_type2 = "primary" if st.session_state.active_nav == "diet" else "secondary"
                if st.button(t("diet_tab_btn"), type=btn_type2, use_container_width=True):
                    st.session_state.active_nav = "diet"
                    st.rerun()

            if st.session_state.active_nav == "trends":
                render_analysis_page()
            else:
                render_diet_planner_page()

if __name__ == "__main__":
    main()
