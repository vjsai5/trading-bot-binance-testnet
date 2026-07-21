

from dataclasses import dataclass, field
from typing import Optional

from .client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from .logging_config import get_logger
from .validators import ValidationError, validate_order_request

logger = get_logger("trading_bot.orders")


@dataclass
class OrderResult:
    success: bool
    request: dict
    response: Optional[dict] = None
    error: Optional[str] = None

    def summary_lines(self) -> list:
        lines = [
            "Order Request:",
            f"  symbol      : {self.request.get('symbol')}",
            f"  side        : {self.request.get('side')}",
            f"  order_type  : {self.request.get('order_type')}",
            f"  quantity    : {self.request.get('quantity')}",
        ]
        if self.request.get("price") is not None:
            lines.append(f"  price       : {self.request.get('price')}")
        if self.request.get("stop_price") is not None:
            lines.append(f"  stop_price  : {self.request.get('stop_price')}")

        if self.success:
            r = self.response or {}
            lines += [
                "",
                "Order Response:",
                f"  orderId     : {r.get('orderId')}",
                f"  status      : {r.get('status')}",
                f"  executedQty : {r.get('executedQty')}",
                f"  avgPrice    : {r.get('avgPrice')}",
                "",
                "Result: SUCCESS",
            ]
        else:
            lines += ["", f"Result: FAILED - {self.error}"]
        return lines


class OrderService:
    """High-level facade used by both the CLI and the Streamlit UI."""

    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def submit_order(self, symbol, side, order_type, quantity,
                      price=None, stop_price=None, time_in_force="GTC") -> OrderResult:
        try:
            validated = validate_order_request(
                symbol, side, order_type, quantity, price, stop_price, time_in_force
            )
        except ValidationError as exc:
            logger.warning("Validation failed: %s", exc)
            return OrderResult(
                success=False,
                request={
                    "symbol": symbol, "side": side, "order_type": order_type,
                    "quantity": quantity, "price": price, "stop_price": stop_price,
                },
                error=f"Validation error: {exc}",
            )

        logger.info(
            "Submitting order: symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
            validated["symbol"], validated["side"], validated["order_type"],
            validated["quantity"], validated["price"], validated["stop_price"],
        )

        try:
            if validated["order_type"] == "MARKET":
                response = self.client.place_market_order(
                    validated["symbol"], validated["side"], validated["quantity"]
                )
            elif validated["order_type"] == "LIMIT":
                response = self.client.place_limit_order(
                    validated["symbol"], validated["side"], validated["quantity"],
                    validated["price"], validated["time_in_force"],
                )
            elif validated["order_type"] in {"STOP", "STOP_MARKET"}:
                response = self.client.place_stop_limit_order(
                    validated["symbol"], validated["side"], validated["quantity"],
                    validated["price"], validated["stop_price"], validated["time_in_force"],
                )
            else:
                raise ValidationError(f"Unsupported order type {validated['order_type']}")

        except BinanceAPIError as exc:
            logger.error("Binance API error: %s (code=%s)", exc, exc.code)
            return OrderResult(success=False, request=validated, error=str(exc))
        except BinanceNetworkError as exc:
            logger.error("Network error: %s", exc)
            return OrderResult(success=False, request=validated, error=f"Network error: {exc}")
        except Exception as exc:  # noqa: BLE001 - final safety net, always logged
            logger.exception("Unexpected error placing order")
            return OrderResult(success=False, request=validated, error=f"Unexpected error: {exc}")

        logger.info(
            "Order placed successfully: orderId=%s status=%s",
            response.get("orderId"), response.get("status"),
        )
        return OrderResult(success=True, request=validated, response=response)
