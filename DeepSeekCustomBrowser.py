# Прямая автоматизация входа в DeepSeek с использованием Selenium
import os
import asyncio
import aiohttp
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

class CustomDeepSeek:
    def __init__(self, email=None, password=None, token=None, chat_id=None, verbose=True, headless=False):
        self.email = email
        self.password = password
        self.token = token
        self.chat_id = chat_id
        self.verbose = verbose
        self.headless = headless
        self.driver = None
        self.session = None
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
        
        # Инициализация aiohttp сессии
        self.session = aiohttp.ClientSession()
        
        if self.email and self.password:
            await self.login_with_email_password()
        elif self.token:
            await self.login_with_token()
        else:
            raise ValueError("Either email/password or token must be provided")

    async def login_with_email_password(self):
        try:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Открываем страницу входа...")
            self.driver.get(f"{self.base_url}/login")
            
            # Ждем появления формы входа
            try:
                # Используем точный CSS-селектор для поля логина
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#root > div > div._99ad066 > div > div > div.ds-sign-up-form__main > div > div:nth-child(2) > div.ds-form-item__content > div > input"))
                )
                # Используем точный CSS-селектор для поля пароля
                password_input = self.driver.find_element(By.CSS_SELECTOR, "#root > div > div._99ad066 > div > div > div.ds-sign-up-form__main > div > div:nth-child(3) > div.ds-form-item__content > div > input[type='password']")
                
                # Вводим учетные данные
                email_input.send_keys(self.email)
                password_input.send_keys(self.password)
                
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Ввели email и пароль")
                
                # Ищем чекбокс и нажимаем на него, если он есть
                try:
                    # Пробуем найти чекбокс по разным селекторам
                    selectors = [
                        "div[class*='ds-checkbox']",
                        "div[role='checkbox']",
                        "div[class*='checkbox']"
                    ]
                    
                    for selector in selectors:
                        try:
                            checkbox = self.driver.find_element(By.CSS_SELECTOR, selector)
                            checkbox.click()
                            if self.verbose:
                                print(f"[{time.strftime('%H:%M:%S')}] Нажали на чекбокс")
                            break
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Не удалось найти чекбокс: {e}")
                
                # Нажимаем кнопку входа используя точный CSS-селектор
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#root > div > div._99ad066 > div > div > div.ds-sign-up-form__main > div > div.ds-button.ds-button--primary.ds-button--filled.ds-button--rect.ds-button--block.ds-button--l.ds-sign-up-form__register-button"))
                )
                login_button.click()
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Нажали кнопку входа")
                
                # Ждем успешного входа
                await asyncio.sleep(5)
                
                # Проверяем успешность входа
                try:
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="profile-button"]'))
                    )
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Успешно вошли в систему")
                    return True
                except TimeoutException:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Не удалось подтвердить успешный вход")
                    # Делаем скриншот для диагностики
                    self.driver.save_screenshot('login_error.png')
                    print("Скриншот ошибки сохранен в 'login_error.png'")
                    return False
                
            except TimeoutException:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Не удалось найти форму входа")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка входа: {e}")
            traceback.print_exc()
            return False

    async def login_with_token(self):
        if not self.token:
            raise ValueError("Token is required for token-based authentication")
        
        try:
            # Открываем страницу чата
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
                return True
            except TimeoutException:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Не удалось войти с использованием токена")
                # Пробуем войти с email/password
                if self.email and self.password:
                    return await self.login_with_email_password()
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка входа с токеном: {e}")
            traceback.print_exc()
            return False

    async def send_message(self, message, deepthink=False, search=False, slow_mode=True, slow_mode_delay=0.25, timeout=120):
        try:
            # Проверяем, что мы на странице чата
            current_url = self.driver.current_url
            if not current_url.startswith(self.base_url):
                self.driver.get(self.base_url)
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
            
            if self.session:
                await self.session.close()
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Сессия закрыта")
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка закрытия ресурсов: {e}")
            traceback.print_exc()

# Основная асинхронная функция
async def main():
    # Инициализация API DeepSeek с использованием email/password и token
    api = CustomDeepSeek(
        email=os.getenv('EMAIL'),
        password=os.getenv('PASSWORD'),
        token=os.getenv('DEEPSEEK_CHAT_TOKEN'),
        verbose=True,
        headless=True,  # Включаем режим headless для избежания проблем с отображением
    )
    
    try:
        # Инициализация API
        print("Инициализация API DeepSeek...")
        await api.initialize()
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
        )

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
        await api.close()

# Запуск приложения
if __name__ == '__main__':
    asyncio.run(main())