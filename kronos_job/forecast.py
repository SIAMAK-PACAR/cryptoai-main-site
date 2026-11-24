"""
kronos_job/forecast.py — runs inside GitHub Actions (never on Render).

Fetches the last ~500 hourly candles for a few coins, runs the open-source
Kronos candlestick model (MIT, github.com/shiyu-coder/Kronos) many times to get
a spread of possible paths for the next 24 hours, and sends a small JSON summary
to the site. The site proves the sender with GitHub's OIDC token, so no secret
has to be stored anywhere.

Output is market direction + a likely range only. No entry points, no buy/sell.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.environ.get("KRONOS_SRC", "kronos-src"))
from model import Kronos, KronosPredictor, KronosTokenizer  # noqa: E402

COINS = [  # symbol, Kraken pair, OKX instId, Coinbase product
    ("BTC", "XBTUSD", "BTC-USDT", "BTC-USD"),
    ("ETH", "ETHUSD", "ETH-USDT", "ETH-USD"),
    ("SOL", "SOLUSD", "SOL-USDT", "SOL-USD"),
    ("XRP", "XRPUSD", "XRP-USDT", "XRP-USD"),
]
LOOKBACK = 480          # hours of history fed to the model (max context is 512)
PRED_LEN = 24           # forecast the next 24 hours
SAMPLES = int(os.environ.get("KRONOS_SAMPLES", "30"))
MODEL = os.environ.get("KRONOS_MODEL", "NeoQuasar/Kronos-small")
TOKENIZER = os.environ.get("KRONOS_TOKENIZER", "NeoQuasar/Kronos-Tokenizer-base")
UA = {"User-Agent": "Mozilla/5.0 (compatible; CryptoAI-forecast/1.0)"}
COLS = ["open", "high", "low", "close", "volume", "amount"]


def _frame(rows):
    df = pd.DataFrame(rows, columns=["timestamps"] + COLS)
    df["timestamps"] = pd.to_datetime(df["timestamps"], unit="s", utc=True).dt.tz_localize(None)
    df[COLS] = df[COLS].astype(float)
    return df.drop_duplicates("timestamps").sort_values("timestamps").reset_index(drop=True)


def kraken(pair):
    r = requests.get("https://api.kraken.com/0/public/OHLC", params={"pair": pair, "interval": 60}, headers=UA, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("error"):
        raise RuntimeError(j["error"])
    data = next(v for k, v in j["result"].items() if k != "last")
    # [time, open, high, low, close, vwap, volume, count]
    return _frame([[int(c[0]), c[1], c[2], c[3], c[4], c[6], float(c[5]) * float(c[6])] for c in data])


def okx(inst):
    rows, after = [], None
    for _ in range(6):  # 100 candles per page
        p = {"instId": inst, "bar": "1H", "limit": 100}
        if after:
            p["after"] = after
        r = requests.get("https://www.okx.com/api/v5/market/history-candles", params=p, headers=UA, timeout=20)
        r.raise_for_status()
        d = r.json().get("data") or []
        if not d:
            break
        # [ts(ms), o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        rows += [[int(c[0]) // 1000, c[1], c[2], c[3], c[4], c[5], c[7]] for c in d]
        after = d[-1][0]
    return _frame(rows)


def coinbase(product):
    rows, end = [], datetime.now(timezone.utc)
    for _ in range(2):  # 300 candles per page
        start = end - timedelta(hours=300)
        r = requests.get(f"https://api.exchange.coinbase.com/products/{product}/candles",
                         params={"granularity": 3600, "start": start.isoformat(), "end": end.isoformat()}, headers=UA, timeout=20)
        r.raise_for_status()
        # [time, low, high, open, close, volume]
        rows += [[c[0], c[3], c[2], c[1], c[4], c[5], c[5] * c[4]] for c in r.json()]
        end = start
    return _frame(rows)


def candles(coin):
    sym, kp, oi, cb = coin
    errors = []
    for name, fn, arg in (("kraken", kraken, kp), ("okx", okx, oi), ("coinbase", coinbase, cb)):
        try:
            df = fn(arg)
            now = pd.Timestamp.utcnow().tz_localize(None).floor("h")
            df = df[df["timestamps"] < now]  # drop the candle that is still forming
            if len(df) >= 200:
                return df.tail(LOOKBACK).reset_index(drop=True), name
            errors.append(f"{name}: only {len(df)} candles")
        except Exception as e:  # try the next exchange
            errors.append(f"{name}: {e}")
    raise RuntimeError(f"{sym}: no candles ({'; '.join(errors)})")


def forecast(predictor, df):
    last_ts = df["timestamps"].iloc[-1]
    y_ts = pd.Series(pd.date_range(last_ts + pd.Timedelta(hours=1), periods=PRED_LEN, freq="h"))
    x_ts = df["timestamps"]
    n = SAMPLES
    preds = predictor.predict_batch(
        df_list=[df[COLS]] * n, x_timestamp_list=[x_ts] * n, y_timestamp_list=[y_ts] * n,
        pred_len=PRED_LEN, T=1.0, top_p=0.9, sample_count=1, verbose=False,
    )
    paths = np.stack([p["close"].to_numpy() for p in preds])      # (n, 24)
    last = float(df["close"].iloc[-1])
    med, p10, p90 = (np.percentile(paths, q, axis=0) for q in (50, 10, 90))
    final = paths[:, -1]
    up_share = float((final > last).mean())
    chg = float(med[-1] / last - 1)
    if up_share >= 0.6 and chg > 0.002:
        bias = "up"
    elif up_share <= 0.4 and chg < -0.002:
        bias = "down"
    else:
        bias = "flat"
    hist = df.tail(48)
    r = lambda a: [round(float(v), 6) for v in a]  # noqa: E731
    return {
        "last": round(last, 6),
        "last_time": last_ts.strftime("%Y-%m-%dT%H:%M:00Z"),
        "bias": bias,
        "up_share": round(up_share, 3),
        "chg_24h": round(chg, 5),
        "range_24h": [round(float(np.percentile(final, 10)), 6), round(float(np.percentile(final, 90)), 6)],
        "history": r(hist["close"]),
        "median": r(med), "p10": r(p10), "p90": r(p90),
    }


def oidc_token(audience):
    url, tok = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL"), os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not tok:
        return None
    r = requests.get(url, params={"audience": audience}, headers={"Authorization": f"bearer {tok}"}, timeout=20)
    r.raise_for_status()
    return r.json()["value"]


def main():
    t0 = time.time()
    tokenizer = KronosTokenizer.from_pretrained(TOKENIZER)
    model = Kronos.from_pretrained(MODEL)
    predictor = KronosPredictor(model, tokenizer, device="cpu", max_context=512)

    out = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "horizon_h": PRED_LEN,
           "samples": SAMPLES, "coins": {}, "errors": {}}
    for coin in COINS:
        try:
            df, source = candles(coin)
            res = forecast(predictor, df)
            res["source"] = source
            out["coins"][coin[0]] = res
            print(f"{coin[0]}: {res['bias']} {res['chg_24h']:+.2%} (up {res['up_share']:.0%}) via {source}", flush=True)
        except Exception as e:
            out["errors"][coin[0]] = str(e)[:300]
            print(f"{coin[0]}: FAILED {e}", flush=True)
    out["runtime_s"] = round(time.time() - t0, 1)

    with open("forecast.json", "w") as f:
        json.dump(out, f)
    if not out["coins"]:
        sys.exit("no coin forecast produced")

    site = os.environ.get("SITE_URL", "https://cryptoai-main-site.onrender.com")
    token = oidc_token("cryptoai-forecast")
    if not token:
        print("no OIDC token (local run) — saved forecast.json only")
        return
    for attempt in range(4):  # the free server may be waking up
        try:
            r = requests.post(f"{site}/api/forecast/ingest", json=out, headers={"Authorization": f"Bearer {token}"}, timeout=90)
            print("site:", r.status_code, r.text[:200])
            if r.ok:
                return
        except Exception as e:
            print("site error:", e)
        time.sleep(30)
    sys.exit("could not deliver the forecast to the site")


if __name__ == "__main__":
    main()
