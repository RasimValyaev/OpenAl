# https://github.com/theAbdoSabbagh/DeeperSeek/blob/main/docs/README.md
# pip install DeeperSeek -U

import os
# Вместо стандартной библиотеки используем нашу кастомную реализацию
from CustomDeepSeek import CustomDeepSeek
from dotenv import load_dotenv
import aiohttp
import asyncio
import chromedriver_autoinstaller
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Загрузка переменных окружения из файла .env
load_dotenv()

# Основная асинхронная функция
async def main():
    chromedriver_autoinstaller.install()
                
    # Инициализация API DeepSeek с использованием email/password
    # Используем нашу кастомную реализацию класса DeepSeek
    api = CustomDeepSeek(
        email=os.getenv('EMAIL'),
        password=os.getenv('PASSWORD'),
        # Не используем token и chat_id для первоначальной авторизации
        # token=os.getenv('DEEPSEEK_CHAT_TOKEN'),
        # chat_id=os.getenv('DEEPSEEK_CHAT_ID'),
        chrome_args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'],
        verbose=True,
        headless=False,
        attempt_cf_bypass=True,
    )
    
    try:
        # Инициализация API - это обязательный шаг согласно документации
        print("Инициализация API DeepSeek...")
        await api.initialize()  # Этот метод должен вызвать login_with_email_password() внутри библиотеки
        print("API успешно инициализирован")
        
        # Проверка успешной авторизации
        print("Проверка авторизации...")
        # Ждем появления элемента профиля, который подтверждает успешную авторизацию
        WebDriverWait(api.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="profile-button"]'))
        )
        print("Авторизация прошла успешно")
        await asyncio.sleep(2)

        # Отправка сообщения
        print("Отправка тестового сообщения...")
        response = await api.send_message(
            "Hey DeepSeek!",
            deepthink=True,
            search=False,
            slow_mode=True,
            slow_mode_delay=0.25,
            timeout=120
        )  # Возвращает объект Response

        # Вывод ответа
        print("Получен ответ:")
        print(response.text)
        print("DeepThink длительность:", response.deepthink_duration)
        print("DeepThink содержание:", response.deepthink_content)
        
    except Exception as e:
        print(f"Ошибка при выполнении: {str(e)}")
        traceback.print_exc()
        # Сделаем скриншот для диагностики, если браузер доступен
        try:
            if hasattr(api, 'driver') and api.driver:
                api.driver.save_screenshot('error_screenshot.png')
                print("Скриншот ошибки сохранен в 'error_screenshot.png'")
        except Exception as screenshot_error:
            print(f"Не удалось сделать скриншот: {str(screenshot_error)}")
    finally:
        # Закрытие браузера и сессии
        try:
            if hasattr(api, 'driver') and api.driver:
                api.driver.quit()
                print("Браузер закрыт")
            if hasattr(api, 'session') and api.session:
                await api.session.close()
                print("Сессия закрыта")
        except Exception as close_error:
            print(f"Ошибка при закрытии ресурсов: {str(close_error)}")


# Запуск приложения
if __name__ == '__main__':
    asyncio.run(main())