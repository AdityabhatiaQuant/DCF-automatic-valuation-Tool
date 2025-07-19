import streamlit as st
import pandas as pd
import numpy as np
from numpy import log, sqrt, exp
import requests
from bs4 import BeautifulSoup
import re

# Function to scrape risk-free rate based on country
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_risk_free_rate(country):
    """
    Scrape 10-year government bond yield as risk-free rate for different countries
    """
    try:
        country_urls = {
            "India": "https://tradingeconomics.com/india/government-bond-yield",
            "USA": "https://tradingeconomics.com/united-states/government-bond-yield", 
            "UK": "https://tradingeconomics.com/united-kingdom/government-bond-yield",
            "Germany": "https://tradingeconomics.com/germany/government-bond-yield",
            "France": "https://tradingeconomics.com/france/government-bond-yield"
        }
        
        if country not in country_urls:
            return 6.0  # Default fallback rate
            
        url = country_urls[country]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the current yield value
        # Trading Economics typically shows the current rate prominently
        rate_element = soup.find('span', {'id': 'p_cur_val'}) or soup.find('div', {'class': 'col-xs-6 col-sm-4 col-md-4 col-lg-3'})
        
        if rate_element:
            rate_text = rate_element.get_text().strip()
            # Extract number from text using regex
            rate_match = re.search(r'(\d+\.?\d*)', rate_text)
            if rate_match:
                return float(rate_match.group(1))
        
        # Fallback: search for any percentage values in the page
        text = soup.get_text()
        percentage_matches = re.findall(r'(\d+\.?\d*)%', text)
        if percentage_matches:
            # Return the first reasonable percentage (between 0 and 20)
            for match in percentage_matches:
                rate = float(match)
                if 0 <= rate <= 20:
                    return rate
        
        # Country-specific fallback rates (approximate current rates)
        fallback_rates = {
            "India": 6.3,
            "USA": 4.4,
            "UK": 4.7,
            "Germany": 2.4,
            "France": 3.0
        }
        return fallback_rates.get(country, 6.0)
        
    except Exception as e:
        st.warning(f"Could not fetch risk-free rate for {country}. Using default rate. Error: {str(e)}")
        # Fallback rates based on recent data
        fallback_rates = {
            "India": 6.3,
            "USA": 4.4,
            "UK": 4.7,
            "Germany": 2.4,
            "France": 3.0
        }
        return fallback_rates.get(country, 6.0)

