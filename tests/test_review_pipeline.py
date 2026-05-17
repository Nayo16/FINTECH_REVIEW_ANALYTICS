import pandas as pd

from src.review_pipeline import clean_reviews_df, normalize_date


def test_normalize_date_with_string():
    assert normalize_date("2024-05-01") == "2024-05-01"
    assert normalize_date("May 1, 2024") == "2024-05-01"
    assert normalize_date("1 May 2024") == "2024-05-01"


def test_clean_reviews_df_removes_empty_and_duplicates():
    raw = pd.DataFrame(
        [
            {"review": "Great app", "rating": 5, "date": "2024-05-01", "bank": "CBE", "source": "Google Play"},
            {"review": "Great app", "rating": 5, "date": "2024-05-01", "bank": "CBE", "source": "Google Play"},
            {"review": "", "rating": 4, "date": "2024-05-02", "bank": "CBE", "source": "Google Play"},
            {"review": "Needs improvement", "rating": None, "date": "2024-05-03", "bank": "CBE", "source": "Google Play"},
            {"review": "Crashes on load", "rating": 2, "date": "May 3, 2024", "bank": "CBE", "source": "Google Play"},
        ]
    )

    clean = clean_reviews_df(raw)
    assert len(clean) == 2
    assert "Great app" in clean["review"].values
    assert "Crashes on load" in clean["review"].values
    assert all(clean["date"] == "2024-05-01") or "2024-05-03" in clean["date"].values
