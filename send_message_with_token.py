# Скрипт для отправки сообщения в DeepSeek с использованием DEEPSEEK_CHAT_ID и DEEPSEEK_CHAT_TOKEN
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
import time

# Загрузка переменных окружения из файла .env
load_dotenv()

class DeepSeekAPI:
    def __init__(self, token, chat_id, verbose=True):
        self.token = token
        self.chat_id = chat_id
        self.verbose = verbose
        self.session = None
        self.base_url = "https://chat.deepseek.com"

    async def initialize(self):
        # Инициализация aiohttp сессии
        self.session = aiohttp.ClientSession()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] Инициализация API с использованием токена")
        return True

    async def send_message(self, message, deepthink=False, search=False):
        try:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Отправка сообщения в чат {self.chat_id}")
            
            payload = {
                "messages": [{"role": "user", "content": message}],
                "stream": False,
                "deepthink": deepthink,
                "search": search,
                "chat_id": self.chat_id
            }
            
            async with self.session.post(f"{self.base_url}/api/chat/completions", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка API: {response.status} - {error_text}")
                    return None
                
                data = await response.json()
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Сообщение успешно отправлено")
                
                return type('Response', (), {
                    'text': data['choices'][0]['message']['content'] if 'choices' in data and len(data['choices']) > 0 else '',
                    'chat_id': data.get('chat_id', self.chat_id)
                })
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка отправки сообщения: {str(e)}")
            raise

    async def close(self):
        if self.session:
            await self.session.close()
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Сессия закрыта")

async def main():
    # Получение токена и ID чата из переменных окружения
    token = os.getenv('DEEPSEEK_CHAT_TOKEN')
    chat_id = os.getenv('DEEPSEEK_CHAT_ID')
    
    if not token or not chat_id:
        print("Ошибка: DEEPSEEK_CHAT_TOKEN или DEEPSEEK_CHAT_ID не найдены в .env файле")
        return
    
    # Создание экземпляра API
    api = DeepSeekAPI(token=token, chat_id=chat_id, verbose=True)
    
    try:
        # Инициализация API
        await api.initialize()
        
        # Отправка тестового сообщения
        message = "Привет! Это тестовое сообщение, отправленное с использованием DEEPSEEK_CHAT_TOKEN и DEEPSEEK_CHAT_ID."
        print(f"\nОтправляемое сообщение: {message}")
        
        response = await api.send_message(message, deepthink=False, search=False)
        
        if response:
            print(f"\nОтвет от DeepSeek:\n{response.text}")
        else:
            print("\nНе удалось получить ответ от DeepSeek")
            
    except Exception as e:
        print(f"Ошибка при выполнении: {str(e)}")
    finally:
        # Закрытие сессии
        await api.close()

# Запуск приложения
if __name__ == '__main__':
    asyncio.run(main())