import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from transformers import Pipeline, pipeline
except ImportError:  # pragma: no cover
    Pipeline = None
    pipeline = None

try:
    import spacy
    from spacy.language import Language
except ImportError:  # pragma: no cover
    spacy = None
    Language = None

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize
except ImportError:  # pragma: no cover
    nltk = None
    stopwords = None
    SentimentIntensityAnalyzer = None
    word_tokenize = None

RAW_CSV_PATH = Path("data/raw/clean_reviews.csv")
PROCESSED_CSV_PATH = Path("data/processed/review_analysis.csv")
THEME_KEYWORDS = {
    "Account Access Issues": [
        "login",
        "log in",
        "sign in",
        "password",
        "otp",
        "authentication",
        "account access",
        "fingerprint",
        "biometric",
        "blocked",
        "locked",
    ],
    "Transaction Performance": [
        "transfer",
        "sent",
        "failed",
        "slow",
        "delay",
        "payment",
        "transaction",
        "processing",
        "withdrawal",
        "deposit",
        "disconnect",
    ],
    "UI & Design": [
        "interface",
        "ui",
        "design",
        "layout",
        "navigation",
        "experience",
        "screen",
        "buttons",
        "menu",
        "feedback",
    ],
    "Customer Support": [
        "support",
        "help",
        "customer service",
        "agent",
        "call center",
        "response",
        "complaint",
        "service",
        "chat",
    ],
    "Feature Requests": [
        "feature",
        "notification",
        "statement",
        "alerts",
        "bill pay",
        "account summary",
        "budget",
        "investment",
        "multi-currency",
        "qr code",
    ],
}


def load_reviews(path: Optional[Path] = None) -> pd.DataFrame:
    path = Path(path or RAW_CSV_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Clean review CSV not found at {path}")

    df = pd.read_csv(path)
    df = df.dropna(subset=["review", "rating", "date", "bank"])
    df = df.reset_index(drop=True)
    if "review_id" not in df.columns:
        df["review_id"] = [f"rev_{i+1}" for i in df.index]
    return df[["review_id", "review", "rating", "date", "bank", "source"]]


def ensure_nltk_resources() -> None:
    if nltk is None:
        raise ImportError("NLTK is required for fallback preprocessing and sentiment scoring.")

    for resource in ["punkt", "stopwords", "vader_lexicon"]:
        try:
            nltk.data.find(resource)
        except LookupError:
            nltk.download(resource, quiet=True)


def load_spacy_nlp() -> Optional[Language]:
    if spacy is None:
        return None

    try:
        return spacy.load("en_core_web_sm", disable=["parser", "ner"])
    except OSError:
        try:
            spacy.cli.download("en_core_web_sm")
            return spacy.load("en_core_web_sm", disable=["parser", "ner"])
        except Exception:
            return None


def build_sentiment_model() -> Tuple[object, bool]:
    if pipeline is not None:
        try:
            sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
            )
            return sentiment_pipeline, True
        except Exception:
            pass

    if SentimentIntensityAnalyzer is not None:
        ensure_nltk_resources()
        return SentimentIntensityAnalyzer(), False

    raise RuntimeError(
        "No sentiment model is available. Install transformers or NLTK with VADER support."
    )


def clean_text(text: str, nlp: Optional[Language] = None) -> str:
    text = str(text or "").strip().lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    if nlp is not None:
        doc = nlp(text)
        tokens = [token.lemma_ for token in doc if token.is_alpha and not token.is_stop]
        return " ".join(tokens)

    ensure_nltk_resources()
    stop_words = set(stopwords.words("english"))
    tokens = [
        token
        for token in word_tokenize(text)
        if token.isalpha() and token not in stop_words
    ]
    return " ".join(tokens)


def predict_sentiment(
    text: str,
    model: object,
    transformer_model: bool = True,
    neutral_threshold: float = 0.60,
) -> Tuple[str, float]:
    if transformer_model:
        result = model(text[:512])
        if isinstance(result, list):
            result = result[0]
        label = result.get("label", "NEUTRAL").lower()
        score = float(result.get("score", 0.0))
        if score < neutral_threshold:
            return "neutral", score
        if label == "positive":
            return "positive", score
        return "negative", score

    ensure_nltk_resources()
    if isinstance(model, SentimentIntensityAnalyzer):
        scores = model.polarity_scores(text)
        compound = float(scores.get("compound", 0.0))
        if compound >= 0.05:
            return "positive", compound
        if compound <= -0.05:
            return "negative", abs(compound)
        return "neutral", abs(compound)

    raise RuntimeError("Unsupported sentiment model instance")


def apply_sentiment(df: pd.DataFrame, model: object, transformer_model: bool = True) -> pd.DataFrame:
    reviews = []
    scores = []
    labels = []

    for text in df["review"]:
        label, score = predict_sentiment(text, model, transformer_model=transformer_model)
        labels.append(label)
        scores.append(score)
        reviews.append(text)

    results = df.copy()
    results["sentiment_label"] = labels
    results["sentiment_score"] = scores
    return results


def get_top_keywords(df: pd.DataFrame, top_n: int = 25) -> List[Tuple[str, float]]:
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words="english", max_features=250)
    matrix = vectorizer.fit_transform(df["review"])
    feature_names = vectorizer.get_feature_names_out()
    average_scores = matrix.mean(axis=0).A1
    ranked_features = sorted(
        zip(feature_names, average_scores), key=lambda item: item[1], reverse=True
    )
    return ranked_features[:top_n]


def assign_theme(review_text: str, keyword_map: Optional[Dict[str, List[str]]] = None) -> str:
    keyword_map = keyword_map or THEME_KEYWORDS
    text = str(review_text or "").lower()
    scores = {
        theme: sum(text.count(keyword) for keyword in keywords)
        for theme, keywords in keyword_map.items()
    }
    best_theme, best_score = max(scores.items(), key=lambda item: item[1])
    return best_theme if best_score > 0 else "Other"


def apply_themes(df: pd.DataFrame) -> pd.DataFrame:
    results = df.copy()
    results["identified_theme"] = results["review"].apply(assign_theme)
    return results


def aggregate_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["bank", "rating"])["sentiment_score"]
        .mean()
        .reset_index()
        .rename(columns={"sentiment_score": "mean_sentiment_score"})
    )


def save_processed_reviews(df: pd.DataFrame, path: Optional[Path] = None) -> Path:
    path = Path(path or PROCESSED_CSV_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    return path


def run_pipeline() -> pd.DataFrame:
    df = load_reviews()

    model, is_transformer = build_sentiment_model()
    df_sentiment = apply_sentiment(df, model, transformer_model=is_transformer)
    df_final = apply_themes(df_sentiment)
    save_processed_reviews(df_final)
    return df_final


if __name__ == "__main__":
    output_df = run_pipeline()
    print(f"Processed {len(output_df)} reviews with sentiment and themes.")
