import re
import json
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import pickle

class TextExtractor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=5000
        )
        self.classifiers = {
            'за_что': RandomForestClassifier(n_estimators=100),
            'номер_договора': RandomForestClassifier(n_estimators=100),
            'номер_счета': RandomForestClassifier(n_estimators=100),
            'номер_накладной': RandomForestClassifier(n_estimators=100),
            'номер_заказа': RandomForestClassifier(n_estimators=100)
        }
        
    def train(self, training_data):
        """
        Обучение модели на размеченных данных
        training_data: список кортежей (текст, разметка)
        """
        texts = [item[0] for item in training_data]
        labels = [item[1] for item in training_data]
        
        # Преобразуем тексты в векторы
        X = self.vectorizer.fit_transform(texts)
        
        # Обучаем классификаторы для каждого поля
        for field in self.classifiers:
            y = [label.get(field, "") for label in labels]
            self.classifiers[field].fit(X, y)
    
    def extract_from_text(self, text):
        """Извлекает информацию из текста"""
        # Преобразуем текст в вектор
        X = self.vectorizer.transform([text])
        
        result = {}
        
        # Предсказываем значения для каждого поля
        for field in self.classifiers:
            result[field] = self.classifiers[field].predict(X)[0]
        
        # Извлекаем даты с помощью регулярных выражений
        dates = re.findall(r'\d{2}\.\d{2}\.\d{4}', text)
        result['дата'] = dates[0] if dates else ""
        
        # Извлекаем период
        period_match = re.search(r'период.*?(\d{2})\.(\d{4})', text, re.IGNORECASE)
        if period_match:
            result['период'] = f"{period_match.group(1)}.{period_match.group(2)}"
        else:
            result['период'] = ""
        
        # Извлекаем НДС
        nds_match = re.search(r'НДС.*?(\d+(?:\.\d+)?)', text)
        if nds_match:
            result['НДС'] = float(nds_match.group(1))
        else:
            result['НДС'] = 0.0
        
        return result
    
    def save_model(self, filename):
        """Сохраняет модель в файл"""
        model_data = {
            'vectorizer': self.vectorizer,
            'classifiers': self.classifiers
        }
        with open(filename, 'wb') as f:
            pickle.dump(model_data, f)
    
    @classmethod
    def load_model(cls, filename):
        """Загружает модель из файла"""
        with open(filename, 'rb') as f:
            model_data = pickle.load(f)
        
        extractor = cls()
        extractor.vectorizer = model_data['vectorizer']
        extractor.classifiers = model_data['classifiers']
        return extractor

# Пример обучающих данных
TRAINING_DATA = [
    (
        """
        Счет №123-45 от 15.03.2024
        По договору №ДП-2024/03 от 01.03.2024
        За поставку канцтоваров согласно накладной №ТН-789
        Сумма НДС: 1250.50 руб.
        За период 03.2024
        """,
        {
            "за_что": "поставка канцтоваров",
            "номер_договора": "ДП-2024/03",
            "номер_счета": "123-45",
            "номер_накладной": "ТН-789",
            "номер_заказа": ""
        }
    ),
    (
        """
        Оплата по заказу №Order-456 
        от 20.03.2024
        НДС не облагается
        """,
        {
            "за_что": "оплата по заказу",
            "номер_договора": "",
            "номер_счета": "",
            "номер_накладной": "",
            "номер_заказа": "Order-456"
        }
    ),
    # Добавьте больше примеров для лучшего обучения
]

def main():
    # Создаем и обучаем экстрактор
    extractor = TextExtractor()
    extractor.train(TRAINING_DATA)
    
    # Сохраняем модель
    extractor.save_model('text_extractor_model.pkl')
    
    # Пример использования
    test_text = """
    Счет №789-10 от 25.03.2024
    По договору №АБВ-2024/15
    За оказание консультационных услуг
    НДС: 3600.00
    Период: 03.2024
    """
    
    result = extractor.extract_from_text(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()