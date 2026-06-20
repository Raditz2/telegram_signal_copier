"""
signal_listener.py — Monitors multiple Telegram channels for new messages
using Telethon (user client, not bot API).
Passes each message to the LLM for parsing, then executes on MT5.
"""
import asyncio
from telethon import TelegramClient, events
from datetime import datetime

import config
from signal_parser import parse_signal
from mt5_executor import execute_signal, close_all_positions, get_open_positions
from risk_manager import RiskManager
from trade_logger import log_trade, log_close


# Shared state for the dashboard to read
listener_state = {
    "connected": False,
    "channels": [],
    "last_message": "",
    "last_message_time": None,
    "last_signal": None,
    "last_trade_results": [],
    "signals_received": 0,
    "signals_executed": 0,
    "signals_skipped": 0,
}

risk_manager = RiskManager(
    risk_per_trade=config.RISK_PER_TRADE,
    max_daily_loss=config.MAX_DAILY_LOSS,
    max_concurrent_positions=config.MAX_CONCURRENT,
    max_drawdown=config.MAX_DRAWDOWN,
    effective_leverage=config.EFFECTIVE_LEVERAGE,
)


async def start_listener(dashboard_callback=None):
    """
    Start the Telethon client and listen for new messages
    from all configured signal channels.
    """
    client = TelegramClient(
        config.SESSION_FILE,
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH,
    )

    await client.start(phone=config.TELEGRAM_PHONE)
    listener_state["connected"] = True

    # Resolve all channels
    channels = []
    for channel_ref in config.SIGNAL_CHANNELS:
        try:
            entity = await client.get_entity(channel_ref)
            title = getattr(entity, "title", channel_ref)
            channels.append(entity)
            listener_state["channels"].append(title)
            print(f"[OK] Connected to channel: {title} ({channel_ref})")
        except Exception as e:
            print(f"[ERROR] Could not resolve channel '{channel_ref}': {e}")
            print("[INFO] Make sure you are subscribed to this channel on your Telegram account")

    if not channels:
        print("[ERROR] No channels could be resolved. Exiting.")
        return

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        message_text = event.message.text
        if not message_text:
            return

        timestamp = datetime.now()

        # Get channel name
        chat = await event.get_chat()
        channel_name = getattr(chat, "title", str(event.chat_id))

        # Update state
        listener_state["last_message"] = f"[{channel_name}] {message_text[:200]}"
        listener_state["last_message_time"] = timestamp

        # Send to LLM for parsing
        signal = await asyncio.to_thread(parse_signal, message_text)

        if signal is None:
            listener_state["signals_skipped"] += 1
            return

        if not signal.get("is_signal", False):
            listener_state["signals_skipped"] += 1
            return

        listener_state["signals_received"] += 1
        listener_state["last_signal"] = signal

        # Get current account info for risk check
        account = None
        try:
            from mt5_executor import get_account_info, get_daily_pnl
            account = get_account_info()
        except Exception:
            pass

        positions = get_open_positions()
        daily_pnl = get_daily_pnl() if hasattr(get_daily_pnl, '__call__') else 0

        # Run risk check
        order = None
        if hasattr(risk_manager, 'evaluate') and account:
            try:
                order = risk_manager.evaluate(
                    signal=signal,
                    balance=account.get("balance", 0),
                    equity=account.get("equity", 0),
                    open_positions_count=len(positions),
                    daily_pnl=0,
                )
            except Exception:
                pass

        # Execute the signal on MT5
        direction = signal.get("direction", "")

        if direction == "CLOSE":
            results = await asyncio.to_thread(close_all_positions)
            listener_state["last_trade_results"] = results
            listener_state["signals_executed"] += 1
            log_close(results, message_text)
            print(f"[TRADE] Closed all positions — {len(results)} closed")
        else:
            results = await asyncio.to_thread(execute_signal, signal)
            listener_state["last_trade_results"] = results
            if results:
                listener_state["signals_executed"] += 1
                log_trade(signal, results, message_text, channel_name)
                for r in results:
                    print(f"[TRADE] {r.get('direction', '?')} {r.get('lot', 0)} {r.get('symbol', '?')} ticket={r.get('ticket', '?')}")
            else:
                print(f"[SKIP] Signal rejected or execution failed")

        # Trigger dashboard refresh if callback provided
        if dashboard_callback:
            dashboard_callback()

    print(f"[OK] Listening to {len(channels)} channel(s): {', '.join(listener_state['channels'])}")
    await client.run_until_disconnected()
