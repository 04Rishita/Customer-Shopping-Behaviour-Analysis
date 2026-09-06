import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import io

# ─────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Data Driven Customer Purchase Insights",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; }

    div[data-testid="metric-container"] {
        background: white;
        border-radius: 10px;
        padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #6b4fa0;
        text-align: center;
    }
    div[data-testid="metric-container"] label {
        font-size: 14px !important;
        color: #718096 !important;
        font-weight: 600 !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: #2d3748 !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 700;
        font-size: 14px;
        padding: 10px 24px;
    }
    .stTabs [aria-selected="true"] {
        color: #6b4fa0 !important;
        border-bottom: 3px solid #6b4fa0 !important;
    }
    .stDownloadButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        background-color: #6b4fa0;
        color: white;
        border: none;
    }
    .stDownloadButton > button:hover {
        background-color: #553d80;
        color: white;
    }
    .dashboard-header {
        background: linear-gradient(135deg, #b39ddb 0%, #7c4dac 100%);
        padding: 20px 30px;
        border-radius: 14px;
        margin-bottom: 22px;
    }
    .dashboard-header h1 {
        color: white !important;
        font-size: 1.75rem !important;
        margin: 0 !important;
        font-weight: 800 !important;
    }
    .dashboard-header p {
        color: rgba(255,255,255,0.8);
        margin: 5px 0 0;
        font-size: 12px;
    }
    .section-label {
        font-size: 12px;
        font-weight: 700;
        color: #6b4fa0;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 14px;
        border-left: 4px solid #6b4fa0;
        padding-left: 10px;
    }
    .recommend-box {
        background: #f0ebfa;
        border-left: 4px solid #6b4fa0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 10px;
        font-size: 13px;
        color: #3d2366;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  POWER BI COLORS
# ─────────────────────────────────────────
PBI_PURPLE = "#3d3d8f"
PBI_PINK   = "#e472b4"
PBI_LINE   = "#3d3d8f"
TMPL       = "plotly_white"

# ─────────────────────────────────────────
#  DB CONNECTION
# ─────────────────────────────────────────
@st.cache_resource
def get_engine():
    connection_url = URL.create(
        drivername="mysql+pymysql",
        username="root",
        password="@12345",
        host="localhost",
        port=3306,
        database="customer_shopping_behaviour"
    )
    return create_engine(connection_url)

engine = get_engine()

# ─────────────────────────────────────────
#  CLEANING FUNCTION
# ─────────────────────────────────────────
def clean_and_transform(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    if "purchase_amount_(usd)" in df.columns:
        df.rename(columns={"purchase_amount_(usd)": "purchase_amount"}, inplace=True)
    if "review_rating" in df.columns and "category" in df.columns:
        df["review_rating"] = df.groupby("category")["review_rating"].transform(
            lambda x: x.fillna(x.median())
        )
    if "age" in df.columns:
        labels = ["Young-Adult", "Adult", "Middle-Aged", "Senior"]
        df["age_group"] = pd.qcut(df["age"], q=4, labels=labels)
    if "frequency_of_purchases" in df.columns:
        freq_map = {
            "Fortnightly": 14, "Weekly": 7,  "Quarterly": 90,
            "Bi-Weekly":   14, "Annually": 365, "Every 3 Months": 90
        }
        df["purchase_frequency_days"] = df["frequency_of_purchases"].map(freq_map)
    if "promo_code_used" in df.columns:
        df.drop("promo_code_used", axis=1, inplace=True)
    if "purchase_amount" in df.columns and "purchase_frequency_days" in df.columns:
        df["total_spend"] = df["purchase_amount"] * df["purchase_frequency_days"]
    return df

# ─────────────────────────────────────────
#  LOAD DATA  (ttl=30 → auto re-fetches)
# ─────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM customer", engine)

# ─────────────────────────────────────────
#  HELPER — recommendation box
# ─────────────────────────────────────────
def recommendation(text: str):
    st.markdown(
        f'<div class="recommend-box">💡 <strong>Business Recommendation:</strong> {text}</div>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛒 Shopping Analytics")
    st.caption("Customer Behaviour Intelligence Portal")
    st.markdown("---")

    st.subheader("📂 Upload New Data")
    st.caption("Your data pipeline: CSV → MySQL → Dashboard. One click.")
    uploaded_file = st.file_uploader(
        "Choose CSV file", type=["csv"], label_visibility="collapsed"
    )
    if uploaded_file is not None:
        try:
            new_df = pd.read_csv(uploaded_file)
            new_df = clean_and_transform(new_df)
            new_df.to_sql("customer", engine, if_exists="append", index=False)
            st.success(f"✅ **{uploaded_file.name}** uploaded!\nAll insights updated.")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")

    st.markdown("---")
    st.subheader("🔽 Filters")
    st.caption("Applies to all tabs")

    df_raw = load_data()

    sel_subscription = st.multiselect(
        "Subscription Status",
        options=sorted(df_raw["subscription_status"].dropna().unique().tolist()),
        default=sorted(df_raw["subscription_status"].dropna().unique().tolist())
    )
    sel_gender = st.multiselect(
        "Gender",
        options=sorted(df_raw["gender"].dropna().unique().tolist()),
        default=sorted(df_raw["gender"].dropna().unique().tolist())
    )
    sel_category = st.multiselect(
        "Category",
        options=sorted(df_raw["category"].dropna().unique().tolist()),
        default=sorted(df_raw["category"].dropna().unique().tolist())
    )
    sel_shipping = st.multiselect(
        "Shipping Type",
        options=sorted(df_raw["shipping_type"].dropna().unique().tolist()),
        default=sorted(df_raw["shipping_type"].dropna().unique().tolist())
    )

    st.markdown("---")

# ─────────────────────────────────────────
#  APPLY FILTERS
# ─────────────────────────────────────────
df = df_raw.copy()
if sel_subscription: df = df[df["subscription_status"].isin(sel_subscription)]
if sel_gender:       df = df[df["gender"].isin(sel_gender)]
if sel_category:     df = df[df["category"].isin(sel_category)]
if sel_shipping:     df = df[df["shipping_type"].isin(sel_shipping)]

# ─────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────
st.markdown("""
<div class="dashboard-header">
    <h1>📊 Data Driven Customer Purchase Insights</h1>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
#  3 KPI CARDS
# ─────────────────────────────────────────
k1, k2, k3 = st.columns(3)
total_customers = len(df)
avg_purchase    = df["purchase_amount"].mean() if len(df) > 0 else 0
avg_rating      = df["review_rating"].mean()   if len(df) > 0 else 0

k1.metric("Number of Customers",     f"{total_customers:,}")
k2.metric("Average Purchase Amount", f"{avg_purchase:,.2f}")
k3.metric("Average Review Rating",   f"{avg_rating:.2f}")

st.markdown("---")

# ─────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────
tab_pbi, tab_sql, tab_download = st.tabs([
    "📊 Power BI Dashboard",
    "📋 SQL Queries Analysis",
    "⬇️ Download Data"
])

# ══════════════════════════════════════════
#  TAB 1 — POWER BI DASHBOARD
# ══════════════════════════════════════════
with tab_pbi:
    st.markdown('<div class="section-label">Power BI Dashboard</div>',
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.2, 1.4, 1.4])

    # Chart 1 — Donut: Customer Distribution by Subscription Plan
    with col1:
        sub_counts = df["subscription_status"].value_counts().reset_index()
        sub_counts.columns = ["Subscription", "Count"]
        fig1 = go.Figure(go.Pie(
            labels=sub_counts["Subscription"],
            values=sub_counts["Count"],
            hole=0.55,
            marker_colors=[PBI_PURPLE if x == "No" else PBI_PINK
                           for x in sub_counts["Subscription"]],
            textinfo="label+percent",
            textfont_size=13,
            direction="clockwise",
            showlegend=False
        ))
        fig1.update_layout(
            title=dict(text="Customer Distribution by Subscription Plan",
                       font=dict(size=13, color="#2d3748"), x=0),
            template=TMPL, height=330,
            margin=dict(t=45, b=10, l=10, r=10)
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2 — Vertical Bar: Revenue Split by Category
    with col2:
        cat_rev = df.groupby("category")["purchase_amount"].sum().reset_index()
        cat_rev.columns = ["Category", "Revenue"]
        cat_rev = cat_rev.sort_values("Revenue", ascending=False)
        fig2 = go.Figure(go.Bar(
            x=cat_rev["Category"],
            y=cat_rev["Revenue"],
            marker_color=PBI_PURPLE,
            text=cat_rev["Revenue"].apply(lambda x: f"{x/1000:.0f}K"),
            textposition="outside",
            textfont=dict(size=11)
        ))
        fig2.update_layout(
            title=dict(text="Revenue Split by Category",
                       font=dict(size=13, color="#2d3748"), x=0),
            template=TMPL, height=330,
            xaxis_title="",
            yaxis=dict(tickformat="~s", title="Revenue"),
            margin=dict(t=45, b=10, l=10, r=10)
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 3 — Horizontal Bar: Sales by Category
    with col3:
        sales_cat = df.groupby("category")["customer_id"].count().reset_index()
        sales_cat.columns = ["Category", "Sales Count"]
        sales_cat = sales_cat.sort_values("Sales Count", ascending=True)
        fig3 = go.Figure(go.Bar(
            y=sales_cat["Category"],
            x=sales_cat["Sales Count"],
            orientation="h",
            marker_color=PBI_PURPLE,
            text=sales_cat["Sales Count"],
            textposition="outside",
            textfont=dict(size=11)
        ))
        fig3.update_layout(
            title=dict(text="Sales by Category",
                       font=dict(size=13, color="#2d3748"), x=0),
            template=TMPL, height=330,
            xaxis_title="Sales Count", yaxis_title="",
            margin=dict(t=45, b=10, l=10, r=30)
        )
        st.plotly_chart(fig3, use_container_width=True)

    col4, col5 = st.columns([1.4, 1.6])

    # Chart 4 — Horizontal Bar: Sales by Age Group
    with col4:
        if "age_group" in df.columns:
            age_order = ["Senior", "Adult", "Middle-Aged", "Young-Adult"]
            age_sales = df.groupby("age_group")["purchase_amount"].sum().reset_index()
            age_sales.columns = ["Age Group", "Total Sales"]
            age_sales["Age Group"] = pd.Categorical(
                age_sales["Age Group"], categories=age_order, ordered=True
            )
            age_sales = age_sales.sort_values("Age Group")
            fig4 = go.Figure(go.Bar(
                y=age_sales["Age Group"].astype(str),
                x=age_sales["Total Sales"],
                orientation="h",
                marker_color=PBI_PURPLE,
                text=age_sales["Total Sales"].apply(lambda x: f"{x/1000:.0f}K"),
                textposition="outside",
                textfont=dict(size=11)
            ))
            fig4.update_layout(
                title=dict(text="Sales by Age Group by age_group",
                           font=dict(size=13, color="#2d3748"), x=0),
                template=TMPL, height=350,
                xaxis=dict(tickformat="~s", title="Total Sales"),
                yaxis_title="",
                margin=dict(t=45, b=10, l=10, r=40)
            )
            st.plotly_chart(fig4, use_container_width=True)

    # Chart 5 — Line: Seasonal Revenue Trend
    with col5:
        season_order = ["Fall", "Spring", "Winter", "Summer"]
        sea_rev = df.groupby("season")["purchase_amount"].sum().reset_index()
        sea_rev.columns = ["Season", "Revenue"]
        sea_rev["Season"] = pd.Categorical(
            sea_rev["Season"], categories=season_order, ordered=True
        )
        sea_rev = sea_rev.sort_values("Season")
        fig5 = go.Figure(go.Scatter(
            x=sea_rev["Season"],
            y=sea_rev["Revenue"],
            mode="lines+markers",
            line=dict(color=PBI_LINE, width=3),
            marker=dict(size=8, color=PBI_LINE)
        ))
        fig5.update_layout(
            title=dict(text="Seasonal Revenue Trend",
                       font=dict(size=13, color="#2d3748"), x=0),
            template=TMPL, height=350,
            xaxis_title="Season",
            yaxis=dict(tickformat="~s", title="Revenue"),
            margin=dict(t=45, b=10, l=10, r=10)
        )
        st.plotly_chart(fig5, use_container_width=True)

# ══════════════════════════════════════════
#  TAB 2 — SQL QUERIES ANALYSIS
#  Option 2 + Option 4:
#  Each query = KPI metrics + Table + Business Recommendation
#  All computed from filtered `df` so they auto-update with new data
# ══════════════════════════════════════════
with tab_sql:
    st.markdown('<div class="section-label">SQL Insights — Auto-updates on new data</div>',
                unsafe_allow_html=True)

    # ── Q1: Revenue by Gender ───────────────────────────────
    with st.expander("💰Revenue by Gender", expanded=False):
        r1 = df.groupby("gender")["purchase_amount"].sum().reset_index()
        r1.columns = ["Gender", "Total Revenue"]
        r1["Total Revenue"] = r1["Total Revenue"].round(2)
        r1 = r1.sort_values("Total Revenue", ascending=False)

        top_gender   = r1.iloc[0]["Gender"]
        top_rev      = r1.iloc[0]["Total Revenue"]
        bottom_rev   = r1.iloc[1]["Total Revenue"] if len(r1) > 1 else 0
        diff_pct     = round((top_rev - bottom_rev) / max(bottom_rev, 1) * 100, 1)

        c1, c2, c3 = st.columns(3)
        c1.metric("Higher Revenue Gender", top_gender)
        c2.metric("Their Total Revenue",   f"{top_rev:,.0f}")
        c3.metric("Difference %",          f"{diff_pct}% more")

        st.dataframe(r1, use_container_width=True, hide_index=True)
        recommendation(
            f"**{top_gender}** customers generate **{diff_pct}% more** revenue. "
            f"Focus marketing campaigns, loyalty rewards, and premium product placements "
            f"towards {top_gender} customers to maximize overall revenue."
        )

    # ── Q2: Discount Users Above Average Spend ──────────────
    with st.expander("🏷️Discount Users Spending Above Average", expanded=False):
        avg_amt = df["purchase_amount"].mean()
        r2 = df[
            (df["discount_applied"] == "Yes") &
            (df["purchase_amount"] >= avg_amt)
        ][["customer_id", "purchase_amount"]].copy()
        r2.columns = ["Customer ID", "Purchase Amount"]
        r2 = r2.sort_values("Purchase Amount", ascending=False).reset_index(drop=True)

        pct_of_total = round(len(r2) / max(len(df), 1) * 100, 1)

        c1, c2, c3 = st.columns(3)
        c1.metric("Customers Found",    f"{len(r2):,}")
        c2.metric("Avg Spend Threshold", f"{avg_amt:,.2f}")
        c3.metric("% of Total Customers", f"{pct_of_total}%")

        st.dataframe(r2.head(20), use_container_width=True, hide_index=True)
        st.caption("Showing top 20 rows")
        recommendation(
            f"**{len(r2):,} customers** ({pct_of_total}% of total) used discounts yet still "
            f"spent above the average of **{avg_amt:,.2f}**. These are high-value discount "
            f"users — consider offering them exclusive loyalty discounts to retain them rather "
            f"than broad discount campaigns."
        )

    # ── Q3: Top 5 Products by Avg Rating ────────────────────
    with st.expander("⭐Top 5 Highest Rated Products", expanded=False):
        r3 = (
            df.groupby("item_purchased")["review_rating"]
            .mean().round(2)
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
        )
        r3.columns = ["Product", "Avg Rating"]

        best_product = r3.iloc[0]["Product"]
        best_rating  = r3.iloc[0]["Avg Rating"]
        worst_of_top = r3.iloc[-1]["Avg Rating"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Best Rated Product", best_product)
        c2.metric("Its Avg Rating",     f"{best_rating} ⭐")
        c3.metric("5th Place Rating",   f"{worst_of_top} ⭐")

        st.dataframe(r3, use_container_width=True, hide_index=True)
        recommendation(
            f"**{best_product}** has the highest customer satisfaction with a rating of "
            f"**{best_rating}★**. Prioritize this product in homepage banners, email campaigns, "
            f"and cross-sell recommendations to leverage its strong reputation."
        )

    # ── Q4: Express vs Standard Shipping ────────────────────
    with st.expander("🚚Shipping Type Purchase Comparison", expanded=False):
        r4 = (
            df[df["shipping_type"].isin(["Express", "Standard"])]
            .groupby("shipping_type")["purchase_amount"]
            .mean().round(2)
            .reset_index()
        )
        r4.columns = ["Shipping Type", "Avg Purchase Amount"]
        r4 = r4.sort_values("Avg Purchase Amount", ascending=False)

        top_ship     = r4.iloc[0]["Shipping Type"]
        top_ship_val = r4.iloc[0]["Avg Purchase Amount"]
        bot_ship_val = r4.iloc[1]["Avg Purchase Amount"] if len(r4) > 1 else 0
        ship_diff    = round(top_ship_val - bot_ship_val, 2)

        c1, c2, c3 = st.columns(3)
        c1.metric("Higher Avg Spend Shipping", top_ship)
        c2.metric("Its Avg Purchase",          f"{top_ship_val:,.2f}")
        c3.metric("Difference vs Other",       f"{ship_diff:,.2f}")

        st.dataframe(r4, use_container_width=True, hide_index=True)
        recommendation(
            f"Customers choosing **{top_ship}** shipping spend **{ship_diff:.2f} more** "
            f"on average. Consider bundling premium shipping with high-value product categories "
            f"or offering free {top_ship} shipping above a spend threshold to increase average order value."
        )

    # ── Q5: Subscriber vs Non-Subscriber ────────────────────
    with st.expander("📊Subscriber vs Non-Subscriber Spending", expanded=False):
        r5 = (
            df.groupby("subscription_status")
            .agg(
                Total_Customers=("customer_id",    "count"),
                Avg_Spend      =("purchase_amount", "mean"),
                Total_Revenue  =("purchase_amount", "sum")
            )
            .round(2)
            .reset_index()
        )
        r5.columns = ["Subscription", "Total Customers", "Avg Spend", "Total Revenue"]
        r5 = r5.sort_values("Total Revenue", ascending=False)

        sub_row   = r5[r5["Subscription"] == "Yes"]
        nosub_row = r5[r5["Subscription"] == "No"]

        sub_avg   = sub_row["Avg Spend"].values[0]   if len(sub_row)   > 0 else 0
        nosub_avg = nosub_row["Avg Spend"].values[0] if len(nosub_row) > 0 else 0
        spend_diff = round(sub_avg - nosub_avg, 2)
        higher     = "Subscribers" if spend_diff > 0 else "Non-Subscribers"

        c1, c2, c3 = st.columns(3)
        c1.metric("Higher Avg Spend",    higher)
        c2.metric("Subscriber Avg",      f"{sub_avg:,.2f}")
        c3.metric("Non-Subscriber Avg",  f"{nosub_avg:,.2f}")

        st.dataframe(r5, use_container_width=True, hide_index=True)
        recommendation(
            f"**{higher}** spend more on average. "
            f"The spend difference is **{abs(spend_diff):.2f} per transaction**. "
            f"Invest in a strong subscription onboarding program — converting even 10% of "
            f"non-subscribers could significantly boost overall revenue."
        )

    # ── Q6: Products with Highest Discount Usage ────────────
    with st.expander("🔥Top 5 Products by Discount Usage", expanded=False):
        disc = df.copy()
        disc["is_discounted"] = (disc["discount_applied"] == "Yes").astype(int)
        r6 = (
            disc.groupby("item_purchased")["is_discounted"]
            .mean().mul(100).round(2)
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
        )
        r6.columns = ["Product", "Discount Rate (%)"]

        top_disc_product = r6.iloc[0]["Product"]
        top_disc_rate    = r6.iloc[0]["Discount Rate (%)"]

        c1, c2 = st.columns(2)
        c1.metric("Most Discounted Product", top_disc_product)
        c2.metric("Its Discount Rate",       f"{top_disc_rate}%")

        st.dataframe(r6, use_container_width=True, hide_index=True)
        recommendation(
            f"**{top_disc_product}** has the highest discount usage at **{top_disc_rate}%**. "
            f"Review if heavy discounting is eroding margins on this product. "
            f"Consider replacing frequent discounts with value-add bundles or loyalty points "
            f"to protect profitability while maintaining customer interest."
        )

    # ── Q7: Customer Segmentation ────────────────────────────
    with st.expander("👥Customer Segmentation: New / Returning / Loyal", expanded=False):
        seg = df.copy()
        seg["segment"] = pd.cut(
            seg["previous_purchases"],
            bins=[-1, 1, 10, float("inf")],
            labels=["New", "Returning", "Loyal"]
        )
        r7 = (
            seg["segment"].value_counts()
            .reset_index()
        )
        r7.columns = ["Customer Segment", "Number of Customers"]
        r7 = r7.sort_values("Number of Customers", ascending=False)

        total       = r7["Number of Customers"].sum()
        top_seg     = r7.iloc[0]["Customer Segment"]
        top_seg_cnt = r7.iloc[0]["Number of Customers"]
        top_seg_pct = round(top_seg_cnt / max(total, 1) * 100, 1)

        loyal_cnt   = r7[r7["Customer Segment"] == "Loyal"]["Number of Customers"].sum()
        new_cnt     = r7[r7["Customer Segment"] == "New"]["Number of Customers"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Largest Segment",  top_seg)
        c2.metric("Loyal Customers",  f"{loyal_cnt:,}")
        c3.metric("New Customers",    f"{new_cnt:,}")

        st.dataframe(r7, use_container_width=True, hide_index=True)
        recommendation(
            f"**{top_seg}** customers make up the largest segment at **{top_seg_pct}%**. "
            f"With **{loyal_cnt:,} loyal customers**, focus on retention programs like VIP rewards. "
            f"For **{new_cnt:,} new customers**, create onboarding offers to convert them into "
            f"returning buyers quickly."
        )

    # ── Q8: Top 3 Products per Category ─────────────────────
    with st.expander("🏆Top 3 Products per Category", expanded=False):
        ic = (
            df.groupby(["category", "item_purchased"])["customer_id"]
            .count().reset_index()
        )
        ic.columns = ["Category", "Product", "Total Orders"]
        ic["Rank"] = ic.groupby("Category")["Total Orders"].rank(
            ascending=False, method="first"
        ).astype(int)
        r8 = (
            ic[ic["Rank"] <= 3]
            .sort_values(["Category", "Rank"])
            .reset_index(drop=True)
        )
        r8 = r8[["Rank", "Category", "Product", "Total Orders"]]

        total_categories = r8["Category"].nunique()
        top_product_row  = r8[r8["Rank"] == 1].sort_values("Total Orders", ascending=False).iloc[0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Categories Analysed",    total_categories)
        c2.metric("Overall Best Product",   top_product_row["Product"])
        c3.metric("Its Orders",             f"{top_product_row['Total Orders']:,}")

        st.dataframe(r8, use_container_width=True, hide_index=True)
        recommendation(
            f"**{top_product_row['Product']}** is the best-selling product overall with "
            f"**{top_product_row['Total Orders']:,} orders**. Ensure sufficient stock levels "
            f"for top products per category and consider cross-promoting rank #2 and #3 products "
            f"alongside rank #1 to boost their visibility."
        )

    # ── Q9: Repeat Buyers vs Subscription ───────────────────
    with st.expander("🔁Repeat Buyers vs Subscription Status", expanded=False):
        r9 = (
            df[df["previous_purchases"] > 5]
            .groupby("subscription_status")["customer_id"]
            .count().reset_index()
        )
        r9.columns = ["Subscription Status", "Repeat Buyers"]
        r9 = r9.sort_values("Repeat Buyers", ascending=False)

        total_repeat  = r9["Repeat Buyers"].sum()
        sub_repeat    = r9[r9["Subscription Status"] == "Yes"]["Repeat Buyers"].sum()
        nosub_repeat  = r9[r9["Subscription Status"] == "No"]["Repeat Buyers"].sum()
        sub_repeat_pct = round(sub_repeat / max(total_repeat, 1) * 100, 1)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Repeat Buyers",          f"{total_repeat:,}")
        c2.metric("Subscribed Repeat Buyers",     f"{sub_repeat:,}")
        c3.metric("% Subscribed Among Repeaters", f"{sub_repeat_pct}%")

        st.dataframe(r9, use_container_width=True, hide_index=True)
        recommendation(
            f"**{sub_repeat_pct}%** of repeat buyers (>5 purchases) are subscribed. "
            f"{'Subscribed customers are more loyal — strengthen the subscription benefits.' if sub_repeat_pct > 50 else 'Many repeat buyers are NOT subscribed — this is a missed opportunity.'} "
            f"Target non-subscribed repeat buyers with a personalised subscription invite "
            f"offering exclusive perks to convert them."
        )

    # ── Q10: Revenue by Age Group ────────────────────────────
    with st.expander("👴Revenue Contribution by Age Group", expanded=False):
        r10 = (
            df.groupby("age_group")["purchase_amount"]
            .sum().round(2)
            .reset_index()
        )
        r10.columns = ["Age Group", "Revenue"]
        r10 = r10.sort_values("Revenue", ascending=False).reset_index(drop=True)

        top_age     = r10.iloc[0]["Age Group"]
        top_age_rev = r10.iloc[0]["Revenue"]
        total_rev   = r10["Revenue"].sum()
        top_age_pct = round(top_age_rev / max(total_rev, 1) * 100, 1)

        c1, c2, c3 = st.columns(3)
        c1.metric("Highest Revenue Age Group", str(top_age))
        c2.metric("Their Total Revenue",       f"{top_age_rev:,.0f}")
        c3.metric("% of Total Revenue",        f"{top_age_pct}%")

        st.dataframe(r10, use_container_width=True, hide_index=True)
        recommendation(
            f"**{top_age}** customers contribute the most revenue at **{top_age_pct}%** of total. "
            f"Design age-specific marketing — for example, social media campaigns for younger "
            f"groups and email/catalog campaigns for older groups — to maximise engagement "
            f"across all age segments."
        )

    st.markdown("---")
    st.caption("⚡ All insights above use filtered data and auto-update when new CSV is uploaded.")

# ══════════════════════════════════════════
#  TAB 3 — DOWNLOAD DATA
# ══════════════════════════════════════════
with tab_download:
    st.subheader("⬇️ Download Your Data")
    st.caption(
        f"Full dataset: **{len(df_raw):,} rows** &nbsp;|&nbsp; "
        f"Filtered view: **{len(df):,} rows**"
    )
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.download_button(
            label="⬇️ Full Data (CSV)",
            data=df_raw.to_csv(index=False),
            file_name="customer_shopping_full.csv",
            mime="text/csv",
            use_container_width=True
        )

    buf_full = io.BytesIO()
    with pd.ExcelWriter(buf_full, engine="openpyxl") as w:
        df_raw.to_excel(w, index=False, sheet_name="Full Data")
    with col2:
        st.download_button(
            label="⬇️ Full Data (Excel)",
            data=buf_full.getvalue(),
            file_name="customer_shopping_full.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col3:
        st.download_button(
            label="⬇️ Filtered Data (CSV)",
            data=df.to_csv(index=False),
            file_name="customer_shopping_filtered.csv",
            mime="text/csv",
            use_container_width=True
        )

    buf_filtered = io.BytesIO()
    with pd.ExcelWriter(buf_filtered, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Filtered Data")
    with col4:
        st.download_button(
            label="⬇️ Filtered Data (Excel)",
            data=buf_filtered.getvalue(),
            file_name="customer_shopping_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("### 👁️ Data Preview")
    prev1, prev2 = st.tabs(["Filtered Data", "Full Data"])

    with prev1:
        st.caption(f"{len(df):,} rows after filters")
        st.dataframe(df, use_container_width=True, height=400)

    with prev2:
        st.caption(f"{len(df_raw):,} rows — complete dataset")
        st.dataframe(df_raw, use_container_width=True, height=400)