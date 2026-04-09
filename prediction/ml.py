import os
import joblib
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient


class CBUPredictor:
    def __init__(
        self,
        model_path,
        mongo_uri,
        db_name="banks_data",
        collection_name="currency_rates",
        cbu_bank_name="CBU",
        currency_code="USD"
    ):
        self.model_path = model_path
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.cbu_bank_name = cbu_bank_name
        self.currency_code = currency_code

        self.model = self._load_model()

    def _load_model(self):
        saved_obj = joblib.load(self.model_path)

        # если сохранили просто model
        if hasattr(saved_obj, "predict"):
            return saved_obj

        # если сохранили {"model": ..., "features": ...}
        if isinstance(saved_obj, dict) and "model" in saved_obj:
            return saved_obj["model"]

        raise ValueError("Не удалось загрузить модель из файла")

    def _extract_current_rate_from_report(self, final_report):
        """
        Достаем текущий курс USD только из CBU внутри final_report.
        Поддерживаются варианты:
        - {"rate": ...}
        - {"buy": ..., "sell": ...}
        """

        banks_data = final_report.get("banks", {})
        cbu_data = banks_data.get(self.cbu_bank_name)

        if not cbu_data:
            raise ValueError(f"В final_report нет данных по банку {self.cbu_bank_name}")

        usd_data = cbu_data.get(self.currency_code)
        if not usd_data:
            raise ValueError(f"В final_report нет данных по валюте {self.currency_code} у {self.cbu_bank_name}")

        # Вариант 1: есть поле rate
        if isinstance(usd_data, dict) and usd_data.get("rate") is not None:
            return float(usd_data["rate"])

        # Вариант 2: берем buy, если это CBU и rate не найден
        if isinstance(usd_data, dict):
            if usd_data.get("buy") is not None:
                return float(usd_data["buy"])
            if usd_data.get("sell") is not None:
                return float(usd_data["sell"])

        raise ValueError(f"Не удалось извлечь курс {self.currency_code} из final_report")

    def _get_previous_rate_from_mongo(self):
        """
        Берем последний сохраненный курс USD Центрального банка из MongoDB.
        """
        client = MongoClient(self.mongo_uri)
        db = client[self.db_name]
        collection = db[self.collection_name]

        # Ищем последнюю запись по CBU и USD
        doc = collection.find_one(
            {
                "bank_name": self.cbu_bank_name,
                "currency": self.currency_code
            },
            sort=[("timestamp", -1)]
        )

        client.close()

        if not doc:
            raise ValueError("В MongoDB не найден предыдущий курс для CBU/USD")

        # Поддержка разных форматов хранения
        if doc.get("rate") is not None:
            return float(doc["rate"])

        if doc.get("buy") is not None:
            return float(doc["buy"])

        if doc.get("sell") is not None:
            return float(doc["sell"])

        raise ValueError("В MongoDB нет подходящего числового курса для CBU/USD")

    def _build_features(self, lag1, lag2, base_timestamp):
        """
        Формируем признаки для прогноза на следующий день.
        lag1 = текущий курс
        lag2 = предыдущий курс из MongoDB
        """
        current_dt = datetime.fromisoformat(base_timestamp)
        next_day = current_dt + timedelta(days=1)

        feature_df = pd.DataFrame([{
            "lag1": lag1,
            "lag2": lag2,
            "day_of_week": next_day.weekday(),
            "month": next_day.month,
            "day_of_month": next_day.day
        }])

        return feature_df, next_day

    def add_prediction_to_report(self, final_report):
        """
        Добавляет прогноз в final_report.
        """
        current_rate = self._extract_current_rate_from_report(final_report)
        previous_rate = self._get_previous_rate_from_mongo()

        feature_df, predicted_date = self._build_features(
            lag1=current_rate,
            lag2=previous_rate,
            base_timestamp=final_report["timestamp"]
        )

        predicted_rate = float(self.model.predict(feature_df)[0])

        if "predictions" not in final_report:
            final_report["predictions"] = {}

        if self.cbu_bank_name not in final_report["predictions"]:
            final_report["predictions"][self.cbu_bank_name] = {}

        final_report["predictions"][self.cbu_bank_name][self.currency_code] = {
            "predicted_for_date": predicted_date.date().isoformat(),
            "predicted_rate": round(predicted_rate, 4),
            "model": "LinearRegression",
            "features_used": {
                "lag1": current_rate,
                "lag2": previous_rate,
                "day_of_week": predicted_date.weekday(),
                "month": predicted_date.month,
                "day_of_month": predicted_date.day
            }
        }

        return final_report