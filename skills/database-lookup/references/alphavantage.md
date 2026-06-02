# Alpha Vantage API Reference

## Overview
Alpha Vantage provides free APIs for real-time and historical stock prices, forex rates, cryptocurrency data, technical indicators, and fundamental data (earnings, balance sheets, income statements). Covers global equities, ETFs, mutual funds, and commodities.

## Base URL
```
https://www.alphavantage.co/query
```

All requests use a single endpoint with `function` parameter to select the data type.

## Authentication
- **API Key: REQUIRED.** Get a free key at https://www.alphavantage.co/support/#api-key
- Pass as query parameter: `&apikey=YOUR_KEY`

## Rate Limits
- **Free tier:** 25 requests per day. 5 calls per minute (as of late 2024; previously was 5/min + 500/day).
- **Premium tiers** available for higher limits (30, 75, 150+ calls/min).
- Exceeding limits returns a polite JSON message, not an error code.

---

## Key Endpoints (by `function` parameter)

### 1. Stock Time Series

#### Intraday
```
GET /query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&apikey={key}
```
| Parameter | Required | Values |
|-----------|----------|--------|
| `symbol` | Yes | Ticker symbol (e.g., `AAPL`, `MSFT`) |
| `interval` | Yes | `1min`, `5min`, `15min`, `30min`, `60min` |
| `outputsize` | No | `compact` (last 100 points, default) or `full` (full history) |
| `adjusted` | No | `true` (default) or `false` |
| `datatype` | No | `json` (default) or `csv` |

**Example:**
```
https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=AAPL&interval=5min&apikey=YOUR_KEY
```

#### Daily
```
GET /query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=YOUR_KEY
```

#### Daily (Adjusted for splits/dividends)
```
GET /query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=AAPL&outputsize=full&apikey=YOUR_KEY
```

#### Weekly / Monthly
```
GET /query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=AAPL&apikey=YOUR_KEY
GET /query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol=AAPL&apikey=YOUR_KEY
```

**Response (Daily):**
```json
{
  "Meta Data": {
    "1. Information": "Daily Prices (open, high, low, close) and Volumes",
    "2. Symbol": "AAPL",
    "3. Last Refreshed": "2024-11-01",
    "4. Output Size": "Compact",
    "5. Time Zone": "US/Eastern"
  },
  "Time Series (Daily)": {
    "2024-11-01": {
      "1. open": "228.6900",
      "2. high": "229.8600",
      "3. low": "225.8200",
      "4. close": "228.5200",
      "5. volume": "50423432"
    },
    "2024-10-31": {
      "1. open": "229.3400",
      "2. high": "230.2000",
      "3. low": "226.3700",
      "4. close": "227.5500",
      "5. volume": "51235678"
    }
  }
}
```

---

### 2. Stock Search (Symbol Lookup)
```
GET /query?function=SYMBOL_SEARCH&keywords={query}&apikey={key}
```

**Example:**
```
https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=microsoft&apikey=YOUR_KEY
```

**Response:**
```json
{
  "bestMatches": [
    {
      "1. symbol": "MSFT",
      "2. name": "Microsoft Corporation",
      "3. type": "Equity",
      "4. region": "United States",
      "5. marketOpen": "09:30",
      "6. marketClose": "16:00",
      "7. timezone": "UTC-04",
      "8. currency": "USD",
      "9. matchScore": "1.0000"
    }
  ]
}
```

---

### 3. Global Quote (Real-Time Price)
```
GET /query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_KEY
```

Returns latest price, volume, change, change percent for a single symbol.

---

### 4. Forex (FX) Rates

#### Real-Time Exchange Rate
```
GET /query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=EUR&apikey=YOUR_KEY
```

#### FX Time Series
```
GET /query?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey=YOUR_KEY
GET /query?function=FX_WEEKLY&from_symbol=EUR&to_symbol=USD&apikey=YOUR_KEY
GET /query?function=FX_MONTHLY&from_symbol=EUR&to_symbol=USD&apikey=YOUR_KEY
GET /query?function=FX_INTRADAY&from_symbol=EUR&to_symbol=USD&interval=5min&apikey=YOUR_KEY
```

---

### 5. Cryptocurrency

#### Real-Time Exchange Rate
```
GET /query?function=CURRENCY_EXCHANGE_RATE&from_currency=BTC&to_currency=USD&apikey=YOUR_KEY
```

