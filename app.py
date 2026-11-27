import os
import re
import json
import random
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict, Any

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import extra_streamlit_components as stx
from streamlit_option_menu import option_menu

import database
import ai_engine
from i18n import LANG_LIST, TRANSLATIONS, t

# =========================================================================
# Page Setup & Streamlit Configuration
# =========================================================================

st.set_page_config(
    page_title="ClinicalAI Decision Support",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database schema and performance pragmas
database.init_db()

# Elderly-Friendly Typography & UI Compaction CSS
st.markdown("""
<style>
    /* CRITICAL UI Compaction rule: remove default top whitespace */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    /* Large elderly-friendly fonts (18-19px typography scale) */
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
# Session State Initialization
# =========================================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

if "lang" not in st.session_state:
    st.session_state.lang = "English 🇬🇧"

if "active_tab_index" not in st.session_state:
    st.session_state.active_tab_index = 0

if "active_cuisine" not in st.session_state:
    st.session_state.active_cuisine = "roti_daal"

if "active_diet_plan" not in st.session_state:
    st.session_state.active_diet_plan = None

if "simulated_otp" not in st.session_state:
    st.session_state.simulated_otp = None

if "otp_target" not in st.session_state:
    st.session_state.otp_target = None

if "logged_out" not in st.session_state:
    st.session_state.logged_out = False

# Persistent Cookie Session
cookie_manager = stx.CookieManager(key="clinical_cookie_store")

if not st.session_state.authenticated and not st.session_state.get("logged_out", False):
    try:
        cached_uid = cookie_manager.get("clinical_auth_uid")
        if cached_uid and str(cached_uid).strip():
            persisted_u = database.get_user_by_id(int(cached_uid))
            if persisted_u:
                st.session_state.user = persisted_u
                st.session_state.authenticated = True
                if persisted_u.get("preferred_language") in TRANSLATIONS:
                    st.session_state.lang = persisted_u["preferred_language"]
    except Exception:
        pass

def change_language(new_lang: str):
    """Synchronizes language across session state and database record."""
    if new_lang in TRANSLATIONS:
        st.session_state.lang = new_lang
        if st.session_state.get("user"):
            try:
                database.update_user_language(st.session_state.user["id"], new_lang)
                st.session_state.user["preferred_language"] = new_lang
                st.session_state.user["language"] = new_lang
            except Exception:
                pass

# =========================================================================
# Authentication Screen (Login, Registration, Forgot PIN)
# =========================================================================

def render_login_screen():
    st.markdown(f"## 🩺 {t('app_title')}")
    st.caption(t("app_sub"))
    st.info(t("safety_disclaimer"))
    st.markdown("---")

    # 1. 12-Language Flag Tile Grid (4x3) right at top of login
    st.markdown(f"#### 🌐 {t('choose_lang')}")
    cols_per_row = 4
    for r in range(0, len(LANG_LIST), cols_per_row):
        row_langs = LANG_LIST[r:r+cols_per_row]
        cols = st.columns(len(row_langs))
        for idx, item in enumerate(row_langs):
            with cols[idx]:
                is_selected = (st.session_state.lang == item["name"])
                btn_type = "primary" if is_selected else "secondary"
                if st.button(f"{item['flag']} {item['label']}", key=f"login_flag_{item['id']}", type=btn_type, use_container_width=True):
                    change_language(item["name"])
                    st.rerun()

    st.markdown("---")

    # 2. Compact Authentication Card
    _, auth_center, _ = st.columns([1, 2, 1])
    with auth_center:
        with st.container(border=True):
            tab_login, tab_register, tab_forgot = st.tabs([t("login_tab"), t("register_tab"), t("forgot_pin_lbl")])

            # --- TAB 1: SIGN IN (4-DIGIT PIN) ---
            with tab_login:
                with st.form("form_login"):
                    u_id = st.text_input(t("identifier_lbl"), placeholder=t("identifier_ph"), key="login_id_in")
                    u_pw = st.text_input(t("pin_lbl"), type="password", placeholder="Enter 4-digit numeric PIN", key="login_pw_in", max_chars=4)
                    btn_login = st.form_submit_button(t("login_btn"), type="primary", use_container_width=True)

                    if btn_login:
                        clean_pin = u_pw.strip()
                        if not u_id or not clean_pin:
                            st.error("Please enter both your phone/email and 4-digit PIN.")
                        elif not clean_pin.isdigit() or len(clean_pin) != 4:
                            st.error("PIN must be strictly 4 numeric digits.")
                        else:
                            auth_user = database.authenticate_user(u_id, clean_pin)
                            if auth_user:
                                st.session_state.logged_out = False
                                st.session_state.user = auth_user
                                st.session_state.authenticated = True
                                if auth_user.get("preferred_language") in TRANSLATIONS:
                                    change_language(auth_user["preferred_language"])
                                try:
                                    cookie_manager.set("clinical_auth_uid", str(auth_user["id"]), expires_at=datetime(2027, 1, 1))
                                except Exception:
                                    pass
                                st.success(f"{t('welcome')}!")
                                st.rerun()
                            else:
                                st.error("Incorrect details. Please check your phone/email or 4-digit PIN.")

            # --- TAB 2: REGISTER (STRICT REGEX & TWO-STEP ATOMIC FORM) ---
            with tab_register:
                if not (st.session_state.get("simulated_otp") and st.session_state.get("otp_target")):
                    with st.form("form_reg_step1"):
                        reg_name = st.text_input(f"{t('name_lbl')} *", placeholder=t("name_ph"), key="reg_name_in")
                        reg_id = st.text_input(f"{t('identifier_lbl')} *", placeholder=t("identifier_ph"), key="reg_id_in")
                        btn_send_otp = st.form_submit_button(t("send_otp_btn"), type="primary", use_container_width=True)

                        if btn_send_otp:
                            if not reg_name or not reg_name.strip():
                                st.error("Please enter your full name.")
                            else:
                                is_valid, norm_id, id_type, err_msg = database.validate_identifier_and_pin(reg_id, "1234")
                                if not is_valid and "PIN" not in err_msg:
                                    st.error(err_msg)
                                else:
                                    existing = database.get_user_by_identifier(norm_id)
                                    if existing:
                                        st.warning(f"An account with '{reg_id.strip()}' is already registered. Please switch to the Sign In tab, or use Forgot PIN.")
                                    else:
                                        otp_val = f"{random.randint(100000, 999999)}"
                                        st.session_state.simulated_otp = otp_val
                                        st.session_state.otp_target = norm_id
                                        st.session_state.reg_name_val = reg_name.strip()
                                        database.store_otp(norm_id, otp_val)

                                        # Attempt real SMTP dispatch if email
                                        if "@" in norm_id:
                                            sent = ai_engine.send_real_email_otp(norm_id, otp_val)
                                            if sent:
                                                st.toast(f"Verification email dispatched to {norm_id}!", icon="📩")

                                        st.rerun()
                else:
                    st.success(f"📱 **Simulated OTP Code:** `{st.session_state.simulated_otp}`")
                    st.info(f"Verification code prepared for **{st.session_state.get('reg_name_val', '')}** ({st.session_state.otp_target})")
                    with st.form("form_reg_verify"):
                        entered_otp = st.text_input(t("otp_lbl"), placeholder=t("otp_ph"), key="reg_entered_otp")
                        reg_pw = st.text_input(t("pin_lbl"), type="password", placeholder="Enter 4-digit numeric PIN", key="reg_pw_in", max_chars=4)
                        btn_reg_done = st.form_submit_button(t("register_btn"), type="primary", use_container_width=True)

                        if btn_reg_done:
                            clean_reg_pin = reg_pw.strip()
                            if entered_otp.strip() != st.session_state.simulated_otp:
                                st.error("Incorrect code. Please enter the 6-digit code shown above.")
                            elif not clean_reg_pin.isdigit() or len(clean_reg_pin) != 4:
                                st.error("PIN must be strictly 4 numeric digits.")
                            else:
                                target_id = st.session_state.otp_target
                                target_name = st.session_state.get("reg_name_val", "")

                                existing_acc = database.get_user_by_identifier(target_id)
                                if existing_acc:
                                    st.warning(f"An account for '{target_id}' is already registered. Please switch to the Sign In tab.")
                                else:
                                    new_u = database.register_user(
                                        target_id,
                                        clean_reg_pin,
                                        preferred_language=st.session_state.lang,
                                        name=target_name
                                    )
                                    if isinstance(new_u, tuple):
                                        new_u = new_u[0]
                                    if new_u:
                                        st.session_state.logged_out = False
                                        st.session_state.user = new_u
                                        st.session_state.authenticated = True
                                        st.session_state.simulated_otp = None
                                        st.session_state.otp_target = None
                                        try:
                                            cookie_manager.set("clinical_auth_uid", str(new_u["id"]), expires_at=datetime(2027, 1, 1))
                                        except Exception:
                                            pass
                                        st.success("Account created successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Could not register. An account with this identifier may already exist or the details are invalid.")

                    if st.button("← Change Details / Re-enter Information", key="btn_cancel_reg_otp", use_container_width=True):
                        st.session_state.simulated_otp = None
                        st.session_state.otp_target = None
                        st.rerun()

            # --- TAB 3: FORGOT PIN FLOW ---
            with tab_forgot:
                if not (st.session_state.get("forgot_otp") and st.session_state.get("forgot_target")):
                    with st.form("form_forgot_step1"):
                        forgot_id = st.text_input(f"{t('identifier_lbl')} *", placeholder=t("identifier_ph"), key="forgot_id_in")
                        btn_send_forgot = st.form_submit_button("📩 " + t("forgot_pin_lbl"), type="primary", use_container_width=True)

                        if btn_send_forgot:
                            clean_fid = forgot_id.strip()
                            if not clean_fid:
                                st.warning("Please enter your phone or email.")
                            else:
                                u_record = database.get_user_by_identifier(clean_fid)
                                if not u_record:
                                    st.error("No account found with this identifier. Please verify or register.")
                                else:
                                    otp_reset = f"{random.randint(100000, 999999)}"
                                    st.session_state.forgot_otp = otp_reset
                                    st.session_state.forgot_target = clean_fid
                                    database.store_otp(clean_fid, otp_reset)

                                    if "@" in clean_fid:
                                        sent = ai_engine.send_real_email_otp(clean_fid, otp_reset)
                                        if sent:
                                            st.toast(f"Reset email dispatched to {clean_fid}!", icon="📩")

                                    st.rerun()
                else:
                    st.success(f"📱 **PIN Reset Code:** `{st.session_state.forgot_otp}`")
                    st.caption(f"Reset code prepared for ({st.session_state.forgot_target})")
                    with st.form("form_reset_pw"):
                        entered_reset_otp = st.text_input(t("otp_lbl"), placeholder=t("otp_ph"), key="forgot_entered_otp")
                        new_pw = st.text_input(t("new_pin_lbl"), type="password", placeholder="Enter new 4-digit numeric PIN", key="forgot_new_pw", max_chars=4)
                        btn_reset_submit = st.form_submit_button(t("reset_pin_btn"), type="primary", use_container_width=True)

                        if btn_reset_submit:
                            clean_reset_pin = new_pw.strip()
                            if not clean_reset_pin.isdigit() or len(clean_reset_pin) != 4:
                                st.error("PIN must be strictly 4 numeric digits.")
                            else:
                                fid = st.session_state.forgot_target
                                ok, msg = database.verify_and_reset_password(fid, entered_reset_otp, clean_reset_pin)
                                if ok:
                                    st.session_state.forgot_otp = None
                                    st.session_state.forgot_target = None
                                    st.success("PIN updated successfully! Please switch to the Sign In tab.")
                                else:
                                    st.error(msg)

                    if st.button("← Change Identifier / Re-enter", key="btn_cancel_forgot_otp", use_container_width=True):
                        st.session_state.forgot_otp = None
                        st.session_state.forgot_target = None
                        st.rerun()

# =========================================================================
# Global Header & Navigation
# =========================================================================

def render_global_header():
    col_lang, col_profile, col_signout = st.columns([3, 6, 3])
    
    with col_lang:
        # Persistent Top-Left Language Switcher
        cur_lang = st.session_state.lang
        idx = [item["name"] for item in LANG_LIST].index(cur_lang) if cur_lang in [item["name"] for item in LANG_LIST] else 0
        new_lang = st.selectbox(
            "Language",
            options=[item["name"] for item in LANG_LIST],
            index=idx,
            key=f"top_header_lang_{st.session_state.lang}",
            label_visibility="collapsed"
        )
        if new_lang != cur_lang:
            change_language(new_lang)
            st.rerun()

    with col_profile:
        user = st.session_state.user
        u_name = user.get("name") or user.get("full_name") or user.get("identifier", "").split("@")[0].capitalize()
        allergies = database.get_user_allergies(user["id"])
        allergy_badge = f" | 🛡️ **Exclusions:** {', '.join(allergies)}" if allergies else ""
        st.markdown(f"👤 **{u_name}** ({user['identifier']}){allergy_badge}")

    with col_signout:
        if st.button(t("sign_out"), key="btn_global_signout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.logged_out = True
            st.session_state.active_tab_index = 0
            try:
                cookie_manager.delete("clinical_auth_uid")
            except Exception:
                pass
            st.rerun()

    # Single-Click State-Bound Navigation
    selected_idx = option_menu(
        menu_title=None,
        options=[
            f"📄 {t('upload_lbl')[:20]}...",
            f"📈 {t('trends_tab_btn')}",
            f"🥗 {t('diet_tab_btn')}"
        ],
        icons=["cloud-upload", "graph-up-arrow", "heart-pulse"],
        menu_icon="cast",
        default_index=st.session_state.active_tab_index,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#f8fafc", "border-radius": "10px"},
            "icon": {"color": "#0284c7", "font-size": "1.1rem"},
            "nav-link": {"font-size": "1.05rem", "text-align": "center", "margin": "0px", "--hover-color": "#e2e8f0"},
            "nav-link-selected": {"background-color": "#0284c7", "color": "white", "font-weight": "600"},
        }
    )

    nav_map = {0: 0, 1: 1, 2: 2}
    opt_indices = [
        f"📄 {t('upload_lbl')[:20]}...",
        f"📈 {t('trends_tab_btn')}",
        f"🥗 {t('diet_tab_btn')}"
    ]
    if selected_idx in opt_indices:
        new_idx = opt_indices.index(selected_idx)
        if new_idx != st.session_state.active_tab_index:
            st.session_state.active_tab_index = new_idx
            st.rerun()

    st.markdown("---")

# =========================================================================
# TAB 1: Upload & Intake + Bot 1 (General Everyday Health Companion)
# =========================================================================

@st.fragment
def render_bot_1_fragment(user_id: int):
    with st.container(border=True):
        st.markdown(f"#### 🤖 {t('health_chat_popover')}")
        st.caption("Ask everyday health questions, home remedies, or gentle wellness habits in your language.")

        chat_history = database.get_chat_history(user_id, "general_upload")
        for msg in chat_history[-6:]:
            role = msg.get("role", "assistant")
            with st.chat_message(role):
                st.write(msg.get("message", ""))

        user_input = st.chat_input("Ask a general wellness question (e.g. 'What helps a mild dry cough?')...", key="bot1_chat_input")
        if user_input and user_input.strip():
            database.save_chat_message(user_id, "general_upload", "user", user_input.strip())
            with st.chat_message("user"):
                st.write(user_input.strip())

            with st.spinner("Thinking gently..."):
                recent_msgs = database.get_chat_history(user_id, "general_upload", limit=8)
                bot_reply = ai_engine.chat_general_health(recent_msgs, language=st.session_state.lang)
                database.save_chat_message(user_id, "general_upload", "assistant", bot_reply)
                with st.chat_message("assistant"):
                    st.write(bot_reply)

        if chat_history and st.button("🗑️ Clear General Health Chat", key="btn_clear_bot1"):
            database.clear_chat_history(user_id, "general_upload")
            st.rerun(scope="fragment")

def render_tab_1():
    user = st.session_state.user
    st.markdown(f"### 📄 {t('no_reports_title')}")
    st.write(t("no_reports_sub"))

    col_files, col_context = st.columns([5, 5])
    with col_files:
        uploaded_files = st.file_uploader(
            t("upload_lbl"),
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="tab1_uploader"
        )
    with col_context:
        meds_val = st.text_area(
            t("current_meds_lbl"),
            value=user.get("medications", ""),
            placeholder=t("current_meds_ph"),
            key="tab1_meds"
        )
        cond_val = st.text_area(
            t("med_history_lbl"),
            value=user.get("preexisting_conditions", ""),
            placeholder=t("med_history_ph"),
            key="tab1_conditions"
        )

    if st.button(t("analyze_btn"), type="primary", use_container_width=True, key="btn_tab1_analyze"):
        if not uploaded_files:
            st.warning("Please select at least one lab report PDF or image.")
        else:
            with st.status("Analyzing health documents...", expanded=True) as status:
                st.write("1. Extracting biomarkers (PyMuPDF / Multimodal Vision)...")
                extraction = ai_engine.extract_multimodal_documents(uploaded_files, language=st.session_state.lang)
                all_reports = extraction.get("reports", [])
                if not all_reports and extraction.get("metrics"):
                    all_reports = [{"report_date": extraction.get("report_date"), "metrics": extraction.get("metrics")}]

                total_extracted = sum(len(r.get("metrics", [])) for r in all_reports)
                if total_extracted == 0:
                    status.update(label="Could not extract quantitative biomarkers.", state="error")
                    st.error("No quantitative lab tests were recognized. Please ensure the document is clear.")
                    return

                num_reports = len(all_reports)
                st.write(f"Recognized {num_reports} consultation report(s) across {total_extracted} biomarkers.")

                # The latest report is the last in chronological order
                latest_report_item = all_reports[-1]
                latest_metrics = latest_report_item.get("metrics", [])
                latest_r_date = latest_report_item.get("report_date", datetime.now().strftime("%Y-%m-%d"))

                st.write("2. Calculating deterministic health score...")
                score_obj = ai_engine.calculate_patient_health_score(latest_metrics)

                st.write("3. Generating simple summary and practical daily tips...")
                summary_text, daily_tips = ai_engine.generate_simple_summary_and_tips(
                    metrics=latest_metrics,
                    medications=meds_val,
                    conditions=cond_val,
                    language=st.session_state.lang
                )

                st.write("4. Checking past history for progress comparison...")
                past_reports = database.get_user_reports(user["id"])
                past_metrics = []
                past_date = ""
                if len(all_reports) > 1:
                    past_metrics = all_reports[-2].get("metrics", [])
                    past_date = all_reports[-2].get("report_date", "")
                elif past_reports:
                    past_metrics = database.get_report_metrics(past_reports[0]["id"])
                    past_date = past_reports[0]["report_date"]

                comp_narrative = ai_engine.generate_comparative_narrative(
                    current_metrics=latest_metrics,
                    past_metrics=past_metrics,
                    past_date=past_date,
                    language=st.session_state.lang
                )

                st.write("5. Committing clinical records to SQLite...")
                database.update_user_profile(user["id"], medications=meds_val, preexisting_conditions=cond_val)
                user["medications"] = meds_val
                user["preexisting_conditions"] = cond_val

                # Commit every distinct report in chronological order
                for idx, rep in enumerate(all_reports):
                    rep_date = rep.get("report_date")
                    rep_m = rep.get("metrics", [])
                    if not rep_m:
                        continue
                    rep_score = ai_engine.calculate_patient_health_score(rep_m)

                    is_latest = (idx == len(all_reports) - 1)
                    if is_latest:
                        s_text = summary_text
                        d_tips = daily_tips
                        c_narr = comp_narrative
                    else:
                        s_text = f"Consultation report recorded on {rep_date}."
                        d_tips = "Historical baseline record."
                        c_narr = ""

                    database.save_clinical_record(
                        user_id=user["id"],
                        report_date=rep_date,
                        health_score=rep_score["score"],
                        params_represented=rep_score["total_params"],
                        narrative_summary=s_text,
                        daily_life_tips=d_tips,
                        comparative_analysis=c_narr,
                        recovery_diet_plan="",
                        cuisine_used="roti_daal",
                        metrics=rep_m,
                        med_history=cond_val,
                        current_meds=meds_val,
                        overwrite=True
                    )

                st.cache_data.clear()
                status.update(label="Processing complete! Routing to Graph & Summary...", state="complete")

            # Single-Click State-Bound Navigation: Auto-route to Tab 2
            st.session_state.active_tab_index = 1
            st.rerun()

    st.markdown("---")
    # Bot 1 at the bottom of Tab 1
    render_bot_1_fragment(user["id"])

# =========================================================================
# TAB 2: Graph, Score & Summary + Bot 2 (Clinical Context Agent)
# =========================================================================

@st.cache_data(ttl=300)
def load_user_metrics_dataframe(user_id: int):
    records = database.get_user_metrics_history(user_id)
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)

@st.fragment
def render_bot_2_fragment(user_id: int, metrics: List[Dict[str, Any]], health_score: int, summary: str, meds: str, conds: str):
    with st.container(border=True):
        st.markdown(f"#### 🤖 {t('trends_chat_popover')}")
        st.caption("Ask questions grounded strictly in your recorded lab tests, trend graph, or health score.")

        chat_history = database.get_chat_history(user_id, "report_analysis")
        for msg in chat_history[-6:]:
            role = msg.get("role", "assistant")
            with st.chat_message(role):
                st.write(msg.get("message", ""))

        user_input = st.chat_input("Ask about your report (e.g. 'Why is my score 78?', 'Is my sugar improving?')...", key="bot2_chat_input")
        if user_input and user_input.strip():
            database.save_chat_message(user_id, "report_analysis", "user", user_input.strip())
            with st.chat_message("user"):
                st.write(user_input.strip())

            with st.spinner("Reviewing your clinical data..."):
                recent_msgs = database.get_chat_history(user_id, "report_analysis", limit=8)
                bot_reply = ai_engine.chat_clinical_context(
                    messages=recent_msgs,
                    metrics=metrics,
                    health_score=health_score,
                    summary=summary,
                    medications=meds,
                    conditions=conds,
                    language=st.session_state.lang
                )
                database.save_chat_message(user_id, "report_analysis", "assistant", bot_reply)
                with st.chat_message("assistant"):
                    st.write(bot_reply)

        if chat_history and st.button("🗑️ Clear Report Analysis Chat", key="btn_clear_bot2"):
            database.clear_chat_history(user_id, "report_analysis")
            st.rerun(scope="fragment")

def render_tab_2():
    user = st.session_state.user
    reports = database.get_user_reports(user["id"])
    if not reports:
        st.info("No clinical reports uploaded yet. Please use Tab 1 to upload your test PDF or image.")
        return

    latest_report = reports[0]
    metrics = database.get_report_metrics(latest_report["id"])
    health_score = latest_report.get("health_score")
    if health_score is None:
        score_obj = ai_engine.calculate_patient_health_score(metrics)
        health_score = score_obj["score"]
    else:
        score_obj = ai_engine.calculate_patient_health_score(metrics)
        score_obj["score"] = health_score

    # Top-Right Health Score Badge directly above Graph
    col_title, col_badge = st.columns([7, 5])
    with col_title:
        st.markdown(f"### 📈 {t('trends_header')}")
        st.caption(f"Showing report date: **{latest_report['report_date']}** | {t('trends_sub')}")

    with col_badge:
        with st.container(border=True):
            b_col1, b_col2 = st.columns([4, 8])
            with b_col1:
                st.markdown(
                    f"<div style='background-color:{score_obj['color']}; color:white; padding:10px 14px; border-radius:12px; text-align:center; font-size:1.8rem; font-weight:800;'>"
                    f"{score_obj['score']}</div>",
                    unsafe_allow_html=True
                )
            with b_col2:
                st.markdown(f"**Health Score:** {score_obj['label']}")
                st.caption(f"{score_obj['total_params']} Tests Analyzed ({score_obj['normal_count']} Normal, {score_obj['attention_count']} Alert)")

    # Longitudinal Plotly Graph with Healthy Reference Range
    df_metrics = load_user_metrics_dataframe(user["id"])
    if not df_metrics.empty and "test_name" in df_metrics.columns:
        test_names = sorted(df_metrics["test_name"].dropna().unique().tolist())
        selected_test = st.selectbox(t("select_marker_lbl"), options=test_names, key="trend_marker_select")

        df_single = df_metrics[df_metrics["test_name"] == selected_test].sort_values("report_date")
        if not df_single.empty:
            cur_val = df_single.iloc[-1]["value"]
            cur_unit = df_single.iloc[-1]["unit"]
            cur_status = df_single.iloc[-1]["status"]
            delta_val = None
            if len(df_single) > 1:
                prev_val = df_single.iloc[-2]["value"]
                delta_val = round(cur_val - prev_val, 2)

            kpi_col, _ = st.columns([4, 8])
            with kpi_col:
                delta_str = f"{delta_val:+} {cur_unit}" if delta_val is not None else None
                st.metric(
                    label=f"Current {selected_test} ({cur_status})",
                    value=f"{cur_val} {cur_unit}",
                    delta=delta_str,
                    delta_color="off"
                )

            # Format dates for x-axis labels: e.g. "08 Jul 2026", "17 Aug 2026", "26 Sep 2026"
            date_labels = []
            for d in df_single["report_date"]:
                try:
                    dt = datetime.strptime(str(d)[:10], "%Y-%m-%d")
                    date_labels.append(dt.strftime("%d %b %Y"))
                except Exception:
                    date_labels.append(str(d))

            # Interactive Plotly Line Chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=date_labels,
                y=df_single["value"],
                mode="lines+markers+text",
                name=selected_test,
                text=[f"{v} {cur_unit}" for v in df_single["value"]],
                textposition="top center",
                line=dict(color="#0284c7", width=3),
                marker=dict(size=9, color="#0369a1"),
                hovertemplate="<b>Date:</b> %{x}<br><b>Measured Value:</b> %{y} " + cur_unit + "<extra></extra>"
            ))

            # Light Green Shaded Healthy Range
            ref_str = str(df_single.iloc[-1].get("reference_range", df_single.iloc[-1].get("range", "")))
            bounds = re.findall(r"([0-9]+(?:\.[0-9]+)?)", ref_str)
            if len(bounds) >= 2:
                try:
                    low_b, high_b = float(bounds[0]), float(bounds[1])
                    fig.add_hrect(
                        y0=low_b,
                        y1=high_b,
                        fillcolor="rgba(34, 197, 94, 0.18)",
                        line_width=0,
                        annotation_text=f"Healthy Normal ({low_b} - {high_b} {cur_unit})",
                        annotation_position="top left",
                        annotation_font_color="#15803d"
                    )
                except Exception:
                    pass

            fig.update_layout(
                title=f"Longitudinal Progression: {selected_test}",
                xaxis=dict(
                    title="Consultation Date",
                    type="category",
                    categoryorder="array",
                    categoryarray=date_labels,
                    showgrid=False
                ),
                yaxis=dict(
                    title=f"Value ({cur_unit})",
                    showgrid=True,
                    gridcolor="#e2e8f0"
                ),
                margin=dict(l=20, r=20, t=40, b=20),
                height=340,
                hovermode="x unified",
                plot_bgcolor="white"
            )
            st.plotly_chart(fig, use_container_width=True)

    # Formatted Biomarker Data Table with hide_index=True
    st.markdown("#### 📋 Detailed Lab Biomarkers")
    table_rows = []
    latest_date_str = latest_report.get("report_date", "")
    try:
        display_date = datetime.strptime(latest_date_str[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        display_date = latest_date_str

    for m in metrics:
        t_name = m.get("test_name", "")
        t_val = m.get("test_value", m.get("value", ""))
        t_unit = m.get("unit", "")
        t_ref = m.get("reference_range", m.get("range", ""))
        t_stat = m.get("status", "Normal")
        table_rows.append({
            "Component / Test Name": t_name,
            "Consultation Date": display_date,
            "Measured Value": f"{t_val} {t_unit}",
            "Healthy Reference Range": t_ref,
            "Clinical Status": f"⚠️ {t_stat}" if str(t_stat).lower() != "normal" else f"✅ {t_stat}"
        })

    if table_rows:
        df_table = pd.DataFrame(table_rows)
        st.dataframe(df_table, hide_index=True, use_container_width=True)

    # Ultra-Simple Summary + Practical Daily Life Tips
    col_sum, col_tips = st.columns([6, 6])
    with col_sum:
        with st.container(border=True):
            st.markdown(f"#### 📝 {t('alerts_header')}")
            summary_txt = latest_report.get("narrative_summary") or latest_report.get("analysis_summary") or "Summary ready."
            st.write(summary_txt)

    with col_tips:
        with st.container(border=True):
            st.markdown("#### 💧 Simple Daily Life Tips")
            tips_txt = latest_report.get("daily_life_tips") or "Stay hydrated with 8 glasses of fresh warm water daily, take gentle 15-minute walks, and rest comfortably."
            st.write(tips_txt)

    # Comparative Progress Note
    if latest_report.get("comparative_analysis"):
        with st.container(border=True):
            st.markdown("#### 🔄 Progress Comparison")
            st.write(latest_report["comparative_analysis"])

    # Consultation History Accordions
    if len(reports) > 1:
        with st.expander(f"📁 Past Consultation History ({len(reports)} records)"):
            for past_r in reports[1:]:
                st.markdown(f"**Date:** {past_r['report_date']} | **Score:** {past_r.get('health_score', 'N/A')}/100")
                p_metrics = database.get_report_metrics(past_r["id"])
                st.caption(f"Recorded {len(p_metrics)} biomarkers. Summary: {past_r.get('narrative_summary', '')[:120]}...")
                st.markdown("---")

    st.markdown("---")
    # Bot 2 at the bottom of Tab 2
    render_bot_2_fragment(
        user_id=user["id"],
        metrics=metrics,
        health_score=score_obj["score"],
        summary=latest_report.get("narrative_summary", ""),
        meds=user.get("medications", ""),
        conds=user.get("preexisting_conditions", "")
    )

# =========================================================================
# TAB 3: Cuisine Diet Planner + Bot 3 (Diet Customizer & Safety Memory)
# =========================================================================

@st.fragment
def render_bot_3_fragment(user_id: int, report_id: int, active_diet: str, cuisine_name: str, metrics: List[Dict[str, Any]]):
    with st.container(border=True):
        st.markdown(f"#### 🤖 {t('diet_chat_popover')}")
        st.caption("Customize your diet plan or state your food allergies. New allergies are automatically saved to your medical profile!")

        chat_history = database.get_chat_history(user_id, "diet_customizer")
        for msg in chat_history[-6:]:
            role = msg.get("role", "assistant")
            with st.chat_message(role):
                st.write(msg.get("message", ""))

        user_input = st.chat_input("e.g. 'I cannot drink milk or eat paneer', 'Please replace spicy dishes with soft khichdi'...", key="bot3_chat_input")
        if user_input and user_input.strip():
            database.save_chat_message(user_id, "diet_customizer", "user", user_input.strip())
            with st.chat_message("user"):
                st.write(user_input.strip())

            with st.spinner("Reviewing ingredients and dietary safety..."):
                recent_msgs = database.get_chat_history(user_id, "diet_customizer", limit=6)
                allergies = database.get_user_allergies(user_id)
                custom_res = ai_engine.chat_diet_customizer(
                    messages=recent_msgs,
                    active_diet=active_diet,
                    cuisine_name=cuisine_name,
                    metrics=metrics,
                    allergies=allergies,
                    language=st.session_state.lang
                )

                # Safety Persistence Loop
                if custom_res.detected_new_allergies_or_restrictions:
                    updated_allergies = database.append_user_allergies(user_id, custom_res.detected_new_allergies_or_restrictions)
                    st.session_state.user["allergies_restrictions"] = updated_allergies
                    st.success(f"🛡️ **Saved to your permanent profile:** Avoid {', '.join(custom_res.detected_new_allergies_or_restrictions)}")

                if custom_res.diet_was_modified and custom_res.updated_diet_plan_markdown:
                    database.update_report_diet(report_id, custom_res.updated_diet_plan_markdown)
                    st.session_state.active_diet_plan = custom_res.updated_diet_plan_markdown

                database.save_chat_message(user_id, "diet_customizer", "assistant", custom_res.assistant_reply)
                with st.chat_message("assistant"):
                    st.write(custom_res.assistant_reply)

                if custom_res.diet_was_modified:
                    st.rerun(scope="fragment")

        if chat_history and st.button("🗑️ Clear Diet Chat", key="btn_clear_bot3"):
            database.clear_chat_history(user_id, "diet_customizer")
            st.rerun(scope="fragment")

def render_tab_3():
    user = st.session_state.user
    reports = database.get_user_reports(user["id"])
    if not reports:
        st.info("No clinical reports uploaded yet. Please use Tab 1 to upload your test PDF or image first.")
        return

    # Report Selector if multiple exist
    date_options = [r["report_date"] for r in reports]
    chosen_date = st.selectbox("Select Consultation Report Date:", options=date_options, key="tab3_date_select")
    selected_report = next(r for r in reports if r["report_date"] == chosen_date)
    metrics = database.get_report_metrics(selected_report["id"])

    st.markdown(f"### 🥗 {t('diet_header')}")
    st.write(t("diet_sub"))

    # Active Allergies Badge & Quick Add
    allergies = database.get_user_allergies(user["id"])
    with st.container(border=True):
        a_col1, a_col2 = st.columns([8, 4])
        with a_col1:
            if allergies:
                st.markdown(f"🛡️ **Active Medical Exclusions:** `{', '.join(allergies)}`")
            else:
                st.markdown("🛡️ **Active Medical Exclusions:** `None recorded yet`")
        with a_col2:
            new_a = st.text_input("Quick Add Allergy:", placeholder="e.g. Peanuts, Milk", label_visibility="collapsed", key="quick_allergy_in")
            if st.button("➕ Add Allergy", key="btn_quick_add_allergy", use_container_width=True):
                if new_a and new_a.strip():
                    database.append_user_allergies(user["id"], [new_a.strip()])
                    st.session_state.user["allergies_restrictions"] = database.get_user_allergies(user["id"])
                    st.success(f"Added '{new_a.strip()}' to safety profile!")
                    st.rerun()

    st.markdown("#### Select Your Regional Comfort Cuisine:")
    c_keys = list(ai_engine.CUISINE_PROMPT_REGISTRY.keys())
    cols = st.columns(3)
    for idx, c_key in enumerate(c_keys):
        c_info = ai_engine.CUISINE_PROMPT_REGISTRY[c_key]
        with cols[idx % 3]:
            is_active = (st.session_state.active_cuisine == c_key)
            btn_type = "primary" if is_active else "secondary"
            if st.button(c_info["title"], key=f"cuisine_btn_{c_key}", type=btn_type, use_container_width=True):
                st.session_state.active_cuisine = c_key
                with st.spinner(f"Preparing custom recovery plan for {c_info['title']}..."):
                    new_diet = ai_engine.generate_localized_cuisine_diet(
                        cuisine_key=c_key,
                        metrics=metrics,
                        medications=user.get("medications", ""),
                        conditions=user.get("preexisting_conditions", ""),
                        allergies=database.get_user_allergies(user["id"]),
                        language=st.session_state.lang
                    )
                    st.session_state.active_diet_plan = new_diet
                    database.update_report_diet(selected_report["id"], new_diet, cuisine_used=c_key)
                st.rerun()

    # Render Active Diet Plan
    current_diet = st.session_state.get("active_diet_plan") or selected_report.get("recovery_diet_plan")
    if not current_diet:
        # Generate initial default diet
        with st.spinner("Formulating personalized recovery meal plan..."):
            current_diet = ai_engine.generate_localized_cuisine_diet(
                cuisine_key=st.session_state.active_cuisine,
                metrics=metrics,
                medications=user.get("medications", ""),
                conditions=user.get("preexisting_conditions", ""),
                allergies=database.get_user_allergies(user["id"]),
                language=st.session_state.lang
            )
            st.session_state.active_diet_plan = current_diet
            database.update_report_diet(selected_report["id"], current_diet, cuisine_used=st.session_state.active_cuisine)

    with st.container(border=True):
        st.markdown(current_diet)

    st.markdown("---")
    # Bot 3 at the bottom of Tab 3
    active_c_title = ai_engine.CUISINE_PROMPT_REGISTRY.get(st.session_state.active_cuisine, {}).get("title", "Desi Indian")
    render_bot_3_fragment(
        user_id=user["id"],
        report_id=selected_report["id"],
        active_diet=current_diet,
        cuisine_name=active_c_title,
        metrics=metrics
    )

# =========================================================================
# Main Router
# =========================================================================

def main():
    if not st.session_state.authenticated:
        render_login_screen()
    else:
        render_global_header()
        if st.session_state.active_tab_index == 0:
            render_tab_1()
        elif st.session_state.active_tab_index == 1:
            render_tab_2()
        elif st.session_state.active_tab_index == 2:
            render_tab_3()

if __name__ == "__main__":
    main()
