import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
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

# Optional: Custom start dates for dividend tracking per ticker (if bought mid-year)
custom_div_start_dates = {}

tickers = list(portfolio_shares.keys())
today = datetime.now()
end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')

# ==========================================
# 2. FETCH DATA & CALCULATE
# ==========================================
with st.spinner('Fetching live ETF market data...'):
    df_all = yf.download(tickers, start="2025-12-31", end=end_date, actions=True, progress=False)

    if isinstance(df_all.columns, pd.MultiIndex):
        df_close = df_all['Close'].copy()
        df_divs = df_all['Dividends'].copy()
    else:
        df_close = df_all[['Close']].copy()
        df_divs = df_all[['Dividends']].copy()

    # Fill missing price gaps
    df_close = df_close.ffill().bfill()

    latest_date = df_close.index[-1].strftime('%Y-%m-%d')
    prev_date = df_close.index[-2].strftime('%Y-%m-%d')

    latest_prices = df_close.iloc[-1].round(2)
    prev_prices = df_close.iloc[-2].round(2)
    year_start_prices = df_close.loc['2025-12-31'].round(2)

    divs_ytd = pd.Series(index=tickers, dtype='float64')
    for ticker in tickers:
        start_date = custom_div_start_dates.get(ticker, '2026-01-01')
        if ticker in df_divs.columns:
            divs_ytd[ticker] = df_divs[ticker].loc[start_date:].sum()
        else:
            divs_ytd[ticker] = 0.0

    df_portfolio = pd.DataFrame({
        'Shares': pd.Series(portfolio_shares),
        'Latest Price': latest_prices,
        'Prev Price': prev_prices,
        'Divs Recd/Share': divs_ytd.round(2)
    })

    df_portfolio['Position Value ($)'] = df_portfolio['Shares'] * df_portfolio['Latest Price']
    df_portfolio['1-Day Change ($)'] = df_portfolio['Shares'] * (df_portfolio['Latest Price'] - df_portfolio['Prev Price'])
    df_portfolio['1-Day Change %'] = ((df_portfolio['Latest Price'] - df_portfolio['Prev Price']) / df_portfolio['Prev Price']) * 100
    df_portfolio['YTD Return %'] = (((df_portfolio['Latest Price'] + df_portfolio['Divs Recd/Share']) - year_start_prices) / year_start_prices) * 100
    df_portfolio['YTD Divs Total ($)'] = df_portfolio['Shares'] * df_portfolio['Divs Recd/Share']

    total_portfolio_value = df_portfolio['Position Value ($)'].sum()
    total_daily_change_dollars = df_portfolio['1-Day Change ($)'].sum()
    prev_total_value = total_portfolio_value - total_daily_change_dollars
    total_daily_change_pct = (total_daily_change_dollars / prev_total_value) * 100
    total_ytd_dividends = df_portfolio['YTD Divs Total ($)'].sum()

# ==========================================
# 3. DISPLAY STREAMLIT UI METRICS
# ==========================================
col1, col2, col3 = st.columns(3)
col1.metric("Total ETF Portfolio Value", f"${total_portfolio_value:,.2f}")
col2.metric("Today's Change ($)", f"${total_daily_change_dollars:+,.2f}", f"{total_daily_change_pct:+.2f}%")
col3.metric("Data Date", latest_date)

st.divider()

# Display Chart
st.subheader("Position Values & Gain/Loss")
colors = ['#2ca02c' if x >= 0 else '#d62728' for x in df_portfolio['1-Day Change ($)']]
fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.bar(df_portfolio.index, df_portfolio['Position Value ($)'], color=colors, alpha=0.85)

ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
max_val = df_portfolio['Position Value ($)'].max()

for i, bar in enumerate(bars):
    yval = bar.get_height()
    day_change = df_portfolio['1-Day Change ($)'].iloc[i]
    ax.text(bar.get_x() + bar.get_width()/2, yval + (max_val * 0.02), f"${yval:,.0f}\n({day_change:+,.0f})", ha='center', va='bottom', fontsize=7, fontweight='bold')

ax.set_ylim(0, max_val * 1.25)
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.3)
st.pyplot(fig)

st.divider()

# Display Table
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

# Total YTD Dividends Banner below the table
st.markdown(f"### 💰 **Total YTD Dividends Received:** `${total_ytd_dividends:,.2f}`")

# Save static files for background Actions
with open("etf_summary.txt", "w") as f:
    f.write(df_display.to_string())
    f.write(f"\n\nTotal YTD Dividends Received: ${total_ytd_dividends:,.2f}")
plt.savefig("latest_etf_chart.png", dpi=300)
