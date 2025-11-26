# src/pack_generator.py
import pandas as pd
from itertools import combinations
from collections import Counter
import streamlit as st


def get_basket_id(df):
    """
    Smartly determines what defines a single 'Order' or 'Basket'.
    """
    # 1. Best Case: We have an explicit Order ID
    order_keywords = ['order_id', 'transaction_id', 'invoice_no', 'basket_id']
    for col in df.columns:
        if any(k in col.lower() for k in order_keywords):
            return [col]

    # 2. Proxy Case: Same Date + Same Customer (Proxy for an order)
    # We combine available columns to create a unique transaction signature
    proxy_cols = ['Date']
    possible_proxies = ['Customer_ID', 'Customer_Name', 'Email', 'Phone', 'Country', 'Region', 'State', 'City',
                        'Customer_Gender', 'Age_Group']

    for p in possible_proxies:
        # Find the column in df that matches our proxy list (case insensitive)
        match = next((c for c in df.columns if p.lower() in c.lower()), None)
        if match:
            proxy_cols.append(match)

    return proxy_cols


@st.cache_data(show_spinner=False)
def suggest_packs(df, min_transactions=5):
    """
    Analyzes products bought together and suggests packs.
    """
    df = df.copy()

    # 1. Define the Basket
    basket_cols = get_basket_id(df)

    # 2. Group products by Basket
    # We only care about baskets with > 1 item
    baskets = df.groupby(basket_cols)['Product'].apply(lambda x: sorted(list(set(x))))
    baskets = baskets[baskets.apply(len) > 1]

    if baskets.empty:
        return pd.DataFrame()

    # 3. Count Pairs
    pair_counts = Counter()
    for items in baskets:
        # Generate all pairs of 2 products
        pair_counts.update(combinations(items, 2))

    # 4. Convert to DataFrame
    suggestions = []

    for (prod_a, prod_b), count in pair_counts.most_common(10):
        if count < min_transactions:
            continue

        # Get individual prices to calculate pack price
        price_a = df[df['Product'] == prod_a]['Price'].mean()
        price_b = df[df['Product'] == prod_b]['Price'].mean()

        # Logic: 10% Discount for the pack
        total_price = price_a + price_b
        pack_price = total_price * 0.90

        suggestions.append({
            'Pack Name': f"{prod_a} + {prod_b} Bundle",
            'Item A': prod_a,
            'Item B': prod_b,
            'Times Bought Together': count,
            'Total Value': round(total_price, 2),
            'Suggested Pack Price (10% Off)': round(pack_price, 2),
            'Savings': round(total_price - pack_price, 2)
        })

    return pd.DataFrame(suggestions)