import argparse
import os
from pathlib import Path
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

BANK_APP_METADATA: Dict[str, str] = {
    "Commercial Bank of Ethiopia Mobile": "Commercial Bank of Ethiopia Mobile",
    "Bank of Abyssinia Mobile App": "Bank of Abyssinia Mobile App",
    "Dashen Bank Mobile Banking": "Dashen Bank Mobile Banking",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS banks (
    bank_id SERIAL PRIMARY KEY,
    bank_name TEXT UNIQUE NOT NULL,
    app_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    bank_id INTEGER NOT NULL REFERENCES banks(bank_id),
    review_text TEXT NOT NULL,
    rating INTEGER,
    review_date DATE,
    sentiment_label TEXT,
    sentiment_score REAL,
    identified_theme TEXT,
    source TEXT
);
"""

DEFAULT_CSV = Path("data/processed/review_analysis.csv")


def load_processed_reviews(path: Path = DEFAULT_CSV) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Processed review file not found at {path}")
    df = pd.read_csv(path)
    df = df.dropna(subset=["review_id", "review", "bank"])
    return df


def create_database_engine(db_url: str) -> Engine:
    return create_engine(db_url, future=True)


def create_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))


def insert_banks(engine: Engine, df: pd.DataFrame) -> None:
    banks = df["bank"].dropna().unique().tolist()
    rows = [
        {
            "bank_name": bank,
            "app_name": BANK_APP_METADATA.get(bank, bank),
        }
        for bank in banks
    ]
    insert_sql = text(
        "INSERT INTO banks (bank_name, app_name) VALUES (:bank_name, :app_name) ON CONFLICT (bank_name) DO NOTHING"
    )
    with engine.begin() as conn:
        for row in rows:
            conn.execute(insert_sql, row)


def get_bank_ids(engine: Engine) -> Dict[str, int]:
    with engine.begin() as conn:
        result = conn.execute(text("SELECT bank_id, bank_name FROM banks"))
        return {row["bank_name"]: row["bank_id"] for row in result}


def insert_reviews(engine: Engine, df: pd.DataFrame) -> None:
    bank_ids = get_bank_ids(engine)
    insert_sql = text(
        "INSERT INTO reviews (review_id, bank_id, review_text, rating, review_date, sentiment_label, sentiment_score, identified_theme, source)"
        " VALUES (:review_id, :bank_id, :review_text, :rating, :review_date, :sentiment_label, :sentiment_score, :identified_theme, :source)"
        " ON CONFLICT (review_id) DO UPDATE SET"
        " review_text = EXCLUDED.review_text,"
        " rating = EXCLUDED.rating,"
        " review_date = EXCLUDED.review_date,"
        " sentiment_label = EXCLUDED.sentiment_label,"
        " sentiment_score = EXCLUDED.sentiment_score,"
        " identified_theme = EXCLUDED.identified_theme,"
        " source = EXCLUDED.source"
    )

    with engine.begin() as conn:
        for _, row in df.iterrows():
            bank_id = bank_ids.get(row["bank"])
            if bank_id is None:
                continue
            conn.execute(
                insert_sql,
                {
                    "review_id": row["review_id"],
                    "bank_id": bank_id,
                    "review_text": row["review"],
                    "rating": int(row["rating"]) if not pd.isna(row["rating"]) else None,
                    "review_date": row["date"],
                    "sentiment_label": row.get("sentiment_label"),
                    "sentiment_score": float(row["sentiment_score"]) if not pd.isna(row.get("sentiment_score")) else None,
                    "identified_theme": row.get("identified_theme"),
                    "source": row.get("source"),
                },
            )


def verify_database(engine: Engine) -> None:
    queries = {
        "reviews_per_bank": "SELECT bank_name, count(r.review_id) AS review_count FROM reviews r JOIN banks b ON r.bank_id = b.bank_id GROUP BY bank_name ORDER BY review_count DESC;",
        "average_rating_per_bank": "SELECT bank_name, AVG(rating) AS avg_rating FROM reviews r JOIN banks b ON r.bank_id = b.bank_id GROUP BY bank_name ORDER BY avg_rating DESC;",
        "null_counts": "SELECT SUM(CASE WHEN review_id IS NULL THEN 1 ELSE 0 END) AS missing_review_id, SUM(CASE WHEN review_text IS NULL THEN 1 ELSE 0 END) AS missing_review_text, SUM(CASE WHEN bank_id IS NULL THEN 1 ELSE 0 END) AS missing_bank_id FROM reviews;",
    }
    with engine.begin() as conn:
        for label, sql in queries.items():
            print(f"--- {label} ---")
            result = conn.execute(text(sql))
            for row in result:
                print(dict(row))
            print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load processed review data into PostgreSQL")
    parser.add_argument(
        "--db-url",
        default=os.getenv("BANK_REVIEWS_DB_URL"),
        help="SQLAlchemy database URL, for example postgresql+psycopg2://user:pass@localhost:5432/bank_reviews",
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help="Path to processed review analysis CSV file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.db_url:
        raise ValueError("Database URL must be provided through --db-url or BANK_REVIEWS_DB_URL")

    df = load_processed_reviews(Path(args.csv))
    engine = create_database_engine(args.db_url)
    create_schema(engine)
    insert_banks(engine, df)
    insert_reviews(engine, df)
    verify_database(engine)


if __name__ == "__main__":
    main()
