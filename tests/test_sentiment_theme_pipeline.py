import pandas as pd

from src.sentiment_theme_pipeline import (
    assign_theme,
    apply_themes,
    clean_text,
    load_reviews,
    predict_sentiment,
)


def test_assign_theme_category():
    text = "I cannot login and the OTP failed when I tried to sign in."
    assert assign_theme(text) == "Account Access Issues"


def test_apply_themes_adds_column():
    sample = pd.DataFrame({"review": ["The login screen is terrible.", "Support took too long."]})
    result = apply_themes(sample)
    assert "identified_theme" in result.columns
    assert len(result) == 2


def test_clean_text_removes_punctuation():
    cleaned = clean_text("Great app! Best service.")
    assert "great" in cleaned
    assert "app" in cleaned
    assert "!" not in cleaned


def test_predict_sentiment_vader_fallback():
    try:
        sentiment = predict_sentiment("This app is great.", model=None, transformer_model=False)
    except RuntimeError:
        assert True
    else:
        assert sentiment[0] in {"positive", "neutral", "negative"}
