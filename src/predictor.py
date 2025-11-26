# src/predictor.py
import pandas as pd
import numpy as np
from prophet import Prophet
import streamlit as st
import matplotlib.pyplot as plt
import io  # <--- NEW IMPORT
import base64  # <--- NEW IMPORT


@st.cache_data(show_spinner=False)
def predict_top5_products_next30days(df):
    if df.empty or 'Date' not in df.columns or 'Product' not in df.columns:
        return pd.DataFrame(), None

    df['Date'] = pd.to_datetime(df['Date'])
    daily_sales = df.groupby(['Date', 'Product'])['Quantity'].sum().reset_index()
    forecasts = []

    # Limit to top 50 products for speed
    # NEW LINE (Faster & Stable):
    top_products = df.groupby('Product')['Quantity'].sum().nlargest(20).index

    for product in top_products:
        product_data = daily_sales[daily_sales['Product'] == product].copy()
        if len(product_data) < 7: continue

        prophet_df = product_data[['Date', 'Quantity']].rename(columns={'Date': 'ds', 'Quantity': 'y'})
        prophet_df = prophet_df.sort_values('ds')

        try:
            m = Prophet(daily_seasonality=False, yearly_seasonality=True)
            try:
                m.add_country_holidays(country_name='TN')
            except:
                pass
            m.fit(prophet_df)
            future = m.make_future_dataframe(periods=30)
            forecast = m.predict(future)
            predicted_units = forecast['yhat'][-30:].clip(lower=0).sum()

            # Demographics Logic
            demo = df[df['Product'] == product]
            total = len(demo)
            male_pct = 50
            if total > 0 and 'Customer_Gender' in demo.columns:
                male_count = demo['Customer_Gender'].astype(str).str.lower().isin(['male', 'm']).sum()
                male_pct = (male_count / total) * 100

            top_age = "Unknown"
            top_age_pct = 0
            if total > 0 and 'Age_Group' in demo.columns:
                age_counts = demo['Age_Group'].value_counts()
                if not age_counts.empty:
                    top_age = age_counts.index[0]
                    top_age_pct = (age_counts.iloc[0] / total * 100)

            forecasts.append({
                'Product': product,
                'Predicted_Units_Next30Days': int(predicted_units),
                'Male_%': round(male_pct, 1),
                'Female_%': round(100 - male_pct, 1),
                'Top_Age_Group': top_age,
                'Top_Age_%': round(top_age_pct, 1)
            })
        except Exception:
            continue

    if not forecasts:
        return pd.DataFrame(), None

    result_df = pd.DataFrame(forecasts).sort_values('Predicted_Units_Next30Days', ascending=False).head(5)

    # --- THE FIX STARTS HERE ---
    # Create figure but DO NOT use st.pyplot() yet
    fig, ax = plt.subplots(figsize=(10, 6))
    result_df.set_index('Product')['Predicted_Units_Next30Days'].plot(
        kind='barh', color='#00C28E', ax=ax, title='Top 5 Predicted Products (Next 30 Days)'
    )
    plt.tight_layout()

    # Save to memory buffer
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    buf.seek(0)

    # Convert to base64 string
    b64_string = base64.b64encode(buf.read()).decode()
    chart_path = f"data:image/png;base64,{b64_string}"

    plt.close(fig)  # Close to free memory
    # --- THE FIX ENDS HERE ---

    return result_df, chart_path


@st.cache_data
def recommend_prices(df, top5_df):
    if top5_df.empty: return pd.DataFrame()
    recommendations = []
    for product in top5_df['Product']:
        product_data = df[df['Product'] == product]
        if product_data.empty: continue
        current_avg = product_data['Price'].mean()
        recommended = current_avg * 1.15
        recommendations.append({
            'Product': product,
            'Current_Avg_Price': round(current_avg, 2),
            'Recommended_Price': round(recommended, 2),
        })
    return pd.DataFrame(recommendations)