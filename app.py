

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from bot.client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from bot.logging_config import setup_logging
from bot.orders import OrderService

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
LOG_PATH = os.path.join("logs", "trading_bot.log")

logger = setup_logging()

st.set_page_config(
    page_title="Futures Testnet Trading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .status-pill {
        display: inline-block; padding: 3px 12px; border-radius: 999px;
        font-size: 0.8rem; font-weight: 600; letter-spacing: 0.03em;
    }
    .status-filled  { background: #133b1f; color: #4ade80; }
    .status-new     { background: #1e2a4a; color: #60a5fa; }
    .status-failed  { background: #3b1414; color: #f87171; }
    .side-buy  { color: #4ade80; font-weight: 700; }
    .side-sell { color: #f87171; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


if "order_history" not in st.session_state:
    st.session_state.order_history = []  # list of dicts for the table
if "client" not in st.session_state:
    st.session_state.client = None
if "connected" not in st.session_state:
    st.session_state.connected = False


def get_status_pill(status: str) -> str:
    status = (status or "").upper()
    cls = "status-new"
    if status in {"FILLED", "PARTIALLY_FILLED"}:
        cls = "status-filled"
    elif status in {"FAILED", "EXPIRED", "REJECTED"}:
        cls = "status-failed"
    return f'<span class="status-pill {cls}">{status or "N/A"}</span>'



with st.sidebar:
    st.title("⚙️ Connection")

    base_url = st.text_input("Base URL", value=DEFAULT_BASE_URL)
    api_key = st.text_input(
        "API Key", value=os.environ.get("BINANCE_API_KEY", ""), type="password"
    )
    api_secret = st.text_input(
        "API Secret", value=os.environ.get("BINANCE_API_SECRET", ""), type="password"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        connect_clicked = st.button("🔌 Connect", use_container_width=True)
    with col_b:
        disconnect_clicked = st.button("Disconnect", use_container_width=True)

    if disconnect_clicked:
        st.session_state.client = None
        st.session_state.connected = False

    if connect_clicked:
        if not api_key or not api_secret:
            st.error("API key and secret are required.")
        else:
            try:
                client = BinanceFuturesClient(api_key, api_secret, base_url=base_url)
                client.ping()
                st.session_state.client = client
                st.session_state.connected = True
                st.success("Connected to Testnet ✅")
            except (BinanceAPIError, BinanceNetworkError, ValueError) as exc:
                st.session_state.connected = False
                st.error(f"Connection failed: {exc}")

    st.divider()

    if st.session_state.connected:
        st.markdown("**Status:** 🟢 Connected")
        if st.button("Refresh Account Info"):
            try:
                info = st.session_state.client.get_account_info()
                usdt = next(
                    (a for a in info.get("assets", []) if a.get("asset") == "USDT"), None
                )
                if usdt:
                    st.metric("USDT Wallet Balance", f"{float(usdt['walletBalance']):.2f}")
                    st.metric("Available Balance", f"{float(usdt['availableBalance']):.2f}")
                else:
                    st.json(info)
            except (BinanceAPIError, BinanceNetworkError) as exc:
                st.error(f"Could not fetch account info: {exc}")
    else:
        st.markdown("**Status:** 🔴 Not connected")

    st.divider()
    st.caption("Logs are written to `logs/trading_bot.log`")


st.title("📈 Binance Futures Testnet — Trading Bot")

tab_order, tab_history, tab_market, tab_logs = st.tabs(
    ["🛒 Place Order", "📒 Order History", "💹 Market Data", "🧾 Logs"]
)


with tab_order:
    if not st.session_state.connected:
        st.info("Connect with your Testnet API key/secret in the sidebar to place orders.")

    left, right = st.columns([1, 1])

    with left:
        with st.form("order_form", clear_on_submit=False):
            st.subheader("New Order")

            c1, c2 = st.columns(2)
            with c1:
                symbol = st.text_input("Symbol", value="BTCUSDT").strip().upper()
                side = st.radio("Side", ["BUY", "SELL"], horizontal=True)
            with c2:
                order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP"])
                time_in_force = st.selectbox(
                    "Time In Force", ["GTC", "IOC", "FOK"],
                    disabled=(order_type == "MARKET"),
                )

            quantity = st.number_input("Quantity", min_value=0.0, value=0.01,
                                        step=0.001, format="%.6f")

            price = None
            stop_price = None
            if order_type in ("LIMIT", "STOP"):
                price = st.number_input("Price", min_value=0.0, value=0.0,
                                         step=0.1, format="%.2f")
            if order_type == "STOP":
                stop_price = st.number_input("Stop Price", min_value=0.0, value=0.0,
                                              step=0.1, format="%.2f")

            submitted = st.form_submit_button(
                "🚀 Place Order", use_container_width=True, type="primary"
            )

        if submitted:
            if not st.session_state.connected:
                st.error("Connect to the API first (see sidebar).")
            else:
                service = OrderService(st.session_state.client)
                with st.spinner("Submitting order to Binance Futures Testnet..."):
                    result = service.submit_order(
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        quantity=quantity,
                        price=price if price else None,
                        stop_price=stop_price if stop_price else None,
                        time_in_force=time_in_force,
                    )

                record = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "symbol": result.request.get("symbol"),
                    "side": result.request.get("side"),
                    "type": result.request.get("order_type"),
                    "quantity": result.request.get("quantity"),
                    "price": result.request.get("price"),
                    "orderId": (result.response or {}).get("orderId") if result.success else None,
                    "status": (result.response or {}).get("status") if result.success else "FAILED",
                    "executedQty": (result.response or {}).get("executedQty") if result.success else None,
                    "avgPrice": (result.response or {}).get("avgPrice") if result.success else None,
                    "error": result.error,
                }
                st.session_state.order_history.insert(0, record)

                if result.success:
                    st.success("Order placed successfully!")
                else:
                    st.error(f"Order failed: {result.error}")

    with right:
        st.subheader("Result")
        if st.session_state.order_history:
            latest = st.session_state.order_history[0]
            m1, m2, m3 = st.columns(3)
            m1.metric("Order ID", latest["orderId"] or "—")
            m2.metric("Status", latest["status"] or "—")
            m3.metric("Executed Qty", latest["executedQty"] or "—")

            side_class = "side-buy" if latest["side"] == "BUY" else "side-sell"
            st.markdown(
                f"**Symbol:** {latest['symbol']} &nbsp;|&nbsp; "
                f"**Side:** <span class='{side_class}'>{latest['side']}</span> &nbsp;|&nbsp; "
                f"**Type:** {latest['type']}",
                unsafe_allow_html=True,
            )
            st.markdown(get_status_pill(latest["status"]), unsafe_allow_html=True)

            if latest["error"]:
                st.error(latest["error"])
            with st.expander("Raw request / response"):
                st.json(latest)
        else:
            st.caption("Submit an order to see the result here.")


with tab_history:
    st.subheader("Session Order History")
    if st.session_state.order_history:
        df = pd.DataFrame(st.session_state.order_history)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Orders", len(df))
        m2.metric("Buy Orders", int((df["side"] == "BUY").sum()))
        m3.metric("Sell Orders", int((df["side"] == "SELL").sum()))
        m4.metric("Failed", int((df["status"] == "FAILED").sum()))

        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download as CSV", csv, "order_history.csv", "text/csv")
    else:
        st.info("No orders placed yet this session.")


with tab_market:
    st.subheader("Live Price Lookup")
    mkt_symbol = st.text_input("Symbol", value="BTCUSDT", key="mkt_symbol").strip().upper()
    if st.button("Get Price"):
        if not st.session_state.connected:
            st.error("Connect to the API first (see sidebar).")
        else:
            try:
                price = st.session_state.client.get_symbol_price(mkt_symbol)
                st.metric(f"{mkt_symbol} Price", f"{price:,.2f}")
            except (BinanceAPIError, BinanceNetworkError) as exc:
                st.error(f"Could not fetch price: {exc}")

    if st.session_state.connected:
        st.divider()
        st.subheader("Open Orders")
        if st.button("Refresh Open Orders"):
            try:
                open_orders = st.session_state.client.get_open_orders()
                if open_orders:
                    st.dataframe(pd.DataFrame(open_orders), use_container_width=True, hide_index=True)
                else:
                    st.caption("No open orders.")
            except (BinanceAPIError, BinanceNetworkError) as exc:
                st.error(f"Could not fetch open orders: {exc}")


with tab_logs:
    st.subheader("Log File Viewer")
    st.caption(f"Reading from `{LOG_PATH}`")

    level_filter = st.multiselect(
        "Filter by level", ["DEBUG", "INFO", "WARNING", "ERROR"],
        default=["INFO", "WARNING", "ERROR"],
    )
    n_lines = st.slider("Lines to show (most recent)", 20, 500, 100)

    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        filtered = [
            line for line in lines
            if not level_filter or any(f"| {lvl:<8}" in line or f"| {lvl} " in line for lvl in level_filter)
        ]
        tail = filtered[-n_lines:]
        st.code("".join(tail) or "No matching log lines.", language="log")

        with open(LOG_PATH, "rb") as f:
            st.download_button("⬇️ Download full log file", f, "trading_bot.log")
    else:
        st.info("No log file yet — place an order to generate one.")
