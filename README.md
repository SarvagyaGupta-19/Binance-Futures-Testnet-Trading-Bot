# Binance Futures Testnet Trading Bot

A lightweight, production-grade Python CLI for placing orders on the **Binance USDT-M Futures Testnet**. Built for the Primetrade.ai Python Developer Intern assignment.

---

## Features

| Capability | Detail |
|---|---|
| Order types | `MARKET`, `LIMIT`, `STOP` (Stop-Limit) |
| Order sides | `BUY`, `SELL` |
| CLI framework | `argparse` with `rich`-powered premium terminal UX |
| Logging | Structured JSON to `trading_bot.log` (rotating, 5 MB × 3 files) |
| Error handling | Typed domain exceptions with descriptive user-facing messages |
| Security | Credentials loaded from `.env`; never logged or echoed |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # BinanceTestnetClient — API wrapper & exception hierarchy
│   ├── orders.py            # Place MARKET / LIMIT / STOP orders; returns normalised OrderResult
│   ├── validators.py        # Pure-function input validation (unit-testable, side-effect-free)
│   └── logging_config.py   # JSON structured logging; RotatingFileHandler + StreamHandler
├── cli.py                   # CLI entry point (argparse + rich)
├── .env                     # ← YOUR credentials (gitignored)
├── .env.example             # Template to copy
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python **3.10+**
- A [Binance Futures Testnet](https://testnet.binancefuture.com) account with API credentials

---

## Setup

### 1. Clone / download the project

```bash
git clone <https://github.com/SarvagyaGupta-19/Binance-Futures-Testnet-Trading-Bot.git>
cd trading_bot
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your testnet credentials:

```dotenv
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> **Note:** The `.env` file is listed in `.gitignore` and will never be committed.

---

## Usage

All commands are run from the `trading_bot/` directory.

### Market Order

Executes immediately at the best available price.

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Limit Order (GTC)

Rests in the order book until matched or cancelled.

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000
```

### Stop-Limit Order (GTC)

Activated when the market price reaches `--stop-price`, then fills as a limit order at `--price`.

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.001 \
    --price 90000 --stop-price 91000
```

### All available flags

| Flag | Required | Description |
|---|---|---|
| `--symbol` | ✅ | Trading pair, e.g. `BTCUSDT` |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` | ✅ | `MARKET`, `LIMIT`, or `STOP` |
| `--quantity` | ✅ | Base asset quantity, e.g. `0.001` |
| `--price` | LIMIT / STOP | Limit execution price |
| `--stop-price` | STOP only | Stop trigger price |

---

## Sample Terminal Output

```
────────── Binance Futures Testnet Trading Bot ──────────

╭─  Order Request  ──────────────────────╮
│  Parameter    Value                     │
│ ──────────────────────────────────────  │
│  Symbol       BTCUSDT                  │
│  Side         BUY                      │
│  Type         MARKET                   │
│  Quantity     0.001                    │
╰── Binance Futures Testnet ─────────────╯

⠸ Submitting MARKET BUY order to testnet…  0:00:01

╭─ ✔  Order Placed Successfully ─────────────────────╮
│  Field            Value                             │
│ ─────────────────────────────────────────────────  │
│  Order ID         123456789                         │
│  Symbol           BTCUSDT                           │
│  Side             BUY                               │
│  Type             MARKET                            │
│  Status           FILLED                            │
│  Executed Qty     0.001                             │
│  Average Price    95423.50                          │
╰────────────────────────────────────────────────────╯

──────── Log written to trading_bot.log ────────
```

---

## Log File

All API requests, responses, and errors are written to `trading_bot.log` as newline-delimited JSON:

```json
{"timestamp": "2026-05-01T09:30:01.123456+00:00", "level": "DEBUG", "logger": "trading_bot.bot.orders", "message": "Placing MARKET order", "symbol": "BTCUSDT", "side": "BUY", "quantity": 0.001}
{"timestamp": "2026-05-01T09:30:01.456789+00:00", "level": "INFO",  "logger": "trading_bot.bot.orders", "message": "MARKET order placed successfully", "orderId": 123456789, "status": "FILLED"}
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing `--price` for LIMIT/STOP | Validation error panel with descriptive hint |
| Missing `.env` credentials | `ConfigurationError` with setup instructions |
| Exchange API error (e.g. invalid symbol) | `APIError` panel with Binance error code |
| Network failure / timeout | `NetworkError` panel with connectivity hint |
| All errors | Process exits with code `1` and logs the error to file |

---

## Architecture

```
cli.py  (Presentation Layer)
  │  argparse   →  _validate_args()  →  _dispatch_order()
  │                                         │
  │                              ┌──────────┴──────────┐
  │                         orders.py            validators.py
  │                    (Order Placement)       (Pure Validation)
  │                              │
  │                         client.py
  │                    (BinanceTestnetClient)
  │                              │
  │                    python-binance REST client
  │                              │
  │                 https://testnet.binancefuture.com
  │
logging_config.py
  ├── RotatingFileHandler → trading_bot.log (JSON, DEBUG+)
  └── StreamHandler       → stderr (WARNING+)
```

---

## Assumptions

1. The Binance Futures Testnet is used exclusively; no mainnet calls are made.
2. `timeInForce=GTC` is applied to all LIMIT and STOP orders.
3. Quantity precision requirements are governed by the testnet exchange symbol rules; pass a value that satisfies the `LOT_SIZE` filter for your symbol.
4. The bot does not maintain local order state; each CLI invocation is stateless.

---

