from groq import Groq
import streamlit as st
import os
from datetime import datetime
import pandas as pd
import plotly.express as px

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)
model = "LLaMA 3.3-70B",
max_tokens = 1000,
temperature = 0.7,
#st.file_uploader() with type="csv","xlsx":
 #pd.read_csv() or pd.read_excel() depending on file type:
df = pd.read_csv("subscription_data.csv")
st.markdown("---")
st.subheader(" Add Expense Manually")

col1, col2 = st.columns(2)

with col1:
    manual_date = st.date_input("Date")
    manual_desc = st.text_input("Expense Description")

with col2:
    manual_amount = st.number_input(
        "Amount", min_value=0 
    )

    renewal_date = st.date_input(
        "Renewal Date"
    )

if "manual_expenses" not in st.session_state:
        st.session_state.manual_expenses = []

if st.button("Add Expense"):
        
    new_expense = {
            "Date": str(manual_date),
            "Description": manual_desc,
            "Amount": manual_amount,
            "Renewal Date": str(renewal_date)
    } 

    st.session_state.manual_expenses.append(
        new_expense
    )
    st.success("Expense added successfully!")

subscriptions = []

grouped = df.groupby("Description")

for name, group in grouped:
    if len(group) >= 2:

        amount_std = group["Amount"].std()
        avg_amount = group["Amount"].mean()

        is_same_amount = (
            amount_std < (avg_amount * 0.1)
        )
        
        known = [
            "netflix",
            "spotify",
            "amazon prime",
            "adobe", 
            "google one", 
            "claude", 
            "youtube", 
            "hotstar", 
            "Microsoft 365", 
            "Apple TV", 
            "canva", 
            "chatgpt", 
            "snapchat", 
            "prime video", 
            "zee5", 
            "MidJourney", 
            "duolingo", 
            "xbox game pass", 
            "playstation plus", 
            "perplexity", 
            "reddit", 
            "hulu", 
            "disney plus", 
            "apple music"
        ]

        is_known = any(
            word in name.lower() 
            for word in known
        )
        
        if is_same_amount or is_known:
            subscriptions.append(name)

# METRICS
# =========================================================

total_spending = int(
    df["Amount"].sum()
)

possible_savings = 0

for sub in subscriptions:

    sub_rows = df[
        df["Description"].str.contains(
            sub,
            case=False
        )
    ]

    possible_savings += int(
        sub_rows["Amount"].mean()
    )

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

    sub_rows = df[
        df["Description"].str.contains(
            sub,
            case=False
        )
    ]

    avg_cost = int(
        sub_rows["Amount"].mean()
    )

    chart_data.append({
        "Subscription": sub,
        "Monthly Cost": avg_cost
    })

chart_df = pd.DataFrame(chart_data)

left,right = st.columns(2) 
with st.expander(
    "🧠 AI Cost-Saving Suggestions"
):

    if st.button(
        "Get AI Suggestions",
        key="ai_button"
    ):

        try:

            summary_text = ""
        except Exception as e:    

            for sub in subscriptions:

                sub_rows = df[
                    df["Description"].str.contains(
                        sub,
                        case=False
                    )
                ]

                avg_cost = int(
                    sub_rows["Amount"].mean()
                )

                summary_text += (
                    f"{sub}: ₹{avg_cost}/month\n"
                )

            prompt = f"""
            Analyze these subscriptions and give smart"""
# ==============================================================================
# RAW DATA
# ==============================================================================

with st.expander(
    "📄 View Raw Expense Data"
):

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

# ==============================================================================
# MONTHLY COST TABLE
# ==============================================================================

with st.expander(
    " 💳 Monthly Subscription Cost"
):

    st.dataframe(
        chart_df,
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")
    #==========================================================================
    # DOWNLOAD REPORT
    #==============================================================================

report = f"""
SUBSCRIPTION WASTE DETECTOR REPORT

Total Spending: ₹ {total_spending}

Detected Subscriptions:
{", ".join(subscriptions)}

Monthly Subscription Costs:
"""

report += chart_df.to_string(index=False)

st.download_button(
    label="📥 Download Report",
    data=report,
    file_name="subscription_report.txt"
)
