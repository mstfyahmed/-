import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime
from pybit.unified_trading import HTTP
import json

# Terminal Design UI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# =========================
# CONFIG (PUT VALUES)
# =========================

TELEGRAM_TOKEN = "8784070781:AAEwYjXS43ZG_vdm-PTnM9eUxSnJafnhkfo"
CHAT_ID = "8338869162"

API_KEY = "SaPMHtTbiMuDYeurDl"
API_SECRET = "JLoWfLUVu2xpZpNeNf2hjok8nQyMs93IpWrx"

SYMBOL = "BTCUSDT"
TIMEFRAME = "15"
QTY = 0.001 

# =========================
# SESSION
# =========================

session = HTTP(
    api_key=API_KEY,
    api_secret=API_SECRET
)

# =========================
# TRADESTREAM ENGINE (CORE)
# =========================

class TradeStreamEngine:
    """Integrated Code Generator and Decision Hub within the Bot."""
    
    @staticmethod
    def generate_tradingview_script(params):
        return f"""//@version=5\nstrategy("TradeStream: Custom", overlay=true)\nrsi = ta.rsi(close, {params.get('rsi', 14)})\nif ta.crossover(rsi, 30)\n    strategy.entry("Long", strategy.long)\nif ta.crossunder(rsi, 70)\n    strategy.close("Long")"""

    @staticmethod
    def log_event(msg, type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if type == "success":
            color = "green"
        elif type == "error":
            color = "red"
        elif type == "warning":
            color = "yellow"
        else:
            color = "cyan"
        console.print(f"[bold white][{timestamp}][/] [bold {color}]{msg.upper()}[/]")

# =========================
# TELEGRAM
# =========================

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# =========================
# MARKET DATA & INDICATORS
# =========================

def get_data():
    try:
        data = session.get_kline(category="linear", symbol=SYMBOL, interval=TIMEFRAME, limit=100)
        candles = data["result"]["list"]
        df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "volume", "turnover"])
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        df = df[::-1].reset_index(drop=True)
        return df
    except Exception as e:
        TradeStreamEngine.log_event(f"Data Fetch Error: {e}", "error")
        return pd.DataFrame()

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =========================
# SIGNAL & TRADE LOGIC
# =========================

def generate_signal(df):
    if df.empty: return None, 0, 0, 0, 0
    
    df["ema50"] = ema(df["close"], 50)
    df["ema200"] = ema(df["close"], 200)
    df["rsi"] = rsi(df["close"])

    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    signal = None
    confidence = 0
    price = last["close"]

    # Simple logic for signal (can be expanded)
    if last["close"] > last["ema200"] and last["rsi"] > 50:
        if prev["rsi"] <= 50:
            signal = "BUY"
            confidence = 85
    elif last["close"] < last["ema200"] and last["rsi"] < 50:
        if prev["rsi"] >= 50:
            signal = "SELL"
            confidence = 80

    sl = price * 0.99 if signal == "BUY" else price * 1.01
    tp = price * 1.02 if signal == "BUY" else price * 0.98

    return signal, confidence, price, sl, tp

# =========================
# UI DASHBOARD GENERATOR
# =========================

def create_dashboard(data_summary, log_lines):
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=5)
    )
    
    layout["main"].split_row(
        Layout(name="market_status"),
        Layout(name="strategy_brain")
    )

    # Header
    layout["header"].update(Panel(f"[bold cyan]TRADESTREAM V3.0[/] | [bold white]{SYMBOL}[/] | [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]", box=box.ROUNDED, style="blue"))

    # Market Status Table
    table = Table(title="Live Market Metrics", box=box.SIMPLE, expand=True)
    table.add_column("Indicator", style="magenta")
    table.add_column("Value", justify="right", style="green")
    table.add_column("Status", style="yellow")
    
    table.add_row("Price", f"{data_summary.get('price', 0):.2f}", "LIVE")
    table.add_row("EMA 50", f"{data_summary.get('ema50', 0):.2f}", "TRENDING")
    table.add_row("RSI (14)", f"{data_summary.get('rsi', 0):.2f}", "NEUTRAL")
    
    layout["market_status"].update(Panel(table, title="[bold]Market Engine[/]"))

    # Strategy Brain
    strat_text = f"[bold]Strategy:[/] Dual EMA + RSI\n[bold]Current Trend:[/] {data_summary.get('trend', 'UNKNOWN')}\n[bold]Signal Alpha:[/] {data_summary.get('signal', 'WAITING')}"
    layout["strategy_brain"].update(Panel(strat_text, title="[bold]Strategy Brain[/]", border_style="cyan"))

    # Logs
    log_content = "\n".join(log_lines[-4:])
    layout["footer"].update(Panel(log_content, title="[bold]Activity Logs[/]", border_style="dim"))

    return layout

# =========================
# MAIN EXECUTION
# =========================

def main():
    log_history = ["Initializing TradeStream Core...", "Engine Active.", "Connecting to Bybit API..."]
    
    with Live(create_dashboard({}, log_history), refresh_per_second=1, screen=True) as live:
        while True:
            try:
                df = get_data()
                if not df.empty:
                    last_row = df.iloc[-1]
                    signal, conf, price, sl, tp = generate_signal(df)
                    
                    trend = "BULLISH" if last_row["close"] > last_row["ema200"] else "BEARISH"
                    
                    data_summary = {
                        "price": price,
                        "ema50": last_row["ema50"] if "ema50" in df else 0,
                        "rsi": last_row["rsi"] if "rsi" in df else 0,
                        "trend": trend,
                        "signal": f"{signal} ({conf}%)" if signal else "SCANNING..."
                    }
                    
                    if signal:
                        log_history.append(f"SIGNAL DETECTED: {signal} @ {price}")
                        send_telegram(f"🚀 TradeStream Signal\n{signal} {SYMBOL}\nPrice: {price}\nSL: {sl}\nTP: {tp}")
                        
                        # Automated Execution Logic
                        # session.place_order(...) 

                    live.update(create_dashboard(data_summary, log_history))
                
                time.sleep(10)
            except Exception as e:
                log_history.append(f"CRITICAL ERROR: {str(e)[:40]}...")
                time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("[bold red]Bot Terminated by User.[/]")
