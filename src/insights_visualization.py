from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROCESSED_CSV = Path("data/processed/review_analysis.csv")
OUTPUT_DIR = Path("reports/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data(path: Path = PROCESSED_CSV) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Processed CSV not found at {path}")
    df = pd.read_csv(path)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    return df


def sentiment_distribution_by_bank(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["bank", "sentiment_label"]).size().unstack(fill_value=0)
    )
    summary.plot(kind="bar", stacked=True, figsize=(10, 6), colormap="tab20")
    plt.title("Sentiment Distribution by Bank")
    plt.ylabel("Review Count")
    plt.xlabel("Bank")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "sentiment_distribution_by_bank.png", dpi=200)
    plt.close()


def rating_distribution(df: pd.DataFrame) -> None:
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x="bank", y="rating", palette="Set2")
    plt.title("Rating Distribution by Bank")
    plt.ylabel("Star Rating")
    plt.xlabel("Bank")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "rating_distribution_by_bank.png", dpi=200)
    plt.close()


def top_themes_by_bank(df: pd.DataFrame, top_n: int = 5) -> None:
    theme_counts = (
        df.groupby(["bank", "identified_theme"]).size().reset_index(name="count")
    )
    top_themes = (
        theme_counts.sort_values(["bank", "count"], ascending=[True, False]).groupby("bank").head(top_n)
    )
    g = sns.catplot(
        data=top_themes,
        x="count",
        y="identified_theme",
        hue="bank",
        kind="bar",
        height=6,
        aspect=1.6,
        palette="muted",
    )
    g.fig.suptitle("Top Themes by Bank")
    g.set_xlabels("Review Count")
    g.set_ylabels("Theme")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "top_themes_by_bank.png", dpi=200)
    plt.close()


def run_visualizations() -> None:
    df = load_data()
    sentiment_distribution_by_bank(df)
    rating_distribution(df)
    top_themes_by_bank(df)
    print(f"Saved figures to {OUTPUT_DIR}")


if __name__ == "__main__":
    run_visualizations()
