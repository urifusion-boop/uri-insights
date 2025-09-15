import requests
from app.core.config import settings
from typing import Any, Dict

from app.domain.enums.sentiment_enum import SentimentEnum

# from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Load tokenizer and model
# tokenizer = AutoTokenizer.from_pretrained("roberta-base")
# model = AutoModelForSequenceClassification.from_pretrained("roberta-base")


class SentimentService:
    @staticmethod
    def analyze_sentiment(text: str) -> Any:
        if text == None or len(text) < 1:
            return "neutral"

        # inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)

        # # Get model predictions
        # outputs = model(**inputs)
        # predicted_label = outputs.logits.argmax().item()

        # # Map predicted label to sentiment
        # sentiment_map = {0: "negative", 1: "neutral", 2: "positive"}
        # sentiment = sentiment_map[predicted_label]

        # return sentiment

    @staticmethod
    def select_sentiment(sentiment: str):
        sentiment_selector = {
            "positive": SentimentEnum.POSITIVE,
            "negative": SentimentEnum.NEGATIVE,
            "neutral": SentimentEnum.NEUTRAL,
        }

        return sentiment_selector[sentiment]
