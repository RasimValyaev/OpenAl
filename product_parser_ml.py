import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import classification_report
from product_parser_re import main_product_parser_re
import random


def get_df():
    # Пример данных из таблицы
    df_source = main_product_parser_re()
    df = pd.DataFrame()
    # Применение функции извлечения данных
    df[
        [  "sku",
            "weight_pred",
            "weight_unit_pred",
            "pieces_pred",
            "containers_pred",
            "container_type_pred",
        ]
    ] = df_source[['sku','weight','weight_unit','pieces','containers','container_type']]


def generate_synthetic_data_from_patterns(pattern, num_samples):
    synthetic_data = []

    for _ in range(num_samples):
        # Выбираем случайный паттерн
        # pattern = random.choice(pattern)

        # Генерируем случайные значения для паттерна
        product_name = f"Product_{random.randint(1, 100)}"
        weight = round(random.uniform(0.1, 100),1)
        pieces = random.randint(1, 100)
        containers = random.randint(1, 50)
        container_type = random.choice(["tray", "jar", "box"])

        # Создаем новый SKU на основе паттерна
        # sku = re.sub(r"\((\w+)\)", f"({product_name})", pattern)
        sku = product_name
        sku = sku.replace("g", f"{weight}g")
        sku = sku.replace("pcs", f"{pieces}pcs")
        sku = sku.replace(container_type, f"{containers}{container_type}")

        # Добавляем новые данные в список
        synthetic_data.append([sku, weight, "g", pieces, containers, container_type])

    # Создаем DataFrame из синтетических данных
    return pd.DataFrame(
        synthetic_data,
        columns=[
            "sku",
            "weight",
            "weight_unit",
            "pieces",
            "containers",
            "container_type",
        ],
    )

def training(df):
    # Векторизация текста
    vectorizer = TfidfVectorizer()
    X_vec = vectorizer.fit_transform(df["sku"])

    # Обучение модели для предсказания веса
    weight_model = RandomForestRegressor()
    weight_model.fit(df[["weight_pred", "pieces_pred", "containers_pred"]], df["weight"])

    # Обучение модели для предсказания типа контейнера
    container_model = RandomForestClassifier()
    container_model.fit(X_vec, df["container_type"])

    # Предсказание и сравнение результатов
    df["weight_pred_ml"] = weight_model.predict(
        df[["weight_pred", "pieces_pred", "containers_pred"]]
    )
    df["container_type_pred_ml"] = container_model.predict(X_vec)

    # Сравнение результатов
    accuracy = (df["weight_pred_ml"] == df["weight"]).mean()
    print(f"Accuracy: {accuracy * 100:.2f}%")

    # Обучение до тех пор, пока данные не совпадут
    while accuracy < 1.0:
        # Обучение модели заново
        weight_model.fit(
            df[["weight_pred", "pieces_pred", "containers_pred"]], df["weight"]
        )
        container_model.fit(X_vec, df["container_type"])

        # Предсказание и сравнение результатов
        df["weight_pred_ml"] = weight_model.predict(
            df[["weight_pred", "pieces_pred", "containers_pred"]]
        )
        df["container_type_pred_ml"] = container_model.predict(X_vec)

        # Сравнение результатов
        accuracy = (df["weight_pred_ml"] == df["weight"]).mean()
        print(f"Accuracy: {accuracy * 100:.2f}%")


if __name__ == "__main__":
    sample = generate_synthetic_data_from_patterns(
        "(\d+(?:[.,]\d+)?)\s*(?:g|gr|gx|г|гр|G|GR|ml|мл)\s*[xXхХ×]\s*(\d+)(?:\s*(?:pcs|pc|шт|p))?\s*[xXхХ×]\s*(\d+)",10,)
    print(sample.to_string())
    # training(sample)
