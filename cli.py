#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet trading bot.

Example:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
    python cli.py --symbol BTCUSDT --side BUY --type STOP --quantity 0.01 \
                   --price 61000 --stop-price 60900
"""

import argparse
import os
import sys

from bot.client import BinanceFuturesClient
from bot.logging_config import setup_logging
from bot.orders import OrderService

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place MARKET / LIMIT / STOP-LIMIT orders on Binance Futures Testnet."
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument("--type", required=True, dest="order_type",
                         choices=["MARKET", "LIMIT", "STOP", "market", "limit", "stop"])
    parser.add_argument("--quantity", required=True, type=str, help="Order quantity")
    parser.add_argument("--price", required=False, type=str, default=None,
                         help="Required for LIMIT / STOP orders")
    parser.add_argument("--stop-price", required=False, type=str, default=None,
                         help="Required for STOP orders")
    parser.add_argument("--time-in-force", required=False, default="GTC",
                         choices=["GTC", "IOC", "FOK"])
    parser.add_argument("--base-url", required=False, default=DEFAULT_BASE_URL,
                         help="Override API base URL (defaults to Futures Testnet)")
    parser.add_argument("--api-key", required=False, default=None,
                         help="Overrides BINANCE_API_KEY env var")
    parser.add_argument("--api-secret", required=False, default=None,
                         help="Overrides BINANCE_API_SECRET env var")
    return parser


def main(argv=None) -> int:
    logger = setup_logging()
    args = build_parser().parse_args(argv)

    api_key = args.api_key or os.environ.get("BINANCE_API_KEY")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print("ERROR: API key/secret not provided. Set BINANCE_API_KEY and "
              "BINANCE_API_SECRET env vars, or pass --api-key/--api-secret.")
        return 2

    try:
        client = BinanceFuturesClient(api_key, api_secret, base_url=args.base_url)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    service = OrderService(client)

    result = service.submit_order(
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
        time_in_force=args.time_in_force,
    )

    print("\n".join(result.summary_lines()))
    logger.info("CLI run complete. success=%s", result.success)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
