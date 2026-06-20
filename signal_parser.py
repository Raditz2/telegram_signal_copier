"""
signal_parser.py — Sends Telegram messages to an LLM (DeepSeek / OpenAI-compatible)
for parsing. The LLM determines if a message is a tradeable signal and extracts
direction, entry, SL, TP, and order type. Works with ANY signal provider format.
"""
import json
import httpx
import config


PARSE_PROMPT = """You are a forex signal parser. Analyze the following message from a Telegram forex signal channel and determine if it contains a tradeable signal.

RULES:
1. If the message is a TRADEABLE SIGNAL (contains a clear buy/sell instruction with price levels), extract the data.
2. If the message is commentary, analysis, news, trade updates (like "TP hit", "running in profit"), motivational posts, or anything that is NOT a new trade instruction, return is_signal: false.
3. If the message says "close" or "close all" or "exit", that's a CLOSE signal.
4. "Buy now" or "Sell now" = market order (entry is 0, meaning use current market price)
5. "Buy limit" = pending buy below current price
6. "Sell limit" = pending sell above current price
7. "Buy stop" = pending buy above current price
8. "Sell stop" = pending sell below current price
9. If there are multiple take profits (TP1, TP2, TP3), include all of them.
10. Extract the instrument/pair from the signal (e.g., XAUUSD, EURUSD, BTCUSD). If not clear, use "UNKNOWN".

Respond ONLY with valid JSON, no markdown, no backticks, no explanation. Just the raw JSON object.

If it IS a signal:
{"is_signal": true, "direction": "BUY" or "SELL", "order_type": "MARKET" or "LIMIT" or "STOP", "entry": 4820.00, "sl": 4800.00, "tp": [4840.00, 4860.00], "instrument": "XAUUSD"}

If it's a CLOSE signal:
{"is_signal": true, "direction": "CLOSE", "order_type": "CLOSE", "entry": 0, "sl": 0, "tp": [], "instrument": "XAUUSD"}

If it is NOT a signal:
{"is_signal": false}

Here is the message to analyze:

"""


def parse_signal(message_text: str) -> dict | None:
    """
    Send a message to the LLM for parsing.
    Returns the parsed signal dict or None if parsing fails.
    """
    if not message_text or not message_text.strip():
        return None

    if not config.LLM_API_KEY:
        print("[ERROR] No LLM API key set in .env")
        return None

    try:
        response = httpx.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": "Bearer " + config.LLM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": config.LLM_MODEL,
                "max_tokens": 300,
                "messages": [
                    {
                        "role": "system",
                        "content": PARSE_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": message_text,
                    }
                ],
            },
            timeout=15.0,
        )

        if response.status_code != 200:
            print(f"[ERROR] LLM API returned {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()

        # Clean up in case the LLM wraps it in backticks
        text = text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(text)
        return parsed

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"[ERROR] Failed to parse LLM response: {e}")
        raw = locals().get("text", "N/A")
        print(f"  Raw text: {raw}")
        return None
    except httpx.TimeoutException:
        print("[ERROR] LLM API request timed out")
        return None
    except Exception as e:
        print(f"[ERROR] Signal parsing failed: {e}")
        return None
