import os
import requests
import streamlit as st
from yfinance import data

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Yahoo Finance AI Portfolio Assistant",
    page_icon="📈",
    layout="wide",
)

if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

def get_auth_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}    

def render_auth_sidebar():
    st.sidebar.title("👤 Account")

    if st.session_state.token:
        st.sidebar.success(f"Logged in as: **{st.session_state.user_email}**")
        if st.sidebar.button("Log Out"):
            st.session_state.token = None
            st.session_state.user_email = None
            st.rerun()
        return True

    auth_mode = st.sidebar.radio("Choose Action", ["Login", "Register"])
    email = st.sidebar.text_input("Email", key="auth_email")
    password = st.sidebar.text_input("Password", type="password", key="auth_pwd")

    if auth_mode == "Register":
        if st.sidebar.button("Create Account"):
            if not email or not password:
                st.sidebar.error("Please fill in all fields.")
                return False
            
            res = requests.post(
                f"{BACKEND_URL}/auth/register",
                json={"email": email, "password": password},
            )
            if res.status_code == 201:
                st.sidebar.success("Account created! Please switch to Login.")
            else:
                st.sidebar.error(res.json().get("detail", "Registration failed."))

    elif auth_mode == "Login":
        if st.sidebar.button("Log In"):
            if not email or not password:
                st.sidebar.error("Please fill in all fields.")
                return False

            res = requests.post(
                f"{BACKEND_URL}/auth/login",
                data={"username": email, "password": password},
            )
            if res.status_code == 200:
                token_data = res.json()
                st.session_state.token = token_data["access_token"]
                st.session_state.user_email = email
                st.sidebar.success("Logged in successfully!")
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials.")

    return False

is_authenticated = render_auth_sidebar()

st.title("📈 Yahoo Finance AI Assistant & Portfolio Tracker")

if not is_authenticated:
    st.info("👈 Please **Log In** or **Register** using the sidebar to access your portfolio and the AI Financial Assistant.")
    st.stop()

tab_portfolio, tab_rag, tab_documents = st.tabs([
    "📊 Portfolio Tracker", 
    "🤖 AI Financial Assistant (RAG)", 
    "📂 Document Ingestion"
])    

ticker = st.text_input("Enter Stock Ticker:", "AAPL").upper().strip()

if st.button("Fetch Data"):
    try:
        response = requests.get(f"http://localhost:8000/stocks/{ticker}")
        
        if response.status_code == 200:
            data = response.json()
            st.metric(label=data["company_name"], value=f"${data['current_price']:,.2f}")
            st.metric(label="Previous Closing Price from Previous Trading Day", value=f"${data['previous_close']:,.2f}")
            st.metric(label="Company Market Cap", value=f"${data['market_cap']:,.2f}")
            st.metric(label="Year-to Day High", value=f"${data['year_to_date_high']:,.2f}")
            st.metric(label="Year-to Day Low", value=f"${data['year_to_date_low']:,.2f}")
            st.metric(label="Trailing Price to Expense Ratio", value=f"{data['trailing_pe']:,.2f}")
            st.metric(label="Forward Price to Expense Ratio", value=f"{data['forward_pe']:,.2f}")

            st.write(data["summary"])
        else:
            # Display the exact exception detail returned by FastAPI
            error_msg = response.json().get("detail", "Unknown server error")
            st.error(f"Backend Error ({response.status_code}): {error_msg}")

    except requests.exceptions.ConnectionError:
        st.error("Could not connect to FastAPI backend at http://localhost:8000.")