import sqlite3
from streamlit.testing.v1 import AppTest
import database
import ai_engine

def test_database_schema_and_integrity():
    database.init_db()
    conn = database.get_connection()
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print(f"Verified Tables: {tables}")
    
    assert "users" in tables, "users table missing"
    assert "reports" in tables, "reports table missing"
    assert "metrics" in tables, "metrics table missing"
    assert "lab_metrics" in tables, "lab_metrics table missing"

    # Verify column structures according to Module 1 & 2 specifications
    user_cols = {c["name"] for c in conn.execute("PRAGMA table_info(users)").fetchall()}
    assert {"id", "identifier", "password", "preferred_language"}.issubset(user_cols), f"Missing user columns: {user_cols}"

    report_cols = {c["name"] for c in conn.execute("PRAGMA table_info(reports)").fetchall()}
    assert {"id", "user_id", "report_date", "med_history", "current_meds", "analysis_summary"}.issubset(report_cols), f"Missing report columns: {report_cols}"

    metric_cols = {c["name"] for c in conn.execute("PRAGMA table_info(metrics)").fetchall()}
    assert {"id", "report_id", "test_name", "value", "range", "status"}.issubset(metric_cols), f"Missing metric columns: {metric_cols}"

    lab_metric_cols = {c["name"] for c in conn.execute("PRAGMA table_info(lab_metrics)").fetchall()}
    assert {"id", "report_id", "test_name", "value", "range", "status"}.issubset(lab_metric_cols), f"Missing lab_metric columns: {lab_metric_cols}"
    
    conn.close()

def test_user_authentication_flow():
    test_email = "test_auth_doc@clinicalai.org"
    test_password = "DoctorSecurePass#2026"
    
    # Register
    user = database.register_user(test_email, test_password, "English")
    if not user:
        user = database.get_user_by_identifier(test_email)
    assert user is not None, "User registration failed"
    
    # Authenticate
    auth = database.authenticate_user(test_email, test_password)
    assert auth is not None, "Authentication failed with valid password"
    assert auth["identifier"] == test_email.lower()

    # Reject invalid password
    bad_auth = database.authenticate_user(test_email, "WrongPassword")
    assert bad_auth is None, "Authentication succeeded with incorrect password"

def test_unique_report_date_and_duplicate_handling():
    user = database.get_user_by_identifier("test_auth_doc@clinicalai.org")
    assert user is not None
    user_id = user["id"]
    test_date = "2026-10-19"
    
    sample_metrics = [
        {"test_name": "Hemoglobin", "value": 14.5, "unit": "g/dL", "reference_range": "13.0 - 17.0", "status": "Normal"},
        {"test_name": "Fasting Blood Glucose", "value": 126.0, "unit": "mg/dL", "reference_range": "70 - 99", "status": "High"},
        {"test_name": "Serum Creatinine", "value": 1.1, "unit": "mg/dL", "reference_range": "0.7 - 1.3", "status": "Normal"}
    ]

    # Save initial report with overwrite=True to ensure clean state
    ok, rep_id, msg = database.save_report_and_metrics(
        user_id=user_id,
        report_date=test_date,
        medical_history="Type 2 Diabetes",
        current_medications="Metformin 500mg",
        metrics=sample_metrics,
        overwrite=True
    )
    assert ok, f"Initial report save failed: {msg}"
    assert rep_id > 0

    # Attempt duplicate save with overwrite=False -> Must trigger duplicate rejection
    ok_dup, dup_id, msg_dup = database.save_report_and_metrics(
        user_id=user_id,
        report_date=test_date,
        medical_history="Type 2 Diabetes",
        current_medications="Metformin 500mg",
        metrics=sample_metrics,
        overwrite=False
    )
    assert not ok_dup, "Duplicate save should fail when overwrite=False"
    assert msg_dup == "DUPLICATE_REPORT", f"Expected DUPLICATE_REPORT, got {msg_dup}"

    # Overwrite existing
    ok_over, over_id, msg_over = database.save_report_and_metrics(
        user_id=user_id,
        report_date=test_date,
        medical_history="Type 2 Diabetes",
        current_medications="Metformin 500mg",
        metrics=sample_metrics,
        overwrite=True
    )
    assert ok_over, f"Overwrite failed: {msg_over}"

    # Verify history
    history = database.get_all_user_metrics_history(user_id)
    assert len(history) >= 3, f"Expected at least 3 metrics in history, got {len(history)}"

def test_ai_engine_components():
    # 1. Simulated OTP
    otp = ai_engine.generate_simulated_otp("patient@test.com")
    assert len(otp) == 6 and otp.isdigit(), f"Invalid OTP format: {otp}"

    # 2. Pydantic Schemas validation
    metric = ai_engine.ExtractedMetric(
        test_name="Total Cholesterol",
        value=215.0,
        unit="mg/dL",
        range="< 200",
        status="High"
    )
    assert metric.test_name == "Total Cholesterol"

    report = ai_engine.ClinicalReportExtraction(
        report_date="2026-10-19",
        metrics=[metric]
    )
    assert report.report_date == "2026-10-19"
    assert len(report.metrics) == 1

def test_streamlit_app_headless_render():
    print("Testing Streamlit app headless render with AppTest...")
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, f"Streamlit application encountered unhandled exceptions: {at.exception}"
    print(f"AppTest succeeded with zero exceptions (Exceptions count: {len(at.exception)})")

if __name__ == "__main__":
    test_database_schema_and_integrity()
    print("[PASS] test_database_schema_and_integrity passed.")
    test_user_authentication_flow()
    print("[PASS] test_user_authentication_flow passed.")
    test_unique_report_date_and_duplicate_handling()
    print("[PASS] test_unique_report_date_and_duplicate_handling passed.")
    test_ai_engine_components()
    print("[PASS] test_ai_engine_components passed.")
    test_streamlit_app_headless_render()
    print("[PASS] test_streamlit_app_headless_render passed.")
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
