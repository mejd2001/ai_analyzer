import pandas as pd
import numpy as np
import re
import io


def normalize(text):
    return str(text).lower().strip().replace(' ', '_').replace('.', '_').replace('/', '_')


def clean_currency(x):
    if isinstance(x, (int, float)):
        return x
    if pd.isna(x) or x == '':
        return 0.0
    s = str(x).lower().strip()
    s = re.sub(r'[a-z$€£dt]+', '', s)
    s = s.replace(',', '').replace(' ', '')
    try:
        return float(s)
    except:
        return 0.0


def find_header_row(df, keywords, max_scan=20):
    best_idx = 0
    max_matches = 0
    all_keywords = [k for sublist in keywords.values() for k in sublist]

    for i in range(min(len(df), max_scan)):
        row_values = [normalize(x) for x in df.iloc[i].astype(str)]
        matches = 0
        for val in row_values:
            if any(k in val for k in all_keywords):
                matches += 1
        if matches > max_matches:
            max_matches = matches
            best_idx = i
    return best_idx


def map_columns_smart(columns, keywords):
    col_map = {}
    used_columns = set()
    matches = []

    # BLACKLIST: If a column contains these words, it CANNOT be a 'product' name
    # This fixes the crash where "product_price" was being picked as "Product"
    product_blacklist = ['price', 'cost', 'revenue', 'total', 'amount', 'qty', 'quantity', 'date', 'id', 'category']

    for field, field_keywords in keywords.items():
        for col in columns:
            norm_col = normalize(col)
            col_words = set(norm_col.split('_'))

            # BLOCKER CHECK
            if field == 'product':
                if any(bad in norm_col for bad in product_blacklist):
                    continue  # Skip this column, it's a trap!

            score = 0
            for k in field_keywords:
                if k == norm_col:
                    score = 100
                elif k in col_words:
                    score = 80
                elif k in norm_col and len(k) > 3:
                    score = 50

            if score > 0:
                matches.append((score, field, col))

    matches.sort(key=lambda x: x[0], reverse=True)

    for score, field, col in matches:
        if field not in col_map and col not in used_columns:
            col_map[field] = col
            used_columns.add(col)

    return col_map


def load_data(path):
    print(f"Loading file: {path}")

    keywords = {
        'date': ['date', 'time', 'jour', 'heure', 'created_at', 'timestamp', 'order_date'],
        'product': ['product', 'item', 'produit', 'article', 'name', 'designation', 'sku', 'model'],
        'category': ['category', 'cat', 'type', 'famille', 'rayon', 'group', 'product_category'],
        'quantity': ['qty', 'quantity', 'qte', 'qté', 'quantité', 'units', 'count', 'nombre', 'volume',
                     'order_quantity'],
        'revenue': ['rev', 'revenue', 'sales', 'total', 'amount', 'montant', 'prix_total', 'ttc', 'turnover', 'ca'],
        'price': ['price', 'prix', 'unit_price', 'selling_price', 'tarif', 'pu', 'unitaire', 'cost', 'unit_cost',
                  'product_price'],
        'gender': ['gender', 'sex', 'genre', 'sexe', 'civilite', 'customer_gender'],
        'age': ['age', 'birth', 'naissance', 'customer_age', 'age_group'],
        'status': ['status', 'etat', 'statut', 'delivery', 'shipment', 'order_status']
    }

    # Reading Logic
    df_raw = None
    try:
        df_raw = pd.read_excel(path, header=None, engine='openpyxl')
    except Exception:
        try:
            df_raw = pd.read_csv(path, header=None, encoding='utf-8', low_memory=False)
        except:
            try:
                df_raw = pd.read_csv(path, header=None, encoding='latin1', low_memory=False)
            except Exception as e:
                raise ValueError(f"Could not read file. Error: {e}")

    # Header Detection
    header_idx = find_header_row(df_raw, keywords)
    df = df_raw.iloc[header_idx + 1:].copy()
    df.columns = df_raw.iloc[header_idx].astype(str)
    df = df.reset_index(drop=True)

    # Column Mapping
    col_map = map_columns_smart(df.columns, keywords)
    print("Column Mapping:", col_map)

    final_df = pd.DataFrame()

    # --- STATUS FILTERING ---
    if 'status' in col_map:
        status_col = df[col_map['status']].astype(str).str.lower().str.strip()
        bad_statuses = ['cancelled', 'canceled', 'annule', 'annulé', 'returned', 'retour', 'refunded']
        mask_valid = ~status_col.isin(bad_statuses)
        df = df[mask_valid].copy()

    # --- DATE ---
    if 'date' in col_map:
        final_df['Date'] = pd.to_datetime(df[col_map['date']], errors='coerce', dayfirst=True)
    else:
        raise ValueError("❌ No Date column found.")

    final_df = final_df.dropna(subset=['Date']).sort_values('Date')

    # --- PRODUCT & CATEGORY (IMPROVED FALLBACK) ---
    # If no Product Name found, use Category Name instead (fixes your specific file)
    prod_col = col_map.get('product')
    cat_col = col_map.get('category')

    if prod_col:
        final_df['Product'] = df[prod_col].astype(str).str.title().str.strip()
    elif cat_col:
        # Fallback: "Fashion Item", "Beauty Item"
        final_df['Product'] = df[cat_col].astype(str).str.title().str.strip() + " Item"
    else:
        final_df['Product'] = "Unknown Product"

    final_df['Category'] = df[cat_col].astype(str).str.title().str.strip() if cat_col else "General"

    # --- NUMERIC DATA ---
    if 'quantity' in col_map:
        final_df['Quantity'] = df[col_map['quantity']].apply(clean_currency).fillna(1).astype(int)
    else:
        final_df['Quantity'] = 1

    if 'revenue' in col_map:
        final_df['Revenue'] = df[col_map['revenue']].apply(clean_currency).fillna(0)
    else:
        final_df['Revenue'] = 0.0

    if 'price' in col_map:
        final_df['Price'] = df[col_map['price']].apply(clean_currency).fillna(0)
    else:
        final_df['Price'] = 0.0

    # Smart Fill
    mask_rev_zero = final_df['Revenue'] == 0
    if mask_rev_zero.any() and 'price' in col_map:
        final_df.loc[mask_rev_zero, 'Revenue'] = final_df.loc[mask_rev_zero, 'Price'] * final_df.loc[
            mask_rev_zero, 'Quantity']

    mask_price_zero = final_df['Price'] == 0
    if mask_price_zero.any() and 'revenue' in col_map:
        final_df.loc[mask_price_zero, 'Price'] = final_df.loc[mask_price_zero, 'Revenue'] / final_df.loc[
            mask_price_zero, 'Quantity'].replace(0, 1)

    # --- DEMOGRAPHICS ---
    if 'gender' in col_map:
        final_df['Customer_Gender'] = df[col_map['gender']].astype(str).str.upper().map({
            'M': 'Male', 'MALE': 'Male', 'HOMME': 'Male', 'MR': 'Male',
            'F': 'Female', 'FEMALE': 'Female', 'FEMME': 'Female', 'MME': 'Female'
        }).fillna('Unknown')
    else:
        final_df['Customer_Gender'] = 'Unknown'

    if 'age' in col_map:
        final_df['Age_Group'] = df[col_map['age']].astype(str)
    else:
        final_df['Age_Group'] = 'Unknown'

    final_df = final_df[['Date', 'Product', 'Category', 'Quantity', 'Price', 'Revenue', 'Customer_Gender', 'Age_Group']]
    print(f"✅ Success! Loaded {len(final_df)} valid rows.")
    return final_df