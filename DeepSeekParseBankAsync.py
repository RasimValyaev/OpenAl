import tiktoken
import aiohttp
import asyncio
import json
from typing import Dict, Any, List
from dotenv import dotenv_values
import os
import pandas as pd
import sys
import subprocess

# Проверка и установка необходимых модулей
try:
    import asyncpg
except ModuleNotFoundError:
    print("Модуль 'asyncpg' не найден. Устанавливаю...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "asyncpg"])
    import asyncpg

# Загрузка переменных окружения
config = dotenv_values(".env")
API_KEY = config["DEEPSEEK_API_KEY"]  # Ключ должен быть в .env
BASE_URL = "https://api.deepseek.com/v1"

# Начальный баланс (указывается вручную в .env)
initial_balance = float(config.get("INITIAL_BALANCE", 0.0))


# из базы pg, таб t_pb извлечем уникальные данные
async def extract_data_from_postgresql():
    user = config["PG_USER"]
    password = config["PG_PASSWORD"]
    host = config["PG_HOST"]
    port = config["PG_PORT"]
    dbname = config["PG_DBNAME"]
    
    conn = await asyncpg.connect(
        user=user, password=password, host=host, 
        port=port, database=dbname
    )
    
    records = await conn.fetch(
        """SELECT DISTINCT osnd FROM t_pb WHERE date_time_dat_od_tim_p::date >= '25.03.2025'::date Limit 5;"""
    )
    await conn.close()
    
    return pd.DataFrame(records, columns=["osnd"])


# Извлечение информации с помощью DeepSeek
async def extract_info(content: str, session: aiohttp.ClientSession, model: str = "deepseek-chat"):
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

    try:
        async with session.post(
            f"{BASE_URL}/chat/completions", headers=headers, json=payload
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_text = await response.text()
                print(f"Ошибка API: {response.status} - {error_text}")
                raise Exception(f"API Error: {response.status} - {error_text}")
    except aiohttp.ClientPayloadError as e:
        print(f"Ошибка загрузки ответа: {str(e)}")
        return json.dumps({"за_что": "", "номер_договора": "", "номер_счета": "", "номер_накладной": "", "номер_заказа": "", "дата": "", "НДС": 0.0, "период": ""})
    except Exception as e:
        print(f"Общая ошибка при запросе: {str(e)}")
        return json.dumps({"за_что": "", "номер_договора": "", "номер_счета": "", "номер_накладной": "", "номер_заказа": "", "дата": "", "НДС": 0.0, "период": ""})


# Подсчет количества токенов в тексте
def count_tokens(text: str, model: str = "deepseek-chat") -> int:
    """Подсчет количества токенов в тексте"""
    encoding = tiktoken.get_encoding("cl100k_base")  # DeepSeek использует ту же кодировку
    return len(encoding.encode(text))


# Получение актуальных тарифов DeepSeek
async def get_deepseek_pricing(session: aiohttp.ClientSession):
    """Получает актуальные тарифы DeepSeek с официального сайта документации"""
    try:
        url = "https://api-docs.deepseek.com/quick_start/pricing"
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Не удалось получить данные о тарифах. Код ответа: {response.status}")
                return {"deepseek-chat": {"input": 0.00027, "output": 0.0011}}

            pricing_html = await response.text()

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

        async with session.post(
            f"{BASE_URL}/chat/completions", headers=headers, json=payload
        ) as pricing_response:
            if pricing_response.status == 200:
                result = await pricing_response.json()
                pricing_data = json.loads(result["choices"][0]["message"]["content"])
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
                    f"Ошибка при извлечении тарифов: {pricing_response.status} - {await pricing_response.text()}"
                )
                return {"deepseek-chat": {"input": 0.00027, "output": 0.0011}}

    except Exception as e:
        print(f"Ошибка при получении тарифов: {str(e)}")
        return {"deepseek-chat": {"input": 0.00027, "output": 0.0011}}


# Расчет стоимости запроса
async def calculate_cost(
    input_tokens: int, output_tokens: int, 
    session: aiohttp.ClientSession, 
    model: str = "deepseek-chat"
) -> Dict[str, float]:
    """Расчет стоимости запроса"""
    # Получаем актуальные тарифы
    rates = await get_deepseek_pricing(session)

    input_cost = (input_tokens / 1000) * rates[model]["input"]
    output_cost = (output_tokens / 1000) * rates[model]["output"]

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
    }


async def process_content(content: str, i: int, session: aiohttp.ClientSession, MODEL: str):
    try:
        print("-" * 80)
        print(f"Обработка контента {i + 1}...")
        result = await extract_info(content, session, MODEL)
        data = json.loads(result)
        
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
        
        return data
        
    except Exception as e:
        print(f"Ошибка при обработке контента {i}: {str(e)}")
        return None


async def extract_from_deepseek_main():
    MODEL = "deepseek-chat"
    df = await extract_data_from_postgresql()
    
    try:
        df["назначение"] = ""
        df["номер_договора"] = ""
        df["номер_счета"] = ""
        df["номер_накладной"] = ""
        df["номер_заказа"] = ""
        df["дата"] = ""
        df["НДС"] = ""
        df["период"] = ""

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, row in df.iterrows():
                task = process_content(row["osnd"], i, session, MODEL)
                tasks.append(task)
            
            # Выполняем задачи параллельно с ограничением в 5 одновременных запросов
            for i in range(0, len(tasks), 5):
                batch = tasks[i:i+5]
                results = await asyncio.gather(*batch)
                
                for j, data in enumerate(results):
                    if data:
                        idx = i + j
                        df.loc[idx, "назначение"] = data["за_что"]
                        df.loc[idx, "номер_договора"] = data["номер_договора"]
                        df.loc[idx, "номер_счета"] = data["номер_счета"]
                        df.loc[idx, "номер_накладной"] = data["номер_накладной"]
                        df.loc[idx, "номер_заказа"] = data["номер_заказа"]
                        df.loc[idx, "дата"] = data["дата"]
                        df.loc[idx, "НДС"] = data["НДС"]
                        df.loc[idx, "период"] = data["период"]
                
                # Небольшая задержка между батчами
                await asyncio.sleep(1)

    except Exception as e:
        print(f"Ошибка: {str(e)}")

    # Сохраняем результаты в excel
    df.to_excel("deepseek_parsed_data_async.xlsx", index=False)


if __name__ == "__main__":
    asyncio.run(extract_from_deepseek_main())