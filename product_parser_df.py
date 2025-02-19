import re
import pandas as pd
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from products_source import test_products, data_initial_dict
import os
import shutil


class MLModel:
    def __init__(self, model_path="ml_model.pkl"):
        self.model_path = model_path
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=2000,
            token_pattern=r"""
                (?ui)
                \b\p{L}+\b |
                \d+(?:[.,]\d+)?
                (?:\s*
                (?:g|kg|pc|pcs|box|boxes|jar|jars|tray|trays|vase|vases|ml|
                ad|adet|kutu|kavanoz|tepsi|vazo|
                г|кг|шт|бл|ml|мл|g|kg|pc|pcs|box|boxes|jar|jars|tray|trays|vase|vases|уп|упак|упаковка|упаковки|банка
                |банки|лоток|лотки|ваза|вазы|мілілітр|мілілітри|упаковка|упаковки|банка|банки|лоток|лотки|ваза|вази
                ))?
        """
        )
        # Отдельные классификаторы для каждого параметра
        self.classifiers = {
            'container_type': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
            'weight': RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
            'weight_unit': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
            'pieces': RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
            'containers': RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        }

        # Начальные обучающие данные с расширенными параметрами
        self.initial_data = data_initial_dict
        self.train_data = []
        self.load_model()

        # Если модель новая, обучаем на начальных данных
        if not self.train_data:
            self.train_on_initial_data()

    def load_model(self):
        """Загрузка модели из файла"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.vectorizer = data["vectorizer"]
                    self.classifiers = data["classifiers"]
                    self.train_data = data.get("train_data", [])
                print(f"Загружена модель с {len(self.train_data)} обучающими примерами")
            except Exception as e:
                print(f"Ошибка загрузки модели: {e}")
                self.train_data = []
        else:
            self.train_data = []

    def save_model(self):
        """Сохранение модели в файл"""
        with open(self.model_path, "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self.vectorizer,
                    "classifiers": self.classifiers,
                    "train_data": self.train_data,
                },
                f,
            )

    def predict(self, text: str) -> Dict:
        """Предсказание всех параметров"""
        if not self.train_data:
            return {
                'container_type': "box",
                'weight': 0.0,
                'weight_unit': "g",
                'pieces': 1,
                'containers': 1,
                'confidences': {k: 0.0 for k in self.classifiers.keys()}
            }

        X = self.vectorizer.transform([text])
        predictions = {}
        confidences = {}

        for param, clf in self.classifiers.items():
            pred = clf.predict(X)[0]
            if hasattr(clf, 'predict_proba'):
                conf = max(clf.predict_proba(X)[0])
            else:
                # For regressors, use a simple confidence metric based on training score
                conf = clf.score(X, [pred])
            predictions[param] = pred
            confidences[param] = conf

        predictions['confidences'] = confidences
        return predictions

    def train_on_initial_data(self):
        """Обучение на начальных данных"""
        self.train_data = list(self.initial_data)
        self.train(retrain=True)

    def generate_synthetic_data(self, text: str, re_extracted: Dict) -> List[Dict]:
        """Генерация синтетических данных на основе примера"""
        synthetic_data = []

        # Базовый пример
        base = {
            'text': text,
            **re_extracted
        }
        synthetic_data.append(base)

        # Генерируем вариации
        variations = [
            # Изменение порядка
            f"{base['weight']}{base['weight_unit']}*{base['pieces']}pcs*{base['containers']}{base['container_type']}s",
            f"{base['containers']}{base['container_type']}s {base['weight']}{base['weight_unit']} {base['pieces']}pcs",
            # Изменение разделителей
            f"{base['weight']}{base['weight_unit']} x {base['pieces']}pcs x {base['containers']}{base['container_type']}s",
            f"{base['weight']}{base['weight_unit']}/{base['pieces']}pcs/{base['containers']}{base['container_type']}s",
            # Добавление описательных слов
            f"Product {base['weight']}{base['weight_unit']} with {base['pieces']}pcs in {base['containers']}{base['container_type']}s",
        ]

        for var_text in variations:
            synthetic_data.append({
                'text': var_text,
                **re_extracted
            })

        return synthetic_data

    def train(self, retrain=False):
        """Обучение моделей"""
        if not self.train_data:
            return

        # Подготовка данных
        texts = [item['text'] for item in self.train_data]
        X = self.vectorizer.fit_transform(texts)

        # Обучение каждого классификатора
        for param, clf in self.classifiers.items():
            y = [item[param] for item in self.train_data]
            clf.fit(X, y)

        # Сохраняем модель
        self.save_model()

        # Оценка качества для каждого параметра
        for param, clf in self.classifiers.items():
            y = [item[param] for item in self.train_data]
            score = clf.score(X, y)
            print(f"Точность ML модели ({param}): {score:.1%}")

    def verify_and_improve(self, text: str, re_extracted: Dict, max_iterations=5):
        """Проверка и улучшение предсказаний"""
        for iteration in range(max_iterations):
            predictions = self.predict(text)

            # Проверяем совпадение предсказаний с re_extracted
            mismatch = False
            for key in re_extracted:
                if key != 'confidences' and predictions.get(key) != re_extracted[key]:
                    mismatch = True
                    break

            if not mismatch:
                print(f"Предсказания совпадают с re после {iteration+1} итераций")
                return True

            # Генерируем синтетические данные и дообучаем
            synthetic_data = self.generate_synthetic_data(text, re_extracted)
            self.train_data.extend(synthetic_data)
            self.train()

        print(f"Не удалось достичь точного совпадения после {max_iterations} итераций")
        return False


class ProductParser:
    def __init__(self):
        # ML модель
        self.ml_model = MLModel()
        self.patterns = [
            # Шаблоны для извлечения чисел

            # Формат с * (16g*24pcs*12boxes)
            (
                r"(\d+)(?:g|gr|gx|г|гр|G|GR|ml|мл)\s*[*]\s*(\d+)(?:\s*(?:pcs|pc|шт|p))?\s*[*]\s*(\d+)",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Формат с * и GR (6GR*6*12)
            (
                r"(\d+)(?:GR|gr|g|G)\s*[*]\s*(\d+)\s*[*]\s*(\d+)",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Формат без разделителей (16g24pcs12boxes)
            (
                r"(\d+)(?:g|gr|gx|г|гр|G|GR|ml|мл)(\d+)(?:pcs|pc|шт|p)?(\d+)(?:boxes|box|jars|jar|tray|trays|vase|vases|bag|bags)",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Формат с весом в начале и конце (500g ... 500Gx 8Boxes)
            (
                r"(?:^|\s)(\d+)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл).*?(\d+)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)\s*[xXхХ*]\s*(\d+)(?:\s|boxes|box|$)",
                lambda m: (float(m.group(2)), 1, int(m.group(3))),
            ),
            # Формат с запятой или точкой (3,5 GX24X8)
            (
                r"(\d+[.,]\d+)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)[xXхХ*]\s*(\d+)[xXхХ*]\s*(\d+)",
                lambda m: (
                    self._to_float(m.group(1)),int(m.group(2)),int(m.group(3)),
                ),
            ),
            # Формат BLOX (12,5 гр 20 Х 30 бл)
            (
                r"(\d+[.,]\d+)\s*(?:г|гр|gr|g|G|GR|мл|ml)\s+(\d+)\s*[хХxX]\s*(\d+)\s*(?:бл|блок|boxes|box)",
                lambda m: (self._to_float(m.group(1)),int(m.group(2)),int(m.group(3)),
                ),
            ),
            # Формат с размерами (10X48X28G)
            (
                r"(\d+)\s*[xXхХ]\s*(\d+)\s*[xXхХ]\s*(\d+)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)(?:\s|$)",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Формат с единицами измерения (100g x 8 pcs x 12tray)
            (
                r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)\s*[xXхХ×]\s*(\d+)(?:\s*(?:pcs|pc|шт|p))?\s*[xXхХ×]\s*(\d+)",
                lambda m: (
                    self._to_float(m.group(1)),int(m.group(2)),int(m.group(3)),
                ),
            ),
            # Формат с × (7g×24pcs×24boxes)
            (
                r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)\s*[×]\s*(\d+)(?:\s*(?:pcs|pc|шт|p))?\s*[×]\s*(\d+)",
                lambda m: (
                    self._to_float(m.group(1)),int(m.group(2)),int(m.group(3)),
                ),
            ),
            # Формат с весом и количеством (900grx6)
            (
                r"(\d+)\s*(?:g|gr|gx|г|гр|ml|мл)[xXхХ*]\s*(\d+)(?:\s|$)",
                lambda m: (float(m.group(1)), 1, int(m.group(2))),
            ),
            # Формат с GR и числами (6GR612)
            (
                r"(\d+)(?:GR|gr|g|G)(\d+)(\d+)",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Формат с числами через пробел (15g 12 24)
            (
                r"(\d+)(?:g|gr|gx|г|гр|G|GR|ml|мл)\s+(\d+)\s+(\d+)",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Формат Kokolin (12*24*18gr)
            (
                r"(\d+)\s*[*]\s*(\d+)\s*[*]\s*(\d+)(?:g|gr|gx|г|гр|G|GR)",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Формат с пробелами и Х (36гр 12шт Х12бл)
            (
                r"(\d+)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)\s+(\d+)\s*(?:шт|штХ|шт\s*[xXхХ])\s*[xXхХ]\s*(\d+)\s*(?:бл|блок|блоков)",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Формат с пробелами и слитным штХ (15 гр 20штХ 4бл)
            (
                r"(\d+)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)\s+(\d+)\s*штХ\s*(\d+)\s*(?:бл|блок|блоков)",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Новый формат для BISCOLATA DUOMAX FINDIKLI 12KT 12AD 44G
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для CRAZY PRINC PATLAK AMB 6KT 24AD 30G KSA
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для BOOMB. H.CV.KAR.PPT. 6KT12ADT35G CIS2
            (
                r"(\d+)\s*KT(\d+)\s*ADT(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для TWINGO KARAMEL 6KT 24AD 42 CIS2
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для WINERGY YER FISTIKLI BAR 6KT 24AD 30G
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для BOOMBASTIC MARSH.BARKEK 6KT12AD40G UA/RU
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z/]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для LUPPO DREAM BAR KAKAOLU 6KT12AD50G
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO CORNET SUTLU 25G 24 ADT 4KT
            (
                r"(\d+)\s*G\s*(\d+)\s*ADT\s*(\d+)\s*KT",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Новый формат для OZMO CORNET MUZ-DRJ 25G 24ADT4KT TASO AZ
            (
                r"(\d+)\s*G\s*(\d+)\s*ADT(\d+)\s*KT\s*[A-Z]+",
                lambda m: (float(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            # Новый формат для OZMO CORNET G-DRJ 4KT24AD25G YD TASO
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO CORNET CILEKLI 4KT24AD25G(AR-EN-RO)
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*\([A-Z-]+\)",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для BISCOLATA MINIS FINDIKLI GOFRT 24PKT117G
            (
                r"(\d+)\s*PKT(\d+)\s*G",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для BOOMB. P.PTKLI FNDKLI GF 6KT12AD32G CIS2
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для TRIPLEX KAPLAMALISZ 6KT 24AD 20G
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для SOLEN LUPPO CAKE BITE DARK 12SP 184G(CS)
            (
                r"(\d+)\s*SP\s*(\d+)\s*G\s*\([A-Z]+\)",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для LUPPO SANDVIC KAKKEK 6KT 24AD 25G LUBNAN
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для LUPPO VISNE MAR.SNDVIC KEK 12SP 182G Y.T
            (
                r"(\d+)\s*SP\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для SOLEN LUPPO CAKE BITE SADE 12SP 184G(CS)
            (
                r"(\d+)\s*SP\s*(\d+)\s*G\s*\([A-Z]+\)",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для LUPPO CAKEBITE CHOCO 6KT24AD25G (UA)
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*\([A-Z]+\)",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для LUPPO KARAMEL SNDVICKEK 12SP 182G BALKAN
            (
                r"(\d+)\s*SP\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для Luppo Red Velvet 12SP 182G
            (
                r"(\d+)\s*SP\s*(\d+)\s*G",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для BISCOLATA MOOD H.CEVZLI 24PK125G UA/RU
            (
                r"(\d+)\s*PK(\d+)\s*G\s*[A-Z/]+",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для OZMO BURGER 6KT 12ADT 40G IHRACAT CS2
            (
                r"(\d+)\s*KT\s*(\d+)\s*ADT\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO HOPPO CIK. 4KT12ADT40G
            (
                r"(\d+)\s*KT(\d+)\s*ADT(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO HOPPO CIK. 24PK 90G
            (
                r"(\d+)\s*PK\s*(\d+)\s*G",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для OZMO HOPPO CILEK 4KT12AD40G (Y.DES)
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*\([A-Z.]+\)",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для BISC.MOOD NIGHT 24PK125G(BITTER) UA/RU
            (
                r"(\d+)\s*PK(\d+)\s*G\s*\([A-Z]+\)\s*[A-Z/]+",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для BISCOLATA MOOD 24PK 115G
            (
                r"(\d+)\s*PK\s*(\d+)\s*G",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для PAPITA PARTY DRJ. SADE BISK 24AD 63G CIS
            (
                r"(\d+)\s*AD\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для PAPITA PARTY DRJ.KAKAOLU BIS24AD 63G CIS
            (
                r"(\d+)\s*AD\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(2)), int(m.group(1)), 1),
            ),
            # Новый формат для BISCOLATA STIX SUTLU 4KT 12AD 40G CIS2
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для BISCOLATA STIX H.CEVIZ 4KT 12AD 32G()
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*\(\)",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для BISCOLATA STIX P.PATLAKLI 4KT 12AD 34G
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для BISCOLATA STIX FINDIKLI 4KT 12AD 32G ()
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G\s*\(\)",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO OGOPOGO CILEKLI KEK 4KT24AD30G
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO OGOPOGO KAK KEK 4KT24AD30G CIS1
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO FUN HAYVAN SERISI 4KT 24AD 23G
            (
                r"(\d+)\s*KT\s*(\d+)\s*AD\s*(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO FUN YILBASI 12KT24AD23G RTS RU/UA
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для CHOCODANS KARAMEL 4KT12AD125G RUSYA OTO
            (
                r"(\d+)\s*KT(\d+)\s*AD(\d+)\s*G\s*[A-Z]+",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            # Новый формат для OZMO HOPPO CIK. 4KT*12ADT*40G
            (
                r"(\d+)\s*KT\s*\*\s*(\d+)\s*ADT\s*\*\s*(\d+)\s*G",
                lambda m: (float(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
        ]

    def _to_float(self, value: str) -> float:
        """Convert string to float handling different decimal separators"""
        return float(value.replace(",", "."))

    def _detect_container_type_re(self, text: str) -> str:
        """Detect container type using regular expressions"""
        text_lower = text.lower()

        if any(x in text_lower for x in ["jar", "jars", "банка", "банки", "каваноз"]):
            return "jar"
        elif any(x in text_lower for x in ["tray", "trays", "лоток", "лотки", "tepsi"]):
            return "tray"
        elif any(x in text_lower for x in ["vase", "vases", "ваза", "вазы", "vazo"]):
            return "vase"
        elif any(x in text_lower for x in ["bag", "bags"]):
            return "bag"
        elif any(x in text_lower for x in ["бл", "блок", "box", "boxes", "кт"]):
            return "box"
        return "box"  # default

    def _detect_container_type(self, text: str) -> Tuple[str, float]:
        """Detect container type using ML and regular expressions"""
        # Get ML predictions
        ml_predictions = self.ml_model.predict(text)
        container_type = ml_predictions['container_type']
        confidence = ml_predictions['confidences'].get('container_type', 0.0)

        # If ML confidence is low, use regular expressions
        if confidence < 0.5:
            container_type = self._detect_container_type_re(text)
            confidence = 1.0

        return container_type, confidence

    def parse_product(self, text: str) -> Dict:
        """Parse product description"""
        # Extract numbers using regular expressions
        weight, pieces, containers = 0.0, 1, 1
        weight_unit = "ml" if "ml" in text.lower() else "g"
        parsed = False

        for pattern, extractor in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    weight, pieces, containers = extractor(match)
                    parsed = True
                    break
                except (ValueError, IndexError):
                    continue

        if parsed:
            # Data extracted using regular expressions
            re_extracted = {
                "weight": weight,
                "weight_unit": weight_unit,
                "pieces": pieces,
                "containers": containers,
                "container_type": self._detect_container_type_re(text)
            }

            # Get ML model predictions
            ml_predictions = self.ml_model.predict(text)

            # Verify predictions match with re and improve model if needed
            self.ml_model.verify_and_improve(text, re_extracted)

            # Use ML predictions if confidence is high, otherwise use re
            result = {}
            confidences = ml_predictions.get('confidences', {})
            max_confidence = 0.0

            for key in re_extracted:
                if key in confidences and confidences[key] >= 0.5:
                    result[key] = ml_predictions[key]
                    max_confidence = max(max_confidence, confidences[key])
                else:
                    result[key] = re_extracted[key]

            return {
                "sku": text,
                "weight": f"{result['weight']:g}",
                "weight_unit": result['weight_unit'],
                "pieces": result['pieces'],
                "containers": result['containers'],
                "container_type": result['container_type'],
                "confidence": f"{max_confidence:.1%}",
                "parsed": True,
            }

        # If regex parsing failed, try ML only
        ml_predictions = self.ml_model.predict(text)
        if all(conf >= 0.7 for conf in ml_predictions.get('confidences', {}).values()):
            return {
                "sku": text,
                "weight": f"{ml_predictions['weight']:g}",
                "weight_unit": ml_predictions['weight_unit'],
                "pieces": ml_predictions['pieces'],
                "containers": ml_predictions['containers'],
                "container_type": ml_predictions['container_type'],
                "confidence": f"{min(ml_predictions['confidences'].values()):.1%}",
                "parsed": True,
            }

        # If parsing failed
        return {
            "sku": text,
            "weight": "",
            "weight_unit": "",
            "pieces": "",
            "containers": "",
            "container_type": "",
            "confidence": "",
            "parsed": False,
        }

    def parse_products(self, products: List[str]) -> None:
        """Парсинг списка продуктов"""
        data = []
        success = 0
        failed = 0

        for text in products:
            result = self.parse_product(text)
            data.append(result)
            if result["parsed"]:
                success += 1
            else:
                print(f"Failed to parse: {text}")
                failed += 1

        # Create DataFrame
        df = pd.DataFrame(data)
        if data:
            # Sort: successfully parsed first, then unparsed
            df = df.sort_values("parsed", ascending=False)

            # Remove parsed column before display
            df = df.drop("parsed", axis=1)

            # Display results
            print("\nProducts table:")
            print(df.to_string(index=False))

            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            df.to_excel(f"parser_results_{timestamp}.xlsx", index=False)

        # Statistics
        total = success + failed
        print(f"\nStatistics:")
        print(f"Total products: {total}")
        print(f"Successfully parsed: {success} ({success/total*100:.1f}%)")
        if failed > 0:
            print(f"Failed to parse: {failed} ({failed/total*100:.1f}%)")

        # Container type statistics
        if success > 0:
            containers = df["container_type"].value_counts()
            print("\nContainer types used:")
            for container, count in containers.items():
                if container:  # Skip empty values
                    print(f"{container}: {count} ({count/success*100:.1f}%)")


def create_backup(model_path):
    """Создание резервной копии модели"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = model_path.split('.')[-2]
    backup_path = f"{model_name}_backup_{timestamp}.pkl"
    if os.path.exists(model_path):
        shutil.copy(model_path, backup_path)
        print(f"Резервная копия создана: {backup_path}")
    else:
        print("Файл модели не найден.")



def main():
    model_path = "ml_model.pkl"
    create_backup(model_path)

    # Создаем парсер и запускаем
    parser = ProductParser()
    parser.parse_products(test_products)


if __name__ == "__main__":
    main()
