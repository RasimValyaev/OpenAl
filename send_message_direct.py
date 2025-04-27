# Скрипт для отправки сообщения в DeepSeek с использованием DEEPSEEK_CHAT_ID и DEEPSEEK_CHAT_TOKEN
import os
import requests
from dotenv import load_dotenv
import time

# Загрузка переменных окружения из файла .env
load_dotenv()

def send_message():
    # Получение токена и ID чата из переменных окружения
    token = os.getenv('DEEPSEEK_CHAT_TOKEN')
    chat_id = os.getenv('DEEPSEEK_CHAT_ID')
    
    if not token or not chat_id:
        print("Ошибка: DEEPSEEK_CHAT_TOKEN или DEEPSEEK_CHAT_ID не найдены в .env файле")
        return
    
    print(f"[{time.strftime('%H:%M:%S')}] Используем CHAT_ID: {chat_id}")
    print(f"[{time.strftime('%H:%M:%S')}] Используем TOKEN: {token[:10]}...{token[-10:]}")
    
    # Формируем URL и заголовки
    url = f"https://chat.deepseek.com/api/chat/{chat_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    
    # Формируем данные сообщения
    message = "Привет! Это тестовое сообщение, отправленное с использованием DEEPSEEK_CHAT_TOKEN и DEEPSEEK_CHAT_ID."
    data = {
        "messages": [{"role": "user", "content": message}],
        "stream": False,
        "deepthink": False,
        "search": False
    }
    
    print(f"\nОтправляемое сообщение: {message}")
    print(f"[{time.strftime('%H:%M:%S')}] Отправка запроса на {url}")
    
    try:
        # Отправляем запрос
        response = requests.post(url, headers=headers, json=data)
        
        # Проверяем статус ответа
        if response.status_code == 200:
            print(f"[{time.strftime('%H:%M:%S')}] Сообщение успешно отправлено")
            print(f"\nОтвет от DeepSeek:\n{response.text}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Ошибка при отправке сообщения: {response.status_code}")
            print(f"Текст ошибки: {response.text}")
    
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Ошибка при выполнении запроса: {str(e)}")

# Запуск функции
if __name__ == '__main__':
    send_message()