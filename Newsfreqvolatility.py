import streamlit as st
import datetime
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from gnews import GNews
from rapidfuzz import fuzz
import plotly.graph_objects as go

# Visually highlights similar article headlines
def highlight_similar_titles(titles, threshold=35):
    highlighted_titles = []
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            similarity_score = fuzz.token_sort_ratio(titles[i], titles[j])
            if similarity_score >= threshold:
                highlighted = f"<b>{titles[i]}</b> <i>vs</i> <b>{titles[j]}</b> | Similarity: {similarity_score}%"
                highlighted_titles.append(highlighted)
    return highlighted_titles


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

# Creates the combined interactive plot with Plotly
def create_plot(news_data, volatility_data, chart_type):
    fig = go.Figure()

    # Add news duplicates plot based on selected chart type
    if chart_type == 'Line':
        fig.add_trace(go.Scatter(x=news_data.index, y=news_data.values, mode='lines', name='Duplicate News', line=dict(color='red')))
    elif chart_type == 'Bar':
        fig.add_trace(go.Bar(x=news_data.index, y=news_data.values, name='Duplicate News', marker=dict(color='red')))
    elif chart_type == 'Scatter':
        fig.add_trace(go.Scatter(x=news_data.index, y=news_data.values, mode='markers', name='Duplicate News', marker=dict(color='red')))

    # Add volatility plot based on selected chart type
    if chart_type == 'Line':
        fig.add_trace(go.Scatter(x=volatility_data.index, y=volatility_data.values, mode='lines', name='S&P 500 Volatility', line=dict(color='blue', dash='dot')))
    elif chart_type == 'Bar':
        fig.add_trace(go.Bar(x=volatility_data.index, y=volatility_data.values, name='S&P 500 Volatility', marker=dict(color='blue', opacity=0.5)))

    fig.update_layout(
        title='News Redundancy vs S&P 500 Volatility',
        xaxis_title='Date',
        yaxis_title='Count of Duplicate News',
        yaxis2=dict(
            title='S&P 500 Volatility',
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        template='plotly_dark'
    )
    return fig

# Streamlit interface
st.title("News Redundancy vs S&P 500 Volatility")

st.sidebar.header("Date Range")
today = datetime.date.today()
start = st.sidebar.date_input("Start", today - datetime.timedelta(days=30))
end = st.sidebar.date_input("End", today)

if start > end:
    st.warning("Start date must be before end date.")
else:
    # Chart type selection
    chart_type = None
    if st.sidebar.checkbox('Line Chart', value=True):
        chart_type = 'Line'
    if st.sidebar.checkbox('Bar Chart'):
        chart_type = 'Bar'
    if st.sidebar.checkbox('Scatter Plot'):
        chart_type = 'Scatter'

    if chart_type is None:
        st.warning("Please select a chart type.")

    if st.button("Generate Plot"):
        with st.spinner("Loading data..."):
            try:
                # Fetch and process news and volatility data
                news_series, similar_titles = get_duplicate_news(start, end)
                vol_series = get_sp500_volatility(start, end)
                # Plot data based on selected chart type
                chart = create_plot(news_series, vol_series, chart_type)
                st.plotly_chart(chart)
                
                # Display similar titles
                if similar_titles:
                    st.subheader("Similar Articles Found")
                    for similar_title in similar_titles:
                        st.markdown(similar_title, unsafe_allow_html=True)
                else:
                    st.write("No similar articles found.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")
