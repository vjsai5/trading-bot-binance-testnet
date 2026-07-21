# Binance Futures Testnet Trading Bot

A small, structured Python app that places **MARKET**, **LIMIT**, and (bonus) **STOP-LIMIT**
orders on **Binance USDT-M Futures Testnet**, usable from either a CLI or an advanced
Streamlit dashboard. Both front ends share the same core `bot/` package, so there is exactly
one implementation of the order logic, validation, and logging.

```
trading_bot/
  bot/
    __init__.py
    client.py         # signed REST client for Binance Futures Testnet
    orders.py         # OrderService: validation + client orchestration + summaries
    validators.py     # input validation (symbol, side, type, qty, price, stop price)
    logging_config.py # rotating file + console logging setup
  cli.py               # argparse CLI entry point
  streamlit_app.py      # advanced Streamlit UI (same bot/ package underneath)
  requirements.txt
  .env.example
  logs/
    trading_bot.log    # created on first run
```

## 1. Setup

### 1.1 Create a Binance Futures Testnet account
1. Go to https://testnet.binancefuture.com and log in with a GitHub account.
2. Generate an **API Key** and **API Secret** from the testnet dashboard.
3. (Optional) Use the testnet faucet to top up your paper USDT balance.

### 1.2 Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1.3 Configure credentials
Copy `.env.example` to `.env` and fill in your testnet keys, **or** export them directly:
```bash
cp .env.example .env
# then edit .env
```
```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```
The CLI reads `BINANCE_API_KEY` / `BINANCE_API_SECRET` from the environment automatically
(or accepts `--api-key` / `--api-secret` flags). The Streamlit app lets you paste them
directly into the sidebar (masked input fields) for convenience, or pre-fills them from
the same environment variables if set.

## 2. Running

### 2.1 CLI
```bash
# Market order
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Limit order
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 61500

# Bonus: Stop-Limit order
python cli.py --symbol BTCUSDT --side BUY --type STOP --quantity 0.01 \
              --price 61000 --stop-price 60900
```
Each run prints the order request summary, the raw response fields (`orderId`, `status`,
`executedQty`, `avgPrice`), and a clear `SUCCESS` / `FAILED` line, and appends a structured
entry to `logs/trading_bot.log`.

### 2.2 Streamlit UI
```bash
streamlit run streamlit_app.py
```
Features:
- **Sidebar** — connect/disconnect with API key/secret, live account balance (USDT wallet
  + available balance), connection status indicator.
- **Place Order tab** — form-based order entry (symbol, side, type, quantity, price,
  stop price, time-in-force), with a live result panel showing status pills, metrics,
  and the raw request/response JSON.
- **Order History tab** — running session table of every order placed, with summary
  metrics (total / buy / sell / failed) and a CSV export button.
- **Market Data tab** — live price lookup for any symbol, plus an open orders viewer.
- **Logs tab** — in-app viewer for `logs/trading_bot.log` with level filtering, a line
  count slider, and a download button for the full log file.

## 3. Assumptions

- Orders are placed against **Binance Futures Testnet (USDT-M)** only
  (`https://testnet.binancefuture.com`); the base URL is configurable but not intended
  for production/mainnet use with this codebase as-is.
- Only `GTC` / `IOC` / `FOK` time-in-force values are supported, matching what the
  MARKET/LIMIT/STOP endpoints accept.
- `STOP` (stop-limit) is implemented as the bonus third order type. `reduceOnly` is
  supported in the client layer but not exposed in the CLI/UI to keep the required
  surface area minimal.
- Quantity/price precision (`stepSize` / `tickSize` per symbol) is **not** auto-rounded —
  the user is expected to enter values valid for the chosen symbol's filters, matching
  the "accept and validate user input" requirement rather than doing exchange-info
  auto-formatting.
- Network calls use a 10s timeout and a 5000ms `recvWindow`; both are configurable via
  `BinanceFuturesClient(...)` constructor arguments if needed.
- The bundled `logs/trading_bot.log` sample was generated against a **mocked** client
  response (network access wasn't available in the environment used to prepare this
  submission) so the two required example entries (one MARKET, one LIMIT) are present
  in the correct format. Running the CLI or Streamlit app against your own Testnet
  keys will append real, live order logs in the exact same structure.

## 4. Error handling & logging

- **Validation errors** (bad symbol, missing price on LIMIT, non-numeric quantity, etc.)
  are caught before any network call and reported clearly, both on screen and in the log
  file at `WARNING` level.
- **API errors** (Binance returns a 4xx/5xx with a `code`/`msg` body) raise
  `BinanceAPIError` and are logged at `ERROR` level with the Binance error code and
  message preserved.
- **Network errors** (timeouts, connection failures) raise `BinanceNetworkError` and are
  logged separately so they're distinguishable from API-level rejections.
- All raw requests and responses are logged at `DEBUG` level to the file handler (not the
  console, to keep console output clean) so the full request/response trail is always
  auditable in `logs/trading_bot.log`.

## 5. Running tests / a quick sanity check

There's no separate test suite, but you can validate the wiring without hitting the
network:
```bash
python -c "
from bot.validators import validate_order_request
print(validate_order_request('btcusdt','buy','market',0.01))
"
```

