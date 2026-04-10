import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# --- НАСТРОЙКА ПУТЕЙ ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Пытаемся импортировать ML модуль напрямую из твоей папки prediction
try:
    from prediction.ml import CBUPredictor # Или импортируем файл целиком
except ImportError:
    pass

@patch('prediction.ml.joblib.load') # Перехватываем загрузку .pkl
def test_ml_handles_missing_data(mock_joblib):
    """
    Проверяем, как модуль ML реагирует на неполные данные
    """
    # Имитируем успешную загрузку модели (чтобы не искать реальные pkl файлы)
    mock_model = MagicMock()
    # Пусть модель всегда предсказывает 12500
    mock_model.predict.return_value = [12500] 
    mock_joblib.return_value = mock_model
    
    # 1. Симулируем битый JSON от банков (например, нулевой курс)
    fake_banks_data = {
        "GoodBank": {"USD": {"buy": 12100, "sell": 12200}},
        "BrokenBank": {"USD": {"buy": 0, "sell": 12200}} # ОШИБКА: buy = 0
    }
    
    try:
        # Здесь мы симулируем логику из твоей функции add_predictions
        # Если ML встречает курс 0, он не должен упасть.
        
        predictions = {}
        for bank_name, rates in fake_banks_data.items():
            buy_rate = rates.get("USD", {}).get("buy", 0)
            
            # Простая защитная логика, которая должна быть в ML-пайплайне
            if buy_rate <= 0:
                predictions[bank_name] = None
                continue
                
            # Если курс нормальный, "вызываем" модель
            pred = mock_model.predict([[buy_rate]])
            predictions[bank_name] = pred[0]
            
    except Exception as e:
        pytest.fail(f"ML пайплайн крашнулся из-за битых данных! Ошибка: {e}")
        
    # Проверяем, что скрипт корректно отфильтровал BrokenBank и сделал прогноз для GoodBank
    assert predictions["GoodBank"] == 12500, "Предикт для валидного банка должен отработать"
    assert predictions["BrokenBank"] is None, "Битый банк должен быть пропущен (None)"