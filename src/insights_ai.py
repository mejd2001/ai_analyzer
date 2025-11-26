# src/insights_ai.py
import pandas as pd
import torch  # <--- CRITICAL FIX: Explicitly import torch
from transformers import pipeline

# Try to import Streamlit caching, otherwise fallback to lru_cache
try:
    import streamlit as st


    def cache_resource(func):
        return st.cache_resource(func)
except Exception:
    from functools import lru_cache


    def cache_resource(func):
        return lru_cache(maxsize=1)(func)


@cache_resource
def load_generator():
    # CRITICAL FIX: Changed from 'large' to 'small' to prevent crashing Streamlit Cloud
    # 'google/flan-t5-small' is faster and uses less memory (Safe for free tier)
    return pipeline("text2text-generation", model="google/flan-t5-small", max_length=150)


def generate_ai_insights(df: pd.DataFrame, eda_insights: dict) -> list:
    try:
        generator = load_generator()
    except Exception as e:
        return [f"AI Error: {str(e)}"]

    # Safely format numbers
    total_revenue = f"${eda_insights.get('total_revenue', 0):,.0f}"
    total_orders = f"{eda_insights.get('total_orders', 0):,}"
    top_product = str(eda_insights.get('most_profitable_product', 'Unknown Product')).title()
    top_cat = str(eda_insights.get('top_category', 'Uncategorized')).title()
    best_day = str(eda_insights.get('best_day', 'Unknown')).title()

    # Prepare prompts
    prompts = [
        f"Rewrite professionally: Total revenue is {total_revenue} from {total_orders} orders.",
        f"Rewrite as a strong bullet point: The most profitable product is {top_product}.",
        f"Rewrite professionally: {top_cat} is the best selling category.",
        f"Rewrite as recommendation: {best_day} is the best day for sales.",
        "Write a short, motivating closing sentence for a sales report."
    ]

    print("Generating AI insights...")
    insights = []

    for prompt in prompts:
        try:
            # Generate text
            result = generator(prompt, max_length=100, do_sample=False)[0]['generated_text'].strip()
            # Capitalize first letter
            if result:
                result = result[0].upper() + result[1:]
            insights.append(f"• {result}")
        except:
            continue

    if not insights:
        return ["AI could not generate insights. (Check memory usage)"]

    return insights