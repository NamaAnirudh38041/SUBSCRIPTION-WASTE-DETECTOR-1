import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq

st.set_page_config(page_title="Subscription Waste Detector", layout="wide")

# ==============================================================================
# STYLES
# ==============================================================================
st.markdown("""
<style>
.metric-card {
    background-color: #1e1e2f;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
}
.metric-card h4 { margin: 0; color: #aaaaaa; font-size: 14px; }
.metric-card h1 { margin: 5px 0 0 0; color: #ffffff; font-size: 28px; }
</style>
""", unsafe_allow_html=True)

st.title("💸 Subscription Waste Detector")

# ==============================================================================
# API KEY (never hardcode secrets in source — pull from st.secrets or ask user)
# ==============================================================================
groq_api_key = st.secrets.get("GROQ_API_KEY") if hasattr(st, "secrets") else None
with st.sidebar:
    st.subheader("Settings")
    if not groq_api_key:
        groq_api_key = st.text_input("Groq API Key", type="password")
    st.caption("Used only for the optional AI suggestions feature.")

# ==============================================================================
# DATA INPUT: FILE UPLOAD
# ==============================================================================
uploaded_file = st.file_uploader("Upload CSV File", type="csv")

uploaded_df = pd.DataFrame(columns=["Date", "Description", "Amount"])
if uploaded_file is not None:
    raw = pd.read_csv(uploaded_file)
    # normalize expected columns if present
    cols = {c.lower().strip(): c for c in raw.columns}
    rename_map = {}
    for target in ["date", "description", "amount"]:
        if target in cols:
            rename_map[cols[target]] = target.capitalize()
    raw = raw.rename(columns=rename_map)
    missing = [c for c in ["Date", "Description", "Amount"] if c not in raw.columns]
    if missing:
        st.error(f"Uploaded CSV is missing required column(s): {', '.join(missing)}")
    else:
        uploaded_df = raw[["Date", "Description", "Amount"]].copy()

st.markdown("---")

# ==============================================================================
# DATA INPUT: MANUAL ENTRY
# ==============================================================================
st.subheader("➕ Add Expense Manually")

if "manual_expenses" not in st.session_state:
    st.session_state.manual_expenses = []

col1, col2 = st.columns(2)
with col1:
    manual_date = st.date_input("Date")
    manual_desc = st.text_input("Expense Description")
with col2:
    manual_amount = st.number_input("Amount", min_value=0)
    renewal_date = st.date_input("Renewal Date")

if st.button("Add Expense"):
    if manual_desc.strip() == "":
        st.warning("Please enter a description before adding an expense.")
    else:
        st.session_state.manual_expenses.append({
            "Date": str(manual_date),
            "Description": manual_desc,
            "Amount": manual_amount,
            "Renewal Date": str(renewal_date),
        })
        st.success("Expense added successfully!")

manual_df = pd.DataFrame(st.session_state.manual_expenses)
if not manual_df.empty:
    manual_df = manual_df[["Date", "Description", "Amount"]]

# ==============================================================================
# COMBINE DATA
# ==============================================================================
df = pd.concat([uploaded_df, manual_df], ignore_index=True)

if df.empty:
    st.info("Upload a CSV or add an expense manually to see your dashboard.")
    st.stop()

df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

# ==============================================================================
# SUBSCRIPTION DETECTION
# ==============================================================================
KNOWN_SUBSCRIPTIONS = [
    "netflix", "spotify", "amazon prime", "adobe", "google one", "claude",
    "youtube", "hotstar", "microsoft 365", "apple tv", "canva", "chatgpt",
    "snapchat", "prime video", "zee5", "midjourney", "duolingo",
    "xbox game pass", "playstation plus", "perplexity", "reddit", "hulu",
    "disney plus", "apple music",
]

subscriptions = []
grouped = df.groupby("Description")
for name, group in grouped:
    if len(group) >= 2:
        amount_std = group["Amount"].std()
        avg_amount = group["Amount"].mean()
        is_same_amount = amount_std < (0.1 * avg_amount) if avg_amount else False
        is_known = any(word in str(name).lower() for word in KNOWN_SUBSCRIPTIONS)
        if is_same_amount and is_known:
            subscriptions.append(name)

# ==============================================================================
# METRICS
# ==============================================================================
total_spending = int(df["Amount"].sum())

possible_savings = 0
for sub in subscriptions:
    sub_rows = df[df["Description"].str.contains(sub, case=False, na=False)]
    possible_savings += int(sub_rows["Amount"].mean())

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h4>💰 Total Spending</h4>
        <h1>₹ {total_spending}</h1>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h4>📌 Active Subscriptions</h4>
        <h1>{len(subscriptions)}</h1>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <h4>💵 Possible Savings</h4>
        <h1>₹ {possible_savings}</h1>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# CHART DATA
# ==============================================================================
chart_data = []
for sub in subscriptions:
    sub_rows = df[df["Description"].str.contains(sub, case=False, na=False)]
    avg_cost = int(sub_rows["Amount"].mean())
    chart_data.append({"Subscription": sub, "Monthly Cost": avg_cost})

chart_df = pd.DataFrame(chart_data)

if not chart_df.empty:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            px.bar(
                chart_df,
                x="Subscription",
                y="Monthly Cost",
                title="Monthly Subscription Costs",
                labels={"Monthly Cost": "Cost (₹)"},
                color="Subscription",
            ),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            px.pie(
                chart_df,
                names="Subscription",
                values="Monthly Cost",
                title="Spending Share by Subscription",
            ),
            use_container_width=True,
        )
else:
    st.info("No recurring subscriptions detected yet in the current data.")

# ==============================================================================
# AI COST-SAVING SUGGESTIONS
# ==============================================================================
with st.expander("🧠 AI Cost-Saving Suggestions"):
    if st.button("Get AI Suggestions", key="ai_button"):
        if not subscriptions:
            st.warning("No subscriptions detected to analyze yet.")
        elif not groq_api_key:
            st.warning("Enter a Groq API key in the sidebar to use this feature.")
        else:
            try:
                summary_text = ""
                for sub in subscriptions:
                    sub_rows = df[df["Description"].str.contains(sub, case=False, na=False)]
                    avg_cost = int(sub_rows["Amount"].mean())
                    summary_text += f"{sub}: ₹{avg_cost}/month\n"

                prompt = f"""Analyze these subscriptions and give smart, specific,
money-saving suggestions (e.g. duplicates, downgrades, bundling, cancellations).
Keep it concise and practical.

Subscriptions:
{summary_text}
"""
                client = Groq(api_key=groq_api_key)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                )
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Could not get AI suggestions: {e}")

# ==============================================================================
# RAW DATA
# ==============================================================================
with st.expander("📄 View Raw Expense Data"):
    st.dataframe(df, use_container_width=True, hide_index=True)

# ==============================================================================
# MONTHLY COST TABLE
# ==============================================================================
with st.expander("💳 Monthly Subscription Cost"):
    st.dataframe(chart_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ==============================================================================
# DOWNLOAD REPORT
# ==============================================================================
report = f"""SUBSCRIPTION WASTE DETECTOR REPORT

Total Spending: ₹ {total_spending}

Detected Subscriptions:
{", ".join(subscriptions) if subscriptions else "None detected"}

Monthly Subscription Costs:
{chart_df.to_string(index=False) if not chart_df.empty else "N/A"}
"""

st.download_button(
    label="📥 Download Report",
    data=report,
    file_name="subscription_report.txt",
)