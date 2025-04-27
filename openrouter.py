# https://www.youtube.com/watch?v=j0VfsZxdUEg

from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import sys

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем API ключ
base_url = "https://openrouter.ai/api/v1"
api_key = os.getenv("OPEN_ROUTER_GEMINI_API_KEY")

# Получаем идентификаторы моделей
gemini_model = os.getenv("MODEL_GEMINI_25", "google/gemini-1.5-pro-latest")
 
# Создаем клиент OpenAI с базовым URL OpenRouter и API ключом
client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

def parse_with_openrouter(content: str, model: str = None):
    """
    Парсит текст с помощью OpenRouter API
    
    Args:
        content: Текст для парсинга
        model: Модель для использования (если None, используется gemini_model)
    
    Returns:
        Распарсенный JSON ответ в виде словаря Python
    """
    if model is None:
        model = gemini_model
    
    # print(f"Используемая модель: {model}")
    
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
                    "}"
                    " Если отсутствует информация, выведи пустоту. НДС извлеки не %, а сумму. "
                    "Дату выводи в формате: dd.mm.yyyy."
                    "Период выводи в формате: mm.yyyy",
                },
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
        )

        # Получаем строку JSON из ответа
        json_str = completion.choices[0].message.content

        # Преобразуем строку JSON в словарь Python
        try:
            result_dict = json.loads(json_str)
            return result_dict
        except json.JSONDecodeError:
            print("Ошибка при декодировании JSON")
            return json_str  # Возвращаем исходную строку в случае ошибки
    except Exception as e:
        print(f"Ошибка при запросе к API: {str(e)}")
        return {"error": str(e)}


# Пример использования
if __name__ == "__main__":
    # print(f"API ключ: {'Установлен' if api_key else 'Не установлен'}")
    # print(f"Модель Gemini: {gemini_model}")
    
    test_text = "ОПЛАТА ЗГ. РАХ № 10116/202503/1617ВІД 01.03.2025РОКУ ПО ДОГОВОРУ 6061 ВІД 01,04,2020Р. У сумі 2500.00 грн., ПДВ - 20 % 500.00 грн."
    result = parse_with_openrouter(test_text)
    # print(f"Тип результата: {type(result)}")
    print(f"Результат: {result}")
