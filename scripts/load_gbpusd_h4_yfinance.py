"""
Load GBPUSD H4 historical data from yfinance into HistoricalBar.

yfinance provides ~2.75 years of free H1 forex data.
We aggregate H1 → H4 buckets (UTC-aligned on 0,4,8,12,16,20h boundaries)
and insert with conflict-skip so the script is idempotent.

Usage:
    python scripts/load_gbpusd_h4_yfinance.py
"""

import sys
import os
import uuid
import json
from datetime import datetime, timezone

import yfinance as yf
import pandas as pd
import psycopg2

# ── config ────────────────────────────────────────────────────────────────────
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5434/moschops",
)
SYMBOL = "GBPUSD"
TIMEFRAME = "H4"
YF_TICKER = "GBPUSD=X"
SOURCE = "YFINANCE"


def fetch_h1() -> pd.DataFrame:
    """Download all available GBPUSD H1 bars from yfinance."""
    print(f"Downloading {YF_TICKER} H1 from yfinance …", flush=True)
    df = yf.download(YF_TICKER, period="730d", interval="1h", progress=False, auto_adjust=True)
    if df.empty:
        raise RuntimeError("yfinance returned no data")

    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    print(f"  H1 rows: {len(df)}  range: {df.index.min()} → {df.index.max()}", flush=True)
    return df[["open", "high", "low", "close", "volume"]]


def aggregate_h1_to_h4(h1: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate H1 bars into UTC-aligned H4 buckets.
    Bucket starts: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC.
    barCloseTimeUtc is the close time of the last H1 bar in the bucket.
    """
    h1 = h1.copy()
    h1.index = h1.index.tz_convert("UTC")

    # Assign each H1 bar to its H4 bucket (floor to nearest 4h)
    h1["bucket"] = h1.index.floor("4h")

    groups = h1.groupby("bucket")
    rows = []
    for bucket_start, grp in groups:
        if len(grp) == 0:
            continue
        grp = grp.sort_index()
        # The barCloseTimeUtc convention used by the system = end of the last bar
        # (i.e., H4 bucket_start + 4h, but we use the actual last H1 close ts + 1h)
        last_bar_open = grp.index[-1]
        bar_close = last_bar_open + pd.Timedelta(hours=1)

        rows.append(
            {
                "barCloseTimeUtc": bar_close.to_pydatetime().replace(tzinfo=None),
                "open": float(grp["open"].iloc[0]),
                "high": float(grp["high"].max()),
                "low": float(grp["low"].min()),
                "close": float(grp["close"].iloc[-1]),
                "volume": float(grp["volume"].sum()),
            }
        )

    h4 = pd.DataFrame(rows).sort_values("barCloseTimeUtc").reset_index(drop=True)
    print(f"  H4 rows after aggregation: {len(h4)}  range: {h4['barCloseTimeUtc'].min()} → {h4['barCloseTimeUtc'].max()}", flush=True)
    return h4


def insert_h4(h4: pd.DataFrame) -> None:
    """Bulk-insert H4 bars into HistoricalBar, skipping conflicts."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    sql = """
        INSERT INTO "HistoricalBar"
            (id, source, symbol, timeframe, "barCloseTimeUtc", open, high, low, close, volume, "rawJson", "createdAt")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source, symbol, timeframe, "barCloseTimeUtc") DO NOTHING
    """

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    inserted = 0
    skipped = 0

    for _, row in h4.iterrows():
        bar_id = str(uuid.uuid4()).replace("-", "")[:25]
        raw = json.dumps({"source": "yfinance_h1_agg"})
        cur.execute(
            sql,
            (
                bar_id,
                SOURCE,
                SYMBOL,
                TIMEFRAME,
                row["barCloseTimeUtc"],
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"] if row["volume"] > 0 else None,
                raw,
                now,
            ),
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted: {inserted}  Skipped (already existed): {skipped}", flush=True)


def main() -> None:
    h1 = fetch_h1()
    h4 = aggregate_h1_to_h4(h1)
    insert_h4(h4)

    # Summary
    print(f"\nDone. {len(h4)} H4 bars for {SYMBOL} loaded (source={SOURCE}).")
    print("Run training with:")
    print(
        f"  --symbol {SYMBOL} --timeframe {TIMEFRAME} "
        f"--train-start {h4['barCloseTimeUtc'].min().strftime('%Y-%m-%d')} ..."
    )


if __name__ == "__main__":
    main()
