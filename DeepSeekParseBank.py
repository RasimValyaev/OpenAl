import tiktoken
import requests
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv
import os
import pandas as pd
import psycopg2

# 1. Загружаем переменные из файла .env в окружение
load_dotenv()  # берёт .env из текущей директории
API_KEY =  os.getenv("DEEPSEEK_API_KEY")  # Ключ должен быть в .env
BASE_URL = "https://api.deepseek.com/v1"

# Начальный баланс (указывается вручную в .env)
initial_balance = float(config.get("INITIAL_BALANCE", 0.0))


# из быза pg, таб t_pb извлечем уникальные данные
def extract_data_from_postgresql():
    user = os.getenv("PG_USER")
    password = os.getenv("PG_PASSWORD")
    host = os.getenv("PG_HOST")
    port = os.getenv("PG_PORT")
    dbname = os.getenv("PG_DBNAME")
    conn = psycopg2.connect(
        user=user, password=password, host=host, port=port, dbname=dbname
    )
    df = pd.read_sql_query(
        """SELECT DISTINCT osnd FROM t_pb WHERE date_time_dat_od_tim_p::date >= '25.03.2025'::date Limit 5;""",
        conn
    )
    conn.close()
    return df


# Извлечение информации с помощью DeepSeek
def extract_info(content: str, model: str = "deepseek-chat"):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Получи НДС, дату, номера договора, накладной, счета "
                           "строго в json формате: "
                           "{"
                           "за_что: str,"
                           "номер_договора: str, "
                           "номер_счета: str, "
                           "номер_накладной: str,"
                           "номер_заказа: str,"
                           "дата:date,"
                           "НДС:float,"
                           "период:str"
                           "}"
                           " Если отсутствует информация, выведи пустоту. НДС извлеки не %, а сумму. "
                           "Дату выводи в формате: dd.mm.yyyy."
                           "Период выводи в формате: mm.yyyy",
            },
            {"role": "user", "content": content},
        ],
        "response_format": {"type": "json_object"},
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions", headers=headers, json=payload
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")


# Подсчет количества токенов в тексте
def count_tokens(text: str, model: str = "deepseek-chat") -> int:
    """Подсчет количества токенов в тексте"""
    encoding = tiktoken.get_encoding(
        "cl100k_base"
    )  # DeepSeek использует ту же кодировку
    return len(encoding.encode(text))


# Получение актуальных тарифов DeepSeek
def get_deepseek_pricing():
    """Получает актуальные тарифы DeepSeek с официального сайта документации"""
    try:
        url = "https://api-docs.deepseek.com/quick_start/pricing"
        response = requests.get(url)

        if response.status_code != 200:
            print(
                f"Не удалось получить данные о тарифах. Код ответа: {response.status_code}"
            )
            return {
                "deepseek-chat": {"input": 0.00027, "output": 0.0011}
            }  # Возвращаем значения по умолчанию

        # Используем DeepSeek для извлечения информации о тарифах из HTML
        pricing_html = response.text

        # Извлекаем информацию о ценах с помощью DeepSeek
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "Извлеки актуальные тарифы для модели deepseek-chat из документации. "
                               "Нужны цены за 1K токенов для input и output в долларах США. "
                               'Верни только числа в формате JSON: {"input": X.XXXXX, "output": X.XXXXX}.'
                               "Данные извлекай для cache miss и текущего времени. "
                               "Часовой пояс UTC+2.",
                },
                {"role": "user", "content": pricing_html},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        pricing_response = requests.post(
            f"{BASE_URL}/chat/completions", headers=headers, json=payload
        )

        if pricing_response.status_code == 200:
            pricing_data = json.loads(
                pricing_response.json()["choices"][0]["message"]["content"]
            )
            print(
                f"Получены актуальные тарифы: input=${pricing_data['input']}, output=${pricing_data['output']} за 1K токенов"
            )
            return {
                "deepseek-chat": {
                    "input": pricing_data["input"],
                    "output": pricing_data["output"],
                }
            }
        else:
            print(
                f"Ошибка при извлечении тарифов: {pricing_response.status_code} - {pricing_response.text}"
            )
            return {
                "deepseek-chat": {"input": 0.00027, "output": 0.0011}
            }  # Возвращаем значения по умолчанию

    except Exception as e:
        print(f"Ошибка при получении тарифов: {str(e)}")
        return {
            "deepseek-chat": {"input": 0.00027, "output": 0.0011}
        }  # Возвращаем значения по умолчанию


# Расчет стоимости запроса
def calculate_cost(input_tokens: int, output_tokens: int, model: str = "deepseek-chat") -> Dict[str, float]:
    """Расчет стоимости запроса"""
    # Получаем актуальные тарифы
    rates = get_deepseek_pricing()

    input_cost = (input_tokens / 1000) * rates[model]["input"]
    output_cost = (output_tokens / 1000) * rates[model]["output"]

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
    }


def extraxt_from_deepseek_main():
    MODEL = "deepseek-chat"
    df = extract_data_from_postgresql()

    try:
        df["назначение"] = ""
        df["номер_договора"] = ""
        df["номер_счета"] = ""
        df["номер_накладной"] = ""
        df["номер_заказа"] = ""
        df["дата"] = ""
        df["НДС"] = ""
        df["период"] = ""

        for i, row in df.iterrows():
            print("-" * 80)
            content = row["osnd"]
            # contents = df["osnd"].tolist()

            # for i, content in enumerate(contents):

            # получаем информацию о входящих токенах
            # input_tokens = count_tokens(content)

            # Извлечение информации
            result = extract_info(content, MODEL)

            # получаем информацию об исходящих токенах
            # output_tokens = count_tokens(result)

            # Расчет стоимости
            # cost = calculate_cost(input_tokens, output_tokens, MODEL)

            # Отчет о стоимости
            # print("\n--- ОТЧЕТ О СТОИМОСТИ ПАРСИНГА ---")
            # print(f"Модель: {MODEL}")
            # print(f"Входные токены: {input_tokens:,} (${cost['input_cost']:.4f})")
            # print(f"Выходные токены: {output_tokens:,} (${cost['output_cost']:.4f})")
            # print(f"ИТОГО: ${cost['total_cost']:.4f}")

            # Парсинг и вывод результатов
            data = json.loads(result)

            # добавим в Series значения
            df.loc[i, "назначение"] = data["за_что"]
            df.loc[i, "номер_договора"] = data["номер_договора"]
            df.loc[i, "номер_счета"] = data["номер_счета"]
            df.loc[i, "номер_накладной"] = data["номер_накладной"]
            df.loc[i, "номер_заказа"] = data["номер_заказа"]
            df.loc[i, "дата"] = data["дата"]
            df.loc[i, "НДС"] = data["НДС"]
            df.loc[i, "период"] = data["период"]

            print(f"content:{i + 1}\n"
                  f"{content}\n"
                  f"за_что:{data['за_что']}\n"
                  f"номер_договора: {data['номер_договора']}\n"
                  f"номер_счета: {data['номер_счета']}\n"
                  f"номер_накладной: {data['номер_накладной']}\n"
                  f"номер_заказа: {data['номер_заказа']}\n"
                  f"дата: {data['дата']}\n"
                  f"НДС:{data['НДС']}\n"
                  f"период:{data['период']}\n"
                  )

    except Exception as e:
        print(f"Ошибка: {str(e)}")

    # Сохраненим результаты в excel
    df.to_excel("deepseek_parsed_data.xlsx", index=False)


if __name__ == "__main__":
    extraxt_from_deepseek_main()
    
    
