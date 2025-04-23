import streamlit as st
import datetime
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
from rapidfuzz import fuzz
from gnews import GNews

# Function to highlight similar parts of the titles
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

    similar_titles_display = []  # Store titles with similarities to display

    for date, titles in daily_titles.items():
        count = 0
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                similarity_score = fuzz.token_sort_ratio(titles[i], titles[j])
                if similarity_score >= threshold:
                    count += 1
                    # Highlight similar titles
                    similar_titles_display.extend(highlight_similar_titles([titles[i], titles[j]], threshold))
        duplicate_counts[date] = count

    all_days = pd.date_range(start, end)
    return pd.Series([duplicate_counts.get(day.date(), 0) for day in all_days], index=all_days), similar_titles_display

# Function to calculate ATR (Average True Range)
def calculate_atr(df, window=14):
    df['H-L'] = df['High'] - df['Low']
    df['H-C'] = abs(df['High'] - df['Close'].shift())
    df['L-C'] = abs(df['Low'] - df['Close'].shift())
    df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=window).mean()
    return df['ATR']

# Function to calculate Historical Volatility (HV)
def calculate_hv(df, window=20):
    df['Return'] = df['Close'].pct_change()
    return df['Return'].rolling(window=window).std() * np.sqrt(252)  # Annualized volatility

# Function to calculate volatility using Bollinger Bands
def calculate_bollinger_bands(df, window=20, multiplier=2):
    df['Moving_Avg'] = df['Close'].rolling(window=window).mean()
    df['Rolling_Std'] = df['Close'].rolling(window=window).std()
    df['Upper_Band'] = df['Moving_Avg'] + (df['Rolling_Std'] * multiplier)
    df['Lower_Band'] = df['Moving_Avg'] - (df['Rolling_Std'] * multiplier)
    df['Volatility'] = (df['Upper_Band'] - df['Lower_Band']) / df['Moving_Avg'] * 100
    return df['Volatility']

# Function to fetch and calculate the volatility based on the selected model
def get_sp500_volatility(start, end, model_type, window=20, multiplier=2):
    df = yf.download('^GSPC', start=start, end=end, auto_adjust=True)
    
    if model_type == 'Standard Deviation of Returns':
        df['Volatility'] = df['Close'].pct_change().rolling(window=window).std()
    
    elif model_type == 'Average True Range (ATR)':
        df['Volatility'] = calculate_atr(df, window)
    
    elif model_type == 'Historical Volatility (HV)':
        df['Volatility'] = calculate_hv(df, window)
    
    elif model_type == 'Bollinger Bands':
        df['Volatility'] = calculate_bollinger_bands(df, window, multiplier)
    
    elif model_type == 'VIX':
        df['Volatility'] = calculate_vix(df)
    
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
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

# Parameters for news similarity threshold
news_threshold = st.sidebar.slider("News Similarity Threshold", min_value=0, max_value=100, value=35, step=1)

# Volatility model selection
model_type = st.sidebar.selectbox(
    "Select Volatility Model", 
    ["Standard Deviation of Returns", "Average True Range (ATR)", "Historical Volatility (HV)", "Bollinger Bands", "VIX"]
)

# Parameters for the selected model
window = st.sidebar.slider("Rolling Window (Days)", min_value=5, max_value=100, value=20)
if model_type == "Bollinger Bands":
    multiplier = st.sidebar.slider("Bollinger Bands Multiplier", min_value=1.0, max_value=3.0, value=2.0, step=0.1)

if start > end:
    st.warning("Start date must be before end date.")
else:
    # Chart type selection with checkboxes
    chart_types = []
    if st.sidebar.checkbox('Line Chart'):
        chart_types.append('Line')
    if st.sidebar.checkbox('Bar Chart'):
        chart_types.append('Bar')
    if st.sidebar.checkbox('Scatter Plot'):
        chart_types.append('Scatter')

    if not chart_types:
        st.warning("Please select at least one chart type.")

    if st.button("Generate Plot"):
        with st.spinner("Loading data..."):
            try:
                # Fetch and process news and volatility data
                news_series, similar_titles = get_duplicate_news(start, end, news_threshold)
                vol_series = get_sp500_volatility(start, end, model_type, window, multiplier)
                
                # Generate the plots for each selected chart type
                for chart_type in chart_types:
                    st.subheader(f"{chart_type} - News Redundancy vs S&P 500 Volatility")
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
