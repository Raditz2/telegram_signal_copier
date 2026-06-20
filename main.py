"""
main.py — Entry point for the AI-Powered Telegram to MT5 Signal Copier.

Connects MT5, starts the Telegram listener, and runs the dashboard.
"""
import asyncio
import signal
import sys

import config
from mt5_executor import connect as mt5_connect
from signal_listener import start_listener


async def main():
    print("╔══════════════════════════════════════════════╗")
    print("║   AI-Powered Telegram → MT5 Signal Copier   ║")
    print("║   LLM: " + config.LLM_MODEL.ljust(30) + "║")
    print("║   Channels: " + str(len(config.SIGNAL_CHANNELS)).ljust(27) + "║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Connect MT5
    print("[*] Connecting to MetaTrader 5...")
    if not mt5_connect():
        print("[ERROR] Failed to connect to MT5. Ensure MT5 terminal is running.")
        sys.exit(1)

    account = None
    try:
        from mt5_executor import get_account_info
        account = get_account_info()
    except Exception:
        pass

    if account:
        print(f"[OK] MT5 connected — {account.get('name', '?')} | "
              f"Balance: ${account.get('balance', 0):.2f} | "
              f"Leverage: 1:{account.get('leverage', 0)}")
    else:
        print("[OK] MT5 connected")

    # Start Telegram listener
    print("[*] Starting Telegram listener...")
    print(f"[*] Listening to {len(config.SIGNAL_CHANNELS)} channel(s): {', '.join(config.SIGNAL_CHANNELS)}")
    print()

    try:
        await start_listener()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted, exiting.")
