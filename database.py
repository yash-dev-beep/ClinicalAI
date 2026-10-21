import sqlite3
import hashlib
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

DB_NAME = "clinical_tracker.db"

def get_connection() -> sqlite3.Connection:
    """Creates and returns an SQLite database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a password using SHA-256 with a secure salt."""
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain password against the stored salt$hash or plain text."""
    if not stored_hash:
        return False
    if "$" not in stored_hash:
        return password == stored_hash
    try:
        salt, hash_val = stored_hash.split("$", 1)
        candidate = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return candidate == hash_val
    except Exception:
        return False

def init_db():
    """
    Initializes the optimized SQLite database schema according to specifications:
    - Table users: id, identifier, password, preferred_language, created_at
    - Table reports: id, user_id, report_date, med_history, current_meds, analysis_summary, UNIQUE(user_id, report_date)
    - Table metrics: id, report_id, test_name, value, range, status
    - Table password_resets: id, identifier, otp_code, expires_at
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        password_hash TEXT,
        preferred_language TEXT DEFAULT 'English',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Column migrations for users
    cursor.execute("PRAGMA table_info(users)")
    user_cols = {row["name"] for row in cursor.fetchall()}
    if "password" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password TEXT")
        if "password_hash" in user_cols:
            cursor.execute("UPDATE users SET password = password_hash WHERE password IS NULL")
        elif "pin" in user_cols:
            cursor.execute("UPDATE users SET password = pin WHERE password IS NULL")
    if "preferred_language" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT DEFAULT 'English'")

    # 2. Reports Table with UNIQUE(user_id, report_date)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        report_date TEXT NOT NULL,
        med_history TEXT,
        current_meds TEXT,
        analysis_summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, report_date),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Column migrations for reports
    cursor.execute("PRAGMA table_info(reports)")
    report_cols = {row["name"] for row in cursor.fetchall()}
    if "med_history" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN med_history TEXT")
        if "history" in report_cols:
            cursor.execute("UPDATE reports SET med_history = history WHERE med_history IS NULL")
        elif "medical_history" in report_cols:
            cursor.execute("UPDATE reports SET med_history = medical_history WHERE med_history IS NULL")

    if "current_meds" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN current_meds TEXT")
        if "medications" in report_cols:
            cursor.execute("UPDATE reports SET current_meds = medications WHERE current_meds IS NULL")
        elif "current_medications" in report_cols:
            cursor.execute("UPDATE reports SET current_meds = current_medications WHERE current_meds IS NULL")

    if "analysis_summary" not in report_cols:
        cursor.execute("ALTER TABLE reports ADD COLUMN analysis_summary TEXT")
        if "narrative_summary" in report_cols:
            cursor.execute("UPDATE reports SET analysis_summary = narrative_summary WHERE analysis_summary IS NULL")

    # Clean legacy duplicates if any before enforcing UNIQUE(user_id, report_date)
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("""
    DELETE FROM reports 
    WHERE id NOT IN (
        SELECT MAX(id) FROM reports GROUP BY user_id, report_date
    );
    """)
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_report_date ON reports(user_id, report_date);")

    # 3. Metrics & Lab Metrics Table (Schema compliance)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        test_name TEXT NOT NULL,
        value REAL NOT NULL,
        range TEXT,
        status TEXT,
        unit TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        test_name TEXT NOT NULL,
        value REAL NOT NULL,
        range TEXT,
        status TEXT,
        unit TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("PRAGMA table_info(metrics)")
    metric_cols = {row["name"] for row in cursor.fetchall()}
    if "range" not in metric_cols:
        cursor.execute("ALTER TABLE metrics ADD COLUMN range TEXT")
        if "reference_range" in metric_cols:
            cursor.execute("UPDATE metrics SET range = reference_range WHERE range IS NULL")
    if "unit" not in metric_cols:
        cursor.execute("ALTER TABLE metrics ADD COLUMN unit TEXT")

    cursor.execute("PRAGMA table_info(lab_metrics)")
    lab_metric_cols = {row["name"] for row in cursor.fetchall()}
    if "test_value" in lab_metric_cols or "user_id" in lab_metric_cols:
        cursor.execute("DROP TABLE lab_metrics;")
        lab_metric_cols = set()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        test_name TEXT NOT NULL,
        value REAL NOT NULL,
        range TEXT,
        status TEXT,
        unit TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO lab_metrics (id, report_id, test_name, value, range, status, unit, created_at)
        SELECT id, report_id, test_name, value, range, status, unit, created_at FROM metrics;
    """)

    # 4. Password Resets / OTP Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT NOT NULL,
        otp_code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indexes for rapid retrieval
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_date ON reports(user_id, report_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_report_id ON metrics(report_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resets_id ON password_resets(identifier);")

    conn.commit()
    conn.close()

# =========================================================================
# Authentication & User Management
# =========================================================================

def register_user(identifier: str, password: str, preferred_language: str = "English") -> Optional[Dict[str, Any]]:
    """Registers a new user with hashed password and preferred language."""
    clean_id = identifier.strip().lower()
    pw_hash = hash_password(password.strip())
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (identifier, password, password_hash, preferred_language)
                VALUES (?, ?, ?, ?)
            """, (clean_id, pw_hash, pw_hash, preferred_language))
            user_id = cursor.lastrowid
            return {
                "id": user_id,
                "identifier": clean_id,
                "preferred_language": preferred_language
            }
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def authenticate_user(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates user credentials and returns the user object if authenticated."""
    clean_id = identifier.strip().lower()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, identifier, password, password_hash, preferred_language, created_at FROM users WHERE identifier = ?", (clean_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        stored_pw = row["password"] or row["password_hash"]
        if verify_password(password.strip(), stored_pw):
            return {
                "id": row["id"],
                "identifier": row["identifier"],
                "preferred_language": row["preferred_language"],
                "created_at": row["created_at"]
            }
        return None
    finally:
        conn.close()

def get_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user record by identifier (email/phone)."""
    clean_id = identifier.strip().lower()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, identifier, preferred_language, created_at FROM users WHERE identifier = ?", (clean_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a user record by primary key."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, identifier, preferred_language, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_user_language(user_id: int, language: str) -> bool:
    """Updates the preferred language for a user."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("UPDATE users SET preferred_language = ? WHERE id = ?", (language, user_id))
        return True
    except Exception:
        return False
    finally:
        conn.close()

# =========================================================================
# OTP & Password Reset Operations
# =========================================================================

def store_otp(identifier: str, otp_code: str, validity_minutes: int = 15) -> bool:
    """Stores a simulated OTP verification code with an expiry timestamp."""
    clean_id = identifier.strip().lower()
    expires_at = datetime.now() + timedelta(minutes=validity_minutes)
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM password_resets WHERE identifier = ?", (clean_id,))
            cursor.execute("""
                INSERT INTO password_resets (identifier, otp_code, expires_at)
                VALUES (?, ?, ?)
            """, (clean_id, str(otp_code), expires_at.isoformat()))
        return True
    except Exception:
        return False
    finally:
        conn.close()

def verify_and_reset_password(identifier: str, otp_code: str, new_password: str) -> Tuple[bool, str]:
    """Validates the OTP and updates the user's password."""
    clean_id = identifier.strip().lower()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM password_resets 
            WHERE identifier = ? AND otp_code = ?
            ORDER BY id DESC LIMIT 1
        """, (clean_id, str(otp_code).strip()))
        row = cursor.fetchone()
        if not row:
            return False, "Invalid or expired verification code."
        
        # Check expiry
        try:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.now() > expires_at:
                return False, "Verification code has expired. Please request a new one."
        except Exception:
            pass

        # Update password in users table
        pw_hash = hash_password(new_password.strip())
        with conn:
            conn.execute("UPDATE users SET password = ?, password_hash = ? WHERE identifier = ?", (pw_hash, pw_hash, clean_id))
            conn.execute("DELETE FROM password_resets WHERE identifier = ?", (clean_id,))
        return True, "Password reset successfully!"
    except Exception as e:
        return False, f"Password reset failed: {str(e)}"
    finally:
        conn.close()

# =========================================================================
# Reports & Metrics Operations
# =========================================================================

def check_report_exists(user_id: int, report_date: str) -> Optional[Dict[str, Any]]:
    """Checks if a report for this user and date already exists."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE user_id = ? AND report_date = ?", (user_id, report_date))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def save_report_and_metrics(
    user_id: int,
    report_date: str,
    med_history: str = "",
    current_meds: str = "",
    analysis_summary: str = "",
    metrics: Optional[List[Dict[str, Any]]] = None,
    overwrite: bool = False,
    **kwargs
) -> Tuple[bool, int, str]:
    """
    Saves a clinical report and its extracted metrics in an atomic transaction.
    Enforces UNIQUE(user_id, report_date).
    If overwrite is True, updates existing report and deletes old metrics.
    If duplicate and overwrite is False, returns (False, existing_id, 'DUPLICATE_REPORT').
    """
    if metrics is None:
        metrics = []
    if not med_history and "medical_history" in kwargs:
        med_history = kwargs["medical_history"]
    if not current_meds and "current_medications" in kwargs:
        current_meds = kwargs["current_medications"]
    if not analysis_summary and "narrative_summary" in kwargs:
        analysis_summary = kwargs["narrative_summary"]

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            existing = check_report_exists(user_id, report_date)
            
            if existing:
                if not overwrite:
                    return False, existing["id"], "DUPLICATE_REPORT"
                
                report_id = existing["id"]
                cursor.execute("""
                    UPDATE reports
                    SET med_history = ?, current_meds = ?, analysis_summary = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (med_history, current_meds, analysis_summary, report_id))
                
                cursor.execute("DELETE FROM metrics WHERE report_id = ?", (report_id,))
                cursor.execute("DELETE FROM lab_metrics WHERE report_id = ?", (report_id,))
            else:
                cursor.execute("""
                    INSERT INTO reports (user_id, report_date, med_history, current_meds, analysis_summary)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, report_date, med_history, current_meds, analysis_summary))
                report_id = cursor.lastrowid

            cursor.execute("PRAGMA table_info(lab_metrics)")
            lm_cols = {row["name"] for row in cursor.fetchall()}

            for m in metrics:
                range_val = m.get("range", m.get("reference_range", "")).strip()
                t_name = m.get("test_name", "Unknown Parameter").strip()
                val = float(m.get("value", 0.0))
                st_val = m.get("status", "Normal").strip().capitalize()
                unit_val = m.get("unit", "").strip()

                cursor.execute("""
                    INSERT INTO metrics (report_id, test_name, value, range, status, unit)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (report_id, t_name, val, range_val, st_val, unit_val))

                if "user_id" in lm_cols and "report_date" in lm_cols:
                    cursor.execute("""
                        INSERT INTO lab_metrics (report_id, user_id, report_date, test_name, value, range, status, unit)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (report_id, user_id, report_date, t_name, val, range_val, st_val, unit_val))
                else:
                    cursor.execute("""
                        INSERT INTO lab_metrics (report_id, test_name, value, range, status, unit)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (report_id, t_name, val, range_val, st_val, unit_val))

        return True, report_id, "SUCCESS"
    except sqlite3.IntegrityError as ie:
        return False, 0, f"IntegrityError: {str(ie)}"
    except Exception as e:
        return False, 0, f"Error: {str(e)}"
    finally:
        conn.close()

def get_user_reports(user_id: int) -> List[Dict[str, Any]]:
    """Returns all clinical reports for a user, sorted newest to oldest."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, report_date, 
                   COALESCE(med_history, '') as med_history, 
                   COALESCE(current_meds, '') as current_meds, 
                   COALESCE(analysis_summary, '') as analysis_summary,
                   created_at
            FROM reports
            WHERE user_id = ?
            ORDER BY report_date DESC, id DESC
        """, (user_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_report_metrics(report_id: int) -> List[Dict[str, Any]]:
    """Returns all metrics for a given report."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, report_id, test_name, value, 
                   COALESCE(range, '') as range, 
                   COALESCE(status, 'Normal') as status, 
                   COALESCE(unit, '') as unit, 
                   created_at
            FROM metrics
            WHERE report_id = ?
            ORDER BY id ASC
        """, (report_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_all_user_metrics_history(user_id: int) -> List[Dict[str, Any]]:
    """
    Returns all historical metrics for a user joined with the report date,
    ordered chronologically for longitudinal Plotly trends.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, m.report_id, m.test_name, m.value, m.range, m.status, m.unit, r.report_date
            FROM metrics m
            JOIN reports r ON m.report_id = r.id
            WHERE r.user_id = ?
            ORDER BY r.report_date ASC, m.test_name ASC
        """, (user_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_latest_report_with_metrics(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the latest clinical report and all its extracted metrics for the given user."""
    reports = get_user_reports(user_id)
    if not reports:
        return None
    latest = reports[0]
    metrics = get_report_metrics(latest["id"])
    latest["metrics"] = metrics
    return latest