import os
import requests
import streamlit as st
import plotly.express as px
import pandas as pd
import yfinance

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

tab_portfolio, tab_stockresearch, tab_rag, tab_documents = st.tabs([
    "📊 Portfolio Tracker",
    "📊 Stock Research",
    "🤖 AI Financial Assistant (RAG)",
    "📂 Document Ingestion"
])

# =====================================================================
# TAB 1: PORTFOLIO TRACKER
# =====================================================================
with tab_portfolio:
    st.header("My Investment Portfolio")
    st.caption("Manage your holdings and monitor real-time performance")

    portfolio_items = []
    fetch_error = False

    try:
        res = requests.get(f"{BACKEND_URL}/portfolio/", headers=get_auth_headers())
        if res.status_code == 200:
            portfolio_items = res.json()
        else:
            fetch_error = True
    except requests.exceptions.ConnectionError:
        fetch_error = True

    if fetch_error:
        st.error("Could not load portfolio holdings from the backend.")
    else:
        # --- TOP KPI SUMMARY ROW ---
        if portfolio_items:
            df_portfolio = pd.DataFrame(portfolio_items)

            df_portfolio['total_cost'] = df_portfolio['shares'] * df_portfolio['buy_price']
            df_portfolio['current_price'] = df_portfolio.get('current_price', df_portfolio['buy_price'])
            df_portfolio['market_value'] = df_portfolio['shares'] * df_portfolio['current_price']
            df_portfolio['unrealized_gain'] = df_portfolio['market_value'] - df_portfolio['total_cost']

            total_portfolio_val = df_portfolio['market_value'].sum()
            total_cost_basis = df_portfolio['total_cost'].sum()
            total_gain_loss = df_portfolio['unrealized_gain'].sum()
            pct_gain_loss = (total_gain_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Total Portfolio Value", f"${total_portfolio_val:,.2f}")
            kpi2.metric("Total Cost Basis", f"${total_cost_basis:,.2f}")
            kpi3.metric(
                "Total Gain / Loss",
                f"${total_gain_loss:+,.2f}",
                delta=f"{pct_gain_loss:+.2f}%"
            )
            kpi4.metric("Total Positions", len(df_portfolio))

            st.divider()

        # --- TWO COLUMN MAIN WORKSPACE ---
        col_form, col_holdings = st.columns([1, 2], gap="large")

        # LEFT COLUMN: Add Holding Form
        with col_form:
            with st.container(border=True):
                st.subheader("➕ Add Position")

                with st.form("add_stock_form", clear_on_submit=True):
                    ticker_input = st.text_input("Ticker Symbol", placeholder="e.g. AAPL, NVDA").upper().strip()

                    c_shares, c_price = st.columns(2)
                    with c_shares:
                        shares_input = st.number_input("Shares Owned", min_value=0.01, step=1.0, value=1.0)
                    with c_price:
                        price_input = st.number_input("Avg Buy Price ($)", min_value=0.01, step=1.0, value=100.0)

                    submitted = st.form_submit_button("Add to Portfolio", type="primary", width="stretch")

                    if submitted:
                        if not ticker_input:
                            st.warning("Please enter a valid ticker symbol.")
                        else:
                            payload = {
                                "ticker": ticker_input,
                                "shares": shares_input,
                                "buy_price": price_input,
                            }
                            res = requests.post(
                                f"{BACKEND_URL}/portfolio/",
                                json=payload,
                                headers=get_auth_headers(),
                            )
                            if res.status_code == 201:
                                st.toast(f"Added {ticker_input} to portfolio!", icon="✅")
                                st.rerun()
                            else:
                                st.error(f"Error adding stock: {res.text}")

        # RIGHT COLUMN: Holdings Table & Visualization
        with col_holdings:
            st.subheader("📊 Current Positions")

            if not portfolio_items:
                st.info("No holdings found. Add your first stock holding using the form on the left!")
            else:
                view_table, view_chart = st.tabs(["📋 Positions Table", "🍩 Asset Allocation"])

                with view_table:
                    display_df = df_portfolio[['id', 'ticker', 'shares', 'buy_price', 'market_value']].copy()
                    display_df.columns = ['ID', 'Ticker', 'Shares', 'Avg Buy Price ($)', 'Market Value ($)']

                    st.dataframe(
                        display_df,
                        column_config={
                            "ID": None,
                            "Avg Buy Price ($)": st.column_config.NumberColumn(format="$%.2f"),
                            "Market Value ($)": st.column_config.NumberColumn(format="$%.2f"),
                            "Shares": st.column_config.NumberColumn(format="%.2f"),
                        },
                        hide_index=True,
                        width="stretch"
                    )

                    with st.expander("🗑️ Manage / Delete Holdings"):
                        del_col1, del_col2 = st.columns([3, 1], vertical_alignment="bottom")
                        with del_col1:
                            target_to_del = st.selectbox(
                                "Select holding to remove:",
                                options=portfolio_items,
                                format_func=lambda x: f"{x['ticker']} — {x['shares']} shares @ ${x['buy_price']:.2f}"
                            )
                        with del_col2:
                            if st.button("Delete", type="secondary", width="stretch"):
                                if target_to_del:
                                    del_res = requests.delete(
                                        f"{BACKEND_URL}/portfolio/{target_to_del['id']}",
                                        headers=get_auth_headers(),
                                    )
                                    if del_res.status_code in (200, 204):
                                        st.toast(f"Removed {target_to_del['ticker']}", icon="🗑️")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete holding.")

                with view_chart:
                    fig_donut = px.pie(
                        df_portfolio,
                        names='ticker',
                        values='market_value',
                        hole=0.5,
                        title="Portfolio Weight Distribution"
                    )
                    fig_donut.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig_donut, width="stretch")


