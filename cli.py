"""
cli.py
~~~~~~
CLI entry point for the Binance Futures Testnet trading bot.

Accepts order parameters via argparse, validates them, and dispatches
to the appropriate order-placement function. All output is rendered
with rich for a clean terminal experience.

Usage (run from the trading_bot/ directory):

    Market BUY:
        python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

    Limit SELL:
        python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000

    Stop-Limit SELL:
        python cli.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.001 --price 90000 --stop-price 91000
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich import box

from bot.client import BinanceTestnetClient, APIError, ConfigurationError, NetworkError
from bot.logging_config import get_logger
from bot.orders import place_limit_order, place_market_order, place_stop_limit_order
from bot.validators import (
    VALID_ORDER_TYPES,
    VALID_SIDES,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = get_logger(__name__)
console = Console(highlight=False, safe_box=True)

# Rich style tokens
_BRAND = "bold cyan"
_SUCCESS = "bold green"
_WARN = "bold yellow"
_DIM = "dim"


# ── Parser ─────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=(
            "Binance Futures Testnet Trading Bot\n"
            "Place MARKET, LIMIT, and STOP-LIMIT orders against the USDT-M testnet."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Market BUY  : python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001\n"
            "  Limit SELL  : python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000\n"
            "  Stop-Limit  : python cli.py --symbol BTCUSDT --side SELL --type STOP "
            "--quantity 0.001 --price 90000 --stop-price 91000"
        ),
    )

    parser.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT, ETHUSDT.",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=sorted(VALID_SIDES),
        metavar="SIDE",
        help=f"Order direction. Choices: {', '.join(sorted(VALID_SIDES))}.",
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=sorted(VALID_ORDER_TYPES),
        metavar="TYPE",
        help=f"Order type. Choices: {', '.join(sorted(VALID_ORDER_TYPES))}.",
    )
    parser.add_argument(
        "--quantity",
        required=True,
        type=float,
        metavar="QTY",
        help="Order quantity in base asset units (e.g. 0.001 for BTC).",
    )
    parser.add_argument(
        "--price",
        type=float,
        default=None,
        metavar="PRICE",
        help="Limit price per unit. Required for LIMIT and STOP order types.",
    )
    parser.add_argument(
        "--stop-price",
        dest="stop_price",
        type=float,
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price. Required for the STOP order type.",
    )

    return parser


# ── Rich output helpers ─────────────────────────────────────────────────────


def _render_request_summary(args: argparse.Namespace) -> None:
    """Print a styled panel summarising the order parameters."""
    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=_BRAND)
    table.add_column("Parameter", style="bold white", min_width=14)
    table.add_column("Value", style="cyan")

    table.add_row("Symbol", args.symbol)
    table.add_row("Side", args.side)
    table.add_row("Type", args.order_type)
    table.add_row("Quantity", str(args.quantity))

    if args.price is not None:
        table.add_row("Price", f"{args.price:,.2f}")
    if args.stop_price is not None:
        table.add_row("Stop Price", f"{args.stop_price:,.2f}")

    console.print(
        Panel(
            table,
            title="[bold cyan]>> Order Request[/]",
            subtitle="[dim]Binance Futures Testnet[/]",
            border_style="cyan",
            expand=False,
        )
    )


def _render_success(result: dict) -> None:
    """Print a green panel with the exchange response fields."""
    table = Table(box=box.ROUNDED, show_header=True, header_style=_SUCCESS)
    table.add_column("Field", style="bold white", min_width=16)
    table.add_column("Value", style="bright_green")

    fields = [
        ("Order ID", str(result["orderId"])),
        ("Client Order ID", result["clientOrderId"]),
        ("Symbol", result["symbol"]),
        ("Side", result["side"]),
        ("Type", result["type"]),
        ("Status", result["status"]),
        ("Executed Qty", result["executedQty"]),
        ("Average Price", result["avgPrice"]),
        ("Limit Price", result["price"]),
        ("Stop Price", result["stopPrice"]),
        ("Time In Force", result["timeInForce"]),
    ]

    for label, value in fields:
        style = _DIM if value in ("0", "") else "bright_green"
        table.add_row(label, Text(value, style=style))

    console.print()
    console.print(
        Panel(
            table,
            title="[bold green]*** Order Placed Successfully ***[/]",
            border_style="green",
            expand=False,
        )
    )


def _render_error(title: str, message: str, hint: str | None = None) -> None:
    """Print a red error panel. Appends a hint line when provided."""
    body = Text(message, style="red")
    if hint:
        body.append(f"\n\nHint: {hint}", style=_WARN)

    console.print()
    console.print(
        Panel(
            body,
            title=f"[bold red]ERROR: {title}[/]",
            border_style="red",
            expand=False,
        )
    )


# ── Validation ──────────────────────────────────────────────────────────────


def _validate_args(args: argparse.Namespace) -> None:
    """Run cross-field semantic validation and normalise values in-place.

    Args:
        args: Parsed argument namespace (mutated in-place).

    Raises:
        ValueError: A field failed validation.
    """
    args.symbol = validate_symbol(args.symbol)
    args.side = validate_side(args.side)
    args.order_type = validate_order_type(args.order_type)
    args.quantity = validate_quantity(args.quantity)

    price_required = args.order_type in ("LIMIT", "STOP")
    args.price = validate_price(args.price, required=price_required)

    stop_required = args.order_type == "STOP"
    args.stop_price = validate_stop_price(args.stop_price, required=stop_required)


# ── Order dispatch ──────────────────────────────────────────────────────────


def _dispatch_order(client: BinanceTestnetClient, args: argparse.Namespace) -> dict:
    """Route validated args to the correct order-placement function.

    Args:
        client: Authenticated testnet client.
        args: Validated argument namespace.

    Returns:
        Normalised order result dictionary.
    """
    if args.order_type == "MARKET":
        return place_market_order(client, args.symbol, args.side, args.quantity)

    if args.order_type == "LIMIT":
        return place_limit_order(client, args.symbol, args.side, args.quantity, args.price)

    return place_stop_limit_order(
        client, args.symbol, args.side, args.quantity, args.price, args.stop_price
    )


# ── Entry point ─────────────────────────────────────────────────────────────


def main() -> None:
    """Parse arguments, validate, place order, and render result."""
    console.rule("[bold cyan]Binance Futures Testnet Trading Bot[/]")
    console.print()

    parser = _build_parser()
    args = parser.parse_args()

    try:
        _validate_args(args)
    except ValueError as exc:
        _render_error("Validation Error", str(exc))
        logger.warning("Argument validation failed: %s", exc)
        sys.exit(1)

    _render_request_summary(args)

    try:
        client = BinanceTestnetClient()
    except ConfigurationError as exc:
        _render_error(
            "Configuration Error",
            str(exc),
            hint="Copy .env.example to .env and fill in your testnet API credentials.",
        )
        sys.exit(1)

    result: dict | None = None
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(
                f"[cyan]Submitting {args.order_type} {args.side} order to testnet...",
                total=None,
            )
            result = _dispatch_order(client, args)

    except APIError as exc:
        _render_error(
            "API Error",
            exc.message,
            hint=(
                f"Binance error code: {exc.error_code}. "
                "Check symbol precision, minimum notional, and account balance."
            ),
        )
        sys.exit(1)

    except NetworkError as exc:
        _render_error(
            "Network Error",
            str(exc),
            hint="Verify your internet connection and that the testnet is reachable.",
        )
        sys.exit(1)

    _render_success(result)
    console.print()
    console.rule("[dim]Log written to trading_bot.log[/]")


if __name__ == "__main__":
    main()
