# Duplicate-news-to-market-volatility

A Streamlit app that explores the relationship between duplicate/redundant news coverage and stock market volatility. It pulls recent news headlines using the GNews API, identifies similar headlines using the fuzzy duplicate library, and compares their frequency against the S&P 500's short-term volatility.

---

## 🔍 What It Does

- Fetches recent stock market news headlines using [GNews](https://github.com/ranahaani/GNews).
- Uses fuzzy string matching to count redundant or duplicated news headlines per day.
- Downloads historical S&P 500 data and calculates rolling 5-day volatility.
- Visualizes both trends side-by-side for any date range you choose.

---

