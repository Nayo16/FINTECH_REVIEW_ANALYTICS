-- PostgreSQL schema for fintech review analytics

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
