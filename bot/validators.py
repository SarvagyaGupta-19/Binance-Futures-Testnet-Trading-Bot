"""
bot.validators
~~~~~~~~~~~~~~
Pure-function input validation for CLI arguments.

All validators are free of side effects and raise ``ValueError`` with
descriptive messages on invalid input, making them independently unit-testable
and reusable outside the CLI context.

Constants ``VALID_SIDES`` and ``VALID_ORDER_TYPES`` are intentionally exported
so the CLI layer can reference them when building ``argparse`` choices, keeping
a single source of truth for allowed values.
"""

from __future__ import annotations

VALID_SIDES: frozenset[str] = frozenset({"BUY", "SELL"})
VALID_ORDER_TYPES: frozenset[str] = frozenset({"MARKET", "LIMIT", "STOP"})


def validate_symbol(symbol: str) -> str:
    """Validate and normalise a trading pair symbol.

    Args:
        symbol: Raw symbol string from the user (e.g. ``"btcusdt"``).

    Returns:
        Upper-cased symbol string (e.g. ``"BTCUSDT"``).

    Raises:
        ValueError: If the symbol is empty or contains whitespace.
    """
    normalised = symbol.strip().upper()
    if not normalised:
        raise ValueError("Symbol must be a non-empty string (e.g. 'BTCUSDT').")
    if " " in normalised:
        raise ValueError(f"Symbol '{normalised}' must not contain spaces.")
    return normalised


def validate_side(side: str) -> str:
    """Validate the order side.

    Args:
        side: Raw side string (case-insensitive).

    Returns:
        Upper-cased canonical side string (``"BUY"`` or ``"SELL"``).

    Raises:
        ValueError: If the side is not one of the allowed values.
    """
    normalised = side.strip().upper()
    if normalised not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return normalised


def validate_order_type(order_type: str) -> str:
    """Validate the order type.

    Args:
        order_type: Raw order-type string (case-insensitive).

    Returns:
        Upper-cased canonical order type (``"MARKET"``, ``"LIMIT"``, or ``"STOP"``).

    Raises:
        ValueError: If the type is not one of the allowed values.
    """
    normalised = order_type.strip().upper()
    if normalised not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return normalised


def validate_quantity(quantity: float | str) -> float:
    """Validate and parse the order quantity.

    Args:
        quantity: Numeric quantity, either as a ``float`` or a string
            representation (e.g. ``"0.001"``).

    Returns:
        Positive ``float`` quantity.

    Raises:
        ValueError: If the quantity is not a positive finite number.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Quantity must be a numeric value, got '{quantity}'.") from exc

    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")

    return qty


def validate_price(price: float | str | None, *, required: bool = False) -> float | None:
    """Validate and parse a limit or stop-limit price.

    Args:
        price: Numeric price value or ``None``.
        required: When ``True``, ``None`` is not accepted (used for LIMIT/STOP orders).

    Returns:
        Positive ``float`` price, or ``None`` when not required and not supplied.

    Raises:
        ValueError: If the price is required but absent, or is not a positive number.
    """
    if price is None:
        if required:
            raise ValueError("Price is required for LIMIT and STOP order types.")
        return None

    try:
        p = float(price)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Price must be a numeric value, got '{price}'.") from exc

    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")

    return p


def validate_stop_price(stop_price: float | str | None, *, required: bool = False) -> float | None:
    """Validate and parse a stop-trigger price.

    Args:
        stop_price: Numeric stop price or ``None``.
        required: When ``True``, ``None`` raises an error.

    Returns:
        Positive ``float`` stop price, or ``None``.

    Raises:
        ValueError: If the stop price is required but absent, or is non-positive.
    """
    if stop_price is None:
        if required:
            raise ValueError("--stop-price is required for STOP order type.")
        return None

    try:
        sp = float(stop_price)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Stop price must be a numeric value, got '{stop_price}'.") from exc

    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero, got {sp}.")

    return sp
