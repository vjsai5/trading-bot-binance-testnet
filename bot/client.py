
import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("trading_bot.client")

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5000
DEFAULT_TIMEOUT = 10  # seconds


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx / error-coded response."""

    def __init__(self, message, status_code=None, code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.payload = payload


class BinanceNetworkError(Exception):
    """Raised on connection/timeout failures reaching Binance."""


class BinanceFuturesClient:
    """
    Minimal signed REST client for Binance USDT-M Futures.

    Usage:
        client = BinanceFuturesClient(api_key, api_secret)
        client.place_market_order("BTCUSDT", "BUY", 0.01)
    """

    def __init__(self, api_key: str, api_secret: str,
                 base_url: str = DEFAULT_BASE_URL,
                 recv_window: int = DEFAULT_RECV_WINDOW,
                 timeout: int = DEFAULT_TIMEOUT):
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret are required")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})


    def _sign(self, params: dict) -> dict:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", self.recv_window)
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, path: str, params: dict = None, signed: bool = False):
        params = params or {}
        url = f"{self.base_url}{path}"

        if signed:
            params = self._sign(params)

        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("REQUEST %s %s params=%s", method, path, safe_params)

        try:
            response = self.session.request(
                method, url, params=params, timeout=self.timeout
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Network timeout calling %s %s: %s", method, path, exc)
            raise BinanceNetworkError(f"Request to {path} timed out") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error calling %s %s: %s", method, path, exc)
            raise BinanceNetworkError(f"Could not connect to {self.base_url}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected network error calling %s %s: %s", method, path, exc)
            raise BinanceNetworkError(str(exc)) from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        logger.debug("RESPONSE %s %s status=%s body=%s", method, path, response.status_code, payload)

        if response.status_code >= 400:
            code = payload.get("code") if isinstance(payload, dict) else None
            msg = payload.get("msg") if isinstance(payload, dict) else str(payload)
            logger.error(
                "API error on %s %s: status=%s code=%s msg=%s",
                method, path, response.status_code, code, msg,
            )
            raise BinanceAPIError(
                msg or "Unknown Binance API error",
                status_code=response.status_code,
                code=code,
                payload=payload,
            )

        return payload


    def get_server_time(self) -> int:
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_symbol_price(self, symbol: str) -> float:
        data = self._request("GET", "/fapi/v1/ticker/price", {"symbol": symbol})
        return float(data["price"])

    def ping(self) -> bool:
        self._request("GET", "/fapi/v1/ping")
        return True


    def get_account_info(self) -> dict:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_open_orders(self, symbol: str = None) -> list:
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/fapi/v1/openOrders", params, signed=True)

    def get_order_status(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "GET", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}, signed=True
        )


    def place_order(self, symbol: str, side: str, order_type: str, quantity: float,
                     price: float = None, stop_price: float = None,
                     time_in_force: str = None, reduce_only: bool = False) -> dict:
        """
        Generic order placement. Maps to POST /fapi/v1/order.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if reduce_only:
            params["reduceOnly"] = "true"
        if order_type in {"LIMIT", "STOP"}:
            params["price"] = price
            params["timeInForce"] = time_in_force or "GTC"
        if order_type in {"STOP", "STOP_MARKET"}:
            params["stopPrice"] = stop_price

        return self._request("POST", "/fapi/v1/order", params, signed=True)

    def place_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        return self.place_order(symbol, side, "MARKET", quantity)

    def place_limit_order(self, symbol: str, side: str, quantity: float,
                           price: float, time_in_force: str = "GTC") -> dict:
        return self.place_order(symbol, side, "LIMIT", quantity, price=price,
                                 time_in_force=time_in_force)

    def place_stop_limit_order(self, symbol: str, side: str, quantity: float,
                                price: float, stop_price: float,
                                time_in_force: str = "GTC") -> dict:
        """Bonus order type: STOP (stop-limit)."""
        return self.place_order(symbol, side, "STOP", quantity, price=price,
                                 stop_price=stop_price, time_in_force=time_in_force)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "DELETE", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}, signed=True
        )