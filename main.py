import streamlit as st
import pandas as pd
import datetime
import os

# Page styling and wide layout
st.set_page_config(page_title="Family Wealth Dashboard", page_icon="📊", layout="wide")

# Theme tweak to make it look clean and modern
st.markdown("""
    <style>
    .metric-card { background-color: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; }
    div[data-testid="stMetric"] { background-color: #111827; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Modern Family Wealth & Expense Hub")
st.markdown("Track, budget, and optimize your joint monthly spending starting July 2026.")

DATA_FILE = "expenses.csv"

# Load or initialize data
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df["Date"] = pd.to_datetime(df["Date"])
else:
    df = pd.DataFrame(columns=["Date", "User", "Category", "Amount", "Description"])

# Sidebar Settings
st.sidebar.header("⚙️ Configuration")
MONTHLY_BUDGET = st.sidebar.number_input("Set Monthly Budget (₹)", min_value=1000.0, value=50000.0, step=1000.0)

# Sidebar Form for entry
st.sidebar.markdown("---")
st.sidebar.header("➕ Add New Expense")
with st.sidebar.form("expense_form", clear_on_submit=True):
    # Enforce date selection from July 1, 2026 onwards
    min_date = datetime.date(2026, 7, 1)
    default_date = max(datetime.date.today(), min_date)

    date = st.date_input("Date", default_date, min_value=min_date)
    user = st.selectbox("Who paid?", ["Husband", "Wife"])
    category = st.selectbox("Category",
                            ["Groceries & Maid", "Rent/Maintenance", "Electricity & Water", "Zomato/Dining Out",
                             "OTT & Entertainment", "Fuel & Transport", "Shopping & Clothes", "Other"])
    amount = st.number_input("Amount (₹)", min_value=0.0, step=50.0, format="%.2f")
    description = st.text_input("Description/Notes")

    submitted = st.form_submit_button("Log Expense")

    if submitted and amount > 0:
        new_row = pd.DataFrame([[pd.to_datetime(date), user, category, amount, description]], columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.sidebar.success("Saved successfully!")
        st.rerun()

# Process data timelines
if not df.empty:
    df["Month_Year"] = df["Date"].dt.to_period("M")
    # Identify what the absolute latest logged month is, or default to July 2026
    current_target = pd.Period("2026-07", freq="M")
    latest_logged = df["Month_Year"].max()
    active_month = max(current_target, latest_logged)
else:
    active_month = pd.Period("2026-07", freq="M")

# -----------------------------------------------------------------
# CREATING THE TWO TABS
# -----------------------------------------------------------------
tab1, tab2 = st.tabs(["🎯 Current Month Status", "⏪ Previous Month Track"])


# Helper function to generate dashboard layout cleanly for any given month
def render_dashboard(filtered_df, budget_amount, is_current_month=True):
    if filtered_df.empty or filtered_df["Amount"].sum() == 0:
        # Zero-state defaults when no expenses are logged yet (e.g., July 1st)
        st.info(
            "ℹ️ No expenses logged yet for this billing cycle. Dynamic analytics will unlock with your first entry!")

        # Display crisp 0 metrics
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Total Spent", "₹ 0.00")
        m_col2.metric("Remaining Budget", f"₹ {budget_amount:,.2f}")
        m_col3.metric("Husband Spent", "₹ 0.00")
        m_col4.metric("Wife Spent", "₹ 0.00")
        return

    filtered_df["Amount"] = filtered_df["Amount"].astype(float)
    total_spent = filtered_df["Amount"].sum()
    remaining_budget = budget_amount - total_spent
    burn_rate = (total_spent / budget_amount)

    # 🚦 Budget Warning Pacing Bar
    st.markdown("#### Budget Pacing Profile")
    if burn_rate < 0.60:
        st.success(f"🟢 **Going Great!** You have used only {burn_rate:.1%} of your budget target.")
    elif burn_rate <= 0.90:
        st.warning(f"🟡 **Warning:** You have consumed {burn_rate:.1%} of your budget allocation.")
    else:
        st.error(f"🔴 **Critical:** Budget threshold breached! You spent {burn_rate:.1%} of your allowance.")

    st.progress(min(burn_rate, 1.0))

    # KPI Metric Grid Boxes
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Total Spent", f"₹ {total_spent:,.2f}")
    m_col2.metric("Remaining Budget", f"₹ {remaining_budget:,.2f}", delta=f"₹ {remaining_budget:,.2f}",
                  delta_color="normal" if remaining_budget > 0 else "inverse")
    m_col3.metric("Husband Spent", f"₹ {filtered_df[filtered_df['User'] == 'Husband']['Amount'].sum():,.2f}")
    m_col4.metric("Wife Spent", f"₹ {filtered_df[filtered_df['User'] == 'Wife']['Amount'].sum():,.2f}")

    st.markdown("---")

    # 📈 Charts Panel
    st.markdown("#### Visual Breakdown Analytics")
    c_col1, c_col2 = st.columns(2)

    with c_col1:
        st.markdown("**Daily Cash Outflow Trend**")
        daily_trend = filtered_df.groupby(filtered_df["Date"].dt.date)["Amount"].sum().reset_index()
        daily_trend = daily_trend.set_index("Date")
        st.line_chart(daily_trend, y="Amount", color="#3b82f6")

    with c_col2:
        st.markdown("**Category Allocation Map**")
        cat_data = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        st.bar_chart(cat_data.set_index("Category"), y="Amount", color="#10b981")

    st.markdown("---")

    # 📜 Detailed Ledger List
    st.markdown("#### Itemized Ledger")
    user_filter = st.radio(f"Filter ledger view ({filtered_df['Date'].dt.strftime('%B %Y').iloc[0]}):",
                           ["All Users", "Husband", "Wife"], horizontal=True,
                           key=f"filter_{budget_amount}_{total_spent}")

    display_df = filtered_df.sort_values(by="Date", ascending=False)
    if user_filter == "Husband":
        display_df = display_df[display_df["User"] == "Husband"]
    elif user_filter == "Wife":
        display_df = display_df[display_df["User"] == "Wife"]

    st.dataframe(
        display_df[["Date", "User", "Category", "Amount", "Description"]],
        use_container_width=True,
        column_config={
            "Amount": st.column_config.NumberColumn(format="₹ %.2f"),
            "Date": st.column_config.DateColumn(format="YYYY-MM-DD")
        }
    )


# -----------------------------------------------------------------
# TAB 1 RUNNER: LIVE CURRENT MONTH
# -----------------------------------------------------------------
with tab1:
    st.subheader(f"📅 Status Cycle: {active_month.strftime('%B %Y')}")
    if not df.empty:
        current_df = df[df["Month_Year"] == active_month].copy()
    else:
        current_df = pd.DataFrame()
    render_dashboard(current_df, MONTHLY_BUDGET, is_current_month=True)

# -----------------------------------------------------------------
# TAB 2 RUNNER: HISTORICAL REVIEWS
# -----------------------------------------------------------------
with tab2:
    st.subheader("⏪ Archive Review Vault")
    if not df.empty:
        # Get historical months excluding the current active live tracking month
        all_months = sorted(df["Month_Year"].unique())
        history_months = [m for m in all_months if m != active_month]

        if history_months:
            selected_history_month = st.selectbox("Select Historical Month to Audit:", history_months,
                                                  index=len(history_months) - 1)
            history_df = df[df["Month_Year"] == selected_history_month].copy()
            render_dashboard(history_df, MONTHLY_BUDGET, is_current_month=False)
        else:
            st.info(
                "No older completed historical cycles found yet. Once you progress past July 2026, archive tabs will list details here automatically.")
    else:
        st.info("No data recorded in the system yet.")