try:
    st.set_page_config(
        page_title="Automatic DCF Valuation Tool",
        page_icon="💸",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except st.errors.StreamlitAPIException:
    pass  # Handle case where config is already set

# Title and Author
st.markdown("""
<div style='display: flex; justify-content: space-between; align-items: center;'>
    <h2>📊 Automatic DCF Valuation Tool</h2>
    <a href="https://www.linkedin.com/in/adityabhatiaquant" target="_blank" style="text-decoration: none; color: white; font-size: 16px;">
        LinkedIn: Aditya Bhatia
    </a>
</div>
""", unsafe_allow_html=True)

# Sidebar Inputs
with st.sidebar:
    st.header("Company Information")
    company_name = st.text_input("Company Name", value="Example Corp")
    country = st.selectbox("Country of Origin", options=["India", "USA", "UK", "Germany", "France", "Other"])

    st.header("WACC Assumptions")
    
    # Auto-fetch risk-free rate based on country
    if st.button("🔄 Fetch Current Risk-Free Rate"):
        with st.spinner(f"Fetching 10-year government bond yield for {country}..."):
            scraped_rate = get_risk_free_rate(country)
            st.session_state.risk_free_rate = scraped_rate
            st.success(f"Updated risk-free rate for {country}: {scraped_rate:.2f}%")
    
    # Initialize session state if not exists
    if 'risk_free_rate' not in st.session_state:
        st.session_state.risk_free_rate = get_risk_free_rate(country)
    
    risk_free_rate = st.number_input(
        "Risk-Free Rate (%)", 
        min_value=0.0, 
        max_value=20.0, 
        value=st.session_state.risk_free_rate, 
        step=0.1,
        help=f"Current 10-year government bond yield for {country}"
    ) / 100
    beta = st.number_input("Beta", min_value=0.0, max_value=5.0, value=1.2, step=0.1)
    market_risk_premium = st.number_input("Market Risk Premium (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.1) / 100
    cost_of_debt = st.number_input("Cost of Debt (%)", min_value=0.0, max_value=20.0, value=8.0, step=0.1) / 100
    tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, value=25.0, step=0.5) / 100
    equity_ratio = st.slider("Equity Weight (%)", min_value=0, max_value=100, value=70)

# Move debt_ratio calculation outside sidebar
debt_ratio = 100 - equity_ratio

# Set currency symbol based on country
currency_symbol = "₹" if country == "India" else "$" if country == "USA" else "£" if country == "UK" else "€" if country in ["Germany", "France"] else "₹"

# Display summary of inputs
st.subheader("Input Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Risk-Free Rate", f"{risk_free_rate * 100:.2f}%")
col2.metric("Beta", f"{beta:.2f}")
col3.metric("Market Premium", f"{market_risk_premium * 100:.2f}%")
col4.metric("Country", country)

# Store values for use
cost_of_equity = risk_free_rate + beta * market_risk_premium
wacc = (equity_ratio / 100) * cost_of_equity + (debt_ratio / 100) * cost_of_debt * (1 - tax_rate)

st.markdown("---")
st.header("Calculated WACC")
st.write(f"**Cost of Equity:** {cost_of_equity * 100:.2f}%")
st.write(f"**WACC:** {wacc * 100:.2f}%")

st.markdown("---")
st.header("Step 2: Revenue and Cash Flow Projections")

projection_years = st.number_input("Number of Projection Years", min_value=3, max_value=10, value=5, step=1)

# Revenue projection method selection
st.subheader("Revenue Projection Method")
revenue_method = st.radio(
    "Choose how to project revenue:",
    ["Manual Input", "Growth Rate Based"],
    horizontal=True
)

revenue = []
ebitda_margin = []
capex = []
depreciation = []
wc_change = []

# Revenue Projection Method (Growth Rate Based)
if revenue_method == "Growth Rate Based":
    st.subheader("Revenue Growth Projections")
    col1, col2 = st.columns(2)
    
    with col1:
        base_revenue = st.number_input(
            f"Base Year Revenue ({currency_symbol})", 
            value=100000000, 
            step=1000000,
            help="Current year or last year's revenue"
        )
    
    with col2:
        st.write("**Revenue Growth Rates by Year:**")
    
    growth_rates = []
    for i in range(projection_years):
        growth_rate = st.number_input(
            f"Year {i+1} Growth Rate (%)", 
            min_value=-50.0, 
            max_value=100.0, 
            value=10.0 - i*1.0,  # Decreasing growth rate over time
            step=0.5,
            key=f"growth_{i}"
        ) / 100
        growth_rates.append(growth_rate)
    
    # Calculate revenue based on growth rates
    current_revenue = base_revenue
    for i in range(projection_years):
        current_revenue = current_revenue * (1 + growth_rates[i])
        revenue.append(current_revenue)
    
    # Show calculated revenues (formatted)
    st.subheader("Calculated Revenue Projections")
    revenue_df = pd.DataFrame({
        "Year": [f"Year {i+1}" for i in range(projection_years)],
        "Growth Rate": [f"{gr*100:.1f}%" for gr in growth_rates],
        f"Revenue ({currency_symbol})": [f"{currency_symbol}{r:,.0f}" for r in revenue]
    })
    st.dataframe(revenue_df, use_container_width=True)

st.subheader("Enter Other Projections")
for i in range(projection_years):
    st.markdown(f"**Year {i+1}**")
    
    if revenue_method == "Manual Input":
        col1, col2, col3, col4, col5 = st.columns(5)
        revenue.append(col1.number_input(f"Revenue ({currency_symbol}) - Year {i+1}", key=f"rev_{i}", value=100000000 + i*10000000))
        ebitda_margin.append(col2.slider(f"EBITDA Margin % - Year {i+1}", min_value=0.0, max_value=100.0, value=25.0, step=0.5, key=f"margin_{i}") / 100)
        capex.append(col3.number_input(f"CapEx ({currency_symbol}) - Year {i+1}", key=f"capex_{i}", value=10000000 + i*1000000))
        depreciation.append(col4.number_input(f"Depreciation ({currency_symbol}) - Year {i+1}", key=f"dep_{i}", value=5000000 + i*500000))
        wc_change.append(col5.number_input(f"Change in WC ({currency_symbol}) - Year {i+1}", key=f"wc_{i}", value=2000000 + i*500000))
    else:
        # For growth rate method, only show other inputs (revenue already calculated)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"Revenue ({currency_symbol})", f"{revenue[i]:,.0f}")
        ebitda_margin.append(col2.slider(f"EBITDA Margin % - Year {i+1}", min_value=0.0, max_value=100.0, value=25.0, step=0.5, key=f"margin_{i}") / 100)
        capex.append(col3.number_input(f"CapEx ({currency_symbol}) - Year {i+1}", key=f"capex_{i}", value=10000000 + i*1000000))
        depreciation.append(col4.number_input(f"Depreciation ({currency_symbol}) - Year {i+1}", key=f"dep_{i}", value=5000000 + i*500000))
        wc_change.append(st.number_input(f"Change in WC ({currency_symbol}) - Year {i+1}", key=f"wc_{i}", value=2000000 + i*500000))

# Calculations for Free Cash Flow
ebitda = [rev * margin for rev, margin in zip(revenue, ebitda_margin)]
ebit = [e - d for e, d in zip(ebitda, depreciation)]  # EBIT = EBITDA - Depreciation
nopat = [e * (1 - tax_rate) for e in ebit]  # NOPAT = EBIT * (1 - Tax Rate)
fcf = [nopat + d - c - wc for nopat, d, c, wc in zip(nopat, depreciation, capex, wc_change)]  # Add back depreciation

# Projected Free Cash Flows (formatted)
st.markdown("---")
st.header("Projected Free Cash Flows")
df_proj = pd.DataFrame({
    "Year": [f"Year {i+1}" for i in range(projection_years)],
    f"Revenue ({currency_symbol})": [f"{currency_symbol}{r:,.0f}" for r in revenue],
    f"EBITDA ({currency_symbol})": [f"{currency_symbol}{e:,.0f}" for e in ebitda],
    f"CapEx ({currency_symbol})": [f"{currency_symbol}{c:,.0f}" for c in capex],
    f"Depreciation ({currency_symbol})": [f"{currency_symbol}{d:,.0f}" for d in depreciation],
    f"Change in WC ({currency_symbol})": [f"{currency_symbol}{wc:,.0f}" for wc in wc_change],
    f"Free Cash Flow ({currency_symbol})": [f"{currency_symbol}{f:,.0f}" for f in fcf]
})
st.dataframe(df_proj, use_container_width=True)

st.markdown("---")
st.header("Step 3: Terminal Value and DCF Valuation")

# Terminal Value and DCF Valuation
st.subheader("Terminal Value Assumptions")
terminal_growth_rate = st.number_input(
    "Terminal Growth Rate (%)",
    min_value=0.0,
    max_value=8.0,
    value=3.0,
    step=0.1
) / 100

# Calculate Terminal Value (Gordon Growth Model)
last_fcf = fcf[-1] if len(fcf) > 0 else 0
if wacc > terminal_growth_rate:
    terminal_value = last_fcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
else:
    terminal_value = np.nan

st.write(f"**Calculated Terminal Value:** {currency_symbol}{terminal_value:,.0f}")

# Discount Free Cash Flows
discount_factors = [(1 + wacc) ** (i + 1) for i in range(projection_years)]
discounted_fcf = [fcf[i] / discount_factors[i] for i in range(projection_years)]

# Discount Terminal Value
discounted_terminal_value = terminal_value / ((1 + wacc) ** projection_years)

# Enterprise Value
enterprise_value = sum(discounted_fcf) + discounted_terminal_value

st.write(f"**Enterprise Value (DCF):** {currency_symbol}{enterprise_value:,.0f}")

st.markdown("---")
st.header("Bear, Base, and Bull Case DCF Valuation")

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Bear Case")
    wacc_bear = st.number_input("WACC (%) - Bear", min_value=0.0, max_value=15.0, value=wacc*100+1, step=0.1) / 100
    tg_bear = st.number_input("Terminal Growth (%) - Bear", min_value=0.0, max_value=8.0, value=terminal_growth_rate*100-1, step=0.1) / 100
with col2:
    st.subheader("Base Case")
    wacc_base = wacc
    tg_base = terminal_growth_rate
    st.write(f"WACC: {wacc_base*100:.2f}%")
    st.write(f"Terminal Growth: {tg_base*100:.2f}%")
with col3:
    st.subheader("Bull Case")
    wacc_bull = st.number_input("WACC (%) - Bull", min_value=0.0, max_value=15.0, value=wacc*100-1, step=0.1) / 100
    tg_bull = st.number_input("Terminal Growth (%) - Bull", min_value=0.0, max_value=8.0, value=terminal_growth_rate*100+1, step=0.1) / 100

def calc_dcf(last_fcf, fcf, wacc, tg, years):
    if wacc > tg:
        tv = last_fcf * (1 + tg) / (wacc - tg)
        discount_factors = [(1 + wacc) ** (i + 1) for i in range(years)]
        discounted_fcf = [fcf[i] / discount_factors[i] for i in range(years)]
        discounted_tv = tv / ((1 + wacc) ** years)
        ev = sum(discounted_fcf) + discounted_tv
        return ev
    else:
        return np.nan

ev_bear = calc_dcf(last_fcf, fcf, wacc_bear, tg_bear, projection_years)
ev_base = calc_dcf(last_fcf, fcf, wacc_base, tg_base, projection_years)
ev_bull = calc_dcf(last_fcf, fcf, wacc_bull, tg_bull, projection_years)

st.write(f"**Bear Case Enterprise Value:** {currency_symbol}{ev_bear:,.0f}")
st.write(f"**Base Case Enterprise Value:** {currency_symbol}{ev_base:,.0f}")
st.write(f"**Bull Case Enterprise Value:** {currency_symbol}{ev_bull:,.0f}")

# --- Sensitivity Analysis Section ---
st.markdown("---")
st.header("Sensitivity Analysis")

st.subheader("Select Variables for Sensitivity Analysis")
wacc_range = st.slider(
    "WACC Range (%)",
    min_value=max(0.0, wacc*100-3),
    max_value=15.0,
    value=(max(0.0, wacc*100-1), min(15.0, wacc*100+1)),
    step=0.1
)
terminal_growth_range = st.slider(
    "Terminal Growth Rate Range (%)",
    min_value=0.0,
    max_value=8.0,
    value=(2.0, 4.0),
    step=0.1
)

wacc_values = np.arange(wacc_range[0], wacc_range[1]+0.01, 0.5) / 100
tg_values = np.arange(terminal_growth_range[0], terminal_growth_range[1]+0.01, 0.5) / 100

results = []
for w in wacc_values:
    row = []
    for g in tg_values:
        if w > g:
            tv = last_fcf * (1 + g) / (w - g)
            # Discount TV and FCFs for each WACC
            discount_factors = [(1 + w) ** (i + 1) for i in range(projection_years)]
            discounted_fcf = [fcf[i] / discount_factors[i] for i in range(projection_years)]
            discounted_tv = tv / ((1 + w) ** projection_years)
            ev = sum(discounted_fcf) + discounted_tv
            # Format as currency
            ev_fmt = f"{currency_symbol}{ev:,.0f}"
        else:
            ev_fmt = "-"
        row.append(ev_fmt)
    results.append(row)

sens_df = pd.DataFrame(
    results,
    index=[f"{w*100:.2f}%" for w in wacc_values],
    columns=[f"{g*100:.2f}%" for g in tg_values]
)
st.write("**Enterprise Value Sensitivity Table**")
st.dataframe(sens_df, use_container_width=True)
