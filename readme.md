# Telegram → MT5 Signal Copier (AI-Powered)

Listens to Telegram forex signal channels, parses them with an LLM, and trades on MetaTrader 5 automatically. Supports multiple channels, any signal format, risk management, and runs headless via Docker.

Forked from [SiriusForex AI Copier](https://github.com/siriusforex-ai/telegram_signal_copier) — swapped Claude for DeepSeek, added multi-group support, risk management, and an RPyC bridge for headless Docker execution.

---

## What's different from the original

| Original | This fork |
|----------|-----------|
| Claude AI (Anthropic) | DeepSeek V4 Flash (~100x cheaper signals) |
| Single channel | Multiple channels (comma-separated in config) |
| Fixed lot size | %-based risk management with daily loss limits |
| Direct MT5 import (Windows only) | RPyC bridge — runs headless in Docker + Wine |
| Hardcoded instrument | Trades whatever the signal says (EURUSD, XAUUSD, etc.) |
| Rich terminal dashboard | Removed — headless operation |
| Python 3.12 needed | Python 3.11 inside container (whatever Wine has) |

---

## How it works

```
Signal posted in Telegram channel
        │
        ▼
Telethon catches it in real time
        │
        ▼
DeepSeek V4 Flash parses the message
  → extracts: direction, entry, SL, TP[], instrument
  → ignores: commentary, news, trade updates ("TP hit", etc.)
        │
        ▼
Risk manager checks:
  → position count, daily loss, drawdown
  → calculates lot size based on account balance
        │
        ▼
RPyC bridge sends to MT5 inside Docker/Wine
  → places trade with split lot across TPs
```

The LLM approach matters because signal groups don't follow one format. Some post emoji-heavy layouts, some use plain text, some mix in analysis with the signal. Regex breaks when the format changes. DeepSeek just reads it.

---

## Features

- **Any format** — works with any signal channel, doesn't care about formatting
- **Multi-channel** — monitor several groups at once
- **All order types** — market, limit, stop for both buy and sell
- **Multiple TPs** — splits the lot across TP1, TP2, TP3 automatically
- **Close signals** — detects close/exit instructions
- **Risk management** — %-based lot sizing, max daily loss, max drawdown, concurrent position cap
- **Headless** — runs in Docker with Wine, no VNC needed day-to-day
- **Reasonable cost** — DeepSeek Flash is ~$0.0001 per signal

---

## Project structure

```
telegram_signal_copier/
├── config.py             # Settings from .env
├── signal_parser.py      # DeepSeek LLM signal parsing
├── mt5_executor.py       # RPyC client → MT5 bridge
├── risk_manager.py       # Risk checks and lot sizing
├── main.py               # Entry point (Telethon + loop)
├── .env                  # Your API keys and credentials
└── requirements.txt
```

Inside the Docker container:
```
mt5_rpyc_server.py        # RPyC server running under Wine Python
mt5_config.json           # MT5 credentials for the bridge
```

---

## Requirements

- **Docker** — the MT5 terminal runs in a container with Wine
- **Python 3.11+** — for the copier itself
- **MT5 Docker image** — [gmag11/metatrader5_vnc](https://hub.docker.com/r/gmag11/metatrader5_vnc)
- **Telegram account** — subscribed to the signal channels
- **Telegram API credentials** — free from https://my.telegram.org
- **DeepSeek API key** — sign up at https://platform.deepseek.com

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Raditz2/telegram_signal_copier.git
cd telegram_signal_copier
pip install -r requirements.txt
```

### 2. Run the MT5 Docker container

```bash
docker run -d \
  --name mt5-terminal \
  -p 3001:3000 \
  -p 8001:8001 \
  gmag11/metatrader5_vnc
```

Connect to VNC at `http://localhost:3001`, log in to your broker.

### 3. Configure copier inside container

```bash
docker cp mt5_rpyc_server.py mt5-terminal:/opt/ai-signal-copier/
docker cp mt5_config.json mt5-terminal:/opt/ai-signal-copier/
docker exec mt5-terminal bash -c \
  "s6-setuidgid abc HOME=/config wine python /opt/ai-signal-copier/mt5_rpyc_server.py"
```

### 4. Create your `.env`

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+your_phone

SIGNAL_CHANNELS=@channel1,-123456789

LLM_API_KEY=sk-your_deepseek_key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

MT5_ACCOUNT=12345678
MT5_PASSWORD=your_mt5_password
MT5_SERVER=YourBroker-Demo

RISK_PER_TRADE=1.0
MAX_DAILY_LOSS=5.0
MAX_CONCURRENT=3
MAX_DRAWDOWN=20.0
```

### 5. Run

```bash
python main.py
```

First run will ask for a Telegram verification code. After that it saves a session file and reconnects automatically.

---

## Risk settings explained

| Setting | Default | What it does |
|---------|---------|--------------|
| RISK_PER_TRADE | 1.0 | % of balance to risk per trade (calculates lot from SL distance) |
| MAX_DAILY_LOSS | 5.0 | % loss limit per day — stops trading after hitting it |
| MAX_CONCURRENT | 3 | Max open positions at once |
| MAX_DRAWDOWN | 20.0 | Stops trading if equity drops this % below balance |
| EFFECTIVE_LEVERAGE | 10.0 | Used for position sizing calculations |

---

## Notes

- Test with a demo account and small lot first. The bot executes fast, but it doesn't make bad signals profitable.
- The RPyC bridge can run on a separate machine — just change the host in mt5_executor.py if you want the copier and MT5 on different boxes.
- DeepSeek Flash costs about $0.0001 per signal. $5 lasts thousands of signals.
- The .session file gives access to your Telegram account. Don't commit it.
- If Telethon auth keeps failing, generate fresh API credentials at my.telegram.org.

---

## License

MIT — do whatever you want with it.
