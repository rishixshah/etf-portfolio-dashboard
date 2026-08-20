import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# Page Configuration
st.set_page_config(page_title="ETF Portfolio Dashboard", layout="wide")

st.title("📊 ETF Portfolio Dashboard")

# ==========================================
# 1. PORTFOLIO CONFIGURATION (YOUR ETFs)
# ==========================================
portfolio_shares = {
    'VIG': 751.162,
    'VOO': 2200.489,
    'VTI': 3893.905,
    'JEPI': 4278.788,
    'QQQ': 1095.637,
    'SOXX': 132.604,
    'SPYI': 3709
}

custom_div_start_dates = {}
tickers = list(portfolio_shares.keys())
current_year_start = "2026-01-01"

# ==========================================
# 2. FETCH DIRECT YAHOO FINANCE DATA
# ==========================================
with st.spinner('Pulling live market data from Yahoo Finance...'):
    latest_prices = {}
    prev_prices = {}
    year_start_prices = {}
    divs_ytd = {}

    for ticker in tickers:
        t = yf.Ticker(ticker)

        # 1. Pull historical daily candles for YTD baseline & backup
        hist = t.history(period="ytd", auto_adjust=False)

        # 2. Extract Exact Official Previous Close from Yahoo Finance
        prev_close_val = None
        try:
            info_dict = t.info
            prev_close_val = info_dict.get('regularMarketPreviousClose') or info_dict.get('previousClose')
        except Exception:
            prev_close_val = None

        if not prev_close_val:
            try:
                prev_close_val = t.fast_info.get('regular_market_previous_close') or t.fast_info.get('previousClose')
            except Exception:
                prev_close_val = hist['Close'].iloc[-2] if len(hist) >= 2 else (hist['Close'].iloc[-1] if not hist.empty else 0.0)

        prev_prices[ticker] = round(float(prev_close_val), 2)

        # 3. Extract Live Market Price
        try:
            live_price = t.fast_info.get('lastPrice') or t.fast_info.get('last_price') or t.info.get('regularMarketPrice')
        except Exception:
            live_price = hist['Close'].iloc[-1] if not hist.empty else 0.0

        latest_prices[ticker] = round(float(live_price), 2)

        # 4. Extract Year-Start Baseline Price for YTD Return
        if not hist.empty:
            year_start_prices[ticker] = round(float(hist['Close'].iloc[0]), 2)
        else:
            year_start_prices[ticker] = latest_prices[ticker]

        # 5. Extract Total YTD Cash Dividends
        start_div_date = custom_div_start_dates.get(ticker, current_year_start)
        try:
            div_series = t.dividends
            if not div_series.empty:
                div_series.index = div_series.index.tz_localize(None)
                divs_ytd[ticker] = round(float(div_series.loc[start_div_date:].sum()), 2)
            else:
                divs_ytd[ticker] = 0.0
        except Exception:
            divs_ytd[ticker] = 0.0

    # Build Portfolio DataFrame
    df_portfolio = pd.DataFrame({
        'Shares': pd.Series(portfolio_shares),
        'Latest Price': pd.Series(latest_prices),
        'Prev Price': pd.Series(prev_prices),
        'Divs Recd/Share': pd.Series(divs_ytd)
    })

    # Calculations
    df_portfolio['Position Value ($)'] = df_portfolio['Shares'] * df_portfolio['Latest Price']
    df_portfolio['1-Day Change ($)'] = df_portfolio['Shares'] * (df_portfolio['Latest Price'] - df_portfolio['Prev Price'])
    df_portfolio['1-Day Change %'] = ((df_portfolio['Latest Price'] - df_portfolio['Prev Price']) / df_portfolio['Prev Price']) * 100
    df_portfolio['YTD Return %'] = (((df_portfolio['Latest Price'] + df_portfolio['Divs Recd/Share']) - pd.Series(year_start_prices)) / pd.Series(year_start_prices)) * 100
    df_portfolio['YTD Divs Total ($)'] = df_portfolio['Shares'] * df_portfolio['Divs Recd/Share']

    total_portfolio_value = df_portfolio['Position Value ($)'].sum()
    total_daily_change_dollars = df_portfolio['1-Day Change ($)'].sum()
    prev_total_value = total_portfolio_value - total_daily_change_dollars
    total_daily_change_pct = (total_daily_change_dollars / prev_total_value) * 100 if prev_total_value != 0 else 0.0
    total_ytd_dividends = df_portfolio['YTD Divs Total ($)'].sum()

# ==========================================
# 3. DISPLAY STREAMLIT UI METRICS
# ==========================================
col1, col2, col3 = st.columns(3)
col1.metric("Total ETF Portfolio Value", f"${total_portfolio_value:,.2f}")
col2.metric("Today's Change ($)", f"{'+' if total_daily_change_dollars >= 0 else '-'}${abs(total_daily_change_dollars):,.2f}", f"{total_daily_change_pct:+.2f}%")
col3.metric("Data Source", "Yahoo Finance (Official Quote)")

st.divider()

# Position Values Chart
st.subheader("Position Values & Gain/Loss")
colors = ['#2ca02c' if x >= 0 else '#d62728' for x in df_portfolio['1-Day Change ($)']]
fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.bar(df_portfolio.index, df_portfolio['Position Value ($)'], color=colors, alpha=0.85)

ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
max_val = df_portfolio['Position Value ($)'].max()

for i, bar in enumerate(bars):
    yval = bar.get_height()
    day_change = df_portfolio['1-Day Change ($)'].iloc[i]
    sign = "+" if day_change >= 0 else "-"
    ax.text(bar.get_x() + bar.get_width()/2, yval + (max_val * 0.02), f"${yval:,.0f}\n({sign}${abs(day_change):,.0f})", ha='center', va='bottom', fontsize=7, fontweight='bold')

ax.set_ylim(0, max_val * 1.25)
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.3)
st.pyplot(fig)

st.divider()

# Holdings Summary Table
st.subheader("Holdings Summary")
df_display = df_portfolio.copy()
df_display['Latest Price'] = df_display['Latest Price'].map('${:,.2f}'.format)
df_display['Prev Price'] = df_display['Prev Price'].map('${:,.2f}'.format)
df_display['Position Value ($)'] = df_display['Position Value ($)'].map('${:,.2f}'.format)
df_display['1-Day Change ($)'] = df_display['1-Day Change ($)'].map(lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}")
df_display['1-Day Change %'] = df_display['1-Day Change %'].map('{:+.2f}%'.format)
df_display['YTD Return %'] = df_display['YTD Return %'].map('{:+.2f}%'.format)
df_display['Divs Recd/Share'] = df_display['Divs Recd/Share'].map('${:,.2f}'.format)
df_display['YTD Divs Total ($)'] = df_display['YTD Divs Total ($)'].map('${:,.2f}'.format)

st.dataframe(df_display, use_container_width=True)

# Bottom Dividend Banner
st.markdown(f"### 💰 **Total YTD Dividends Received:** `${total_ytd_dividends:,.2f}`")

# Static export files
with open("etf_summary.txt", "w") as f:
    f.write(df_display.to_string())
    f.write(f"\n\nTotal YTD Dividends Received: ${total_ytd_dividends:,.2f}")
plt.savefig("latest_etf_chart.png", dpi=300)
