import re
import pandas as pd
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from products_source import test_products
import os


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
        self.classifier = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42
        )

        # Начальные обучающие данные
        self.initial_data = [
            ("Diamond Light Candy boxes", "box"),
            ("Ice Lolly Jelly boxes", "box"),
            ("Jelly cup in Monkey Jar", "jar"),
            ("Bear Pudding tray", "tray"),
            ("Long CC Stick Candy bags", "bag"),
            ("Colour Candy Ball Stick vases", "vase"),
            ("BLOX жувальна гумка блок", "box"),
            ("candy box", "box"),
            ("candy jar", "jar"),
            ("candy tray", "tray"),
            ("candy bag", "bag"),
            ("candy vase", "vase"),
            ("KT", "box"),
        ]
        self.train_data = []
        self.load_model()

        # Если модель новая, обучаем на начальных данных
        if not self.train_data:
            texts, types = zip(*self.initial_data)
            self.train(texts, types)

    def load_model(self):
        """Загрузка модели из файла"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.vectorizer = data["vectorizer"]
                    self.classifier = data["classifier"]
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
                    "classifier": self.classifier,
                    "train_data": self.train_data,
                },
                f,
            )

    def predict(self, text: str) -> Tuple[str, float]:
        """Предсказание типа контейнера"""
        if not self.train_data:
            return "box", 0.0

        X = self.vectorizer.transform([text])
        container_type = self.classifier.predict(X)[0]
        confidence = max(self.classifier.predict_proba(X)[0])
        return container_type, confidence

    def train(self, texts: List[str], container_types: List[str], retrain=False):
        """Обучение модели"""
        if retrain:
            self.train_data = list(self.initial_data)  # Начинаем с начальных данных

        # Добавляем новые данные
        for text, container_type in zip(texts, container_types):
            if (text, container_type) not in self.train_data:
                self.train_data.append((text, container_type))

        if not self.train_data:
            return

        # Разделяем данные на тексты и метки
        texts, types = zip(*self.train_data)

        # Обучаем модель
        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, types)

        # Сохраняем модель
        self.save_model()

        # Оценка качества
        score = self.classifier.score(X, types)
        print(f"Точность ML модели: {score:.1%}")


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
        """Преобразование строки в число с учетом разных разделителей"""
        return float(value.replace(",", "."))

    def _detect_container_type(self, text: str) -> Tuple[str, float]:
        """Определение типа контейнера по тексту"""
        # Сначала пробуем через ML
        container_type, confidence = self.ml_model.predict(text)
        if confidence > 0.8:  # Высокая уверенность ML
            return container_type, confidence

        # Если ML не уверен, используем правила
        text_lower = text.lower()
        if "tray" in text_lower:
            return "tray", 1.0
        elif "jar" in text_lower:
            return "jar", 1.0
        elif "bag" in text_lower:
            return "bag", 1.0
        elif "vase" in text_lower:
            return "vase", 1.0
        elif any(x in text_lower for x in ["бл", "блок", "box", "boxes","кт"]):
            return "box", 1.0
        return "box", 0.5  # по умолчанию с низкой уверенностью

    def parse_product(self, text: str) -> Dict:
        """Парсинг описания продукта"""
        # Извлечение чисел
        for pattern, extractor in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    weight, pieces, containers = extractor(match)
                    container_type, confidence = self._detect_container_type(text)

                    # Если распознали через правила, дообучаем ML
                    if confidence == 1.0:
                        self.ml_model.train([text], [container_type])

                    return {
                        "sku": text,
                        "weight": f"{weight:g}",
                        "weight_unit": "мл" if "ml" in text.lower() else "г",
                        "pieces": pieces,
                        "containers": containers,
                        "container_type": container_type,
                        "confidence": f"{confidence:.1%}",
                        "parsed": True,
                    }
                except (ValueError, IndexError):
                    continue

        # Если не удалось разобрать
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
                print(f"Не удалось разобрать: {text}")
                failed += 1

        if data:
            # Создаем DataFrame
            df = pd.DataFrame(data)

            # Сортируем: сначала успешно разобранные, потом неразобранные
            df = df.sort_values("parsed", ascending=False)

            # Удаляем колонку parsed перед выводом
            df = df.drop("parsed", axis=1)

            # Выводим результаты
            print("\nТаблица продуктов:")
            print(df.to_string(index=False))

            # Сохраняем результаты
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            df.to_excel(f"parser_results_{timestamp}.xlsx", index=False)

        # Статистика
        total = success + failed
        print(f"\nСтатистика:")
        print(f"Всего продуктов: {total}")
        print(f"Успешно разобрано: {success} ({success/total*100:.1f}%)")
        if failed > 0:
            print(f"Не удалось разобрать: {failed} ({failed/total*100:.1f}%)")

        # Статистика по типам контейнеров
        if success > 0:
            containers = df["container_type"].value_counts()
            print("\nИспользованные типы контейнеров:")
            for container, count in containers.items():
                if container:  # Пропускаем пустые значения
                    print(f"{container}: {count} ({count/success*100:.1f}%)")


def main():
    # Создаем парсер и запускаем
    parser = ProductParser()
    parser.parse_products(test_products)


if __name__ == "__main__":
    main()
