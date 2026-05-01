"""
bot.orders
~~~~~~~~~~
Order-placement functions for Binance USDT-M Futures Testnet.

Each function maps to one supported order type and returns a normalised
OrderResult TypedDict. Normalisation decouples callers from the raw Binance
response schema and handles the two distinct response shapes returned by
the testnet (regular orders vs. algo/conditional STOP orders).

Supported types:
  MARKET     - Executes immediately at the best available price.
  LIMIT      - Rests in the book at a specified price (GTC).
  STOP       - Stop-Limit: triggers at stopPrice, fills at price (GTC).
"""

from __future__ import annotations

from typing import TypedDict

from bot.client import BinanceTestnetClient
from bot.logging_config import get_logger

logger = get_logger(__name__)

_GTC = "GTC"


class OrderResult(TypedDict):
    """Normalised order response returned by all placement functions.

    Keys match the field names printed to the terminal and written to the
    log file, regardless of whether the underlying response was a regular
    order or an algo/conditional order.
    """

    orderId: int
    clientOrderId: str
    symbol: str
    side: str
    type: str
    status: str
    executedQty: str
    avgPrice: str
    price: str
    stopPrice: str
    timeInForce: str


def place_market_order(
    client: BinanceTestnetClient,
    symbol: str,
    side: str,
    quantity: float,
) -> OrderResult:
    """Place a MARKET order. Executes immediately at the best available price.

    Args:
        client: Authenticated BinanceTestnetClient.
        symbol: Trading pair, e.g. 'BTCUSDT'.
        side: 'BUY' or 'SELL'.
        quantity: Order size in base asset units.

    Returns:
        Normalised OrderResult.

    Raises:
        APIError: Exchange returned an error code.
        NetworkError: Request could not be delivered.
    """
    logger.debug("Placing MARKET order", extra={"symbol": symbol, "side": side, "quantity": quantity})

    raw = client.futures_create_order(
        symbol=symbol,
        side=side,
        type="MARKET",
        quantity=quantity,
    )

    result = _normalise(raw)
    logger.info("MARKET order placed", extra={"orderId": result["orderId"], "status": result["status"]})
    return result


def place_limit_order(
    client: BinanceTestnetClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
) -> OrderResult:
    """Place a LIMIT GTC order. Rests in the book until matched or cancelled.

    Args:
        client: Authenticated BinanceTestnetClient.
        symbol: Trading pair, e.g. 'BTCUSDT'.
        side: 'BUY' or 'SELL'.
        quantity: Order size in base asset units.
        price: Limit price per unit.

    Returns:
        Normalised OrderResult.

    Raises:
        APIError: Exchange returned an error code.
        NetworkError: Request could not be delivered.
    """
    logger.debug("Placing LIMIT order", extra={"symbol": symbol, "side": side, "quantity": quantity})

    raw = client.futures_create_order(
        symbol=symbol,
        side=side,
        type="LIMIT",
        quantity=quantity,
        price=price,
        timeInForce=_GTC,
    )

    result = _normalise(raw)
    logger.info("LIMIT order placed", extra={"orderId": result["orderId"], "status": result["status"]})
    return result


def place_stop_limit_order(
    client: BinanceTestnetClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop_price: float,
) -> OrderResult:
    """Place a Stop-Limit GTC order.

    Inactive until the market price reaches stop_price, then submitted as
    a limit order at price. Useful for stop-loss and breakout strategies.

    Args:
        client: Authenticated BinanceTestnetClient.
        symbol: Trading pair, e.g. 'BTCUSDT'.
        side: 'BUY' or 'SELL'.
        quantity: Order size in base asset units.
        price: Limit fill price once the order is triggered.
        stop_price: Market price that activates the order.

    Returns:
        Normalised OrderResult.

    Raises:
        APIError: Exchange returned an error code.
        NetworkError: Request could not be delivered.
    """
    logger.debug("Placing STOP-LIMIT order", extra={"symbol": symbol, "side": side, "quantity": quantity})

    raw = client.futures_create_order(
        symbol=symbol,
        side=side,
        type="STOP",
        quantity=quantity,
        price=price,
        stopPrice=stop_price,
        timeInForce=_GTC,
    )

    result = _normalise(raw)
    logger.info("STOP-LIMIT order placed", extra={"orderId": result["orderId"], "status": result["status"]})
    return result


def _normalise(raw: dict) -> OrderResult:
    """Map a raw Binance response to a stable OrderResult.

    The Futures testnet returns two distinct schemas:
      - Regular orders (MARKET, LIMIT): orderId, status, stopPrice.
      - Algo/conditional orders (STOP): algoId, algoStatus, triggerPrice.

    The is_algo flag selects the correct field names transparently.

    Args:
        raw: Parsed JSON response from the Binance Futures REST API.

    Returns:
        Fully populated OrderResult.
    """
    is_algo = "algoId" in raw

    return OrderResult(
        orderId=raw.get("algoId" if is_algo else "orderId", 0),
        clientOrderId=raw.get("clientAlgoId" if is_algo else "clientOrderId", ""),
        symbol=raw.get("symbol", ""),
        side=raw.get("side", ""),
        type=raw.get("algoType" if is_algo else "type", ""),
        status=raw.get("algoStatus" if is_algo else "status", ""),
        executedQty=raw.get("quantity" if is_algo else "executedQty", "0"),
        avgPrice=raw.get("avgPrice", "0"),
        price=raw.get("price", "0"),
        stopPrice=raw.get("triggerPrice" if is_algo else "stopPrice", "0"),
        timeInForce=raw.get("timeInForce", ""),
    )
