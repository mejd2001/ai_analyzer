# src/fb_ads_loader.py
import pandas as pd
import numpy as np
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights
from datetime import datetime, timedelta
import streamlit as st


def generate_demo_data(days=90):
    """Generates fake data so you can test the app without a Facebook account."""
    dates = pd.date_range(end=datetime.now(), periods=days)
    products = ['Summer Dress', 'Leather Jacket', 'Running Shoes', 'Smart Watch', 'Denim Jeans']
    categories = ['Clothing', 'Clothing', 'Footwear', 'Electronics', 'Clothing']

    data = []
    for date in dates:
        # Simulate 5-10 orders per day
        num_orders = np.random.randint(5, 15)
        for _ in range(num_orders):
            prod_idx = np.random.randint(0, len(products))
            qty = np.random.randint(1, 3)
            price = np.random.uniform(50, 200)

            row = {
                'Date': date,
                'Product': products[prod_idx],
                'Category': categories[prod_idx],
                'Quantity': qty,
                'Price': round(price, 2),
                'Revenue': round(price * qty, 2),
                'Customer_Gender': np.random.choice(['Male', 'Female'], p=[0.4, 0.6]),
                'Age_Group': np.random.choice(['18-24', '25-34', '35-44', '45+'], p=[0.2, 0.5, 0.2, 0.1])
            }
            data.append(row)

    return pd.DataFrame(data)


@st.cache_data(ttl=3600)
def load_fb_ads_data(access_token, ad_account_id, days_back=90):
    """
    Tries to load real Facebook data.
    If it fails (account suspended), it loads DEMO data automatically.
    """
    try:
        # 1. FIX: Ensure Ad Account ID has 'act_' prefix
        ad_account_id = str(ad_account_id).strip()
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        # 2. Try to Connect
        FacebookAdsApi.init(access_token=access_token)
        account = AdAccount(ad_account_id)

        fields = [
            AdsInsights.Field.date_start,
            AdsInsights.Field.ad_name,
            AdsInsights.Field.campaign_name,
            AdsInsights.Field.spend,
            AdsInsights.Field.inline_link_clicks,
        ]
        params = {
            'time_range': {'since': (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d'),
                           'until': datetime.now().strftime('%Y-%m-%d')},
            'level': 'ad',
            'limit': 1000
        }

        insights = account.get_insights(fields=fields, params=params)

        if not insights:
            raise ValueError("No data found")

        # Process Real Data
        data_list = [dict(x) for x in insights]
        df = pd.DataFrame(data_list)
        df['Date'] = pd.to_datetime(df['date_start'])
        df['Product'] = df['ad_name'].fillna('Unknown').astype(str)
        df['Category'] = df['campaign_name'].fillna('General').astype(str)
        df['Revenue'] = pd.to_numeric(df['spend'], errors='coerce').fillna(0)
        df['Quantity'] = pd.to_numeric(df['inline_link_clicks'], errors='coerce').fillna(0)
        df['Price'] = df['Revenue'] / df['Quantity'].replace(0, 1)
        df = df[['Date', 'Product', 'Category', 'Quantity', 'Price', 'Revenue']].copy()

        # Add dummy demographics for real data (since API doesn't give individual rows)
        df['Customer_Gender'] = 'Unknown'
        df['Age_Group'] = 'Unknown'

        return df

    except Exception as e:
        # 3. FALLBACK: If real connection fails, use DEMO data
        st.warning(f"⚠️ Could not connect to Facebook (Account Suspended?). Switching to **DEMO MODE**.")
        st.info("Using simulated data so you can test the dashboard features.")
        return generate_demo_data(days_back)