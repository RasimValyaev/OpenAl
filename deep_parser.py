import tiktoken
import requests
import json
from typing import Dict, Any
from dotenv import dotenv_values

# Загрузка переменных окружения
config = dotenv_values(".env")
API_KEY = config["DEEPSEEK_API_KEY"]  # Ключ должен быть в .env
BASE_URL = "https://api.deepseek.com/v1"

# Начальный баланс (указывается вручную в .env)
initial_balance = float(config.get("INITIAL_BALANCE", 0.0))


def scrape_html(url: str) -> str:
    """Получение HTML-кода страницы"""
    response = requests.get(url)
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
                "content": "Получи наименования, код и грамм со страницы строго в json формате: {sku: [ {sku: str, code: str, gr: str} ]}."
            },
            {
                "role": "user",
                "content": content
            }
        ],
        "response_format": {"type": "json_object"}
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
        "deepseek-chat": {"input": 0.001, "output": 0.002}  # $ за 1K токенов
    }

    input_cost = (input_tokens / 1000) * rates[model]["input"]
    output_cost = (output_tokens / 1000) * rates[model]["output"]

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost
    }


if __name__ == "__main__":
    # URL = "http://sku.toscrape.com/"
    URL = "https://eviza.com.tr/product-category/chewing-gum"
    MODEL = "deepseek-chat"

    try:
        html_content = scrape_html("https://r.jina.ai/" + URL)
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
        print(f"Всего книг извлечено: {len(parsed_data['sku'])}")
        print("\nПример данных (первые 3 книги):")
        for i, sku in enumerate(parsed_data['sku']):
            print(f"{str(i + 1).zfill(4)}. {sku['sku']}; {sku['code']}; {sku['gr']}")

        # Сохранение результатов
        with open("deepseek_parsed_books.json", "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)

        print("\nРезультаты сохранены в deepseek_parsed_books.json")

    except Exception as e:
        print(f"Ошибка: {str(e)}")