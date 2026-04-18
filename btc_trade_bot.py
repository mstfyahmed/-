import requests
import time
import pandas as pd
from pybit.unified_trading import HTTP

# =========================
# CONFIG (PUT VALUES)
# =========================

TELEGRAM_TOKEN = "8784070781:AAEwYjXS43ZG_vdm-PTnM9eUxSnJafnhkfo"
CHAT_ID = "8338869162"

API_KEY = "SaPMHtTbiMuDYeurDl"
API_SECRET = "JLoWfLUVu2xpZpNeNf2hjok8nQyMs93IpWrx"

SYMBOL = "BTCUSDT"
TIMEFRAME = "15"

# =========================
# SESSION
# =========================

session = HTTP(
    api_key=API_KEY,
    api_secret=API_SECRET
)

# =========================
# TELEGRAM
# =========================

def send_telegram(msg):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    requests.post(url,data=data)

# =========================
# MARKET DATA
# =========================

def get_data():

    data = session.get_kline(
        category="linear",
        symbol=SYMBOL,
        interval=TIMEFRAME,
        limit=200
    )

    candles = data["result"]["list"]

    df = pd.DataFrame(candles)

    df = df.iloc[:,0:6]

    df.columns = ["time","open","high","low","close","volume"]

    df[["open","high","low","close"]] = df[["open","high","low","close"]].astype(float)

    df = df[::-1]

    df.reset_index(drop=True,inplace=True)

    return df

# =========================
# INDICATORS
# =========================

def ema(series,period):
    return series.ewm(span=period).mean()

def rsi(series,period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    return 100-(100/(1+rs))

# =========================
# SIGNAL LOGIC
# =========================

def generate_signal():

    df = get_data()

    df["ema50"] = ema(df["close"],50)
    df["ema200"] = ema(df["close"],200)
    df["rsi"] = rsi(df["close"])

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = last["close"]

    confidence = 0

    # Trend detection
    if last["ema50"] > last["ema200"]:
        trend = "BULLISH"
        confidence += 30
    else:
        trend = "BEARISH"
        confidence += 30

    # RSI signal
    if last["rsi"] > 55:
        signal = "BUY"
        confidence += 30
    elif last["rsi"] < 45:
        signal = "SELL"
        confidence += 30
    else:
        signal = None

    # Candle strength
    if last["close"] > last["open"]:
        confidence += 20

    if signal is None:
        return None,None,None,None,None,None

    entry = price

    if signal == "BUY":

        sl = prev["low"]

        tp = entry + (entry - sl)

    else:

        sl = prev["high"]

        tp = entry - (sl - entry)

    move = abs(tp-entry)

    return signal,trend,entry,sl,tp,confidence

# =========================
# RUN
# =========================

def run():

    signal,trend,entry,sl,tp,confidence = generate_signal()

    if signal is None:
        return

    msg=f"""
🚀 BTC SIGNAL BOT

Symbol : BTCUSDT

Direction : {signal}

Entry : {round(entry,2)}

Stop Loss : {round(sl,2)}

Take Profit : {round(tp,2)}

Trend : {trend}

Confidence : {confidence}%

Strategy : EMA + RSI
Timeframe : 15m
"""

    send_telegram(msg)

    print("Signal Sent")

# =========================
# LOOP
# =========================

while True:

    try:

        print("Scanning Market...")

        run()

    except Exception as e:

        print("Error:",e)

    time.sleep(300)
