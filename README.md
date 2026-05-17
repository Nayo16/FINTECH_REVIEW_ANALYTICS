# Fintech Review Analytics

A structured analytics pipeline for scraping, preprocessing, and analyzing Google Play Store reviews for Ethiopian fintech apps.

## Project Structure

- `src/`: Python modules for review collection and cleaning.
- `data/raw/`: Raw and cleaned review exports (ignored by Git).
- `tests/`: Unit tests for pipeline functions.
- `.github/workflows/unittests.yml`: CI workflow to install dependencies and run tests.
- `requirements.txt`: Python dependencies.

## Data Collection Methodology

This project uses the `google-play-scraper` Python library to fetch Play Store reviews for the following apps:

- Commercial Bank of Ethiopia Mobile
- Bank of Abyssinia Mobile App
- Dashen Bank Mobile Banking

For each app, the scraper collects review text, rating, date, bank/app name, and source.

### Preprocessing steps

- Remove duplicate reviews.
- Drop rows with missing review text or rating.
- Normalize dates to `YYYY-MM-DD`.
- Save cleaned output to `data/raw/clean_reviews.csv`.

## Running the scraper

```powershell
pip install -r requirements.txt
python -m src.review_pipeline
```

This writes a cleaned CSV file to `data/raw/clean_reviews.csv`.

### Latest verified run
- Total cleaned reviews: `1787`
- Commercial Bank of Ethiopia Mobile: `592`
- Bank of Abyssinia Mobile App: `598`
- Dashen Bank Mobile Banking: `597`

## Limitations and notes

- Google Play review scraping can be rate-limited or blocked by the Play Store API. If fewer than 400 reviews are returned per bank, the script will document that limitation and continue with the available reviews.
- The cleaned CSV is excluded from Git via `.gitignore`.
- The CI workflow validates the code with `pytest` on pushes to `main`.
