import duckdb as db
import streamlit as st
import plotly.express as px
from datetime import date
from millify import millify

# Define constants
CURRENT_DATE = date(2019, 9, 15)  # Current date for data filtering
current_year = CURRENT_DATE.year  # Extract the current year
current_month = CURRENT_DATE.month  # Extract the current month

# Read data
data = db.read_csv("Sales_Product_Combined.csv")  # Load sales data from CSV file

# Define SQL query functions

def get_sales_data(current_date):
    """
    Generates an SQL query to retrieve sales data up to the specified date.

    Args:
        current_date (date): The current date for filtering sales data.

    Returns:
        str: The SQL query string.
    """
    return f"""
    SELECT
        "Order Date",
        DAY("Order Date") AS "Order Day",
        STRFTIME("Order Date", '%B %Y') AS "Order Month",
        STRFTIME("Order Date", '%Y%m')::INT AS "MonthYearSort",
        "City",
        "Product Type",
        SUM("Quantity Ordered") AS "Quantity Ordered",
        ROUND(SUM(REPLACE("Price", ',', '')::FLOAT), 2) AS "Price"
    FROM
        data
    WHERE
        "Order Date" < '{current_date}'
    GROUP BY ALL
    """

def get_cumulative_sales():
    """
    Generates an SQL query to calculate cumulative sales.

    Returns:
        str: The SQL query string.
    """
    return """
    SELECT
        "Order Day",
        "Order Month",
        SUM("Price") OVER (PARTITION BY "Order Month" ORDER BY "Order Day") AS "Cumulative Price"
    FROM
        filtered_sales
    ORDER BY
        "Order Date"
    """

def get_cities():
    """
    Generates an SQL query to retrieve distinct cities. 'All Cities' is added at the top for holistic views.

    Returns:
        str: The SQL query string.
    """
    return """
    WITH cities AS (
        SELECT '  All Cities' AS "City"
        UNION
        SELECT DISTINCT "City"
        FROM db_dataset
    )
    SELECT * FROM cities ORDER BY "City"
    """

def get_product_types():
    """
    Generates an SQL query to retrieve distinct product types.

    Returns:
        str: The SQL query string.
    """
    return """
    SELECT DISTINCT "Product Type"
    FROM db_dataset
    """

def get_months():
    """
    Generates an SQL query to retrieve distinct order months and their sort order.

    Returns:
        str: The SQL query string.
    """
    return """
    SELECT DISTINCT "Order Month", "MonthYearSort"
    FROM db_dataset
    ORDER BY "MonthYearSort"
    """

# Execute SQL queries
db_dataset = db.sql(get_sales_data(current_date=CURRENT_DATE))
db_cities = db.sql(get_cities())
db_product_types = db.sql(get_product_types())
db_months = db.sql(get_months())

# Define color mapping for months
months_list = [
    "January", "February", "March", "April", "May", "June", "July", 
    "August", "September", "October", "November", "December"
]
color_discrete_map = {f"{month} {current_year}": 'grey' for month in months_list}
color_discrete_map[f"{months_list[current_month - 1]} {current_year}"] = 'red'  # Highlight current month in red
if current_month > 1:
    color_discrete_map[f"{months_list[current_month - 2]} {current_year}"] = 'orange'  # Highlight previous month in orange

# Streamlit page configuration
st.set_page_config(layout="wide")

# Sidebar filters
selected_city = st.sidebar.selectbox("Select a city", db_cities.df()["City"].tolist())

# Apply filters to dataset
filtered_sales = db_dataset
if selected_city != "  All Cities":
    filtered_sales = db.sql(f"""
    SELECT * FROM filtered_sales WHERE "City" = '{selected_city}'
    """)

mtd_filtered_sales = db.sql(f"""
    SELECT * FROM filtered_sales WHERE DATE_TRUNC('month', "Order Date") = DATE_TRUNC('month', '{CURRENT_DATE}'::DATE)
""")

# KPIs calculation
kpi_sales_ytd = db.sql(f"""SELECT SUM("Price") AS "Price" FROM filtered_sales""").df()["Price"].iloc[0]
kpi_sales_qty_ytd = db.sql(f"""SELECT SUM("Quantity Ordered") AS "Quantity Ordered" FROM filtered_sales""").df()["Quantity Ordered"].iloc[0]
kpi_sales_mtd = db.sql(f"""SELECT SUM("Price") AS "Price" FROM mtd_filtered_sales""").df()["Price"].iloc[0]
kpi_sales_qty_mtd = db.sql(f"""SELECT SUM("Quantity Ordered") AS "Quantity Ordered" FROM mtd_filtered_sales""").df()["Quantity Ordered"].iloc[0]

# Create a histogram of orders by month using Plotly
hist_order_by_month = px.histogram(
    filtered_sales.df(), 
    x="Order Month", 
    y="Price",
    category_orders={"Order Month": db_months.df()["Order Month"], "Product Type": db_product_types.df()["Product Type"]},
    facet_row="Product Type",
    color="Order Month",
    color_discrete_map=color_discrete_map
).update_layout(height=700).update_yaxes(showticklabels=False, title="").for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

# Create a line chart of cumulative sales by day using Plotly
line_agg_sales = db.sql(get_cumulative_sales())
line_order_by_month = px.line(
    line_agg_sales.df(), 
    x="Order Day", 
    y="Cumulative Price", 
    color="Order Month", 
    color_discrete_map=color_discrete_map
).update_layout(height=700, showlegend=False)

# Layout the Streamlit dashboard
st.title(f"Executive Sales Dashboard - {selected_city}")

# KPI Section
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("YTD Sales $", millify(kpi_sales_ytd, precision=2))
with kpi2:
    st.metric("YTD Sales Qty", millify(kpi_sales_qty_ytd, precision=2))
with kpi3:
    st.metric("MTD Sales $", millify(kpi_sales_mtd, precision=2))
with kpi4:
    st.metric("MTD Sales Qty", millify(kpi_sales_qty_mtd, precision=2))

# Middle Section
main1, main2 = st.columns((1, 2))
with main1:
    st.plotly_chart(line_order_by_month, use_container_width=True)
with main2:
    st.plotly_chart(hist_order_by_month, use_container_width=True)

# Bottom Section
bot1, bot2, bot3, bot4 = st.columns(4)
with bot1:
    pass
with bot2:
    pass
with bot3:
    pass
with bot4:
    st.write(f"Effective as at {CURRENT_DATE.strftime('%d %B %Y')}")