#### Crypto Time Series
```
GET /query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey=YOUR_KEY
GET /query?function=DIGITAL_CURRENCY_WEEKLY&symbol=BTC&market=USD&apikey=YOUR_KEY
GET /query?function=DIGITAL_CURRENCY_MONTHLY&symbol=BTC&market=USD&apikey=YOUR_KEY
```

---

### 6. Technical Indicators
```
GET /query?function={INDICATOR}&symbol={symbol}&interval={interval}&time_period={n}&series_type={type}&apikey={key}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `function` | Yes | Indicator name (see list below) |
| `symbol` | Yes | Ticker symbol |
| `interval` | Yes | `1min`, `5min`, `15min`, `30min`, `60min`, `daily`, `weekly`, `monthly` |
| `time_period` | Yes* | Number of data points for calculation (e.g., 14 for RSI) |
| `series_type` | Yes* | `close`, `open`, `high`, `low` |

*Required for most indicators; some (like MACD, BBANDS) have additional parameters.

**Common Indicator Functions:**
`SMA`, `EMA`, `WMA`, `DEMA`, `TEMA`, `VWAP`, `RSI`, `MACD`, `STOCH`, `ADX`, `CCI`, `AROON`, `BBANDS`, `AD`, `OBV`, `ATR`, `WILLR`, `MOM`

**Example -- RSI (14-day):**
```
https://www.alphavantage.co/query?function=RSI&symbol=AAPL&interval=daily&time_period=14&series_type=close&apikey=YOUR_KEY
```

**Example -- MACD:**
```
https://www.alphavantage.co/query?function=MACD&symbol=AAPL&interval=daily&series_type=close&apikey=YOUR_KEY
```

---

### 7. Fundamental Data

#### Company Overview
```
GET /query?function=OVERVIEW&symbol=AAPL&apikey=YOUR_KEY
```
Returns: market cap, PE ratio, EPS, dividend yield, 52-week high/low, sector, description, and ~60 other fields.

#### Income Statement
```
GET /query?function=INCOME_STATEMENT&symbol=AAPL&apikey=YOUR_KEY
```

#### Balance Sheet
```
GET /query?function=BALANCE_SHEET&symbol=AAPL&apikey=YOUR_KEY
```

#### Cash Flow
```
GET /query?function=CASH_FLOW&symbol=AAPL&apikey=YOUR_KEY
```

#### Earnings
```
GET /query?function=EARNINGS&symbol=AAPL&apikey=YOUR_KEY
```

Returns both annual and quarterly earnings (EPS, estimated EPS, surprise).

---

### 8. Commodities & Economic Indicators
```
GET /query?function=WTI&interval=monthly&apikey=YOUR_KEY
GET /query?function=BRENT&interval=monthly&apikey=YOUR_KEY
GET /query?function=NATURAL_GAS&interval=monthly&apikey=YOUR_KEY
GET /query?function=COPPER&interval=monthly&apikey=YOUR_KEY
GET /query?function=ALUMINUM&interval=monthly&apikey=YOUR_KEY
GET /query?function=WHEAT&interval=monthly&apikey=YOUR_KEY
GET /query?function=CORN&interval=monthly&apikey=YOUR_KEY
GET /query?function=COTTON&interval=monthly&apikey=YOUR_KEY
GET /query?function=SUGAR&interval=monthly&apikey=YOUR_KEY
GET /query?function=COFFEE&interval=monthly&apikey=YOUR_KEY
```

Economic indicators:
```
GET /query?function=REAL_GDP&interval=quarterly&apikey=YOUR_KEY
GET /query?function=CPI&interval=monthly&apikey=YOUR_KEY
GET /query?function=INFLATION&apikey=YOUR_KEY
GET /query?function=RETAIL_SALES&apikey=YOUR_KEY
GET /query?function=UNEMPLOYMENT&apikey=YOUR_KEY
GET /query?function=FEDERAL_FUNDS_RATE&interval=monthly&apikey=YOUR_KEY
GET /query?function=TREASURY_YIELD&interval=monthly&maturity=10year&apikey=YOUR_KEY
```

---

## Notes
- All values are returned as strings in JSON.
- JSON keys use numbered prefixes (e.g., `"1. open"`, `"2. high"`).
- Time series data is keyed by date/timestamp strings, not arrays.
- When rate limited, the API returns: `{"Note": "Thank you for using Alpha Vantage! ..."}`
- For `outputsize=full`, daily data goes back 20+ years.
- The `datatype=csv` option returns simpler CSV output for any endpoint.
- Free tier is very restrictive (25/day). For production use, a premium key is recommended.
