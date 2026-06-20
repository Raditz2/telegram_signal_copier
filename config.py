"""
config.py — All settings for the AI Signal Copier Bot
Loads from .env file or environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════
#  TELEGRAM (Telethon)
# ═══════════════════════════════════════════════
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")

# Signal channels to monitor — comma-separated usernames or IDs
SIGNAL_CHANNELS = [s.strip() for s in os.getenv("SIGNAL_CHANNELS", "").split(",") if s.strip()]

# ═══════════════════════════════════════════════
#  LLM PROVIDER (DeepSeek / OpenAI-compatible)
# ═══════════════════════════════════════════════
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# ═══════════════════════════════════════════════
#  METATRADER 5
# ═══════════════════════════════════════════════
MT5_ACCOUNT = int(os.getenv("MT5_ACCOUNT", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
MT5_DEMO = os.getenv("MT5_DEMO", "true").lower() == "true"
MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", "400401"))
DEVIATION = int(os.getenv("DEVIATION", "20"))

# Symbol mapping — signal says "Gold" or "XAUUSD", broker calls it "GOLD" etc.
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "XAUUSD")

# ═══════════════════════════════════════════════
#  TRADE SETTINGS
# ═══════════════════════════════════════════════
DEFAULT_LOT_SIZE = float(os.getenv("DEFAULT_LOT_SIZE", "0.01"))
MIN_LOT = float(os.getenv("MIN_LOT", "0.01"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "1.0"))  # % of balance to risk
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "5.0"))   # % daily loss limit
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))
MAX_DRAWDOWN = float(os.getenv("MAX_DRAWDOWN", "20.0"))
EFFECTIVE_LEVERAGE = float(os.getenv("EFFECTIVE_LEVERAGE", "10.0"))

# If entry price is within this many points of current price, use market order
MARKET_ORDER_THRESHOLD = int(os.getenv("MARKET_ORDER_THRESHOLD", "50"))

# ═══════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════
TRADE_LOG_FILE = os.getenv("TRADE_LOG_FILE", "trade_log.json")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ═══════════════════════════════════════════════
#  SESSION FILE
# ═══════════════════════════════════════════════
SESSION_FILE = os.getenv("SESSION_FILE", "signal_copier_session")
