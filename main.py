import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import matplotlib.pyplot as plt
import os
import yaml
from yaml.loader import SafeLoader
from datetime import datetime
import bcrypt

# ── IMPORTS FROM YOUR SRC FOLDER ───────────────────────────────────
from src.data_loader import load_data
from src.fb_ads_loader import load_fb_ads_data
from src.eda import (
    perform_eda,
    plot_yoy_trend,
    plot_pareto_products,
    plot_category_sunburst,
    plot_price_vs_volume
)
from src.insights_ai import generate_ai_insights
from src.predictor import predict_top5_products_next30days, recommend_prices
from src.facebook_integraation import generate_ad_suggestions
from src.pack_generator import suggest_packs  # <--- NEW FEATURE IMPORT

# ── 1. PAGE CONFIGURATION (Must be first) ──────────────────────────
st.set_page_config(
    page_title="Tunisia Sales AI Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 2. SAAS AUTHENTICATION (Universal Fix) ─────────────────────────
users = [
    ('admin', 'Admin User', '123', 'admin@company.tn'),
    ('client', 'Tunisia Client', '456', 'client@shop.tn')
]

# Manual Hashing
hashed_passwords = []
for u in users:
    plain_password = u[2]
    pwd_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
    hashed_passwords.append(hashed)

# Config Dictionary
credentials = {'usernames': {}}
for (username, name, _, email), hash_pass in zip(users, hashed_passwords):
    credentials['usernames'][username] = {
        'name': name,
        'password': hash_pass,
        'email': email
    }

config = {
    'credentials': credentials,
    'cookie': {'expiry_days': 30, 'key': 'random_signature_key', 'name': 'sales_ai_cookie'},
}

# Initialize Authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- LOGIN WIDGET ---
authenticator.login('main')

if st.session_state["authentication_status"] is False:
    st.error('❌ Username/password is incorrect')
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning('🔐 Please enter your username and password')
    st.stop()

name = st.session_state["name"]

# ── 3. APP HEADER ──────────────────────────────────────────────────
st.sidebar.success(f"Welcome, {name}!")
try:
    authenticator.logout('Logout', 'sidebar')
except:
    pass

st.sidebar.markdown("---")
st.markdown("<h1 style='text-align: center; color:#00C28E;'>🚀 AI Sales Analyzer Pro</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>Intelligent Dashboard for Tunisian Businesses</h4>",
            unsafe_allow_html=True)

# ── 4. DATA SOURCE SELECTION ───────────────────────────────────────
st.sidebar.header("📂 Data Source")
data_source = st.sidebar.radio(
    "Choose Source:",
    options=["Upload Excel/CSV", "Connect Facebook Ads"],
    key="source"
)

df = None
eda_insights = {}
temp_path = "temp_uploaded_file"

# A) FILE UPLOAD
if data_source == "Upload Excel/CSV":
    uploaded_file = st.sidebar.file_uploader("Upload your messy file", type=['csv', 'xlsx', 'xls'])
    if uploaded_file:
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            with st.spinner("🧠 Universal Loader is cleaning your file..."):
                df = load_data(temp_path)
                eda_insights = perform_eda(df)
            st.sidebar.success("✅ File Loaded & Cleaned!")
        except Exception as e:
            st.error(f"Error loading file: {e}")

# B) FACEBOOK ADS (With Demo Mode)
else:
    st.sidebar.info("If your account is suspended, type ANY random text below to activate Demo Mode.")
    fb_token = st.sidebar.text_input("Access Token", type="password")
    fb_id = st.sidebar.text_input("Ad Account ID (act_...)")

    if st.sidebar.button("Connect to Facebook"):
        with st.spinner("Connecting..."):
            df = load_fb_ads_data(fb_token, fb_id, days_back=90)
            if not df.empty:
                eda_insights = perform_eda(df)
                st.success("Data Loaded Successfully!")

# ── 5. MAIN DASHBOARD ──────────────────────────────────────────────
if df is not None and not df.empty:

    # --- KPIs Row ---
    st.markdown("### 📊 Key Performance Indicators")
    k1, k2, k3, k4 = st.columns(4)

    total_rev = df['Revenue'].sum()
    k1.metric("Total Revenue", f"TND {total_rev:,.0f}")
    k2.metric("Total Orders", f"{len(df):,}")
    k3.metric("Top Product", eda_insights.get('most_profitable_product', 'N/A'))
    k4.metric("Top Category", eda_insights.get('top_category', 'N/A'))

    st.markdown("---")

    # --- ROW 1: Trends & Hierarchy ---
    c1, c2 = st.columns([2, 1])
    with c1:
        st.plotly_chart(plot_yoy_trend(df), use_container_width=True)
    with c2:
        st.plotly_chart(plot_category_sunburst(df), use_container_width=True)

    # --- ROW 2: Strategy & Pareto ---
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(plot_pareto_products(df), use_container_width=True)
    with c4:
        st.plotly_chart(plot_price_vs_volume(df), use_container_width=True)

    # --- ROW 3: AI Insights ---
    st.markdown("---")
    st.subheader("🤖 AI Business Analyst Insights")

    with st.expander("Click to generate AI Analysis", expanded=False):
        with st.spinner("AI is analyzing your data..."):
            ai_text = generate_ai_insights(df, eda_insights)
            for insight in ai_text:
                st.write(f"• {insight}")

    # --- ROW 4: Future Predictions (WITH 2:1 LAYOUT) ---
    st.markdown("---")
    st.subheader("🔮 Sales Forecast (Next 30 Days)")

    with st.spinner("Predicting future trends..."):
        top5_df, chart_path = predict_top5_products_next30days(df)

    if top5_df is not None and not top5_df.empty:
        # HERE IS THE CHANGE: [2, 1] gives table double space
        col_pred_table, col_pred_chart = st.columns([2, 1])

        with col_pred_table:
            st.markdown("#### Top 5 Products to Stock Up")
            st.dataframe(
                top5_df[['Product', 'Predicted_Units_Next30Days', 'Male_%', 'Female_%', 'Top_Age_Group']]
                .style.background_gradient(cmap="Greens", subset=['Predicted_Units_Next30Days']),
                use_container_width=True
            )

            st.markdown("#### 🏷️ Recommended Price Adjustments")
            price_recs = recommend_prices(df, top5_df)
            st.dataframe(price_recs, use_container_width=True)

        with col_pred_chart:
            if chart_path:
                st.image(chart_path, use_column_width=True)

        # --- ROW 5: PACK SUGGESTIONS (New Feature) ---
        st.markdown("---")
        st.subheader("📦 Smart Pack Suggestions (Bought Together)")

        with st.spinner("Analyzing purchase patterns..."):
            packs_df = suggest_packs(df)

        if not packs_df.empty:
            col_pack_text, col_pack_metric = st.columns([2, 1])
            with col_pack_text:
                st.info("💡 Strategy: Create these bundles to increase Average Order Value.")
                display_packs = packs_df[
                    ['Pack Name', 'Times Bought Together', 'Total Value', 'Suggested Pack Price (10% Off)', 'Savings']]
                st.dataframe(display_packs.style.background_gradient(cmap="Blues", subset=['Times Bought Together']),
                             use_container_width=True)
            with col_pack_metric:
                best_pack = packs_df.iloc[0]
                st.metric(label="🔥 Top Opportunity", value=best_pack['Pack Name'],
                          delta=f"Sold {best_pack['Times Bought Together']} times")
                st.write(f"**Offer it at:** TND {best_pack['Suggested Pack Price (10% Off)']}")
        else:
            st.info("Not enough data to find products bought together (Need Order IDs or multiple items per customer).")

        # --- ROW 6: Actionable Ads ---
        st.markdown("---")
        st.subheader("📢 Facebook Ad Targeting Generator")
        st.info("Copy this JSON code directly into Facebook Ads Manager")

        ad_df = generate_ad_suggestions(top5_df, "dummy_token", "dummy_id")

        if not ad_df.empty:
            st.json(ad_df.to_dict(orient='records'))
    else:
        st.warning("Not enough history to generate predictions (need at least 7 days of data).")

    # Clean up
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except:
            pass

else:
    st.info("👈 Please upload a file or connect Facebook Ads to begin.")
    st.markdown("""
    ### Features:
    - **Universal Loader:** Works with English, French, CSV, Excel.
    - **Smart Charts:** Pareto, Sunburst, YoY Trends.
    - **AI Predictions:** Forecast next 30 days of sales.
    - **Smart Packs:** Suggests bundles based on purchase history.
    - **Ad Targeting:** Auto-generate audiences.
    """)