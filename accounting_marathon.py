import streamlit as st
import time
import os
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
import hashlib


# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="Accountooze Accounting Marathon",
    layout="centered"
)

# =================================================
# BRANDING (Accountooze)
# =================================================
st.markdown("""
<style>
.block-container { padding-top: 2rem; }
body { background-color: #f6f8fb; }
h1, h2, h3 { color: #0f2a44; }

.stButton button {
    background-color: #0f2a44;
    color: white;
    border-radius: 6px;
    font-weight: 600;
    padding: 0.5rem 1.2rem;
}

.accountooze-card {
    background: white;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    margin-bottom: 1.5rem;
}

.footer {
    text-align: center;
    font-size: 0.85rem;
    color: #777;
    margin-top: 3rem;
}
</style>
""", unsafe_allow_html=True)

# =================================================
# DATABASE
# =================================================
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def clean_email(email: str) -> str:
    return email.strip().lower()

def normalize_password(pwd: str) -> str:
    """
    Pre-hash password to fixed length so bcrypt never sees >72 bytes

    """
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

def hash_password(pwd: str) -> str:
    return pwd_context.hash(normalize_password(pwd))

def verify_password(pwd: str, hashed: str) -> bool:
    return pwd_context.verify(normalize_password(pwd), hashed)

def validate_password(pwd: str):
    if len(pwd) < 8:
        return "Password must be at least 8 characters"
    return None
# =================================================
# CREATE TABLES
# =================================================
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS results (
            id SERIAL PRIMARY KEY,
            user_id INT,
            score INT,
            time_taken FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

# =================================================
# QUESTIONS
# =================================================
MCQS = [
    ("Security deposit received from tenant should be recorded as:",
     "Liability",
     ["Rental Income", "Liability", "Accounts Receivable", "Owner Contribution"]),

    ("Loan taken from bank will increase which account?",
     "Liability",
     ["Expense", "Income", "Asset", "Liability"]),

    ("Owner withdrawal should be recorded as:",
     "Equity / Draw",
     ["Expense", "Equity / Draw", "Liability", "Income"]),

    ("Which report does a CPA review first at tax time?",
     "Balance Sheet",
     ["Profit & Loss", "Trial Balance", "Balance Sheet", "Cash Flow"]),

    ("Security deposits should appear on which report?",
     "Balance Sheet",
     ["Profit & Loss", "Balance Sheet", "Cash Flow", "AR Aging"]),
]

BANK_TASKS = [
    {
        "description": "AMZN Mktp US*2A45 Office Supplies Seattle",
        "vendor": "amazon",
        "gl": "Office Supplies Expense"
    },
    {
        "description": "UBER *TRIP HELP.UBER.COM",
        "vendor": "uber",
        "gl": "Travel Expense"
    },
    {
        "description": "COMCAST CABLE INTERNET",
        "vendor": "comcast",
        "gl": "Internet Expense"
    }
]

GL_OPTIONS = [
    "Office Supplies Expense",
    "Travel Expense",
    "Internet Expense",
    "Repairs & Maintenance",
    "Rent Expense",
    "Advertising Expense"
]

# =================================================
# SESSION STATE INIT
# =================================================
for key in ["user_id", "email", "score", "start_time", "submitted"]:
    if key not in st.session_state:
        st.session_state[key] = None

# =================================================
# HEADER
# =================================================
st.markdown("""
<div class="accountooze-card">
<h1>Accountooze Accounting Marathon</h1>
<p>Real-world accounting skill evaluation platform</p>
</div>
""", unsafe_allow_html=True)

# =================================================
# AUTHENTICATION
# =================================================
if not st.session_state.user_id:

    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Create Account"])

    # ---------------- LOGIN ----------------
    with tab_login:
        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)

        email_raw = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            email = clean_email(email_raw)

            with engine.connect() as conn:
                user = conn.execute(
                    text("SELECT id, password FROM users WHERE lower(email)=:e"),
                    {"e": email}
                ).fetchone()

            if user and verify_password(password, user.password):
                st.session_state.user_id = user.id
                st.session_state.email = email
                st.session_state.score = 0
                st.session_state.start_time = time.time()
                st.session_state.submitted = False
                st.experimental_rerun()
            else:
                st.error("Invalid email or password")

        st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- REGISTER ----------------
    with tab_register:
        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)

        reg_email_raw = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pwd")

        if st.button("Create Account"):
            email = clean_email(reg_email_raw)
            pwd_error = validate_password(reg_password)

            if not email or not reg_password:
                st.error("Email and password are required")
            elif pwd_error:
                st.error(pwd_error)
            else:
                with engine.begin() as conn:
                    existing = conn.execute(
                        text("SELECT id FROM users WHERE lower(email)=:e"),
                        {"e": email}
                    ).fetchone()

                    if existing:
                        st.error("Account already exists. Please login.")
                    else:
                        conn.execute(
                            text("""
                                INSERT INTO users (email, password)
                                VALUES (:e, :p)
                            """),
                            {
                                "e": email,
                                "p": hash_password(reg_password)
                            }
                        )
                        st.success("Account created successfully. Please login.")
                        st.stop()

        st.markdown('</div>', unsafe_allow_html=True)

# =================================================
# TEST
# =================================================
else:
    if not st.session_state.submitted:

        # -------- MCQs --------
        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.subheader("🧠 MCQs")

        for q, correct, options in MCQS:
            ans = st.radio(q, options, key=q)
            if ans == correct:
                st.session_state.score += 1

        st.markdown('</div>', unsafe_allow_html=True)

        # -------- BANK TASK --------
        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.subheader("🏦 Bank Transaction Classification")

        for i, task in enumerate(BANK_TASKS):
            st.write(f"**Bank Description:** {task['description']}")
            vendor_input = st.text_input("Vendor Name", key=f"vendor_{i}")
            gl_input = st.selectbox("GL Account", GL_OPTIONS, key=f"gl_{i}")

            if vendor_input.strip().lower() == task["vendor"]:
                st.session_state.score += 1
            if gl_input == task["gl"]:
                st.session_state.score += 2

        if st.button("Submit Test"):
            st.session_state.submitted = True
            st.session_state.end_time = time.time()
            st.experimental_rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # =================================================
    # RESULTS + LEADERBOARD
    # =================================================
    else:
        time_taken = round(st.session_state.end_time - st.session_state.start_time, 2)

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO results (user_id, score, time_taken)
                    VALUES (:u, :s, :t)
                """),
                {
                    "u": st.session_state.user_id,
                    "s": st.session_state.score,
                    "t": time_taken
                }
            )

            leaderboard = conn.execute(text("""
                SELECT u.email, r.score, r.time_taken
                FROM results r
                JOIN users u ON u.id = r.user_id
                ORDER BY r.score DESC, r.time_taken ASC
                LIMIT 10
            """)).fetchall()

        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.success("✅ Test Completed")
        st.write(f"Score: **{st.session_state.score}**")
        st.write(f"Time Taken: **{time_taken} seconds**")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.subheader("🏆 Leaderboard")
        st.table(leaderboard)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Logout"):
            st.session_state.clear()
            st.experimental_rerun()

# =================================================
# FOOTER
# =================================================
st.markdown("""
<div class="footer">
© 2026 Accountooze Outstaffing · Accounting Training Platform
</div>
""", unsafe_allow_html=True)
