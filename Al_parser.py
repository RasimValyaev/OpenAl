# pip install requests tiktoken python-dotenv

import tiktoken
import requests
import json
import time
from typing import Dict
from dotenv import dotenv_values

# Загрузка переменных окружения
config = dotenv_values(".env")
API_KEY = config["DEEPSEEK_API_KEY"]  # Ключ должен быть в .env
BASE_URL = "https://api.deepseek.com/v1"

from selenium import webdriver

def get_dynamic_html(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)  # Ждем загрузки JS
    html = driver.page_source
    driver.quit()
    return html

def scrape_html(url: str) -> str:
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    """Получение HTML-кода страницы"""
    full_url = f"{url}&_={int(time.time())}"
    response = requests.get(full_url, headers=headers)
    return response.text

def extract_info(content: str, model: str = "deepseek-chat"):
    """Извлечение информации с помощью DeepSeek"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                # "content": "Получи цену и рейтинг на все книги со страницы строго в json формате: {[ {rate: str, price: float, rating: int} ]}."
                "content": "Извлеки первые 10 строк из таблицы. Нужны курсы покупки и продажи в json формате: "
                           "{курсы: [{покупка: float, продажа: float}, время:time]}. "
                           "Результат отсортируй в порядке убывания времени"
            },
            {
                "role": "user",
                "content": content
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7  # Добавляем случайность для избежания кеша
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")


def count_tokens(text: str, model: str = "deepseek-chat") -> int:
    """Подсчет количества токенов в тексте"""
    encoding = tiktoken.get_encoding("cl100k_base")  # DeepSeek использует ту же кодировку
    return len(encoding.encode(text))


def calculate_cost(input_tokens: int, output_tokens: int, model: str = "deepseek-chat") -> Dict[str, float]:
    """Расчет стоимости запроса"""
    # Актуальные тарифы DeepSeek (проверьте перед использованием)
    rates = {
        "deepseek-chat": {"input": 0.00027, "output": 0.0011}  # $ за 1K токенов
    }

    input_cost = (input_tokens / 1000) * rates[model]["input"]
    output_cost = (output_tokens / 1000) * rates[model]["output"]

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost
    }


if __name__ == "__main__":
    URL = "https://minfin.com.ua/currency/auction/exchanger/usd/sell/kiev/?order=newest"
    MODEL = "deepseek-chat"

    try:
        html_content = get_dynamic_html("https://r.jina.ai/" + URL)
        # html_content = scrape_html("https://r.jina.ai/" + URL)
        input_tokens = count_tokens(html_content)

        # Извлечение информации
        result = extract_info(html_content, MODEL)
        output_tokens = count_tokens(result)

        # Расчет стоимости
        cost = calculate_cost(input_tokens, output_tokens, MODEL)

        # Отчет о стоимости
        print("\n--- ОТЧЕТ О СТОИМОСТИ ПАРСИНГА ---")
        print(f"Модель: {MODEL}")
        print(f"Входные токены: {input_tokens:,} (${cost['input_cost']:.4f})")
        print(f"Выходные токены: {output_tokens:,} (${cost['output_cost']:.4f})")
        print(f"ИТОГО: ${cost['total_cost']:.4f}")

        # Парсинг и вывод результатов
        parsed_data = json.loads(result)

        print("\n--- РЕЗУЛЬТАТЫ ПАРСИНГА ---")
        print(f"Всего книг извлечено: {len(parsed_data['курсы'])}")
        for i, rate in enumerate(parsed_data['курсы']):
            print(f"{i + 1}. {rate['покупка']}; {rate['продажа']}; {rate['время']}")

        # Сохранение результатов
        with open("deepseek_parsed_rates.json", "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)

        print("\nРезультаты сохранены в deepseek_parsed_rates.json")

    except Exception as e:
        print(f"Ошибка: {str(e)}")