def format_large_number(num):
    if num is None:
        return "N/A"
    if num >= 1e12:
        return f"${num / 1e12:,.2f}T"
    elif num >= 1e9:
        return f"${num / 1e9:,.2f}B"
    elif num >= 1e6:
        return f"${num / 1e6:,.2f}M"
    return f"${num:,.2f}"


# =====================================================================
# TAB 2: STOCK RESEARCH
# =====================================================================
with tab_stockresearch:
    st.header("Stock Research Terminal")
    st.caption("Real-time financial metrics and company overview powered by FastAPI & Yahoo Finance")

    col_search, col_btn = st.columns([4, 1], vertical_alignment="bottom")
    with col_search:
        ticker = st.text_input("Enter Stock Ticker:", help="e.g. AAPL, NVDA, MSFT").upper().strip()

    if ticker:
        try:
            with st.spinner(f"Fetching market data for {ticker}..."):
                response = requests.get(f"{BACKEND_URL}/stocks/{ticker}")

            if response.status_code == 200:
                data = response.json()

                curr_price = data.get('current_price', 0)
                prev_close = data.get('previous_close', 0)
                price_change = curr_price - prev_close if prev_close else 0
                pct_change = (price_change / prev_close * 100) if prev_close else 0

                st.subheader(f"{data.get('company_name', ticker)} ({ticker})")

                st.metric(
                    label="Current Price",
                    value=f"${curr_price:,.2f}",
                    delta=f"${price_change:+,.2f} ({pct_change:+.2f}%)"
                )

                st.divider()

                st.markdown("##### 📈 Historical Price Chart")

                selected_period = st.pills(
                    "Select Range:",
                    options=["1mo", "3mo", "6mo", "ytd", "1y", "5y", "max"],
                    default="ytd",
                    key="chart_period"
                )

                try:
                    stock_obj = yfinance.Ticker(ticker)
                    hist_df = stock_obj.history(period=selected_period)

                    if not hist_df.empty:
                        hist_df = hist_df.reset_index()

                        first_close = hist_df['Close'].iloc[0]
                        last_close = hist_df['Close'].iloc[-1]
                        line_color = "#00C805" if last_close >= first_close else "#FF5000"

                        fig = px.line(
                            hist_df,
                            x="Date",
                            y="Close",
                            title=f"{ticker} Price Movement ({selected_period.upper()})",
                            labels={"Date": "Date", "Close": "Price ($)"}
                        )

                        fig.update_traces(line_color=line_color, line_width=2)
                        fig.update_layout(
                            template="plotly_dark",
                            height=400,
                            margin=dict(l=20, r=20, t=40, b=20),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            hovermode="x unified",
                            xaxis_title=None,
                            yaxis_title="Stock Price ($)"
                        )

                        st.plotly_chart(fig, width="stretch")
                    else:
                        st.warning("No historical price data returned for this ticker.")

                except Exception as chart_err:
                    st.error(f"Could not load historical price chart: {chart_err}")

                st.divider()

                st.markdown("##### 📊 Key Fundamentals & Valuation")

                m1, m2, m3 = st.columns(3)
                m1.metric("Market Cap", format_large_number(data.get("market_cap")))
                m2.metric("Previous Close", f"${prev_close:,.2f}")
                m3.metric("52-Wk / YTD High", f"${data.get('year_to_date_high', 0):,.2f}")

                m4, m5, m6 = st.columns(3)
                m4.metric("52-Wk / YTD Low", f"${data.get('year_to_date_low', 0):,.2f}")

                trailing_pe = data.get("trailing_pe")
                m5.metric("Trailing P/E", f"{trailing_pe:,.2f}" if trailing_pe else "N/A")

                forward_pe = data.get("forward_pe")
                m6.metric("Forward P/E", f"{forward_pe:,.2f}" if forward_pe else "N/A")

                st.divider()

                with st.expander(f"📖 About {data.get('company_name', ticker)}", expanded=True):
                    st.write(data.get("summary", "No company profile available."))

            else:
                error_msg = response.json().get("detail", "Unknown server error")
                st.error(f"Backend Error ({response.status_code}): {error_msg}")

        except requests.exceptions.ConnectionError:
            st.error(f"Could not connect to FastAPI backend at {BACKEND_URL}.")


