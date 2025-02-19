import re
from datetime import datetime
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PaymentPurposeExtractor:
    """
    Класс для извлечения информации из назначения платежа.
    Использует комбинацию регулярных выражений и машинного обучения.
    """

    def __init__(self):
        # Пути к файлам для сохранения/загрузки модели и данных
        self.model_path = Path('payment_model.pkl')
        self.vectorizer_path = Path('vectorizer.pkl')
        self.training_data_path = Path('training_data.pkl')

        # Загружаем существующую модель или создаем новую
        if self.model_path.exists() and self.vectorizer_path.exists():
            try:
                self.model = self._load_model()
                self.vectorizer = self._load_vectorizer()
                logger.info("Модель успешно загружена")
            except Exception as e:
                logger.error(f"Ошибка загрузки модели: {e}")
                self._initialize_new_model()
        else:
            logger.info("Создание новой модели")
            self._initialize_new_model()

        # Загружаем или создаем тренировочные данные
        if self.training_data_path.exists():
            try:
                with open(self.training_data_path, 'rb') as f:
                    self.training_data = pickle.load(f)
            except Exception:
                self.training_data = {'texts': [], 'labels': []}
        else:
            self.training_data = {'texts': [], 'labels': []}

    def _initialize_new_model(self):
        """Инициализация новой модели и обучение на базовом наборе данных"""
        # Базовый набор данных для обучения
        initial_texts = [
            "Оплата згідно договору поставки №123 від 01.01.2023",
            "За товар по накладной №456 от 02.02.2023",
            "Оплата по счету №789 от 03.03.2023",
            "Платіж за договором №321 від 04.04.2023",
            "Оплата по рахунку №654 від 05.05.2023",
            "По видатковій накладній №987 від 06.06.2023"
        ]
        initial_labels = [
            {'type': 'договор', 'number': '123'},
            {'type': 'накладная', 'number': '456'},
            {'type': 'счет', 'number': '789'},
            {'type': 'договор', 'number': '321'},
            {'type': 'счет', 'number': '654'},
            {'type': 'накладная', 'number': '987'}
        ]

        # Сохраняем тренировочные данные
        self.training_data = {
            'texts': initial_texts,
            'labels': initial_labels
        }
        with open(self.training_data_path, 'wb') as f:
            pickle.dump(self.training_data, f)

        logger.info("Тренировочные данные инициализированы")

    def _load_model(self):
        with open(self.model_path, 'rb') as f:
            return pickle.load(f)

    def _load_vectorizer(self):
        with open(self.vectorizer_path, 'rb') as f:
            return pickle.load(f)

    def _save_model(self):
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)

    def _save_vectorizer(self):
        with open(self.vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)

    def _normalize_amount(self, amount_str):
        """
        Нормализует строку с суммой в число с плавающей точкой.
        Обрабатывает:
        - Замену запятой на точку
        - Удаление пробелов между цифрами
        - Удаление символов подчеркивания
        """
        if not amount_str:
            return None

        # Удаляем пробелы между цифрами и заменяем запятую на точку
        amount_str = re.sub(r'(\d)\s+(\d)', r'\1\2', amount_str)
        amount_str = amount_str.replace(',', '.').replace('_', '')

        try:
            return float(amount_str)
        except ValueError:
            return None

    def _extract_date(self, text):
        """
        Извлекает дату из текста.
        Поддерживает форматы:
        - дд.мм.гггг
        - дд.мм.гг
        - дд/мм/гггг
        - дд-мм-гггг
        - дд месяц гггг
        """
        # Словарь месяцев
        months = {
            'січня': '01', 'лютого': '02', 'березня': '03', 'квітня': '04',
            'травня': '05', 'червня': '06', 'липня': '07', 'серпня': '08',
            'вересня': '09', 'жовтня': '10', 'листопада': '11', 'грудня': '12',
            'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
            'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
            'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
        }

        # Шаблон для дат с месяцем прописью
        word_date = r'(\d{1,2})\s+([а-яіїє]+)\s+(\d{4})'
        match = re.search(word_date, text.lower())
        if match:
            day, month_name, year = match.groups()
            if month_name in months:
                day = day.zfill(2)
                return f"{year}-{months[month_name]}-{day}"

        date_patterns = [
            # После слов "від"/"от"
            r'(?:від|от)\s+(\d{2}[./-]\d{2}[./-]\d{2,4})',
            # С указанием года (р/г)
            r'(\d{2}[./-]\d{2}[./-]\d{2,4})\s*(?:р|року|г|года)',
            # Дата в начале текста
            r'^(\d{2}[./-]\d{2}[./-]\d{2,4})',
            # Дата в специальном формате
            r'(\d{2}[./-]\d{2}[./-]\d{2,4})\s*(?:р\.?|г\.?)',
            # Просто дата в тексте (последний приоритет)
            r'(\d{2}[./-]\d{2}[./-]\d{2,4})'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    for fmt in ['%d.%m.%Y', '%d.%m.%y', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except ValueError:
                    continue
        return None

    def _extract_document_info(self, text):
        """
        Извлекает информацию о документе: тип и номер.
        Поддерживает:
        - Договоры (договір/договор/дог)
        - Накладные (накладна/накл/РН/ВН)
        - Счета (рахунок/счет)
        - Акты
        """
        doc_patterns = {
            'договор': [
                # Договор поставки
                r'договор[уа]?\s+поставк[иі](?:\s+\([^)]+\))?\s*[№N#]?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Номер после №
                r'(?:дог(?:овір|овор|\.)|договор[уа]?|contract)\s*[№N#]\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # После слова "згідно"
                r'(?:зг|згідно|с-но)\s+(?:дог|дог\.|договор[уа]?)\s*[№N#]?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Сокращенная форма дог.
                r'(?:дог|дог\.|договор[уа]?|contract)\s+[№N#]?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Договор с номером в конце
                r'договір\s+поставки\s+товарів\s+([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|$)',
                # По договорам
                r'по\s+договор[уа]?м?[: ]+([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|$)',
                # За договором
                r'за\s+договором\s+([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)'
            ],
            'накладная': [
                # Список накладных через запятую
                r'накладн(?:ої|ых|их)[:;, ]+([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # После слова "згідно"
                r'(?:зг|згідно|с-но)\s+(?:накл(?:адна|\.)|накладн(?:ої|ых|их))\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # Видаткова накладна
                r'видатков(?:ої|их|а)\s*накл(?:адна|\.)\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # Стандартный формат
                r'(?:накл(?:адна|\.)|РН|ВН)\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Сокращенная форма
                r'(?:накл|н/н)\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # Просто номер после №
                r'№\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_,;]+)(?=\s|від|$)'
            ],
            'налогЗП': [
                # Список накладных через запятую
                r'накладн(?:ої|ых|их)[:;, ]+([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # После слова "згідно"
                r'(?:зг|згідно|с-но)\s+(?:накл(?:адна|\.)|накладн(?:ої|ых|их))\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # Видаткова накладна
                r'видатков(?:ої|их|а)\s*накл(?:адна|\.)\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # Стандартный формат
                r'(?:накл(?:адна|\.)|РН|ВН)\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Сокращенная форма
                r'(?:накл|н/н)\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_,]+)(?=\s|від|$)',
                # Просто номер после №
                r'НДФЛ)'
            ],
            'счет': [
                # Список счетов через пробелы
                r'(?:сч(?:ет|\.)|СЧ)\.\s+([A-Za-zА-Яа-яІіЇїЄє\d\-/_\s]+)(?=\s|Н\.?Д|$)',
                # Стандартный формат
                r'(?:рах(?:унок|\.)|сч(?:ет|\.)|рах-фактура)\s*[№N#]\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Счет-фактура
                r'(?:рах(?:унок|\.)|сч(?:ет|\.)|сч[её]т-фактура)\s*[№N#]\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Сокращенная форма
                r'(?:РАХ|СЧТ)\.\s*[№N#]?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # После слова "згідно"
                r'(?:зг|згідно)\s+рах\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|$)',
                # Счет номер
                r'(?:счет|счёт|рахунок)\s+номер\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?=\s|від|от|$)'
            ],
            'акт': [
                r'(?:акт|акту)\s*(?:№|N|#)?\s*([A-Za-zА-Яа-яІіЇїЄє\d\-/_]+)(?:\s|$)'
            ]
        }

        for doc_type, patterns in doc_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return {
                        'type': doc_type,
                        'number': match.group(1).strip()
                    }
        return {'type': None, 'number': None}

    def _extract_vat(self, text):
        """
        Извлекает сумму НДС (ПДВ) из текста.
        Поддерживает различные форматы записи:
        - ПДВ - 20% 100.00
        - в т.ч. ПДВ 20% - 100.00
        - ПДВ 100.00 грн
        - в т.ч. ПДВ 314.42
        - Без ПДВ
        """
        # Проверяем на "Без ПДВ" или "ПДВ - 0%"
        if re.search(r'без\s+пдв', text.lower()) or re.search(r'(?:ПДВ|НДС)\s*[-—]\s*0\s*%', text):
            return 0.0

        # Заменяем разделители в числах и нормализуем текст
        text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)
        text = text.replace('_', ' ')
        text = text.replace('=', ' = ').replace(':', ' : ')

        vat_patterns = [
            # ПДВ 20% - 100.00 грн
            r'(?:ПДВ|НДС)\s*[-—]*\s*20\s*%\s*[-—:=]*\s*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?',
            # в т.ч. ПДВ 20% - 100.00
            r'в\s*т\.?\s*ч\.?\s*(?:ПДВ|НДС)\s*[-—]*\s*20\s*%\s*[-—:=]*\s*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?',
            # ПДВ (20%) - 100.00
            r'(?:ПДВ|НДС)\s*\(?20\s*%\)?\s*[-—:=]*\s*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?',
            # ПДВ_20%_:_100.00
            r'(?:ПДВ|НДС)[_ ]*20[_ ]*%[_ ]*[:=][_ ]*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?',
            # в т.ч. ПДВ - 100.00
            r'в\s*т\.?\s*ч\.?\s*(?:ПДВ|НДС)\s*[-—:=]*\s*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?',
            # ПДВ - 100.00 грн
            r'(?:ПДВ|НДС)\s*[-—:=]*\s*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?',
            # в т.ч. ПДВ 100.00
            r'в\s*т\.?\s*ч\.?\s*(?:ПДВ|НДС)\s*[-—:=]*\s*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?',
            # ПДВ 100.00
            r'(?:ПДВ|НДС)\s*(\d+[.,]\d+)(?:\s*(?:грн|UAH|Грн))?'
        ]

        for pattern in vat_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._normalize_amount(match.group(1))
        return None

    def _extract_total_amount(self, text):
        """
        Извлекает общую сумму платежа из текста.
        Поддерживает форматы:
        - сума 100.00
        - 100.00 грн
        - на суму 100.00
        """
        amount_patterns = [
            # Сумма с указанием валюты
            r'(?:сум[аі]|вартість)\s*(\d+[.,]\d+)\s*(?:грн|UAH)',
            # Сумма после слова "сума/сумі"
            r'(?:сум[аі]|вартість)\s*(\d+[.,]\d+)',
            # Сумма с единицей валюты
            r'(\d+[.,]\d+)\s*(?:грн|UAH)',
            # После фразы "на суму"
            r'на\s*суму\s*(\d+[.,]\d+)',
            # Просто число с копейками
            r'(\d{3,}[.,]\d{2})'
        ]

        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._normalize_amount(match.group(1))
        return None

    def extract_info(self, text):
        """
        Извлекает всю информацию из текста назначения платежа и обновляет модель
        """
        # Извлекаем информацию с помощью регулярных выражений
        doc_info = self._extract_document_info(text)
        result = {
            'date': self._extract_date(text),
            'document_type': doc_info.get('type'),
            'document_number': doc_info.get('number'),
            'vat_amount': self._extract_vat(text)
        }

        # Если нашли информацию с помощью регулярных выражений,
        # добавляем в тренировочные данные
        if any(v is not None for v in result.values()):
            self._update_training_data(text, result)

        return result

    def _update_training_data(self, text, result):
        """
        Обновляет тренировочные данные
        """
        # Добавляем новый пример в тренировочные данные
        self.training_data['texts'].append(text)
        self.training_data['labels'].append(result)

        # Сохраняем обновленные данные
        try:
            with open(self.training_data_path, 'wb') as f:
                pickle.dump(self.training_data, f)
            # logger.info("Тренировочные данные успешно обновлены")
        except Exception as e:
            logger.error(f"Ошибка при сохранении тренировочных данных: {e}")

    def train(self, texts, labels):
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        self._save_model()
        self._save_vectorizer()

    def predict(self, text):
        X = self.vectorizer.transform([text])
        return self.model.predict(X)[0]


# извлекаем данные из postgresql в pandas DataFrame
def extract_data_from_postgresql():
    """
    Извлекаем данные из базы данных PostgreSQL
    """
    import psycopg2

    conn = psycopg2.connect(
        dbname='prestige', user='postgres', password='hfvpfc15', host='194.183.173.133' # параметры подключения
    )
    df = pd.read_sql_query('''SELECT DISTINCT osnd FROM t_pb;''', conn)
    conn.close()
    return df


def main():
    """
    Пример использования экстрактора для анализа платежных документов
    """
    extractor = PaymentPurposeExtractor()

    test_texts = extract_data_from_postgresql().values.tolist()
    test_texts = [text[0] for text in test_texts]

    results = []
    for text in test_texts:
        try:
            info = extractor.extract_info(text)
            info['text'] = text
            results.append(info)
        except Exception as e:
            logger.error(f"Ошибка при обработке текста: {e}")
            continue

    # Создаем DataFrame
    df = pd.DataFrame(results)

    # сохраним в Excel
    df.to_excel('payment_purpose.xlsx', index=False)

    # Переименовываем колонки для удобства
    column_names = {
        'text': 'Текст платежа',
        'date': 'Дата',
        'document_type': 'Тип документа',
        'document_number': 'Номер документа',
        'vat_amount': 'Сумма НДС'
    }
    df = df.rename(columns=column_names)

    # Заменяем None на 'Не указано'
    df = df.fillna('Не указано')

    # Выводим результат
    pd.set_option('display.max_colwidth', None)
    print("\nРезультаты анализа платежей:")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()