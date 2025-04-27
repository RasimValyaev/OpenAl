# https://openrouter.ai/
# https://www.youtube.com/watch?v=j0VfsZxdUEg
import asyncio
from datetime import datetime
import aiohttp
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import pandas as pd
import asyncpg

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем API ключ
base_url = "https://openrouter.ai/api/v1"
model_and_api_keys = [
    {os.getenv("GEMINI_25_MODEL"): os.getenv("GEMINI_25_API_KEY")},
    {os.getenv("DEEP_SEEK_MODEL"): os.getenv("DEEP_SEEK_API_KEY")},
    {os.getenv("BYTEDANCE_UI_TARS_MODEL"): os.getenv("BYTEDANCE_UI_TARS_API_KEY")},
    {os.getenv("QWEN_MODEL"): os.getenv("QWEN_API_KEY")},
    {os.getenv("QWERKY_MODEL"): os.getenv("QWERKY_API_KEY")},
    {os.getenv("MISTRAL_MODEL"): os.getenv("MISTRAL_API_KEY")},
    {os.getenv("ANUBIS_MODEL"): os.getenv("ANUBIS_API_KEY")},
]

client = None

# из базы pg, таб t_pb извлечем уникальные данные
async def extract_data_from_postgresql():
    user = os.getenv("PG_USER")
    password = os.getenv("PG_PASSWORD")
    host = os.getenv("PG_HOST_LOCAL")  # os.getenv("PG_HOST"]
    port = os.getenv("PG_PORT")
    dbname = os.getenv("PG_DBNAME")

    conn = await asyncpg.connect(
        user=user, password=password, host=host,
        port=port, database=dbname
    )

    records = await conn.fetch(
        """SELECT DISTINCT osnd FROM t_pb WHERE date_time_dat_od_tim_p::date >= '01.03.2025'::date;"""
    )
    await conn.close()

    return pd.DataFrame(records, columns=["osnd"])


async def parse_with_openrouter(content: str)-> dict:
    """
    Парсит текст с помощью OpenRouter API
    
    Args:
        content: Текст для парсинга
        model: Модель для использования (если None, используется gemini_model)
    
    Returns:
        Распарсенный JSON ответ в виде словаря Python
    """
    for i in range(3):
        for model_and_api_key in model_and_api_keys:
            model = list(model_and_api_key.keys())[0]
            api_key = list(model_and_api_key.values())[0]

            # Создаем клиент OpenAI с базовым URL OpenRouter и API ключом
            client = OpenAI(base_url=base_url, api_key=api_key)

            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
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
                            "}."
                            " Если отсутствует информация, выведи пустоту. НДС извлеки не %, а сумму. "
                            "Дату выводи в формате: dd.mm.yyyy."
                            "Период выводи в формате: mm.yyyy.",
                        },
                        {"role": "user", "content": content},
                    ],
                    response_format={"type": "json_object"},
                )

                # Получаем строку JSON из ответа
                if hasattr(completion, 'choices') and completion.choices:
                    json_str = completion.choices[0].message.content

                    # Преобразуем строку JSON в словарь Python
                    try:
                        # Очищаем строку от маркеров кода и лишних символов
                        if json_str.startswith('```json'):
                            # Удаляем маркеры кода markdown
                            clean_json = json_str.replace('```json', '').replace('```', '').strip()
                        else:
                            clean_json = json_str

                        result_dict = json.loads(clean_json)

                        # Преобразуем None в 0 для поля НДС
                        if result_dict.get('НДС') is None:
                            result_dict['НДС'] = 0.0

                        # Проверяем и преобразуем другие поля при необходимости
                        for key in ['за_что', 'номер_договора', 'номер_счета', 'номер_накладной', 'номер_заказа', 'дата', 'период']:
                            if result_dict.get(key) is None:
                                result_dict[key] = ""

                        return result_dict
                    except json.JSONDecodeError:
                        print("Ошибка при декодировании JSON")
                        print(f"Проблемная строка: {json_str}")
                        print({"error": "JSON decode error", "raw": json_str})
                        continue
                elif hasattr(completion, 'error'):
                    # Обработка ошибки rate limit
                    if completion.error.get('code') == 429:
                        reset_time = int(completion.error.get('metadata', {}).get('headers', {}).get('X-RateLimit-Reset', 0)) / 1000
                        current_time = datetime.now().timestamp()
                        wait_time = max(5, min(60, reset_time - current_time))  # Ждем не менее 5 сек, но не более 60

                        print(f"{model};\nRate limit exceeded. Waiting for {wait_time:.1f} seconds before retry...")
                        await asyncio.sleep(wait_time)
                        continue  # Повторяем попытку после ожидания

                    return {"error": f"API Error: {completion.error.get('message', 'Unknown error')}"}
                else:
                    return {"error": "Unknown response format"}

            except Exception as e:
                print(f"Ошибка при запросе к API: {str(e)}")
                await asyncio.sleep(5)  # Добавляем задержку перед повторной попыткой

    # Если все попытки исчерпаны
    return {"error": "Exceeded maximum retry attempts"}


async def DeepSeekParseBankOpenRouter_main():
    df = await extract_data_from_postgresql()
    print(df)
    for i, row in df.iterrows():
        print("-" * 80)
        content = row["osnd"]
        result = await parse_with_openrouter(content)
        if 'error' in result.keys():
            print(f"Ошибка при обработке контента {content}:")
            print(result['error'])
            continue
        print(f"content:{i + 1}\n"
            f"{content}\n"
            f"за_что:{result['за_что']}\n"
            f"номер_договора: {result['номер_договора']}\n"
            f"номер_счета: {result['номер_счета']}\n"
            f"номер_накладной: {result['номер_накладной']}\n"
            f"номер_заказа: {result['номер_заказа']}\n"
            f"дата: {result['дата']}\n"
            f"НДС:{result['НДС']}\n"
            f"период:{result['период']}\n"
        )

# Получение списка моделей. Далее из них будем отбирать бесплатные
async def get_models():
    url = "https://openrouter.ai/api/v1/models"
    result = await aiohttp.ClientSession().get(url)
    print(result.status)
    if result.status != 200:
        print("Error")
        return
    print(await result.json())
    return await result.json()


# из json отберем все бесплатные модели
def get_free_models_from_json(json_data)->json:
    free_models = {"data":[{i['id']:i['name']} for i in models['data'] if i['pricing']['prompt'] == '0']}
    return free_models

# Пример использования
if __name__ == "__main__":
    print(f"время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    models = asyncio.run(get_models())
    print(get_free_models_from_json(models))
    asyncio.run(DeepSeekParseBankOpenRouter_main())
    print(f"время конца: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
