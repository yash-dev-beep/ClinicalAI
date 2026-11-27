import sqlite3
import hashlib
import os
import re
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

DB_NAME = "clinical_tracker.db"

# Strict Registration Constraints
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")
PIN_REGEX = re.compile(r"^[0-9]{4}$")

def get_connection() -> sqlite3.Connection:
    """
    Creates and returns an SQLite database connection with row factory, WAL, and foreign keys enabled.
    Activates PRAGMA journal_mode=WAL, PRAGMA synchronous=NORMAL, PRAGMA foreign_keys=ON,
    and PRAGMA temp_store=MEMORY to prevent database locked errors under multithreaded reads/writes.
    """
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a secure salt."""
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"pbkdf2${salt}${hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain password against stored PBKDF2 hash, SHA-256 hash, or plain text."""
    if not stored_hash:
        return False
    if "$" not in stored_hash:
        return password == stored_hash
    parts = stored_hash.split("$")
    try:
        if len(parts) == 3 and parts[0] == "pbkdf2":
            salt, hash_val = parts[1], parts[2]
            candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
            return candidate == hash_val
        elif len(parts) == 2:
            salt, hash_val = parts[0], parts[1]
            candidate = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
            return candidate == hash_val
    except Exception:
        return False
    return False

def init_db():
    """
    Initializes the unified relational database schema with WAL mode, foreign keys,
    strict constraints, and safe column migrations.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Unified Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT UNIQUE NOT NULL,
        identifier_type TEXT DEFAULT 'email',
        pin_hash TEXT NOT NULL,
        full_name TEXT,
        name TEXT,
        pin TEXT,
        password TEXT,
        password_hash TEXT,
        preferred_language TEXT DEFAULT 'English',
        language TEXT DEFAULT 'English',
        medications TEXT DEFAULT '',
        preexisting_conditions TEXT DEFAULT '',
        allergies_restrictions TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safe column migrations for users
    cursor.execute("PRAGMA table_info(users)")
    user_cols = {row["name"] for row in cursor.fetchall()}
    migrations = [
        ("identifier_type", "TEXT DEFAULT 'email'"),
        ("pin_hash", "TEXT"),
        ("full_name", "TEXT"),
        ("name", "TEXT"),
        ("pin", "TEXT"),
        ("password", "TEXT"),
        ("password_hash", "TEXT"),
        ("preferred_language", "TEXT DEFAULT 'English'"),
        ("language", "TEXT DEFAULT 'English'"),
        ("medications", "TEXT DEFAULT ''"),
        ("preexisting_conditions", "TEXT DEFAULT ''"),
        ("allergies_restrictions", "TEXT DEFAULT '[]'")
    ]
    for col_name, col_type in migrations:
        if col_name not in user_cols:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    # Synchronize legacy columns if present
    try:
        if "pin_hash" in user_cols:
            cursor.execute("UPDATE users SET password_hash = pin_hash WHERE (password_hash IS NULL OR password_hash = '') AND pin_hash IS NOT NULL")
        if "password" in user_cols:
            cursor.execute("UPDATE users SET password_hash = password WHERE (password_hash IS NULL OR password_hash = '') AND password IS NOT NULL")
            cursor.execute("UPDATE users SET password = password_hash WHERE (password IS NULL OR password = '') AND password_hash IS NOT NULL")
        if "full_name" in user_cols and "name" in user_cols:
            cursor.execute("UPDATE users SET full_name = name WHERE (full_name IS NULL OR full_name = '') AND name IS NOT NULL")
            cursor.execute("UPDATE users SET name = full_name WHERE (name IS NULL OR name = '') AND full_name IS NOT NULL")
    except Exception:
        pass

    # 2. Unified Reports Table with UNIQUE(user_id, report_date)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        report_date TEXT NOT NULL,
        health_score INTEGER,
        params_represented INTEGER,
        narrative_summary TEXT,
        daily_life_tips TEXT,
        comparative_analysis TEXT,
        recovery_diet_plan TEXT,
        cuisine_used TEXT,
        med_history TEXT DEFAULT '',
        current_meds TEXT DEFAULT '',
        analysis_summary TEXT DEFAULT '',
        narrative TEXT DEFAULT '',
        safety TEXT DEFAULT '',
        diet_json TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, report_date),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Safe column migrations for reports
    cursor.execute("PRAGMA table_info(reports)")
    report_cols = {row["name"] for row in cursor.fetchall()}
    report_migrations = [
        ("health_score", "INTEGER"),
        ("params_represented", "INTEGER"),
        ("narrative_summary", "TEXT"),
        ("daily_life_tips", "TEXT"),
        ("comparative_analysis", "TEXT"),
        ("recovery_diet_plan", "TEXT"),
        ("cuisine_used", "TEXT"),
        ("med_history", "TEXT DEFAULT ''"),
        ("current_meds", "TEXT DEFAULT ''"),
        ("analysis_summary", "TEXT DEFAULT ''"),
        ("narrative", "TEXT DEFAULT ''"),
        ("safety", "TEXT DEFAULT ''"),
        ("diet_json", "TEXT DEFAULT ''")
    ]
    for col_name, col_type in report_migrations:
        if col_name not in report_cols:
            try:
                cursor.execute(f"ALTER TABLE reports ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    # 3. Lab Metrics Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        test_name TEXT NOT NULL,
        test_value REAL NOT NULL,
        unit TEXT,
        reference_range TEXT,
        status TEXT,
        report_date TEXT NOT NULL,
        range TEXT,
        value REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Safe column migrations for lab_metrics
    cursor.execute("PRAGMA table_info(lab_metrics)")
    lm_cols = {row["name"] for row in cursor.fetchall()}
    lm_migrations = [
        ("user_id", "INTEGER"),
        ("report_date", "TEXT"),
        ("test_value", "REAL"),
        ("reference_range", "TEXT"),
        ("range", "TEXT"),
        ("value", "REAL")
    ]
    for col_name, col_type in lm_migrations:
        if col_name not in lm_cols:
            try:
                cursor.execute(f"ALTER TABLE lab_metrics ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    # Backfill user_id and report_date in lab_metrics from reports if missing
    try:
        cursor.execute("""
            UPDATE lab_metrics 
            SET user_id = (SELECT user_id FROM reports WHERE reports.id = lab_metrics.report_id),
                report_date = (SELECT report_date FROM reports WHERE reports.id = lab_metrics.report_id)
            WHERE user_id IS NULL OR report_date IS NULL
        """)
    except Exception:
        pass

    # Also keep legacy metrics table for backward compatibility
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
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
    );
    """)

    # 4. Chat History Table (per tab agent separation)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        agent_type TEXT NOT NULL, -- 'general_upload', 'report_analysis', 'diet_customizer'
        role TEXT NOT NULL, -- 'user' or 'assistant'
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 5. Password Resets / OTP Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT NOT NULL,
        otp_code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_identifier ON users(identifier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_date ON reports(user_id, report_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lab_metrics_report ON lab_metrics(report_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lab_metrics_user ON lab_metrics(user_id, report_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_agent ON chat_history(user_id, agent_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resets_id ON password_resets(identifier);")

    conn.commit()
    conn.close()

# =========================================================================
# User Registration & Authentication Operations
# =========================================================================

def validate_identifier_and_pin(identifier: str, pin: str) -> Tuple[bool, str, str, str]:
    """
    Validates identifier (email or phone) and 4-6 digit numeric PIN against strict regex.
    Returns (is_valid, normalized_id, id_type, error_msg).
    """
    raw_id = str(identifier).strip()
    raw_pin = str(pin).strip()

    if not raw_id:
        return False, "", "", "Identifier cannot be empty."

    if "@" in raw_id:
        norm_id = raw_id.lower()
        id_type = "email"
        if ".." in norm_id or not EMAIL_REGEX.match(norm_id):
            return False, "", "", "Please enter a valid email address (e.g. name@domain.com)."
    else:
        norm_id = re.sub(r"[\s\-]", "", raw_id)
        id_type = "phone"
        if not PHONE_REGEX.match(norm_id):
            return False, "", "", "Please enter a valid 10-15 digit phone number (e.g. 9876543210 or +919876543210)."

    if not PIN_REGEX.match(raw_pin):
        return False, "", "", "PIN must be strictly 4 numeric digits."

    return True, norm_id, id_type, ""

def register_user(
    identifier: str,
    password: str,
    preferred_language: str = "English",
    name: str = "",
    medications: str = "",
    preexisting_conditions: str = "",
    allergies: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Registers a new user enforcing strict constraints on identifier and PIN/password.
    Returns the user dict if successful, or None on failure.
    """
    is_valid, norm_id, id_type, err_msg = validate_identifier_and_pin(identifier, password)
    if not is_valid:
        return None

    clean_pin = str(password).strip()
    pw_hash = hash_password(clean_pin)
    user_name = name.strip() if name else norm_id.split("@")[0].capitalize()
    allergies_json = json.dumps(allergies or [])

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            cols = {row["name"] for row in cursor.fetchall()}

            insert_data = {
                "identifier": norm_id,
                "identifier_type": id_type,
                "pin_hash": pw_hash,
                "full_name": user_name,
                "name": user_name,
                "pin": clean_pin,
                "password": pw_hash,
                "password_hash": pw_hash,
                "preferred_language": preferred_language,
                "language": preferred_language,
                "medications": medications.strip(),
                "preexisting_conditions": preexisting_conditions.strip(),
                "allergies_restrictions": allergies_json
            }

            active_cols = [k for k in insert_data.keys() if k in cols]
            active_vals = [insert_data[k] for k in active_cols]

            placeholders = ", ".join(["?"] * len(active_cols))
            col_names = ", ".join(active_cols)
            cursor.execute(f"INSERT INTO users ({col_names}) VALUES ({placeholders})", active_vals)
            user_id = cursor.lastrowid

            return {
                "id": user_id,
                "identifier": norm_id,
                "identifier_type": id_type,
                "name": user_name,
                "full_name": user_name,
                "preferred_language": preferred_language,
                "medications": medications.strip(),
                "preexisting_conditions": preexisting_conditions.strip(),
                "allergies_restrictions": allergies or []
            }
    except Exception:
        return None
    finally:
        conn.close()

def authenticate_user(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates user credentials (4-6 digit numeric PIN or hashed password) and returns user record."""
    raw_id = str(identifier).strip()
    norm_id = raw_id.lower() if "@" in raw_id else re.sub(r"[\s\-]", "", raw_id)
    candidate = str(password).strip()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE identifier = ? OR identifier = ?", (norm_id, raw_id))
        row = cursor.fetchone()
        if not row:
            return None

        row_keys = row.keys()
        stored_pin = str(row["pin"]).strip() if "pin" in row_keys and row["pin"] else None
        stored_hash = (
            (row["pin_hash"] if "pin_hash" in row_keys else None) or
            (row["password_hash"] if "password_hash" in row_keys else None) or
            (row["password"] if "password" in row_keys else None)
        )

        authenticated = False
        if stored_pin and candidate == stored_pin:
            authenticated = True
        elif stored_hash and verify_password(candidate, stored_hash):
            authenticated = True

        if authenticated:
            d_name = (row["full_name"] if "full_name" in row_keys and row["full_name"] else None) or \
                     (row["name"] if "name" in row_keys and row["name"] else None) or \
                     row["identifier"].split("@")[0].capitalize()
            pref_lang = (row["preferred_language"] if "preferred_language" in row_keys else None) or \
                        (row["language"] if "language" in row_keys else None) or "English 🇬🇧"

            raw_allergies = row["allergies_restrictions"] if "allergies_restrictions" in row_keys else "[]"
            try:
                allergies_list = json.loads(raw_allergies) if raw_allergies else []
            except Exception:
                allergies_list = []

            return {
                "id": row["id"],
                "identifier": row["identifier"],
                "identifier_type": row["identifier_type"] if "identifier_type" in row_keys else ("email" if "@" in row["identifier"] else "phone"),
                "name": d_name,
                "full_name": d_name,
                "preferred_language": pref_lang,
                "language": pref_lang,
                "medications": row["medications"] if "medications" in row_keys else "",
                "preexisting_conditions": row["preexisting_conditions"] if "preexisting_conditions" in row_keys else "",
                "allergies_restrictions": allergies_list,
                "created_at": row["created_at"] if "created_at" in row_keys else None
            }
        return None
    finally:
        conn.close()

def reset_user_pin(identifier: str, new_pin: str) -> bool:
    """Updates user PIN and hash securely."""
    clean_pin = str(new_pin).strip()
    if not PIN_REGEX.match(clean_pin):
        return False
    pw_hash = hash_password(clean_pin)
    raw_id = str(identifier).strip()
    norm_id = raw_id.lower() if "@" in raw_id else re.sub(r"[\s\-]", "", raw_id)

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            cols = {row["name"] for row in cursor.fetchall()}

            set_clauses = []
            vals = []
            if "pin" in cols:
                set_clauses.append("pin = ?")
                vals.append(clean_pin)
            if "pin_hash" in cols:
                set_clauses.append("pin_hash = ?")
                vals.append(pw_hash)
            if "password" in cols:
                set_clauses.append("password = ?")
                vals.append(pw_hash)
            if "password_hash" in cols:
                set_clauses.append("password_hash = ?")
                vals.append(pw_hash)

            if set_clauses:
                vals.extend([norm_id, raw_id])
                sql = f"UPDATE users SET {', '.join(set_clauses)} WHERE identifier = ? OR identifier = ?"
                cursor.execute(sql, tuple(vals))
                return cursor.rowcount > 0
        return False
    except Exception:
        return False
    finally:
        conn.close()

def get_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user record by identifier (email or phone)."""
    raw_id = str(identifier).strip()
    norm_id = raw_id.lower() if "@" in raw_id else re.sub(r"[\s\-]", "", raw_id)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE identifier = ? OR identifier = ?", (norm_id, raw_id))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["name"] = d.get("full_name") or d.get("name") or d["identifier"].split("@")[0].capitalize()
        d["full_name"] = d["name"]
        raw_allergies = d.get("allergies_restrictions", "[]")
        try:
            d["allergies_restrictions"] = json.loads(raw_allergies) if raw_allergies else []
        except Exception:
            d["allergies_restrictions"] = []
        return d
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a user record by primary key."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["name"] = d.get("full_name") or d.get("name") or d["identifier"].split("@")[0].capitalize()
        d["full_name"] = d["name"]
        raw_allergies = d.get("allergies_restrictions", "[]")
        try:
            d["allergies_restrictions"] = json.loads(raw_allergies) if raw_allergies else []
        except Exception:
            d["allergies_restrictions"] = []
        return d
    finally:
        conn.close()

def update_user_language(user_id: int, language: str) -> bool:
    """Updates user preferred language."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("UPDATE users SET preferred_language = ?, language = ? WHERE id = ?", (language, language, user_id))
        return True
    except Exception:
        return False
    finally:
        conn.close()

def update_user_profile(
    user_id: int,
    medications: Optional[str] = None,
    preexisting_conditions: Optional[str] = None,
    allergies: Optional[List[str]] = None
) -> bool:
    """Updates medications, conditions, and allergies for the user."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            set_clauses = []
            vals = []
            if medications is not None:
                set_clauses.append("medications = ?")
                vals.append(medications.strip())
            if preexisting_conditions is not None:
                set_clauses.append("preexisting_conditions = ?")
                vals.append(preexisting_conditions.strip())
            if allergies is not None:
                set_clauses.append("allergies_restrictions = ?")
                vals.append(json.dumps(allergies))

            if set_clauses:
                vals.append(user_id)
                cursor.execute(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?", tuple(vals))
                return cursor.rowcount > 0
        return False
    except Exception:
        return False
    finally:
        conn.close()

# =========================================================================
# Allergies & Dietary Restrictions Persistence
# =========================================================================

def get_user_allergies(user_id: int) -> List[str]:
    """Returns the persistent list of allergies and dietary restrictions for the user."""
    user = get_user_by_id(user_id)
    if not user:
        return []
    return user.get("allergies_restrictions", [])

def append_user_allergies(user_id: int, new_allergies: List[str]) -> List[str]:
    """
    Appends newly detected allergies/restrictions to user's persistent profile in SQLite.
    Prevents duplicates (case-insensitive) and returns the updated combined list.
    """
    if not new_allergies:
        return get_user_allergies(user_id)

    current = get_user_allergies(user_id)
    existing_lower = {a.lower().strip() for a in current}
    added = False

    for item in new_allergies:
        clean_item = str(item).strip()
        if clean_item and clean_item.lower() not in existing_lower:
            current.append(clean_item)
            existing_lower.add(clean_item.lower())
            added = True

    if added:
        update_user_profile(user_id, allergies=current)
    return current

# =========================================================================
# OTP & Password Reset Operations
# =========================================================================

def store_otp(identifier: str, otp_code: str, validity_minutes: int = 15) -> bool:
    """Stores an OTP verification code with an expiry timestamp."""
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
    """Validates the OTP and updates the user's password/PIN."""
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

        try:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.now() > expires_at:
                return False, "Verification code has expired. Please request a new one."
        except Exception:
            pass

        # Update PIN in users
        clean_pin = str(new_password).strip()
        if not PIN_REGEX.match(clean_pin):
            return False, "PIN must be strictly 4 numeric digits."

        ok = reset_user_pin(clean_id, clean_pin)
        if ok:
            with conn:
                conn.execute("DELETE FROM password_resets WHERE identifier = ?", (clean_id,))
            return True, "PIN updated successfully!"
        return False, "Failed to update PIN. User may not exist."
    except Exception as e:
        return False, f"Password reset failed: {str(e)}"
    finally:
        conn.close()

# =========================================================================
# Clinical Reports & Metrics Operations
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

def save_clinical_record(
    user_id: int,
    report_date: str,
    health_score: Optional[int] = None,
    params_represented: Optional[int] = None,
    narrative_summary: str = "",
    daily_life_tips: str = "",
    comparative_analysis: str = "",
    recovery_diet_plan: str = "",
    cuisine_used: str = "",
    metrics: Optional[List[Dict[str, Any]]] = None,
    overwrite: bool = True,
    **kwargs
) -> Tuple[bool, int, str]:
    """
    Atomic transaction saving a report and all its extracted biomarkers into reports and lab_metrics.
    Enforces UNIQUE(user_id, report_date).
    """
    if metrics is None:
        metrics = []

    med_history = kwargs.get("med_history", kwargs.get("medical_history", ""))
    current_meds = kwargs.get("current_meds", kwargs.get("current_medications", ""))
    analysis_summary = kwargs.get("analysis_summary", narrative_summary)
    narrative = kwargs.get("narrative", narrative_summary)
    safety = kwargs.get("safety", "")
    diet_json = kwargs.get("diet_json", "")

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
                    SET health_score = ?, params_represented = ?, narrative_summary = ?,
                        daily_life_tips = ?, comparative_analysis = ?, recovery_diet_plan = ?,
                        cuisine_used = ?, med_history = ?, current_meds = ?,
                        analysis_summary = ?, narrative = ?, safety = ?, diet_json = ?,
                        created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    health_score, params_represented, narrative_summary, daily_life_tips,
                    comparative_analysis, recovery_diet_plan, cuisine_used, med_history,
                    current_meds, analysis_summary, narrative, safety, diet_json, report_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO reports (
                        user_id, report_date, health_score, params_represented,
                        narrative_summary, daily_life_tips, comparative_analysis,
                        recovery_diet_plan, cuisine_used, med_history, current_meds,
                        analysis_summary, narrative, safety, diet_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, report_date, health_score, params_represented,
                    narrative_summary, daily_life_tips, comparative_analysis,
                    recovery_diet_plan, cuisine_used, med_history, current_meds,
                    analysis_summary, narrative, safety, diet_json
                ))
                report_id = cursor.lastrowid

            # Upsert lab metrics by test_name to avoid deleting complementary tests
            cursor.execute("SELECT id, LOWER(test_name) as t_key FROM lab_metrics WHERE report_id = ?", (report_id,))
            existing_lm = {row["t_key"]: row["id"] for row in cursor.fetchall()}

            for m in metrics:
                t_name = str(m.get("test_name", "Unknown Marker")).strip()
                t_val = float(m.get("test_value", m.get("value", 0.0)))
                t_unit = str(m.get("unit", "")).strip()
                t_range = str(m.get("reference_range", m.get("range", ""))).strip()
                t_status = str(m.get("status", "Normal")).strip().capitalize()
                t_key = t_name.lower()

                if t_key in existing_lm:
                    lm_id = existing_lm[t_key]
                    cursor.execute("""
                        UPDATE lab_metrics
                        SET test_value = ?, value = ?, unit = ?, reference_range = ?, range = ?, status = ?
                        WHERE id = ?
                    """, (t_val, t_val, t_unit, t_range, t_range, t_status, lm_id))
                    cursor.execute("""
                        UPDATE metrics
                        SET value = ?, unit = ?, range = ?, status = ?
                        WHERE report_id = ? AND LOWER(test_name) = ?
                    """, (t_val, t_unit, t_range, t_status, report_id, t_key))
                else:
                    cursor.execute("""
                        INSERT INTO lab_metrics (report_id, user_id, report_date, test_name, test_value, unit, reference_range, status, range, value)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (report_id, user_id, report_date, t_name, t_val, t_unit, t_range, t_status, t_range, t_val))
                    cursor.execute("""
                        INSERT INTO metrics (report_id, test_name, value, range, status, unit)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (report_id, t_name, t_val, t_range, t_status, t_unit))

        return True, report_id, "SUCCESS"
    except sqlite3.IntegrityError as ie:
        return False, 0, f"IntegrityError: {str(ie)}"
    except Exception as e:
        return False, 0, f"Error: {str(e)}"
    finally:
        conn.close()

def save_report_and_metrics(*args, **kwargs) -> Tuple[bool, int, str]:
    """Backward-compatible alias for save_clinical_record."""
    return save_clinical_record(*args, **kwargs)

def get_user_reports(user_id: int) -> List[Dict[str, Any]]:
    """Returns all clinical reports for a user, ordered newest to oldest."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM reports
            WHERE user_id = ?
            ORDER BY report_date DESC, id DESC
        """, (user_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_report_metrics(report_id: int) -> List[Dict[str, Any]]:
    """Returns all biomarker records for a given report."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, report_id, user_id, test_name, 
                   COALESCE(test_value, value) as test_value,
                   COALESCE(test_value, value) as value,
                   COALESCE(unit, '') as unit,
                   COALESCE(reference_range, range, '') as reference_range,
                   COALESCE(reference_range, range, '') as range,
                   COALESCE(status, 'Normal') as status,
                   report_date, created_at
            FROM lab_metrics
            WHERE report_id = ?
            ORDER BY id ASC
        """, (report_id,))
        rows = cursor.fetchall()
        if not rows:
            cursor.execute("""
                SELECT id, report_id, test_name, value as test_value, value,
                       COALESCE(unit, '') as unit, COALESCE(range, '') as reference_range,
                       COALESCE(range, '') as range, COALESCE(status, 'Normal') as status,
                       created_at
                FROM metrics
                WHERE report_id = ?
                ORDER BY id ASC
            """, (report_id,))
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_user_metrics_history(user_id: int) -> List[Dict[str, Any]]:
    """
    Returns all historical biomarker metrics for a user, ordered chronologically (report_date ASC).
    Used directly for Plotly longitudinal trend graphs.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT lm.id, lm.report_id, lm.user_id, lm.test_name,
                   COALESCE(lm.test_value, lm.value) as test_value,
                   COALESCE(lm.test_value, lm.value) as value,
                   COALESCE(lm.unit, '') as unit,
                   COALESCE(lm.reference_range, lm.range, '') as reference_range,
                   COALESCE(lm.reference_range, lm.range, '') as range,
                   COALESCE(lm.status, 'Normal') as status,
                   r.report_date
            FROM lab_metrics lm
            JOIN reports r ON lm.report_id = r.id
            WHERE r.user_id = ?
            ORDER BY r.report_date ASC, lm.test_name ASC
        """, (user_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def get_all_user_metrics_history(user_id: int) -> List[Dict[str, Any]]:
    """Backward-compatible alias for get_user_metrics_history."""
    return get_user_metrics_history(user_id)

def get_latest_report_with_metrics(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the latest clinical report and all its extracted metrics for the given user."""
    reports = get_user_reports(user_id)
    if not reports:
        return None
    latest = reports[0]
    latest["metrics"] = get_report_metrics(latest["id"])
    return latest

def update_report_diet(report_id: int, new_diet_plan: str, cuisine_used: Optional[str] = None) -> bool:
    """Updates the recovery diet plan on an existing report."""
    conn = get_connection()
    try:
        with conn:
            if cuisine_used:
                conn.execute(
                    "UPDATE reports SET recovery_diet_plan = ?, cuisine_used = ? WHERE id = ?",
                    (new_diet_plan, cuisine_used, report_id)
                )
            else:
                conn.execute(
                    "UPDATE reports SET recovery_diet_plan = ? WHERE id = ?",
                    (new_diet_plan, report_id)
                )
        return True
    except Exception:
        return False
    finally:
        conn.close()

# =========================================================================
# Chat History Persistence Operations (Bot 1, Bot 2, Bot 3)
# =========================================================================

def save_chat_message(user_id: int, agent_type: str, role: str, message: str) -> bool:
    """
    Saves a chat message for a specific bot agent ('general_upload', 'report_analysis', 'diet_customizer').
    """
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO chat_history (user_id, agent_type, role, message)
                VALUES (?, ?, ?, ?)
            """, (user_id, agent_type.strip(), role.strip(), message.strip()))
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_chat_history(user_id: int, agent_type: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves chat history for a specific bot agent ordered chronologically (created_at ASC).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, agent_type, role, message, created_at
            FROM chat_history
            WHERE user_id = ? AND agent_type = ?
            ORDER BY id ASC
            LIMIT ?
        """, (user_id, agent_type.strip(), limit))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def clear_chat_history(user_id: int, agent_type: str) -> bool:
    """Clears conversation history for a specific bot agent."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM chat_history WHERE user_id = ? AND agent_type = ?", (user_id, agent_type.strip()))
        return True
    except Exception:
        return False
    finally:
        conn.close()
