"""
mt5_executor.py — Connects to MetaTrader 5, places trades,
manages positions, and handles order types.
"""

import MetaTrader5 as mt5
import time
import config


def connect():
    """Initialize MT5 and log in."""
    if not mt5.initialize():
        print(f"[ERROR] MT5 initialize failed: {mt5.last_error()}")
        return False

    if not mt5.login(config.MT5_ACCOUNT, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print(f"[ERROR] MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return False

    # Select the configured default symbol
    if config.DEFAULT_SYMBOL and not mt5.symbol_select(config.DEFAULT_SYMBOL, True):
        print(f"[WARN] Failed to select {config.DEFAULT_SYMBOL}")

    return True


def disconnect():
    """Shut down MT5 connection."""
    mt5.shutdown()


def is_connected():
    """Check if MT5 is still connected."""
    info = mt5.account_info()
    return info is not None


def reconnect():
    """Try to reconnect to MT5."""
    disconnect()
    time.sleep(2)
    return connect()


def get_account_info():
    """Return account info dict or None."""
    info = mt5.account_info()
    if info is None:
        return None
    return {
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "profit": info.profit,
        "leverage": info.leverage,
        "name": info.name,
        "server": info.server,
        "currency": info.currency,
    }


def get_daily_pnl():
    """Get today's profit/loss from closed deals."""
    import datetime as dt
    today_start = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    history = mt5.history_deals_get(today_start, dt.datetime.now())
    if history is None:
        return 0.0
    return sum(d.profit + d.swap + d.commission for d in history if d.profit is not None) if history else 0.0


def get_tick(instrument=None):
    """Get current bid/ask for the symbol."""
    return mt5.symbol_info_tick(instrument or config.DEFAULT_SYMBOL)


def get_symbol_info(instrument=None):
    """Get symbol details."""
    return mt5.symbol_info(instrument or config.DEFAULT_SYMBOL)


def get_open_positions(instrument=None):
    """Return all open positions placed by this bot."""
    if instrument:
        positions = mt5.positions_get(symbol=instrument)
    else:
        positions = mt5.positions_get()
    if positions is None:
        return []
    return [p for p in positions if p.magic == config.MAGIC_NUMBER]


def execute_signal(signal: dict) -> list:
    """
    Execute a parsed signal on MT5.
    Handles market orders, pending orders, and close signals.
    Returns a list of trade results (one per TP split).
    """
    if not is_connected():
        if not reconnect():
            print("[ERROR] Cannot reconnect to MT5")
            return []

    direction = signal.get("direction", "")
    order_type = signal.get("order_type", "")
    entry = signal.get("entry", 0)
    sl = signal.get("sl", 0)
    tp_list = signal.get("tp", [])
    instrument = signal.get("instrument", config.DEFAULT_SYMBOL)

    # Handle close signal
    if direction == "CLOSE" or order_type == "CLOSE":
        return close_all_positions()

    # Select the instrument symbol
    if not mt5.symbol_select(instrument, True):
        print(f"[ERROR] Failed to select symbol {instrument}")
        return []

    # If no TPs provided, use entry as single TP (no TP set)
    if not tp_list:
        tp_list = [0]

    # Calculate lot size per TP
    num_splits = len(tp_list)
    lot_per_tp = round(config.DEFAULT_LOT_SIZE / num_splits, 2)
    if lot_per_tp < config.MIN_LOT:
        lot_per_tp = config.MIN_LOT

    # Get current price
    tick = get_tick(instrument)
    if tick is None:
        print(f"[ERROR] Cannot get tick data for {instrument}")
        return []

    sym_info = get_symbol_info(instrument)
    if sym_info is None:
        print(f"[ERROR] Cannot get symbol info for {instrument}")
        return []

    digits = sym_info.digits

    results = []

    for i, tp in enumerate(tp_list):
        # Determine order type and price
        if direction == "BUY":
            current_price = tick.ask

            if order_type == "MARKET" or entry == 0:
                # Market buy
                mt5_type = mt5.ORDER_TYPE_BUY
                price = current_price
            elif order_type == "LIMIT":
                # Buy limit (entry below current price)
                mt5_type = mt5.ORDER_TYPE_BUY_LIMIT
                price = entry
            elif order_type == "STOP":
                # Buy stop (entry above current price)
                mt5_type = mt5.ORDER_TYPE_BUY_STOP
                price = entry
            else:
                # Auto-detect: if entry is close to current price, market order
                if abs(current_price - entry) <= config.MARKET_ORDER_THRESHOLD * sym_info.point:
                    mt5_type = mt5.ORDER_TYPE_BUY
                    price = current_price
                elif entry < current_price:
                    mt5_type = mt5.ORDER_TYPE_BUY_LIMIT
                    price = entry
                else:
                    mt5_type = mt5.ORDER_TYPE_BUY_STOP
                    price = entry

        elif direction == "SELL":
            current_price = tick.bid

            if order_type == "MARKET" or entry == 0:
                mt5_type = mt5.ORDER_TYPE_SELL
                price = current_price
            elif order_type == "LIMIT":
                mt5_type = mt5.ORDER_TYPE_SELL_LIMIT
                price = entry
            elif order_type == "STOP":
                mt5_type = mt5.ORDER_TYPE_SELL_STOP
                price = entry
            else:
                if abs(current_price - entry) <= config.MARKET_ORDER_THRESHOLD * sym_info.point:
                    mt5_type = mt5.ORDER_TYPE_SELL
                    price = current_price
                elif entry > current_price:
                    mt5_type = mt5.ORDER_TYPE_SELL_LIMIT
                    price = entry
                else:
                    mt5_type = mt5.ORDER_TYPE_SELL_STOP
                    price = entry
        else:
            print(f"[ERROR] Unknown direction: {direction}")
            return results

        # Build the order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL if mt5_type in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL) else mt5.TRADE_ACTION_PENDING,
            "symbol": instrument,
            "volume": lot_per_tp,
            "type": mt5_type,
            "price": round(price, digits),
            "sl": round(sl, digits) if sl else 0,
            "tp": round(tp, digits) if tp else 0,
            "deviation": config.DEVIATION,
            "magic": config.MAGIC_NUMBER,
            "comment": f"AI-Copier TP{i+1}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None:
            print(f"[ERROR] Order send returned None: {mt5.last_error()}")
        elif result.retcode == mt5.TRADE_RETCODE_DONE:
            order_type_name = get_order_type_name(mt5_type)
            results.append({
                "ticket": result.order,
                "symbol": instrument,
                "type": order_type_name,
                "direction": direction,
                "entry": round(price, digits),
                "sl": round(sl, digits) if sl else 0,
                "tp": round(tp, digits) if tp else 0,
                "lot": lot_per_tp,
                "tp_number": i + 1,
            })
        else:
            print(f"[ERROR] Order failed: retcode={result.retcode}")

    return results


def close_all_positions() -> list:
    """Close all positions opened by this bot."""
    positions = get_open_positions()
    results = []

    for pos in positions:
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            continue

        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            close_price = tick.bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            close_price = tick.ask

        sym_info = mt5.symbol_info(pos.symbol)
        digits = sym_info.digits if sym_info else 2

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": round(close_price, digits),
            "deviation": config.DEVIATION,
            "magic": config.MAGIC_NUMBER,
            "comment": "AI-Copier Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "position": pos.ticket,
        }

        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            direction = "LONG" if pos.type == mt5.ORDER_TYPE_BUY else "SHORT"
            results.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "direction": direction,
                "entry": pos.price_open,
                "exit": close_price,
                "pnl": pos.profit,
                "action": "CLOSED",
            })

    return results


def get_order_type_name(mt5_type):
    """Return a readable name for the order type."""
    names = {
        mt5.ORDER_TYPE_BUY: "Market Buy",
        mt5.ORDER_TYPE_SELL: "Market Sell",
        mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit",
        mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit",
        mt5.ORDER_TYPE_BUY_STOP: "Buy Stop",
        mt5.ORDER_TYPE_SELL_STOP: "Sell Stop",
    }
    return names.get(mt5_type, "Unknown")
