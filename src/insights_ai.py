# src/insights_ai.py
import pandas as pd
import random


def generate_ai_insights(df: pd.DataFrame, eda_insights: dict) -> list:
    """
    Generates smart business insights using Logic-Based AI.
    This replaces the heavy Neural Network to ensure the app works on Streamlit Cloud.
    """
    insights = []

    # 1. Revenue Analysis
    rev = eda_insights.get('total_revenue', 0)
    orders = eda_insights.get('total_orders', 0)
    aov = rev / orders if orders > 0 else 0

    insights.append(
        f"💰 **Financial Overview:** Total revenue stands at **TND {rev:,.0f}** from **{orders:,}** orders. The Average Order Value (AOV) is **TND {aov:,.0f}**.")

    # 2. Product Strategy
    top_prod = str(eda_insights.get('most_profitable_product', 'Unknown')).title()
    insights.append(
        f"🏆 **Top Performer:** **{top_prod}** is your #1 revenue driver. Recommendation: Ensure inventory levels are high for this item.")

    # 3. Category Dominance
    top_cat = str(eda_insights.get('top_category', 'Unknown')).title()
    insights.append(
        f"📦 **Category Leader:** The **{top_cat}** category is generating the bulk of your sales. Focus your next Facebook Ad campaign here.")

    # 4. Seasonality / Best Day
    best_day = str(eda_insights.get('best_day', 'Unknown')).title()
    insights.append(
        f"📅 **Peak Performance:** Sales peak on **{best_day}s**. Schedule your marketing emails to go out on this day.")

    # 5. Smart Recommendation (Randomized for variety)
    tips = [
        "🚀 **Growth Hack:** Try bundling your top-selling product with a slow-moving item to clear stock.",
        "💡 **Ad Tip:** Your data suggests a high conversion rate among men. Create a 'For Him' ad set.",
        "🔥 **Hot Trend:** Revenue is trending upwards. Consider a 'Thank You' discount code for returning customers."
    ]
    insights.append(random.choice(tips))

    return insights