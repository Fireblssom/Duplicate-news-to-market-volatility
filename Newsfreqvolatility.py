import streamlit as st
import datetime
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

# Function to calculate Simple Moving Average (SMA) volatility
def calculate_sma_volatility(df, window=20):
    df['SMA'] = df['Close'].rolling(window=window).mean()
    df['Volatility'] = df['Close'].pct_change().rolling(window=window).std() * np.sqrt(252)  # Annualized volatility
    return df['Volatility']

# Function to fetch and calculate the SMA volatility
def get_sp500_volatility(start, end, window=20):
    df = yf.download('^GSPC', start=start, end=end, auto_adjust=True)
    
    # Calculate the SMA volatility (Simple Moving Average of returns)
    df['Volatility'] = calculate_sma_volatility(df, window)
    
    return df['Volatility']

# Creates the combined interactive plot with Plotly
def create_plot(volatility_data, chart_type):
    fig = go.Figure()

    # Add volatility plot based on selected chart type
    if chart_type == 'Line':
        fig.add_trace(go.Scatter(x=volatility_data.index, y=volatility_data.values, mode='lines', name='S&P 500 Volatility', line=dict(color='blue', dash='dot')))
    elif chart_type == 'Bar':
        fig.add_trace(go.Bar(x=volatility_data.index, y=volatility_data.values, name='S&P 500 Volatility', marker=dict(color='blue', opacity=0.5)))
    elif chart_type == 'Scatter':
        fig.add_trace(go.Scatter(x=volatility_data.index, y=volatility_data.values, mode='markers', name='S&P 500 Volatility', marker=dict(color='blue')))

    fig.update_layout(
        title='S&P 500 Volatility (SMA)',
        xaxis_title='Date',
        yaxis_title='Volatility',
        hovermode='x unified',
        template='plotly_dark'
    )
    return fig

# Streamlit interface
st.title("S&P 500 Volatility (SMA)")

st.sidebar.header("Date Range")
today = datetime.date.today()
start = st.sidebar.date_input("Start", today - datetime.timedelta(days=30))
end = st.sidebar.date_input("End", today)

# Volatility model selection (only SMA here)
window = st.sidebar.slider("Rolling Window (Days)", min_value=5, max_value=100, value=20)

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
                # Fetch and process volatility data
                vol_series = get_sp500_volatility(start, end, window)
                
                # Generate the plots for each selected chart type
                for chart_type in chart_types:
                    st.subheader(f"{chart_type} - S&P 500 Volatility (SMA)")
                    chart = create_plot(vol_series, chart_type)
                    st.plotly_chart(chart)
            except Exception as e:
                st.error(f"Something went wrong: {e}")


