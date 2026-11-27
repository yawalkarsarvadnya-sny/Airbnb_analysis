
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="Airbnb Analytics Dashboard",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f7f9fc, #eef3f8);
}
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 2rem;
}
h1, h2, h3 {
    color: #172b4d;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e6ebf2;
    padding: 16px 18px;
    border-radius: 14px;
    box-shadow: 0 3px 12px rgba(25,42,70,.06);
}
div[data-testid="stMetricLabel"] {
    color: #64748b;
}
div[data-testid="stMetricValue"] {
    color: #172b4d;
}
section[data-testid="stSidebar"] {
    background: white;
}
</style>
""", unsafe_allow_html=True)

st.title("🏡 Airbnb Listings & Market Analytics")
st.caption("Explore listing locations, prices, availability, hosts and guest reviews.")

# ---------------- LOAD DATA ----------------

@st.cache_data(show_spinner="Reading your Airbnb data...")
def load_data(file_bytes):

    from io import BytesIO

    data = pd.read_csv(
        BytesIO(file_bytes),
        low_memory=False
    )

    # Standardize column names

    data.columns = (
        data.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    aliases = {
        "name": "name",
        "host_id": "host_id",
        "host_name": "host_name",
        "neighbourhood_group": "neighbourhood_group",
        "neighbourhood": "neighbourhood",
        "room_type": "room_type",
        "construction_year": "construction_year",
        "price": "price",
        "service_fee": "service_fee",
        "minimum_nights": "minimum_nights",
        "number_of_reviews": "number_of_reviews",
        "last_review": "last_review",
        "reviews_per_month": "reviews_per_month",
        "review_rate_number": "review_rate_number",
        "calculated_host_listings_count":
            "calculated_host_listings_count",
        "availability_365": "availability",
        "availability": "availability",
        "host_identity_verified": "host_identity_verified",
        "instant_bookable": "instant_bookable",
        "cancellation_policy": "cancellation_policy",
        "country": "country"
    }

    data = data.rename(
        columns={
            c: aliases[c]
            for c in data.columns
            if c in aliases
        }
    )

    # Convert numeric columns

    numeric_cols = [
        "price",
        "service_fee",
        "minimum_nights",
        "number_of_reviews",
        "reviews_per_month",
        "review_rate_number",
        "availability",
        "construction_year",
        "calculated_host_listings_count",
        "host_id"
    ]

    for col in numeric_cols:

        if col in data.columns:

            data[col] = pd.to_numeric(
                data[col].astype(str).str.replace(
                    r"[$,]", "", regex=True
                ),
                errors="coerce"
            )

    # Date conversion

    if "last_review" in data.columns:

        data["last_review"] = pd.to_datetime(
            data["last_review"],
            errors="coerce"
        )

        data["Year"] = data["last_review"].dt.year
        data["Month"] = data["last_review"].dt.month_name()

    # Handle missing categorical values

    for col in data.select_dtypes(
        include=["object", "string"]
    ).columns:

        data[col] = data[col].fillna("Unknown")

    return data


# ---------------- SIDEBAR UPLOAD ----------------

with st.sidebar:

    st.header("📂 Upload Your Data")

    uploaded_file = st.file_uploader(
        "Upload Airbnb CSV File",
        type=["csv"],
        help="Upload your 35 MB dataset directly."
    )

    st.divider()

    st.markdown("**Dashboard Controls**")
    st.caption("Upload your CSV to activate filters and charts.")


if uploaded_file is None:

    st.info(
        "👈 Upload your Airbnb CSV file from the sidebar."
    )

    st.markdown("""
    ### Dashboard Features

    - Total Listings
    - Average Price
    - Average Availability
    - Unique Hosts
    - Total Reviews
    - Location Analysis
    - Pricing Analysis
    - Availability Analysis
    - Host and Review Analysis
    """)

    st.stop()


# ---------------- READ CSV ----------------

try:

    df = load_data(uploaded_file.getvalue())

except Exception as exc:

    st.error(f"Unable to read CSV file: {exc}")
    st.stop()


if df.empty:

    st.warning("Uploaded CSV contains no rows.")
    st.stop()


# ---------------- HELPER FUNCTIONS ----------------

def has(col):
    return col in df.columns


def numeric(col):
    return (
        has(col)
        and pd.api.types.is_numeric_dtype(df[col])
    )


def money(value):

    if pd.notna(value):
        return f"${value:,.0f}"

    return "—"


# ---------------- SIDEBAR FILTERS ----------------

with st.sidebar:

    st.divider()
    st.subheader("🔎 Filters")

    filtered = df.copy()

    # Neighbourhood filter

    if has("neighbourhood_group"):

        vals = sorted(
            filtered["neighbourhood_group"]
            .dropna()
            .astype(str)
            .unique()
        )

        selected = st.multiselect(
            "Neighbourhood Group",
            vals,
            default=vals
        )

        filtered = filtered[
            filtered["neighbourhood_group"]
            .astype(str)
            .isin(selected)
        ]

    # Room type filter

    if has("room_type"):

        vals = sorted(
            filtered["room_type"]
            .dropna()
            .astype(str)
            .unique()
        )

        selected = st.multiselect(
            "Room Type",
            vals,
            default=vals
        )

        filtered = filtered[
            filtered["room_type"]
            .astype(str)
            .isin(selected)
        ]

    # Price filter

    if has("price"):

        prices = filtered["price"].dropna()

        if not prices.empty:

            lo = float(prices.min())
            hi = float(prices.quantile(0.99))

            if lo < hi:

                price_range = st.slider(
                    "Price Range (USD)",
                    min_value=float(lo),
                    max_value=float(hi),
                    value=(float(lo), float(hi))
                )

                filtered = filtered[
                    filtered["price"].between(*price_range)
                ]

    # Minimum nights filter

    if (
        has("minimum_nights")
        and filtered["minimum_nights"].notna().any()
    ):

        max_nights = int(
            max(
                1,
                min(filtered["minimum_nights"].max(), 365)
            )
        )

        min_nights = st.number_input(
            "Maximum Minimum Nights",
            1,
            max_nights,
            max_nights
        )

        filtered = filtered[
            filtered["minimum_nights"].fillna(0)
            <= min_nights
        ]


st.caption(
    f"Showing {len(filtered):,} of {len(df):,} listings."
)

if filtered.empty:

    st.warning(
        "No listings match the selected filters."
    )

    st.stop()


# ---------------- KPI CARDS ----------------

total_listings = len(filtered)

avg_price = (
    filtered["price"].mean()
    if numeric("price")
    else float("nan")
)

avg_availability = (
    filtered["availability"].mean()
    if numeric("availability")
    else float("nan")
)

total_hosts = (
    filtered["host_id"].nunique()
    if has("host_id")
    else (
        filtered["host_name"].nunique()
        if has("host_name")
        else 0
    )
)

total_reviews = (
    filtered["number_of_reviews"].sum()
    if numeric("number_of_reviews")
    else 0
)

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total Listings", f"{total_listings:,}")

k2.metric("Average Price", money(avg_price))

k3.metric(
    "Avg. Availability",
    f"{avg_availability:,.1f} days"
    if pd.notna(avg_availability)
    else "—"
)

k4.metric("Unique Hosts", f"{total_hosts:,}")

k5.metric("Total Reviews", f"{total_reviews:,.0f}")

st.divider()


# ---------------- DASHBOARD TABS ----------------

tab1, tab2, tab3, tab4 = st.tabs([
    "📍 Location & Rooms",
    "💰 Pricing",
    "📅 Availability",
    "⭐ Hosts & Reviews"
])

CHART = {
    "template": "plotly_white",
    "font": {
        "family": "Arial",
        "size": 12,
        "color": "#24324a"
    }
}


# ==================================================
# TAB 1: LOCATION AND ROOM ANALYSIS
# ==================================================

with tab1:

    st.subheader("Location & Room Type Insights")

    c1, c2 = st.columns(2)

    # Listings by neighbourhood group

    if has("neighbourhood_group"):

        loc = (
            filtered["neighbourhood_group"]
            .value_counts()
            .head(12)
            .rename_axis("Neighbourhood group")
            .reset_index(name="Listings")
        )

        fig = px.bar(
            loc.sort_values("Listings"),
            x="Listings",
            y="Neighbourhood group",
            orientation="h",
            text="Listings",
            title="Listings by Neighbourhood Group",
            color="Listings",
            color_continuous_scale="Teal"
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            **CHART,
            coloraxis_showscale=False,
            height=430,
            margin=dict(l=10, r=35, t=60, b=20)
        )

        c1.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        c1.info("neighbourhood_group column not found.")

    # Room type distribution

    if has("room_type"):

        room = (
            filtered["room_type"]
            .value_counts()
            .rename_axis("Room type")
            .reset_index(name="Listings")
        )

        fig = px.pie(
            room,
            names="Room type",
            values="Listings",
            hole=0.58,
            title="Share of Listings by Room Type",
            color_discrete_sequence=px.colors.qualitative.Set2
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent+label"
        )

        fig.update_layout(
            **CHART,
            height=430,
            margin=dict(l=10, r=10, t=60, b=10)
        )

        c2.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        c2.info("room_type column not found.")

    # Top 10 neighbourhoods

    if has("neighbourhood"):

        top = (
            filtered["neighbourhood"]
            .value_counts()
            .head(10)
            .sort_values()
            .rename_axis("Neighbourhood")
            .reset_index(name="Listings")
        )

        fig = px.bar(
            top,
            x="Listings",
            y="Neighbourhood",
            orientation="h",
            text="Listings",
            title="Top 10 Neighbourhoods by Listings",
            color="Listings",
            color_continuous_scale="Blues"
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            **CHART,
            coloraxis_showscale=False,
            height=430,
            margin=dict(l=10, r=35, t=60, b=20)
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # Room type across neighbourhood groups

    if has("neighbourhood_group") and has("room_type"):

        cross = (
            filtered.groupby(
                ["neighbourhood_group", "room_type"],
                observed=True
            )
            .size()
            .reset_index(name="Listings")
        )

        fig = px.bar(
            cross,
            x="neighbourhood_group",
            y="Listings",
            color="room_type",
            barmode="stack",
            title="Room Type Mix Across Neighbourhood Groups",
            color_discrete_sequence=px.colors.qualitative.Safe
        )

        fig.update_layout(
            **CHART,
            height=440,
            xaxis_title="Neighbourhood Group",
            yaxis_title="Listings"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ==================================================
# TAB 2: PRICING ANALYSIS
# ==================================================

with tab2:

    st.subheader("Pricing Analysis")

    if numeric("price"):

        c1, c2 = st.columns(2)

        # Price distribution

        price_data = filtered[
            filtered["price"].between(
                0,
                filtered["price"].quantile(0.99)
            )
        ]

        fig = px.histogram(
            price_data,
            x="price",
            nbins=45,
            marginal="box",
            title="Price Distribution",
            labels={"price": "Price (USD)"},
            color_discrete_sequence=["#16A6A1"]
        )

        fig.update_layout(
            **CHART,
            height=420,
            yaxis_title="Number of Listings"
        )

        c1.plotly_chart(
            fig,
            use_container_width=True
        )

        # Average price by room type

        if has("room_type"):

            room_price = (
                filtered.groupby(
                    "room_type",
                    observed=True
                )["price"]
                .mean()
                .sort_values(ascending=False)
                .reset_index()
            )

            fig = px.bar(
                room_price,
                x="room_type",
                y="price",
                text_auto=".2f",
                title="Average Price by Room Type",
                color="price",
                color_continuous_scale="Sunset"
            )

            fig.update_layout(
                **CHART,
                coloraxis_showscale=False,
                height=420,
                yaxis_title="Average Price (USD)"
            )

            c2.plotly_chart(
                fig,
                use_container_width=True
            )

        # Top 10 neighbourhoods by average price

        if has("neighbourhood"):

            nprice = (
                filtered.groupby("neighbourhood")["price"]
                .mean()
                .nlargest(10)
                .sort_values()
                .reset_index()
            )

            fig = px.bar(
                nprice,
                x="price",
                y="neighbourhood",
                orientation="h",
                text_auto=".2f",
                title="Top 10 Neighbourhoods by Average Price",
                color="price",
                color_continuous_scale="Oranges"
            )

            fig.update_layout(
                **CHART,
                coloraxis_showscale=False,
                height=450,
                yaxis_title=""
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        # Price vs reviews

        if numeric("number_of_reviews"):

            scatter_data = filtered.dropna(
                subset=["price", "number_of_reviews"]
            )

            if len(scatter_data) > 5000:

                scatter_data = scatter_data.sample(
                    5000,
                    random_state=42
                )

            fig = px.scatter(
                scatter_data,
                x="price",
                y="number_of_reviews",
                color="room_type" if has("room_type") else None,
                hover_data=[
                    c for c in [
                        "name",
                        "neighbourhood",
                        "host_name"
                    ]
                    if has(c)
                ],
                title="Price vs Number of Reviews",
                opacity=0.55
            )

            fig.update_layout(
                **CHART,
                height=450
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    else:

        st.info("Numeric price column not found.")


# ==================================================
# TAB 3: AVAILABILITY ANALYSIS
# ==================================================

with tab3:

    st.subheader("Availability Trends")

    if numeric("availability"):

        c1, c2 = st.columns(2)

        # Availability distribution

        av = filtered["availability"].dropna()

        fig = px.histogram(
            av,
            x="availability",
            nbins=40,
            title="Listing Availability Distribution",
            labels={
                "availability": "Available Days Per Year"
            },
            color_discrete_sequence=["#5577C8"]
        )

        fig.update_layout(
            **CHART,
            height=420,
            yaxis_title="Number of Listings"
        )

        c1.plotly_chart(
            fig,
            use_container_width=True
        )

        # Average availability by room type

        if has("room_type"):

            av_room = (
                filtered.groupby(
                    "room_type",
                    observed=True
                )["availability"]
                .mean()
                .reset_index()
            )

            fig = px.bar(
                av_room,
                x="room_type",
                y="availability",
                text_auto=".1f",
                title="Average Availability by Room Type",
                color="availability",
                color_continuous_scale="Viridis"
            )

            fig.update_layout(
                **CHART,
                coloraxis_showscale=False,
                height=420,
                yaxis_title="Average Available Days"
            )

            c2.plotly_chart(
                fig,
                use_container_width=True
            )

        # Availability by year

        if has("Year"):

            yearly = (
                filtered.dropna(subset=["Year"])
                .groupby("Year")["availability"]
                .mean()
                .reset_index()
            )

            if not yearly.empty:

                fig = px.line(
                    yearly,
                    x="Year",
                    y="availability",
                    markers=True,
                    title="Average Availability by Last Review Year"
                )

                fig.update_traces(
                    line_width=3,
                    marker_size=8
                )

                fig.update_layout(
                    **CHART,
                    height=420,
                    yaxis_title="Average Available Days"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

    else:

        st.info("Availability column not found.")


# ==================================================
# TAB 4: HOST AND REVIEW ANALYSIS
# ==================================================

with tab4:

    st.subheader("Host & Guest Review Insights")

    c1, c2 = st.columns(2)

    # Top 10 hosts by reviews

    if has("host_name") and numeric("number_of_reviews"):

        hosts = (
            filtered.groupby("host_name")["number_of_reviews"]
            .sum()
            .nlargest(10)
            .sort_values()
            .reset_index()
        )

        fig = px.bar(
            hosts,
            x="number_of_reviews",
            y="host_name",
            orientation="h",
            text="number_of_reviews",
            title="Top 10 Hosts by Total Reviews",
            color="number_of_reviews",
            color_continuous_scale="Purples"
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            **CHART,
            coloraxis_showscale=False,
            height=430,
            yaxis_title=""
        )

        c1.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        c1.info("Host or review column not found.")

    # Host verification and ratings

    if has("host_identity_verified") and numeric("review_rate_number"):

        verify = (
            filtered.groupby("host_identity_verified")
            ["review_rate_number"]
            .mean()
            .reset_index()
        )

        fig = px.bar(
            verify,
            x="host_identity_verified",
            y="review_rate_number",
            text_auto=".2f",
            title="Average Review Rating by Host Verification",
            color="host_identity_verified",
            color_discrete_sequence=["#2A9D8F", "#E9C46A"]
        )

        fig.update_layout(
            **CHART,
            height=430,
            yaxis_title="Average Review Rating",
            xaxis_title="Host Identity Verified"
        )

        c2.plotly_chart(
            fig,
            use_container_width=True
        )

    elif has("review_rate_number"):

        fig = px.histogram(
            filtered,
            x="review_rate_number",
            nbins=20,
            title="Review Rating Distribution",
            color_discrete_sequence=["#E76F51"]
        )

        fig.update_layout(
            **CHART,
            height=430
        )

        c2.plotly_chart(
            fig,
            use_container_width=True
        )

    # Price vs review rating

    if numeric("price") and numeric("review_rate_number"):

        scatter_data = filtered.dropna(
            subset=["price", "review_rate_number"]
        )

        if len(scatter_data) > 5000:

            scatter_data = scatter_data.sample(
                5000,
                random_state=42
            )

        fig = px.scatter(
            scatter_data,
            x="price",
            y="review_rate_number",
            color="room_type" if has("room_type") else None,
            hover_data=[
                c for c in [
                    "name",
                    "host_name",
                    "neighbourhood"
                ]
                if has(c)
            ],
            title="Price vs Review Rating",
            opacity=0.55
        )

        fig.update_layout(
            **CHART,
            height=440
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ==================================================
# DATA PREVIEW AND DOWNLOAD
# ==================================================

with st.expander("📋 View Filtered Data"):

    st.dataframe(
        filtered.head(1000),
        use_container_width=True,
        height=350
    )

    st.caption(
        "Showing first 1,000 filtered rows."
    )

    st.download_button(
        "⬇️ Download Filtered Data as CSV",
        data=filtered.to_csv(
            index=False
        ).encode("utf-8"),
        file_name="airbnb_filtered_data.csv",
        mime="text/csv"
    )


# ---------------- FOOTER ----------------

st.markdown("---")

st.caption(
    "Built with Streamlit + Plotly | Airbnb Analytics Dashboard"
)
