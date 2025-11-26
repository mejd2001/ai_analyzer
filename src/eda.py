# src/eda.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def perform_eda(df: pd.DataFrame) -> dict:
    """Calculates basic KPIs for the dashboard."""
    insights = {}
    insights['total_revenue'] = df['Revenue'].sum()
    insights['total_orders'] = len(df)

    top_prod = df.groupby('Product')['Revenue'].sum().nlargest(1)
    insights['most_profitable_product'] = top_prod.index[0] if not top_prod.empty else "Unknown"

    top_cat = df.groupby('Category')['Revenue'].sum().nlargest(1)
    insights['top_category'] = top_cat.index[0] if not top_cat.empty else "Unknown"

    return insights


# --- 1. YEAR-OVER-YEAR TREND (The "Are we growing?" Chart) ---
def plot_yoy_trend(df):
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month_name()
    # Sort months correctly
    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']

    monthly = df.groupby(['Year', 'Month'])['Revenue'].sum().reset_index()

    fig = px.line(monthly, x='Month', y='Revenue', color='Year', markers=True,
                  category_orders={'Month': month_order},
                  title="📈 Year-Over-Year Performance Comparison",
                  color_discrete_sequence=px.colors.qualitative.Prism)
    fig.update_layout(xaxis_title="", yaxis_title="Revenue", hovermode="x unified")
    return fig


# --- 2. PARETO CHART (The "What matters?" Chart) ---
def plot_pareto_products(df):
    # Group by product and sort
    data = df.groupby('Product')['Revenue'].sum().sort_values(ascending=False).reset_index()
    data['Cumulative %'] = 100 * data['Revenue'].cumsum() / data['Revenue'].sum()

    # Take top 20 products to keep it readable
    top_data = data.head(20)

    fig = go.Figure()
    # Bar Chart (Revenue)
    fig.add_trace(go.Bar(
        x=top_data['Product'], y=top_data['Revenue'], name='Revenue',
        marker_color='#00C28E'
    ))
    # Line Chart (Cumulative %)
    fig.add_trace(go.Scatter(
        x=top_data['Product'], y=top_data['Cumulative %'], name='Cumulative %',
        yaxis='y2', mode='lines+markers', marker_color='red'
    ))

    fig.update_layout(
        title="🏆 Top 20 Products (Pareto Analysis)",
        yaxis=dict(title="Revenue"),
        yaxis2=dict(title="Cumulative %", overlaying='y', side='right', range=[0, 110]),
        showlegend=False
    )
    return fig


# --- 3. SUNBURST CHART (The "Drill Down" Chart) ---
def plot_category_sunburst(df):
    # Hierarchical view: Category -> Product
    # We aggregate first to handle large data
    agg = df.groupby(['Category', 'Product'])['Revenue'].sum().reset_index()

    fig = px.sunburst(agg, path=['Category', 'Product'], values='Revenue',
                      title="🎯 Revenue by Category (Click to Zoom)",
                      color='Revenue', color_continuous_scale='Greens')
    return fig


# --- 4. SCATTER MATRIX (The "Strategy" Chart) ---
def plot_price_vs_volume(df):
    # Group by Product
    prod = df.groupby('Product').agg({
        'Revenue': 'sum',
        'Quantity': 'sum',
        'Price': 'mean',
        'Category': 'first'
    }).reset_index()

    fig = px.scatter(prod, x='Price', y='Quantity', size='Revenue', color='Category',
                     hover_name='Product', log_x=True,
                     title="💎 Price vs. Volume Strategy Matrix",
                     labels={'Price': 'Avg Price (Log Scale)', 'Quantity': 'Total Units Sold'})
    return fig