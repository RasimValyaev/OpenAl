import pandas as pd
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
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
            token_pattern=r"(?u)\b\p{L}+\b|\d+(?:[.,]\d+)?(?:\s*(?:г|кг|шт|бл|ml|мл|g|kg|pc|pcs|box|boxes|jar|jars|tray|trays|vase|vases|уп|упак|упаковка|упаковки|банка|банки|лоток|лотки|ваза|вазы|мілілітр|мілілітри|упаковка|упаковки|банка|банки|лоток|лотки|ваза|вази))?"
        )
        self.classifier = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42
        )
        self.regressor_weight = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42
        )
        self.regressor_pieces = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42
        )
        self.regressor_containers = RandomForestRegressor(
            n_estimators=100, max_depth=10, random_state=42
        )

        # Начальные обучающие данные
        self.initial_data = [
            ('''Diamond Light Candy 6gx24pcsx12boxes''', 'box', 6, 24, 12),
            ('''POP MANIA MAXXI STRAWBERRY 10X48X28G''', 'box', 28, 48, 10),
            ('''LUPPO DREAM BAR KAKAOLU 6KT12AD50G''', 'box', 50, 12, 6),
            ('''BOOMBASTIC MARSH.BARKEK 6KT12AD40G UA/RU''', 'box', 40, 12, 6),
            ('''WINERGY YER FISTIKLI BAR 6KT 24AD 30G''', 'box', 30, 24, 6),
            ('''TWINGO KARAMEL 6KT 24AD 42 CIS2''', 'box', 42, 24, 6),
            ('''BOOMB. H.CV.KAR.PPT. 6KT12ADT35G CIS2''', 'box', 35, 12, 6),
            ('''CRAZY PRINC PATLAK AMB 6KT 24AD 30G KSA''', 'box', 30, 24, 6),
            ('''BISCOLATA DUOMAX SUTLU 12KT 12AD 44G''', 'box', 44, 12, 12),
            ('''BISCOLATA DUOMAX FINDIKLI 12KT 12AD 44G''', 'box', 44, 12, 12),
            ('''Princess (Mini sandwich with strw cream) 900grx6''', 'box', 900, 1, 6),
            ('''JELLYREX MIX 15g*12*24 JELLY CANDY''', 'box', 15, 12, 24),
            ('''Kokolin draje şeker kaplamalı 12*24*12gr PUNTO''', 'box', 12, 24, 12),
            ('''kokolin draje şek.kaplm.12*24*18gr choco punto''', 'box', 18, 24, 12),
            ('''SLIM TRANSPARENT EGG 6GR*6*12 army tank''', 'box', 6, 6, 12),
            ('''POP MANIA MAXXI RASPBERRY 10X48X28G''', 'box', 28, 48, 10),
            ('''OZMO CORNET SUTLU 25G 24 ADT 4KT''', 'box', 25, 24, 4),
            ('''POP MANIA MAXXI GREEN APPLE 10X48X28G''', 'box', 28, 48, 10),
            ('''LOLLIPOP MAXXI WATERMELON 10X48X28G''', 'box', 28, 48, 10),
            ('''LOLLIPOP MAXXI SOUR CHERRY 10X48X28G''', 'box', 28, 48, 10),
            ('''500g Macaron Cookies (Mixed Flavors) 500Gx 8Boxes''', 'box', 500, 1, 8),
            ('''Ice Cream Popsicle Marshmallow 11gx30pcsx24boxes''', 'box', 11, 30, 24),
            ('''Ice Cream Lolly Marshmallow 12gx30pcsx24boxes''', 'box', 12, 30, 24),
            ('''Cup Coffee Candy 15gx12pcsx12boxes''', 'box', 15, 12, 12),
            ('''Skateboard Crazy Hair candy 20gx20pcsx12boxes''', 'box', 20, 20, 12),
            ('''Queen Cup Jelly (Strawberry) 100g x 8 pcs x 12tray''', 'tray', 100, 8, 12),
            ('''Pizza Jelly Grape 50gx30pcsx10boxes''', 'box', 50, 30, 10),
            ('''Skeleton Jelly 32gx70pcsx6jars''', 'jar', 32, 70, 6),
            ('''Animal shape + heart marshmallow stick 11gx30pcsx24boxes''', 'box', 11, 30, 24),
            ('''Lighting Torch Candy 4.5gx20pcsx12boxes''', 'box', 4.5, 20, 12),
            ('''LUPPO DREAM BAR KARAMEL 6KT12AD50G''', 'box', 50, 12, 6),
            ('''OZMO CORNET MUZ-DRJ 25G 24ADT4KT TASO AZ''', 'box', 25, 24, 4),
            ('''Ice Lolly Jelly 14gx30pcsx20boxes''', 'box', 14, 30, 20),
            ('''OZMO HOPPO CIK. 24PK 90G''', 'box', 90, 24, 1),
            ('''OZMO FUN YILBASI 12KT24AD23G RTS RU/UA''', 'box', 23, 24, 12),
            ('''OZMO FUN HAYVAN SERISI  4KT 24AD 23G''', 'box', 23, 24, 4),
            ('''OZMO OGOPOGO KAK KEK 4KT24AD30G CIS1''', 'box', 30, 24, 4),
            ('''OZMO OGOPOGO CILEKLI KEK 4KT24AD30G''', 'box', 30, 24, 4),
            ('''BISCOLATA STIX FINDIKLI 4KT 12AD 32G ()''', 'box', 32, 12, 4),
            ('''BISCOLATA STIX P.PATLAKLI 4KT 12AD 34G''', 'box', 34, 12, 4),
            ('''BISCOLATA STIX H.CEVIZ 4KT 12AD 32G()''', 'box', 32, 12, 4),
            ('''BISCOLATA STIX SUTLU 4KT 12AD 40G CIS2''', 'box', 40, 12, 4),
            ('''PAPITA PARTY DRJ.KAKAOLU BIS24AD 63G CIS''', 'box', 63, 24, 1),
            ('''PAPITA PARTY DRJ. SADE BISK 24AD 63G CIS''', 'box', 63, 24, 1),
            ('''BISCOLATA MOOD 24PK 115G''', 'box', 115, 24, 1),
            ('''BISC.MOOD NIGHT 24PK125G(BITTER) UA/RU''', 'box', 125, 24, 1),
            ('''OZMO HOPPO CILEK 4KT12AD40G (Y.DES)''', 'box', 40, 12, 4),
            ('''OZMO HOPPO CIK. 4KT*12ADT*40G ''', 'box', 40, 12, 4),
            ('''OZMO CORNET G-DRJ 4KT24AD25G YD TASO''', 'box', 25, 24, 4),
            ('''OZMO BURGER 6KT 12ADT 40G IHRACAT CS2''', 'box', 40, 12, 6),
            ('''BISCOLATA MOOD H.CEVZLI 24PK125G UA/RU''', 'box', 125, 24, 1),
            ('''Luppo Red Velvet 12SP 182G''', 'box', 182, 12, 1),
            ('''LUPPO KARAMEL SNDVICKEK 12SP 182G BALKAN''', 'box', 182, 12, 1),
            ('''LUPPO CAKEBITE CHOCO 6KT24AD25G (UA)''', 'box', 25, 24, 6),
            ('''SOLEN LUPPO CAKE BITE SADE 12SP 184G(CS)''', 'box', 184, 12, 1),
            ('''LUPPO VISNE MAR.SNDVIC KEK 12SP 182G Y.T''', 'box', 182, 12, 1),
            ('''LUPPO SANDVIC KAKKEK 6KT 24AD 25G LUBNAN''', 'box', 25, 24, 6),
            ('''SOLEN LUPPO CAKE BITE DARK 12SP 184G(CS)''', 'box', 184, 12, 1),
            ('''TRIPLEX KAPLAMALISZ 6KT 24AD 20G''', 'box', 20, 24, 6),
            ('''BOOMB. P.PTKLI FNDKLI GF 6KT12AD32G CIS2''', 'box', 32, 12, 6),
            ('''BISCOLATA MINIS FINDIKLI GOFRT 24PKT117G''', 'box', 117, 24, 1),
            ('''OZMO CORNET CILEKLI 4KT24AD25G(AR-EN-RO)''', 'box', 25, 24, 4),
            ('''Skeleton Pop candy 7gx30pcsx24boxes''', 'box', 7, 30, 24),
            ('''harmonica Candy +fish Candy 3gx60pcsx12jars''', 'jar', 3, 60, 12),
            ('''Marshmallow Hamburger Pop 18gx24pcsx12boxes''', 'box', 18, 24, 12),
            ('''Super Car Gummy 20gx20pcsx12boxes''', 'box', 20, 20, 12),
            ('''Birthday Cake Gummy 12gx20pcsx12boxes''', 'box', 12, 20, 12),
            ('''Snake Gummy 8gx30pcsx20boxes''', 'box', 8, 30, 20),
            ('''Long CC Stick Candy 4gx50pcsx40bags''', 'bag', 4, 50, 40),
            ('''Biberon Liquid Candy 30mlX30pcsx18boxes''', 'box', 30, 30, 18),
            ('''EYEBALL CANDY SATND 3,5 GX24X8''', 'box', 3.5, 24, 8),
            ('''EYE CANDY STAND 3,5 GX24X8''', 'box', 3.5, 24, 8),
            ('''Bear Pudding 40gx20pcsx18tray''', 'tray', 40, 20, 18),
            ('''Cow Eyes Gummy 7gx60pcsx12jars''', 'box', 7, 60, 12),
            ('''Cola Tin Spray Candy 30mlx24pcsx12boxes''', 'box', 30, 24, 12),
            ('''2in1 Crazy Hair Candy 20gx20pcsx12boxes''', 'box', 20, 20, 12),
            ('''Crocodile jelly 35gx48pcsx6jars''', 'jar', 35, 48, 6),
            ('''Snake jelly 35gx48pcsx6jars''', 'jar', 35, 48, 6),
            ('''Toy and Jelly 30gx50pcsx6jars''', 'jar', 30, 50, 6),
            ('''Dinosaur Gummy 8gx12pcsx20boxes''', 'box', 8, 12, 20),
            ('''Birthday gummy 46gx6pcsx12box''', 'box', 46, 6, 12),
            ('''5D Fruits Gummy Candy 10gx50pcsx12jars''', 'jar', 10, 50, 12),
            ('''HOTDOG GUMMY 16g*24pcs*12boxes''', 'box', 16, 24, 12),
            ('''COBRA GUMMY 16g*24pcs*12boxes''', 'box', 16, 24, 12),
            ('''Baby bottle(Whistle candy) 9gx100pcsx6jars''', 'jar', 9, 100, 6),
            ('''Winx Spray Candy 30gx12pcsx12boxes''', 'box', 30, 12, 12),
            ('''Mini cup jlly (Benben bear Jar) 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Mini Jelly cup in (Trush can) 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Mini cup Jelly (Hippo Jar) 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Mini cup Jelly (Owl Jar) 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Mini cup Jelly (Duck Jar) 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Jelly cup in Koala Jar 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Mini Cup Jelly (Panda Bag) 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Jelly cup in Monkey Jar 13gx100pcsx6jars''', 'jar', 13, 100, 6),
            ('''Jelly (Skeleton shape) 35gx55pcsx6jars''', 'jar', 35, 55, 6),
            ('''Mini Jackpot Gum Ball 20gx12pcsx 12boxes''', 'box', 20, 12, 12),
            ('''Bear Jelly 35gx30pcsx12boxes''', 'box', 35, 30, 12),
            ('''Butterfly Jelly 35gx30pcsx12boxes''', 'box', 35, 30, 12),
            ('''5in1 Sour Powder 10gX50pcsx20boxes''', 'box', 10, 50, 20),
            ('''Colour Candy Ball Stick 12gx40pcsx8vases''', 'vase', 12, 40, 8),
            ('''WATERMELON GUMMY 8g*30pcs*20jars''', 'jar', 8, 30, 20),
            ('''LADY BIRD GUMMY 8g*30pcs*20jars''', 'jar', 8, 30, 20),
            ('''BILLARDS GUMMY 8g*30pcs*20jars''', 'jar', 8, 30, 20),
            ('''DEVIL GUMMY 8g*30pcs*20jars''', 'jar', 8, 30, 20),
            ('''stick eyeball gummy 10g*30pcs*20jars''', 'jar', 10, 30, 20),
            ('''Stick grape gummy 10g*30pcs*20jars''', 'jar', 10, 30, 20),
            ('''Biberon liquit candy 40g*30pcs*16boxes''', 'box', 40, 30, 16),
            ('''Toilet Candy 13gx24pcsx12boxes''', 'box', 13, 24, 12),
            ('''Lighting New Spray Candy 25gx30pcsx20boxes''', 'box', 25, 30, 20),
            ('''Bracelet Candy 10gx48pcsx12boxes UNI''', 'box', 10, 48, 12),
            ('''Mega sour jam 30gx20pcsx12boxes''', 'box', 30, 20, 12),
            ('''Microphone pudding 33gx30pcsx12jars''', 'jar', 33, 30, 12),
            ('''Skull Candy + bear Candy 6gx60pcsx12jars''', 'jar', 6, 60, 12),
            ('''Stretch frog candy 5gx12pcsx6boxes''', 'box', 5, 12, 6),
            ('''Twins eyeball Gummy 4g*100pcs*12jars''', 'jar', 4, 100, 12),
            ('''Roll Gum 7g×24pcs×24boxes''', 'box', 7, 24, 24),
            ('''Big Foot lollipop+Sour Powder Candy 7.5gx30pcsx24boxes''', 'box', 7.5, 30, 24),
            ('''Mini Lollipop Shooter 3gx12pcsx 24boxes''', 'box', 3, 12, 24),
            ('''Big Burger Gummy 32gx8pcsx8boxes''', 'box', 32, 8, 8),
            ('''Super Sour Hard Candy 12gx24pcsx20boxes''', 'box', 12, 24, 20),
            ('''Fruits Press Candy 10gx30pcsx20boxes''', 'box', 10, 30, 20),
            ('''Rabbit Candy 6gx30pcsx24trays''', 'tray', 6, 30, 24),
            ('''Mouse Candy 6gx30pcsx24trays''', 'tray', 6, 30, 24),
            ('''Ice Cream 3in1 16gx24pcsx10boxes''', 'box', 16, 24, 10),
            ('''3in1 Squeeze Candy 45gx12pcsx12boxes''', 'box', 45, 12, 12),
            ('''CHOCODANS KARAMEL 4KT12AD125G RUSYA OTO''', 'box', 125, 12, 4),
        ]
        self.train_data = []
        self.load_model()

        # Если модель новая, обучаем на начальных данных
        if not self.train_data:
            texts, types, weights, pieces, containers = zip(*self.initial_data)
            self.train(texts, types, weights, pieces, containers)

    def load_model(self):
        """Загрузка модели из файла"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.vectorizer = data["vectorizer"]
                    self.classifier = data["classifier"]
                    self.regressor_weight = data["regressor_weight"]
                    self.regressor_pieces = data["regressor_pieces"]
                    self.regressor_containers = data["regressor_containers"]
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
                    "regressor_weight": self.regressor_weight,
                    "regressor_pieces": self.regressor_pieces,
                    "regressor_containers": self.regressor_containers,
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

    def predict_weight(self, text: str) -> float:
        """Предсказание веса"""
        if not self.train_data:
            return 0.0

        X = self.vectorizer.transform([text])
        weight = self.regressor_weight.predict(X)[0]
        return weight

    def predict_pieces(self, text: str) -> int:
        """Предсказание количества штук"""
        if not self.train_data:
            return 0

        X = self.vectorizer.transform([text])
        pieces = self.regressor_pieces.predict(X)[0]
        return int(pieces)

    def predict_containers(self, text: str) -> int:
        """Предсказание количества контейнеров"""
        if not self.train_data:
            return 0

        X = self.vectorizer.transform([text])
        containers = self.regressor_containers.predict(X)[0]
        return int(containers)

    def train(self, texts: List[str], container_types: List[str], weights: List[float], pieces: List[int], containers: List[int], retrain=False):
        """Обучение модели"""
        if retrain:
            self.train_data = list(self.initial_data)  # Начинаем с начальных данных

        # Добавляем новые данные
        for text, container_type, weight, piece, container in zip(texts, container_types, weights, pieces, containers):
            if (text, container_type, weight, piece, container) not in self.train_data:
                self.train_data.append((text, container_type, weight, piece, container))

        if not self.train_data:
            return

        # Разделяем данные на тексты и метки
        texts, types, weights, pieces, containers = zip(*self.train_data)

        # Обучаем модель
        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, types)
        self.regressor_weight.fit(X, weights)
        self.regressor_pieces.fit(X, pieces)
        self.regressor_containers.fit(X, containers)

        # Сохраняем модель
        self.save_model()

        # Оценка качества
        score_classifier = self.classifier.score(X, types)
        score_weight = self.regressor_weight.score(X, weights)
        score_pieces = self.regressor_pieces.score(X, pieces)
        score_containers = self.regressor_containers.score(X, containers)
        print(f"Точность ML модели (классификация): {score_classifier:.1%}")
        print(f"Точность ML модели (вес): {score_weight:.1%}")
        print(f"Точность ML модели (количество штук): {score_pieces:.1%}")
        print(f"Точность ML модели (количество контейнеров): {score_containers:.1%}")

class ProductParser:
    def __init__(self):
        # ML модель
        self.ml_model = MLModel()

    def _detect_container_type(self, text: str) -> Tuple[str, float]:
        """Определение типа контейнера по тексту"""
        # Используем только ML
        container_type, confidence = self.ml_model.predict(text)
        return container_type, confidence

    def parse_product(self, text: str) -> Dict:
        """Парсинг описания продукта"""
        # Используем только ML для определения типа контейнера и предсказания веса, количества штук и количества контейнеров
        container_type, confidence = self._detect_container_type(text)
        weight = self.ml_model.predict_weight(text)
        pieces = self.ml_model.predict_pieces(text)
        containers = self.ml_model.predict_containers(text)

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
