import streamlit as st
import time
import os
from sqlalchemy import create_engine, text
from passlib.context import CryptContext

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Accountooze Accounting Marathon", layout="centered")

# -------------------------------------------------
# BRANDING
# -------------------------------------------------
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
}
.accountooze-card {
    background: white;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    margin-bottom: 1.5rem;
}
.footer {
    text-align:center;
    font-size:0.85rem;
    color:#777;
    margin-top:3rem;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# DATABASE
# -------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pwd):
    return pwd_context.hash(pwd)

def verify_password(pwd, hashed):
    return pwd_context.verify(pwd, hashed)

# -------------------------------------------------
# TABLES
# -------------------------------------------------
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT
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

# -------------------------------------------------
# QUESTIONS
# -------------------------------------------------
MCQS = [
    ("Security deposit received from tenant should be recorded as:", "Liability",
     ["Rental Income", "Liability", "Accounts Receivable", "Owner Contribution"]),
    ("Loan taken from bank will increase which account?", "Liability",
     ["Expense", "Income", "Asset", "Liability"]),
    ("Owner withdrawal should be recorded as:", "Equity / Draw",
     ["Expense", "Equity / Draw", "Liability", "Income"]),
    ("Which report does a CPA use to start tax return?", "Balance Sheet",
     ["Profit & Loss", "Trial Balance", "Balance Sheet", "Cash Flow"]),
    ("Security deposits should appear on which report?", "Balance Sheet",
     ["Profit & Loss", "Balance Sheet", "Cash Flow", "AR Aging"])
]

BANK_TASKS = [
    {
        "description": "AMZN Mktp US*2A45 Office Supplies Seattle",
        "vendor": "Amazon",
        "gl": "Office Supplies Expense"
    },
    {
        "description": "UBER *TRIP HELP.UBER.COM",
        "vendor": "Uber",
        "gl": "Travel Expense"
    },
    {
        "description": "COMCAST CABLE INTERNET",
        "vendor": "Comcast",
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

# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
for k in ["user_id", "email", "score", "submitted", "start_time"]:
    if k not in st.session_state:
        st.session_state[k] = None

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown("""
<div class="accountooze-card">
<h1>Accountooze Accounting Marathon</h1>
<p>Real-world accounting skill evaluation</p>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# AUTH
# -------------------------------------------------
if not st.session_state.user_id:
    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            with engine.connect() as conn:
                user = conn.execute(
                    text("SELECT id, password FROM users WHERE email=:e"),
                    {"e": email}
                ).fetchone()

            if user and verify_password(password, user.password):
                st.session_state.user_id = user.id
                st.session_state.email = email
                st.session_state.score = 0
                st.session_state.start_time = time.time()
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        new_email = st.text_input("Email", key="r1")
        new_password = st.text_input("Password", type="password", key="r2")

        if st.button("Create Account"):
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO users (email, password) VALUES (:e, :p)"),
                        {"e": new_email, "p": hash_password(new_password)}
                    )
                st.success("Account created. Login now.")
            except:
                st.error("Email already exists")
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------
# TEST
# -------------------------------------------------
else:
    if not st.session_state.submitted:
        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.subheader("🧠 MCQs")

        for q, ans, opts in MCQS:
            user_ans = st.radio(q, opts, key=q)
            if user_ans == ans:
                st.session_state.score += 1
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.subheader("🏦 Bank Transaction Classification")

        for i, task in enumerate(BANK_TASKS):
            st.write(f"**Bank Description:** {task['description']}")
            vendor = st.text_input("Vendor Name", key=f"v{i}")
            gl = st.selectbox("GL Account", GL_OPTIONS, key=f"g{i}")

            if vendor.strip().lower() == task["vendor"].lower():
                st.session_state.score += 1
            if gl == task["gl"]:
                st.session_state.score += 2

        if st.button("Submit Test"):
            st.session_state.submitted = True
            st.session_state.end_time = time.time()
            st.experimental_rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------
    # RESULTS
    # -------------------------------------------------
    else:
        time_taken = round(st.session_state.end_time - st.session_state.start_time, 2)

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO results (user_id, score, time_taken) VALUES (:u,:s,:t)"),
                {"u": st.session_state.user_id,
                 "s": st.session_state.score,
                 "t": time_taken}
            )

            leaderboard = conn.execute(text("""
                SELECT u.email, r.score, r.time_taken
                FROM results r
                JOIN users u ON u.id = r.user_id
                ORDER BY r.score DESC, r.time_taken ASC
                LIMIT 10
            """)).fetchall()

        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.success("Test Completed")
        st.write(f"Score: **{st.session_state.score}**")
        st.write(f"Time Taken: **{time_taken} sec**")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="accountooze-card">', unsafe_allow_html=True)
        st.subheader("🏆 Leaderboard")
        st.table(leaderboard)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Logout"):
            st.session_state.clear()
            st.experimental_rerun()

# -------------------------------------------------
# FOOTER
# -------------------------------------------------
st.markdown("""
<div class="footer">
© 2026 Accountooze Outstaffing · Accounting Training Platform
</div>
""", unsafe_allow_html=True)
