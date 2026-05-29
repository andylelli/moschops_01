"""
Feature store: database-backed cache for computed feature DataFrames.

Connects to PostgreSQL via DATABASE_URL environment variable, or falls back
to a local SQLite file (feature_store.sqlite in the training/ directory) when
DATABASE_URL is not set.

One row is stored per (symbol, timeframe, schema_version, bar_close_utc).
Feature values are serialised as a JSON object so the schema is version-agnostic.

Usage:
    from feature_store import FeatureStore

    store = FeatureStore()

    # Persist computed features for EURUSD D1 bars
    n = store.save(df, symbol="EURUSD", timeframe="D1", schema_version="v2")

    # Load back (returns None on cache miss)
    df_cached = store.load("EURUSD", "D1", "v2", start_date="2025-01-01")
    if df_cached is not None:
        print(f"Cache hit: {len(df_cached)} bars")

    # Check existence without loading
    if store.exists("EURUSD", "D1", "v2"):
        print("already computed")
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_DEFAULT_SQLITE = str(Path(__file__).parent / "feature_store.sqlite")

# DDL templates — PostgreSQL uses SERIAL and ON CONFLICT DO NOTHING;
# SQLite uses AUTOINCREMENT and INSERT OR IGNORE.
_DDL_PG = """
CREATE TABLE IF NOT EXISTS feature_cache (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR(32)  NOT NULL,
    timeframe       VARCHAR(16)  NOT NULL,
    schema_version  VARCHAR(16)  NOT NULL,
    bar_close_utc   TIMESTAMP    NOT NULL,
    features_json   TEXT         NOT NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, timeframe, schema_version, bar_close_utc)
)
"""

_DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS feature_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    timeframe       TEXT NOT NULL,
    schema_version  TEXT NOT NULL,
    bar_close_utc   TEXT NOT NULL,
    features_json   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE (symbol, timeframe, schema_version, bar_close_utc)
)
"""


def _get_engine(db_url: str | None = None):
    from sqlalchemy import create_engine  # noqa: PLC0415
    url = db_url or os.getenv("DATABASE_URL") or f"sqlite:///{_DEFAULT_SQLITE}"
    return create_engine(url, pool_pre_ping=True)


def _ensure_table(engine) -> None:
    from sqlalchemy import text  # noqa: PLC0415
    ddl = _DDL_SQLITE if engine.dialect.name == "sqlite" else _DDL_PG
    with engine.begin() as conn:
        conn.execute(text(ddl))


