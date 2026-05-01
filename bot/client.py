"""
bot.client
~~~~~~~~~~
Binance Futures Testnet client wrapper.

Loads API credentials from the environment, configures the python-binance
Client to target the USDT-M Futures Testnet endpoint, and exposes a single
futures_create_order method that logs every request and response.

Note: testnet=True alone only reconfigures Spot URLs. The Futures base URL
must be overridden manually to https://testnet.binancefuture.com.
"""

import os
from typing import Any

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv

from bot.logging_config import get_logger

logger = get_logger(__name__)

_TESTNET_FUTURES_URL = "https://testnet.binancefuture.com"


class ConfigurationError(Exception):
    """Raised when required environment variables are absent or empty."""


class APIError(Exception):
    """Raised when the Binance API returns a non-success response.

    Attributes:
        status_code: HTTP status code from the exchange.
        error_code: Binance-specific error code (negative integer).
        message: Human-readable description from the API.
    """

    def __init__(self, status_code: int, error_code: int, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message} (HTTP {status_code})")


class NetworkError(Exception):
    """Raised when a network-level failure prevents reaching the exchange."""


class BinanceTestnetClient:
    """Authenticated client for the Binance USDT-M Futures Testnet.

    Reads BINANCE_API_KEY and BINANCE_API_SECRET from the .env file and
    wires the underlying python-binance Client to the testnet base URL.

    Args:
        env_path: Path to a .env file. Defaults to trading_bot/.env.

    Example:
        client = BinanceTestnetClient()
        response = client.futures_create_order(
            symbol="BTCUSDT", side="BUY", type="MARKET", quantity=0.001
        )
    """

    def __init__(self, env_path: str | None = None) -> None:
        self._load_credentials(env_path)
        self._client = self._build_client()
        logger.info("BinanceTestnetClient initialised", extra={"url": _TESTNET_FUTURES_URL})

    def futures_create_order(self, **kwargs: Any) -> dict:
        """Place a Futures order on the testnet and return the parsed response.

        All keyword arguments are forwarded to binance.Client.futures_create_order.

        Args:
            **kwargs: Order parameters (symbol, side, type, quantity, price, etc.).

        Returns:
            Parsed JSON response dict from the exchange.

        Raises:
            APIError: The exchange returned an error code.
            NetworkError: The request could not be delivered.
        """
        # Log request context without exposing price values.
        log_ctx = {k: v for k, v in kwargs.items() if k not in ("price", "stopPrice")}
        logger.debug("Sending futures order request", extra=log_ctx)

        try:
            response: dict = self._client.futures_create_order(**kwargs)
        except BinanceAPIException as exc:
            logger.error(
                "Binance API error",
                extra={
                    "status_code": exc.status_code,
                    "error_code": exc.code,
                    "api_message": exc.message,
                },
            )
            raise APIError(exc.status_code, exc.code, exc.message) from exc
        except BinanceRequestException as exc:
            logger.error("Network error contacting Binance", extra={"detail": str(exc)})
            raise NetworkError(str(exc)) from exc

        logger.debug(
            "Futures order response received",
            extra={
                "orderId": response.get("orderId"),
                "status": response.get("status"),
                "symbol": response.get("symbol"),
            },
        )
        return response

    # ── Private helpers ────────────────────────────────────────────────────

    def _load_credentials(self, env_path: str | None) -> None:
        """Load .env and store API credentials as private instance attributes."""
        if env_path is None:
            env_path = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", ".env")
            )

        load_dotenv(dotenv_path=env_path, override=False)

        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            raise ConfigurationError(
                "BINANCE_API_KEY and BINANCE_API_SECRET must be set. "
                f"Expected .env location: {env_path}"
            )

        # Stored without logging to prevent credential leakage.
        self._api_key = api_key
        self._api_secret = api_secret

    def _build_client(self) -> Client:
        """Construct the python-binance Client and point it at the Futures testnet."""
        client = Client(api_key=self._api_key, api_secret=self._api_secret, testnet=True)
        # testnet=True only fixes Spot URLs; override Futures URL manually.
        client.FUTURES_URL = _TESTNET_FUTURES_URL + "/fapi"
        return client