# =====================================================================
# TAB 3: AI RAG ASSISTANT
# =====================================================================
with tab_rag:
    st.header("Financial Document Assistant (RAG)")
    st.caption("Ask questions about company notes indexed in ChromaDB.")

    col_query, col_filter = st.columns([3, 1])
    with col_filter:
        ticker_filter = st.text_input("Filter Ticker (Optional)", placeholder="e.g., AAPL")
        top_k = st.slider("Context Chunks", min_value=1, max_value=8, value=4)

    with col_query:
        query_text = st.text_area("Your Question", placeholder="Can you describe what Apple does as a company?")

    if st.button("Ask Assistant 🤖", type="primary"):
        if not query_text.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Searching vector store and generating answer with Gemini..."):
                payload = {
                    "query": query_text,
                    "ticker": ticker_filter.strip().upper() if ticker_filter.strip() else None,
                    "top_k": top_k,
                }
                res = requests.post(
                    f"{BACKEND_URL}/rag/query",
                    json=payload,
                    headers=get_auth_headers(),
                )

                if res.status_code == 200:
                    rag_data = res.json()
                    st.subheader("Answer")
                    st.write(rag_data.get("answer", "No answer returned."))

                    # Robust Chunk Rendering
                    retrieved_chunks = rag_data.get("retrieved_context", [])
                    st.divider()
                    with st.expander("🔍 View Retrieved Document Chunks", expanded=False):
                        if not retrieved_chunks:
                            st.info("No reference document chunks were retrieved from ChromaDB for this query.")
                        else:
                            for idx, chunk in enumerate(retrieved_chunks, 1):
                                # Extract content across common schema variations
                                content = (
                                    chunk.get("content") 
                                    or chunk.get("text") 
                                    or chunk.get("document", "No chunk text available")
                                )
                                metadata = chunk.get("metadata", {})
                                source = metadata.get("source", "Unknown Source")
                                ticker_meta = metadata.get("ticker", "N/A")
                                chunk_idx = metadata.get("chunk_idx", "N/A")

                                st.markdown(
                                    f"**Chunk #{idx}** | 📄 Source: `{source}` | 📈 Ticker: `{ticker_meta}` | 🔢 Index: `{chunk_idx}`"
                                )
                                st.info(content)
                else:
                    st.error(f"Error querying RAG assistant: {res.text}")


# =====================================================================
# TAB 4: DOCUMENT INGESTION
# =====================================================================
with tab_documents:
    st.header("Vector Store Indexing")
    st.markdown(
        """
        Place your target financial documents (`.txt` or `.md`) into the `./docs` directory on the server.
        
        **Naming convention recommendation:**
        * `NVDA_10K.txt` (Starts with ticker + underscore for automatic metadata labeling)
        * `AAPL_Q3_2024.md`
        """
    )

    if st.button("Ingest Files from `./docs` Directory", type="primary"):
        with st.spinner("Indexing documents into ChromaDB..."):
            res = requests.post(
                f"{BACKEND_URL}/rag/ingest",
                headers=get_auth_headers(),
            )
            if res.status_code == 200:
                result = res.json()
                st.success(f"Ingestion complete! Successfully indexed **{result.get('chunks_ingested', 0)}** document chunks into ChromaDB.")
            else:
                st.error(f"Failed to ingest documents: {res.text}")