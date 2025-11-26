# src/insights_ai.py  — Generate short AI-polished insights (safe, factual)
import pandas as pd

# Try to import Streamlit caching, otherwise fallback to lru_cache
try:
    import streamlit as st
    def cache_resource(func):
        return st.cache_resource(func)
except Exception:
    from functools import lru_cache
    def cache_resource(func):
        return lru_cache(maxsize=1)(func)

from transformers import pipeline


@cache_resource
def load_generator():
    # NOTE: this will download a model if not present.
    # You can change model to a lighter one if needed.
    return pipeline("text2text-generation", model="google/flan-t5-large", max_length=150)


# Lazily load generator when needed
def generate_ai_insights(df: pd.DataFrame, eda_insights: dict) -> list:
    generator = load_generator()
    total_revenue = f"${eda_insights['total_revenue']:,}"
    total_orders = f"{eda_insights['total_orders']:,}"
    top_product_ever = eda_insights.get('most_profitable_product', 'Unknown Product').title()
    top_category = eda_insights.get('top_category', 'Uncategorized')
    best_day = eda_insights.get('best_day', 'Unknown')

    latest = df['Date'].max()
    start_3m = latest - pd.Timedelta(days=90)
    recent = df[df['Date'] >= start_3m]
    if not recent.empty:
        top_3m_series = recent.groupby('Product')['Revenue'].sum()
        top_3m_product = top_3m_series.idxmax().title() if not top_3m_series.empty else "Unknown Product"
        top_3m_revenue = f"${int(top_3m_series.max()):,}" if not top_3m_series.empty else "$0"
    else:
        top_3m_product = "No recent data"
        top_3m_revenue = "$0"
    period_3m = f"{start_3m.strftime('%B %Y')} – {latest.strftime('%B %Y')}"

    prompts = [
        f"Rewrite professionally: Total revenue is {total_revenue} from {total_orders} orders.",
        f"Rewrite as a strong bullet: The all-time most profitable product is {top_product_ever}.",
        f"Rewrite professionally: {top_category} is the dominant category and generates the majority of revenue.",
        f"Rewrite as recommendation: {best_day} is the highest-performing day of the week for sales.",
        f"Hot trend alert: In the last 3 months ({period_3m}), the best-selling product has been {top_3m_product} with {top_3m_revenue} in revenue.",
        f"Based on {top_3m_product} being the current top seller, suggest one realistic 30-day marketing promotion.",
        f"Write one short, confident closing sentence for a sales performance report."
    ]

    print("Generating accurate AI insights...")
    insights = []
    for prompt in prompts:
        result = generator(prompt, max_length=110, do_sample=False)[0]['generated_text'].strip()
        if result and not result[0].isupper():
            result = result[0].upper() + result[1:]
        if not result.endswith(('.', '!', '?')):
            result += '.'
        insights.append(f"• {result}")

    return insights
