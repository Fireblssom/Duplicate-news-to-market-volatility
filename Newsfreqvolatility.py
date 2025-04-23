import streamlit as st
import datetime
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from gnews import GNews
from rapidfuzz import fuzz

# Returns a series with the number of fuzzy duplicate news titles per day
def get_duplicate_news(start, end, threshold=35):
    news_api = GNews()
    news_api.start_date = (start.year, start.month, start.day)
    news_api.end_date = (end.year, end.month, end.day)
    news_api.max_results = 100

    raw_results = news_api.get_news("stock market")
    if not raw_results:
        raise Exception("No news data found for given range.")

    df = pd.DataFrame(raw_results)
    df['published date'] = pd.to_datetime(df['published date']).dt.date
    df = df[(df['published date'] >= start) & (df['published date'] <= end)]

    daily_titles = df.groupby('published date')['title'].apply(list)
    duplicate_counts = {}

    for date, titles in daily_titles.items():
        count = 0
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                if fuzz.token_sort_ratio(titles[i], titles[j]) >= threshold:
                    count += 1
        duplicate_counts[date] = count

    all_days = pd.date_range(start, end)
    return pd.Series([duplicate_counts.get(day.date(), 0) for day in all_days], index=all_days)

# Returns rolling 5-day volatility for the S&P 500
def get_sp500_volatility(start, end):
    df = yf.download('^GSPC', start=start, end=end, auto_adjust=True)
    df['Return'] = df['Close'].pct_change()
    df['Volatility'] = df['Return'].rolling(window=5).std()
    return df['Volatility']

# Creates the combined plot
def create_plot(news_data, volatility_data):
    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax1.plot(news_data.index, news_data.values, color='red', label='Duplicate News')
    ax1.set_ylabel('Duplicate News', color='red')
    ax1.tick_params(axis='y', labelcolor='red')

    ax2 = ax1.twinx()
    ax2.plot(volatility_data.index, volatility_data.values, color='blue', label='Volatility')
    ax2.set_ylabel('S&P 500 Volatility', color='blue')
    ax2.tick_params(axis='y', labelcolor='blue')

    ax1.set_xlabel('Date')
    fig.tight_layout()
    return fig

# App interface
st.title("News Redundancy vs S&P 500 Volatility")

st.sidebar.header("Date Range")
today = datetime.date.today()
start = st.sidebar.date_input("Start", today - datetime.timedelta(days=30))
end = st.sidebar.date_input("End", today)

if start > end:
    st.warning("Start date must be before end date.")
else:
    if st.button("Generate Plot"):
        with st.spinner("Loading data..."):
            try:
                news_series = get_duplicate_news(start, end)
                vol_series = get_sp500_volatility(start, end)
                chart = create_plot(news_series, vol_series)
                st.pyplot(chart)
                st.markdown("""
                    **Explanation of the Axes**:
                    - **X-axis**: Date range (from start date to end date). It shows the timeline of the data.
                    - **Left Y-axis (Red)**: The number of duplicate news articles on a given day. Higher values indicate more redundancy in news stories.
                    - **Right Y-axis (Blue)**: The rolling 5-day volatility of the S&P 500 index, representing market price fluctuations over the selected period.
                """)
            
            except Exception as e:
                st.error(f"Something went wrong: {e}")
