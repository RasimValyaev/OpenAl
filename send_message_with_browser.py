# Скрипт для отправки сообщения в DeepSeek с использованием DEEPSEEK_CHAT_ID и DEEPSEEK_CHAT_TOKEN через браузер
import os
import asyncio
from dotenv import load_dotenv
import chromedriver_autoinstaller
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Загрузка переменных окружения из файла .env
load_dotenv()

class DeepSeekBrowser:
    def __init__(self, token, chat_id, verbose=True, headless=False):
        self.token = token
        self.chat_id = chat_id
        self.verbose = verbose
        self.headless = headless
        self.driver = None
        self.base_url = "https://chat.deepseek.com"

    async def initialize(self):
        # Инициализация браузера
        chromedriver_autoinstaller.install()
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        
        # Добавляем аргументы для обхода защиты от автоматизации
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        self.driver = webdriver.Chrome(options=options)
        
        try:
            # Открываем страницу чата
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Открываем страницу DeepSeek...")
            self.driver.get(self.base_url)
            
            # Устанавливаем cookie с токеном
            self.driver.add_cookie({
                'name': 'userToken',
                'value': self.token,
                'domain': 'chat.deepseek.com',
                'path': '/',
            })
            
            # Перезагружаем страницу
            self.driver.refresh()
            
            # Ждем успешного входа
            await asyncio.sleep(5)
            
            # Проверяем успешность входа
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="profile-button"]'))
                )
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Успешно вошли в систему с использованием токена")
                
                # Переходим в указанный чат, если есть chat_id
                if self.chat_id:
                    chat_url = f"{self.base_url}/chat/{self.chat_id}"
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Переходим в чат: {chat_url}")
                    self.driver.get(chat_url)
                    await asyncio.sleep(3)
                
                return True
            except TimeoutException:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Не удалось войти с использованием токена")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка инициализации: {e}")
            traceback.print_exc()
            return False

    async def send_message(self, message, deepthink=False, search=False, slow_mode=True, slow_mode_delay=0.25, timeout=120):
        try:
            # Проверяем, что мы на странице чата
            current_url = self.driver.current_url
            if not current_url.startswith(self.base_url):
                self.driver.get(f"{self.base_url}/chat/{self.chat_id}")
                await asyncio.sleep(2)
            
            # Находим текстовое поле для ввода сообщения
            textbox = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea'))
            )
            
            # Вводим сообщение
            if slow_mode:
                for char in message:
                    textbox.send_keys(char)
                    await asyncio.sleep(slow_mode_delay)
            else:
                textbox.send_keys(message)
            
            # Находим и нажимаем кнопки опций, если нужно
            if deepthink or search:
                # Находим кнопки опций
                option_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
                
                # Включаем DeepThink, если нужно
                if deepthink:
                    for button in option_buttons:
                        if "DeepThink" in button.get_attribute("innerHTML"):
                            if not "active" in button.get_attribute("class"):
                                button.click()
                            break
                
                # Включаем Search, если нужно
                if search:
                    for button in option_buttons:
                        if "Search" in button.get_attribute("innerHTML"):
                            if not "active" in button.get_attribute("class"):
                                button.click()
                            break
            
            # Находим и нажимаем кнопку отправки
            send_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
            for button in send_buttons:
                if button.get_attribute("aria-label") == "Send message":
                    button.click()
                    break
            
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Сообщение отправлено")
            
            # Ждем ответа
            start_time = time.time()
            response_text = ""
            deepthink_content = ""
            deepthink_duration = 0
            
            # Если включен DeepThink, ждем его завершения
            if deepthink:
                try:
                    deepthink_start = time.time()
                    # Ждем появления блока DeepThink
                    WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="deepthink"]'))
                    )
                    
                    # Ждем завершения DeepThink
                    while True:
                        if time.time() - start_time > timeout:
                            break
                        
                        try:
                            # Проверяем, завершился ли DeepThink
                            deepthink_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="deepthink"]')
                            if not deepthink_elements:
                                break
                            
                            # Получаем содержимое DeepThink
                            deepthink_content = deepthink_elements[0].text
                            
                            await asyncio.sleep(1)
                        except:
                            break
                    
                    deepthink_duration = time.time() - deepthink_start
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] DeepThink завершен за {deepthink_duration:.2f} секунд")
                except TimeoutException:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Таймаут ожидания DeepThink")
            
            # Ждем ответа от модели
            try:
                # Ждем появления ответа
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="message-content"]'))
                )
                
                # Ждем завершения генерации ответа
                while True:
                    if time.time() - start_time > timeout:
                        break
                    
                    # Проверяем, есть ли индикатор загрузки
                    loading_indicators = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="loading"]')
                    if not loading_indicators:
                        # Получаем текст ответа
                        message_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="message-content"]')
                        if message_elements:
                            response_text = message_elements[-1].text
                        break
                    
                    await asyncio.sleep(1)
                
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Получен ответ")
            except TimeoutException:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Таймаут ожидания ответа")
            
            # Создаем объект ответа
            response = type('Response', (), {
                'text': response_text,
                'deepthink_content': deepthink_content,
                'deepthink_duration': deepthink_duration
            })
            
            return response
            
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка отправки сообщения: {e}")
            traceback.print_exc()
            raise

    async def close(self):
        try:
            if self.driver:
                self.driver.quit()
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Браузер закрыт")
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка закрытия ресурсов: {e}")
            traceback.print_exc()

async def main():
    # Получение токена и ID чата из переменных окружения
    token = os.getenv('DEEPSEEK_CHAT_TOKEN')
    chat_id = os.getenv('DEEPSEEK_CHAT_ID')
    
    if not token or not chat_id:
        print("Ошибка: DEEPSEEK_CHAT_TOKEN или DEEPSEEK_CHAT_ID не найдены в .env файле")
        return
    
    # Создание экземпляра браузера
    browser = DeepSeekBrowser(token=token, chat_id=chat_id, verbose=True, headless=False)
    
    try:
        # Инициализация браузера
        success = await browser.initialize()
        if not success:
            print("Не удалось инициализировать браузер")
            return
        
        # Отправка тестового сообщения
        message = "Привет! Это тестовое сообщение, отправленное с использованием DEEPSEEK_CHAT_TOKEN и DEEPSEEK_CHAT_ID через браузер."
        print(f"\nОтправляемое сообщение: {message}")
        
        response = await browser.send_message(
            message,
            deepthink=False,
            search=False,
            slow_mode=True,
            slow_mode_delay=0.1,
            timeout=120
        )
        
        if response:
            print(f"\nОтвет от DeepSeek:\n{response.text}")
        else:
            print("\nНе удалось получить ответ от DeepSeek")
            
    except Exception as e:
        print(f"Ошибка при выполнении: {str(e)}")
        traceback.print_exc()
    finally:
        # Закрытие браузера
        await browser.close()

# Запуск приложения
if __name__ == '__main__':
    asyncio.run(main())