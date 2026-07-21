

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP", "STOP_MARKET"}
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK"}

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(ValueError):
    """Raised when user-supplied order input fails validation."""


def validate_symbol(symbol: str) -> str:
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol is required, e.g. BTCUSDT")
    symbol = symbol.strip().upper()
    if not _SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected an uppercase alphanumeric "
            "trading pair like 'BTCUSDT'."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side or not isinstance(side, str):
        raise ValidationError("Side is required (BUY or SELL)")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type or not isinstance(order_type, str):
        raise ValidationError("Order type is required (MARKET or LIMIT)")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}"
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'")
    if quantity <= 0:
        raise ValidationError(f"Quantity must be positive, got {quantity}")
    return quantity


def validate_price(price, required: bool) -> float | None:
    if price is None or price == "":
        if required:
            raise ValidationError("Price is required for LIMIT / STOP orders")
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'")
    if price <= 0:
        raise ValidationError(f"Price must be positive, got {price}")
    return price


def validate_stop_price(stop_price, required: bool) -> float | None:
    if stop_price is None or stop_price == "":
        if required:
            raise ValidationError("Stop price is required for STOP / STOP_MARKET orders")
        return None
    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'")
    if stop_price <= 0:
        raise ValidationError(f"Stop price must be positive, got {stop_price}")
    return stop_price


def validate_time_in_force(tif: str) -> str:
    tif = (tif or "GTC").strip().upper()
    if tif not in VALID_TIME_IN_FORCE:
        raise ValidationError(f"Invalid timeInForce '{tif}'. Must be one of {sorted(VALID_TIME_IN_FORCE)}")
    return tif


def validate_order_request(symbol, side, order_type, quantity, price=None,
                            stop_price=None, time_in_force="GTC") -> dict:
    """Validate a full order request and return normalized fields."""
    order_type = validate_order_type(order_type)
    price_required = order_type in {"LIMIT", "STOP"}
    stop_required = order_type in {"STOP", "STOP_MARKET"}

    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": order_type,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, required=price_required),
        "stop_price": validate_stop_price(stop_price, required=stop_required),
        "time_in_force": validate_time_in_force(time_in_force) if order_type != "MARKET" else None,
    }