class FeatureStore:
    """
    Database-backed cache for computed feature rows.

    Parameters
    ----------
    db_url : str | None — SQLAlchemy connection URL.  If None, uses
             DATABASE_URL env var or falls back to local SQLite.
    """

    def __init__(self, db_url: str | None = None) -> None:
        self._engine = _get_engine(db_url)
        _ensure_table(self._engine)

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        schema_version: str = "v2",
        bar_time_col: str | None = None,
    ) -> int:
        """
        Persist df rows to the cache.

        Rows with duplicate (symbol, timeframe, schema_version, bar_close_utc)
        are silently skipped (insert-ignore / on-conflict-do-nothing).

        The bar timestamp is resolved in this priority order:
        1. bar_time_col parameter (column name in df)
        2. DatetimeIndex of df
        3. 'bar_close_utc' column

        Parameters
        ----------
        df             : pd.DataFrame of feature values (one row per bar)
        symbol         : str — e.g. "EURUSD"
        timeframe      : str — e.g. "D1"
        schema_version : str — e.g. "v2"
        bar_time_col   : str | None — explicit timestamp column name

        Returns
        -------
        int — number of rows passed to the insert statement.
        """
        from sqlalchemy import text  # noqa: PLC0415

        # Resolve timestamps
        if bar_time_col is not None:
            times = df[bar_time_col].astype(str).tolist()
            feature_cols = [c for c in df.columns if c != bar_time_col]
        elif isinstance(df.index, pd.DatetimeIndex):
            times = df.index.astype(str).tolist()
            feature_cols = list(df.columns)
        elif "bar_close_utc" in df.columns:
            times = df["bar_close_utc"].astype(str).tolist()
            feature_cols = [c for c in df.columns if c != "bar_close_utc"]
        else:
            raise ValueError(
                "Cannot resolve bar timestamp. "
                "Use a DatetimeIndex, pass bar_time_col, or include a 'bar_close_utc' column."
            )

        now_str = datetime.now(timezone.utc).isoformat()
        dialect = self._engine.dialect.name
        insert_sql = (
            "INSERT OR IGNORE INTO feature_cache "
            "(symbol, timeframe, schema_version, bar_close_utc, features_json, created_at) "
            "VALUES (:symbol, :timeframe, :schema_version, :bar_close_utc, :features_json, :created_at)"
            if dialect == "sqlite"
            else
            "INSERT INTO feature_cache "
            "(symbol, timeframe, schema_version, bar_close_utc, features_json, created_at) "
            "VALUES (:symbol, :timeframe, :schema_version, :bar_close_utc, :features_json, :created_at) "
            "ON CONFLICT DO NOTHING"
        )

        with self._engine.begin() as conn:
            for i, t in enumerate(times):
                row = df.iloc[i][feature_cols].replace([np.inf, -np.inf], np.nan)
                features_json = json.dumps(
                    row.where(row.notna(), other=None).to_dict()
                )
                conn.execute(text(insert_sql), {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "schema_version": schema_version,
                    "bar_close_utc": t,
                    "features_json": features_json,
                    "created_at": now_str,
                })

        return len(times)

    # ── Read ──────────────────────────────────────────────────────────────────

    def load(
        self,
        symbol: str,
        timeframe: str,
        schema_version: str = "v2",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame | None:
        """
        Load cached feature rows for (symbol, timeframe, schema_version).

        Parameters
        ----------
        start_date : str | None — ISO date/datetime string, inclusive lower bound
        end_date   : str | None — ISO date/datetime string, inclusive upper bound

        Returns
        -------
        pd.DataFrame indexed by bar_close_utc (UTC DatetimeIndex), or None if
        no rows exist.
        """
        from sqlalchemy import text  # noqa: PLC0415

        # Build parameterised WHERE clause from static fragments only
        where = (
            "symbol = :symbol "
            "AND timeframe = :timeframe "
            "AND schema_version = :schema_version"
        )
        params: dict = {
            "symbol": symbol,
            "timeframe": timeframe,
            "schema_version": schema_version,
        }
        if start_date:
            where += " AND bar_close_utc >= :start_date"
            params["start_date"] = start_date
        if end_date:
            where += " AND bar_close_utc <= :end_date"
            params["end_date"] = end_date

        sql = (
            "SELECT bar_close_utc, features_json FROM feature_cache "
            f"WHERE {where} ORDER BY bar_close_utc"
        )

        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()

        if not rows:
            return None

        records = []
        for bar_close_utc, features_json in rows:
            rec = json.loads(features_json)
            rec["bar_close_utc"] = bar_close_utc
            records.append(rec)

        result = pd.DataFrame(records)
        result["bar_close_utc"] = pd.to_datetime(result["bar_close_utc"], utc=True)
        return result.set_index("bar_close_utc").sort_index()

    # ── Existence / housekeeping ───────────────────────────────────────────────

    def exists(
        self,
        symbol: str,
        timeframe: str,
        schema_version: str = "v2",
    ) -> bool:
        """Return True if any rows exist for the given key."""
        from sqlalchemy import text  # noqa: PLC0415
        sql = (
            "SELECT 1 FROM feature_cache "
            "WHERE symbol = :symbol AND timeframe = :timeframe "
            "AND schema_version = :schema_version LIMIT 1"
        )
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {"symbol": symbol, "timeframe": timeframe, "schema_version": schema_version},
            ).fetchone()
        return row is not None

    def delete(
        self,
        symbol: str,
        timeframe: str,
        schema_version: str = "v2",
    ) -> int:
        """
        Delete all rows for the given (symbol, timeframe, schema_version).

        Returns the number of rows deleted.
        """
        from sqlalchemy import text  # noqa: PLC0415
        sql = (
            "DELETE FROM feature_cache "
            "WHERE symbol = :symbol AND timeframe = :timeframe "
            "AND schema_version = :schema_version"
        )
        with self._engine.begin() as conn:
            result = conn.execute(
                text(sql),
                {"symbol": symbol, "timeframe": timeframe, "schema_version": schema_version},
            )
        return result.rowcount
