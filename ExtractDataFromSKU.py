# pip install requests tiktoken python-dotenv
# извлекает информацию из текста с помощью DeepSeek API.
# Скрипт отправляет запрос к API DeepSeek, получает ответ в формате JSON и парсит его.
# Извлекает грамм, шт, блок из текста и выводит их в формате: "грамм: {грамм}; шт: {шт}; блок: {блок}"
# Также подсчитывает количество токенов в запросе и ответе, а также стоимость запроса.
# и считает стоимость запроса
import tiktoken
import requests
import json
from typing import Dict
from dotenv import dotenv_values

# Загрузка переменных окружения
config = dotenv_values(".env")
API_KEY = config["DEEPSEEK_API_KEY"]  # Ключ должен быть в .env
BASE_URL = "https://api.deepseek.com/v1"

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
                "content": "Извлеки грамм, шт, блок в json формате: "
                           "{грамм: float, шт: float, блок:int}."
                           "Если данных нет, тогда ставь 1"
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
    MODEL = "deepseek-chat"

    try:
        contents = [
            """89111 Цукерки жувальні "SOUR  STRAWBERRY PENCILS "(олівці) з получним смаком 70гр х12 х6""",
            """89113 Цукерки жувальні "SOUR COLORED STRAWBERRY PENCILS "(олівці) з получним смаком 70гр х12 х6""",
            """8x1kg McBON COFFEE/KAHVELI  Цукерки карамель з кавовою начинкою   "McBON  COFFEE ", 1 кг х 8 шт""",
            """9210 Цукерки жувальні "SOUR COLORED STRAWBERRY PENCILS UNICORN" (олівці)  15 гр * 12*12 бл""",
            """9223 Цукерки жувальні "SOUR TUTTI-FRUTTI PENCILS" (олівці)  15 гр * 12*12 бл""",
            """9224 Цукерки жув. "Docile SOUR COLORED STRAWBERRY PENCILS"(олівці) з получним смаком,15 гр * 12*12бл""",
            """9225 Цукерки жувальні "STRAWBERRY PENCILS" (олівці) з полуничним смаком V2 12шт*70гр""",
            """88902 Цукерка жувальна BLACK BERRIES 1кг х12 """,
            """80051 Цукерки жувальні COLORED STRAWBERRY PENCILS UNICORN BIG 26gX24X6""",
            """9227 Цукерки жувальні "SOUR TUTTI-FRUTTI PENCILS" (олівці) V2 12шт*70гр""",
        ]
        for content in contents:
            input_tokens = count_tokens(content)

            # Извлечение информации
            result = extract_info(content, MODEL)

            # Парсинг и вывод результатов
            data = json.loads(result)
            print(f"{content}; грм: {data['грамм']}; шт: {data['шт']}; блок: {data['блок']}")

    except Exception as e:
        print(f"Ошибка: {str(e)}")