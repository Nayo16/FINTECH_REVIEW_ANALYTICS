import csv
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from google_play_scraper import Sort, reviews


APP_MAP = {
    "prod.cbe.birr": "Commercial Bank of Ethiopia Mobile",
    "com.boa.boaMobileBanking": "Bank of Abyssinia Mobile App",
    "com.dashen.dashensuperapp": "Dashen Bank Mobile Banking",
}

OUTPUT_PATH = "data/raw/clean_reviews.csv"


def normalize_date(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    for fmt in ["%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%Y/%m/%d"]:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    try:
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date().isoformat()
    except Exception:
        return None


def fetch_google_play_reviews(
    app_id: str,
    bank_name: str,
    count: int = 600,
    lang: str = "en",
    country: str = "us",
) -> pd.DataFrame:
    all_reviews: List[Dict] = []
    batch_size = 200
    continuation_token = None

    while len(all_reviews) < count:
        try:
            batch, continuation_token = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=batch_size,
                filter_score_with=None,
                continuation_token=continuation_token,
            )
        except Exception as exc:
            print(f"Warning: Failed to fetch reviews for {bank_name}: {exc}")
            break

        if not batch:
            break

        for item in batch:
            all_reviews.append(
                {
                    "review": item.get("content", "").strip(),
                    "rating": item.get("score"),
                    "date": item.get("at"),
                    "bank": bank_name,
                    "source": "Google Play",
                }
            )

        if continuation_token is None:
            break

    df = pd.DataFrame(all_reviews[:count])
    return df


def clean_reviews_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    initial_count = len(df)

    df["review"] = df["review"].astype(str).str.strip()
    df = df[df["review"].astype(bool)]
    df = df[df["rating"].notna()]

    df["date"] = df["date"].apply(lambda value: normalize_date(value))
    df = df[df["date"].notna()]

    df = df.drop_duplicates(subset=["review", "bank", "rating", "date"])
    final_count = len(df)
    print(f"Cleaned reviews: {initial_count} -> {final_count} rows")

    df = df[["review", "rating", "date", "bank", "source"]]
    return df


def save_reviews(df: pd.DataFrame, path: str = OUTPUT_PATH) -> None:
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"Saved cleaned review dataset to {path}")


def collect_and_save_all_reviews() -> pd.DataFrame:
    frames: List[pd.DataFrame] = []

    for app_id, bank_name in APP_MAP.items():
        print(f"Fetching reviews for {bank_name} ({app_id})")
        df = fetch_google_play_reviews(app_id, bank_name)
        if df.empty:
            print(f"No reviews fetched for {bank_name}")
            continue
        frames.append(df)

    if not frames:
        raise RuntimeError("No reviews were fetched for any app.")

    raw_df = pd.concat(frames, ignore_index=True)
    clean_df = clean_reviews_df(raw_df)
    save_reviews(clean_df)
    return clean_df


if __name__ == "__main__":
    collect_and_save_all_reviews()
