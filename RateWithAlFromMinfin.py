# pip install requests tiktoken python-dotenv
# извлекает информацию из текста с помощью DeepSeek API.
# Скрипт отправляет запрос к API DeepSeek, получает ответ в формате JSON и парсит его.
# Извлекает последние 10 курсов покупки и продажи из текста и выводит их в формате: "покупка: {покупка}; продажа: {продажа}; время: {время}"
# Также подсчитывает количество токенов в запросе и ответе, а также стоимость запроса.
# и считает стоимость запроса
# !!! из-за кеширования https://r.jina.ai/ выдает старые данные из кеша. ChromeDriver - не помогает
import tiktoken
import requests
import json
import time
import random
import string
from typing import Dict
from dotenv import dotenv_values
from datetime import datetime, timezone, timedelta
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Загрузка переменных окружения
config = dotenv_values(".env")
API_KEY = config["DEEPSEEK_API_KEY"]  # Ключ должен быть в .env
BASE_URL = "https://api.deepseek.com/v1"


def get_fresh_html(url):
    """Получение свежего HTML с использованием Selenium Wire"""
    # Настройка опций Chrome
    options = Options()
    options.add_argument("--headless")  # Запуск в фоновом режиме
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Случайный User-Agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
    ]
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    # Настройка Selenium Wire для перехвата и модификации запросов
    seleniumwire_options = {
        'disable_encoding': True,  # Отключаем сжатие
        'verify_ssl': False,       # Отключаем проверку SSL
    }
    
    # Инициализация драйвера
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
        seleniumwire_options=seleniumwire_options
    )
    
    # Добавляем перехватчик запросов для модификации заголовков
    def interceptor(request):
        # Добавляем случайные заголовки для обхода кеширования
        request.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        request.headers['Pragma'] = 'no-cache'
        request.headers['Expires'] = '0'
        request.headers['X-Random'] = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
    
    driver.request_interceptor = interceptor
    
    try:
        # Добавляем случайные параметры для обхода кеша
        timestamp = int(time.time())
        cache_buster = ''.join(random.choices(string.ascii_letters + string.digits, k=15))
        
        if "?" in url:
            full_url = f"{url}&nocache={cache_buster}&t={timestamp}"
        else:
            full_url = f"{url}?nocache={cache_buster}&t={timestamp}"
        
        print(f"Загрузка страницы: {full_url}")
        print(f"Текущее время: {datetime.now().strftime('%H:%M:%S')}")
        
        # Загрузка страницы
        driver.get(full_url)
        
        # Ждем загрузки контента и выполнения JavaScript
        time.sleep(15)  # Увеличиваем время ожидания
        
        # Выполняем JavaScript для обновления страницы
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # Получаем HTML
        html = driver.page_source
        
        # Сохраняем HTML для отладки
        with open("latest_page.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        # Сохраняем скриншот для визуальной проверки
        driver.save_screenshot("screenshot.png")
        
        return html
    finally:
        driver.quit()


def extract_info(content: str, model: str = "deepseek-chat"):
    """Извлечение информации с помощью DeepSeek"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Определяем киевское смещение (UTC+2 зимой, UTC+3 летом)
    kiev_offset = 2  # Фиксируем на UTC+2, как указано в требовании

    # Получаем текущее время в UTC
    utc_now = datetime.utcnow()
    # Вычисляем текущее время в Киеве (UTC+2)
    kiev_now = utc_now.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=kiev_offset)))
    current_time = kiev_now.strftime('%H:%M')

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": f"Извлеки первые 10 строк из таблицы курсов валют. "
                f"Нужны курсы покупки и продажи в json формате: "
                f"{{курсы: [{{покупка: float, продажа: float, время: string}}]}}. "
                f"Время указано для UTC. Переведи его для Киева. "
                f"Текущее время в Киеве (UTC+2): {current_time}. "
                f"Результат отсортируй в порядке убывания времени (сначала самые свежие).",
            },
            {"role": "user", "content": content},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,  # Снижаем температуру для более точных результатов
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


def get_deepseek_pricing():
    """Получает актуальные тарифы DeepSeek с официального сайта документации"""
    try:
        url = "https://api-docs.deepseek.com/quick_start/pricing"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Не удалось получить данные о тарифах. Код ответа: {response.status_code}")
            return {"deepseek-chat": {"input": 0.00027, "output": 0.0011}}  # Возвращаем значения по умолчанию

        # Используем DeepSeek для извлечения информации о тарифах из HTML
        pricing_html = response.text

        # Извлекаем информацию о ценах с помощью DeepSeek
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
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
                    "Часовой пояс UTC+2."
                },
                {"role": "user", "content": pricing_html},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        pricing_response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )

        if pricing_response.status_code == 200:
            pricing_data = json.loads(pricing_response.json()["choices"][0]["message"]["content"])
            print(f"Получены актуальные тарифы: input=${pricing_data['input']}, output=${pricing_data['output']} за 1K токенов")
            return {"deepseek-chat": {"input": pricing_data["input"], "output": pricing_data["output"]}}
        else:
            print(f"Ошибка при извлечении тарифов: {pricing_response.status_code} - {pricing_response.text}")
            return {"deepseek-chat": {"input": 0.00027, "output": 0.0011}}  # Возвращаем значения по умолчанию

    except Exception as e:
        print(f"Ошибка при получении тарифов: {str(e)}")
        return {"deepseek-chat": {"input": 0.00027, "output": 0.0011}}  # Возвращаем значения по умолчанию


def calculate_cost(input_tokens: int, output_tokens: int, model: str = "deepseek-chat") -> Dict[str, float]:
    """Расчет стоимости запроса"""
    # Получаем актуальные тарифы
    rates = get_deepseek_pricing()

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
        # html_content = get_dynamic_html("https://r.jina.ai/" + URL)
        html_content = get_fresh_html("https://r.jina.ai/" + URL)
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
        
        # Получаем текущую и вчерашнюю даты
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Обрабатываем даты в результатах
        for rate in parsed_data['курсы']:
            # Проверяем, содержит ли время слова "Сегодня" или "Вчера"
            if 'Сегодня' in rate['время']:
                rate['время'] = rate['время'].replace('Сегодня', today)
            elif 'Вчера' in rate['время']:
                rate['время'] = rate['время'].replace('Вчера', yesterday)
            # Если время не содержит дату, добавляем сегодняшнюю дату
            elif ':' in rate['время'] and ' ' not in rate['время']:
                rate['время'] = f"{today} {rate['время']}"

        print("\n--- РЕЗУЛЬТАТЫ ПАРСИНГА ---")
        print(f"Всего записей извлечено: {len(parsed_data['курсы'])}")
        for i, data in enumerate(parsed_data['курсы']):
            print(f"{i + 1}. покупка: {data['покупка']}; продажа: {data['продажа']}; время: {data['время']}")

        # Расчет средних значений
        if parsed_data['курсы']:
            avg_buy = sum(rate['покупка'] for rate in parsed_data['курсы']) / len(parsed_data['курсы'])
            avg_sell = sum(rate['продажа'] for rate in parsed_data['курсы']) / len(parsed_data['курсы'])
            print("\n--- СРЕДНИЕ ЗНАЧЕНИЯ ---")
            print(f"Средняя покупка: {round(avg_buy,2)}")
            print(f"Средняя продажа: {round(avg_sell,2)}")

        # Сохранение результатов
        with open("deepseek_parsed_rates.json", "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)

        print("\nРезультаты сохранены в deepseek_parsed_rates.json")

    except Exception as e:
        print(f"Ошибка: {str(e)}")
