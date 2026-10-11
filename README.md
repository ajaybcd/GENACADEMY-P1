# Portfolio Lens

A Streamlit US stock portfolio dashboard with validated CSV uploads, FIFO accounting, market prices, allocation, historical value, XIRR and grounded Groq chat.

## Run

Use Python 3.10 or later. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The offline demo works without external credentials. Disable it after uploading your CSV to request real prices. Download the included sample from the sidebar. For AI, enter your Groq API key in the sidebar or set `GROQ_API_KEY` in your environment or `.streamlit/secrets.toml`. `GROQ_MODEL` is optional; the model can also be changed in the sidebar. Never commit secrets.

## CSV contract

Required fields: `date,symbol,action,quantity,price`; optional `fees` defaults to zero. Dates use YYYY-MM-DD. BUY/SELL quantities and USD prices must be positive. Fees must be nonnegative. Future dates, nonfinite numbers and sales exceeding owned shares are rejected. Same-day transactions use CSV order; duplicate rows are counted as supplied, so remove accidental duplicates before uploading.

Accounting uses FIFO with purchase fees in basis and sale fees deducted from proceeds. Total gain equals remaining market value plus net sale proceeds minus total purchases. Return percentage divides that gain by total purchase outflows. XIRR uses dated cash flows and a terminal valuation, reports a unique numerical root within its search range, and otherwise displays unavailable. Closed positions need no quote. Unpriced open holdings suppress overall value and return metrics; allocation is labeled partial.

Daily history uses unadjusted closing prices, forward-filled only after a quote exists. This app excludes dividends, idle cash, taxes, currency conversion, transfers and short positions. Corporate actions are not applied automatically: transaction quantities and prices must be normalized for stock splits. Returns therefore reflect only supplied trades and holdings prices. It is an analytical prototype, not tax-lot reporting software.

Prices are cached for 15 minutes; the sidebar refresh clears market cache. Quote dates and stale quotes are displayed. Network failures leave affected holdings unpriced. Uploaded transactions stay in session memory; market history is cached across sessions. AI is optional and sends the complete validated transaction data and computed context to Groq only on explicit summary/chat actions. Large portfolios may exceed the model context limit; API errors are handled without exposing credentials. Chat resets when uploaded data, prices or model change.

## Verify

```powershell
python -m unittest -v
```

Integration references: [Streamlit uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader), [yfinance history](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html), [Groq chat API](https://console.groq.com/docs/text-chat).
