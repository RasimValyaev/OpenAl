# pip install chromedriver-autoinstaller selenium python-dotenv aiohttp

# Прямая автоматизация входа в DeepSeek с использованием Selenium
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
import chromedriver_autoinstaller
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

chromedriver_autoinstaller.install()

load_dotenv()

class DeepSeek:
    def __init__(self, email=None, password=None, token=None, chat_id=None, verbose=False, headless=False, attempt_cf_bypass=False):
        self.email = email
        self.password = password
        self.token = token
        self.chat_id = chat_id
        self.verbose = verbose
        self.headless = headless
        self.attempt_cf_bypass = attempt_cf_bypass
        self.browser = None
        self.session = None
        self.base_url = "https://chat.deepseek.com"

    async def initialize(self):
        # Инициализация браузера
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        if self.attempt_cf_bypass:
            options.add_argument('--disable-blink-features=AutomationControlled')
        
        service = Service()
        self.browser = webdriver.Chrome(service=service, options=options)
        
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
            self.browser.get(f"{self.base_url}/login")
            # Ждем появления формы входа
            email_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            password_input = self.browser.find_element(By.CSS_SELECTOR, "input[type='password']")
            
            # Вводим учетные данные
            email_input.send_keys(self.email)
            password_input.send_keys(self.password)
            
            # Нажимаем кнопку входа
            login_button = self.browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Ждем успешного входа
            await asyncio.sleep(5)
            
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Successfully logged in")
            return True
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Login failed: {e}")
            return False

    async def login_with_token(self):
        if not self.token:
            raise ValueError("Token is required for token-based authentication")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return True

    async def send_message(self, message, slow_mode=False, deepthink=False, search=False, slow_mode_delay=0.25):
        try:
            payload = {
                "messages": [{"role": "user", "content": message}],
                "stream": slow_mode,
                "deepthink": deepthink,
                "search": search
            }
            
            if self.chat_id:
                payload["chat_id"] = self.chat_id
            
            async with self.session.post(f"{self.base_url}/api/chat/completions", json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return type('Response', (), {'text': data['choices'][0]['message']['content'], 'chat_id': data.get('chat_id')})
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Failed to send message: {e}")
            raise

async def main():
    # Загрузка учетных данных из .env
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')
    token = os.getenv('DEEPSEEK_CHAT_TOKEN')
    chat_id = os.getenv('DEEPSEEK_CHAT_ID')

    # Создание экземпляра класса с включенным режимом вывода отладочной информации
    client = DeepSeek(email=email, password=password, token=token, chat_id=chat_id, verbose=True)

    try:
        # Инициализация клиента
        await client.initialize()

        # Отправка тестового сообщения
        response = await client.send_message("Привет! Как дела?")
        print(f"\nОтвет от API: {response.text}")

    except Exception as e:
        print(f"Ошибка при выполнении: {str(e)}")
    finally:
        # Закрытие браузера и сессии
        if client.browser:
            client.browser.quit()
        if client.session:
            await client.session.close()

if __name__ == "__main__":
    asyncio.run(main())

    async def regenerate_response(self):
        if not self.chat_id:
            raise ValueError("No chat_id available for regeneration")
        try:
            async with self.session.post(f"{self.base_url}/api/chat/{self.chat_id}/regenerate") as response:
                response.raise_for_status()
                data = await response.json()
                return type('Response', (), {'text': data['choices'][0]['message']['content'], 'chat_id': self.chat_id})
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Failed to regenerate response: {e}")
            raise

    async def reset_chat(self):
        if not self.chat_id:
            return
        try:
            async with self.session.post(f"{self.base_url}/api/chat/{self.chat_id}/reset") as response:
                response.raise_for_status()
                self.chat_id = None
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Failed to reset chat: {e}")
            raise

    async def retrieve_token(self):
        try:
            async with self.session.get(f"{self.base_url}/api/auth/token") as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('token')
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Failed to retrieve token: {e}")
            raise

    async def logout(self):
        try:
            if self.browser:
                self.browser.quit()
            if self.session:
                await self.session.close()
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Failed to logout: {e}")
            raise

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()

# Класс для расширения функциональности DeepSeek с поддержкой пользовательских селекторов
class CustomDeepSeek(DeepSeek):
    def __init__(self, email=None, password=None, token=None, chat_id=None, verbose=False, headless=False, attempt_cf_bypass=False,
                 email_selector=None, password_selector=None):
        super().__init__(email, password, token, chat_id, verbose, headless, attempt_cf_bypass)
        self.email_selector = email_selector
        self.password_selector = password_selector
    
    async def login_with_email_password(self):
        """Полностью переопределяем метод входа для использования пользовательских селекторов"""
        try:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Using custom selectors for login...")
            
            # Переход на страницу логина, если мы еще не на ней
            current_url = await self.browser.page.evaluate("window.location.href")
            if "login" not in current_url:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Navigating to login page...")
                await self.browser.page.goto("https://chat.deepseek.com/login")
                await asyncio.sleep(3)  # Ждем загрузку страницы
            
            # Использование пользовательских селекторов для ввода данных
            if self.email_selector and self.password_selector:
                # Ввод email
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Filling email field with selector: {self.email_selector}")
                
                # Делаем скриншот для отладки перед вводом данных
                await self.browser.page.screenshot({"path": "login_before.png"})
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Screenshot saved as login_before.png")
                
                # Проверяем наличие поля email
                email_exists = await self.browser.page.evaluate(f"!!document.querySelector('{self.email_selector}')")
                if not email_exists:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Email field not found with selector: {self.email_selector}")
                    raise Exception(f"Email field not found with selector: {self.email_selector}")
                
                # Ввод email с использованием JavaScript
                await self.browser.page.evaluate(f'''
                    const emailInput = document.querySelector("{self.email_selector}");
                    emailInput.value = "{self.email}";
                    emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    emailInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                ''')
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Email entered successfully")
                
                await asyncio.sleep(1)
                
                # Ввод пароля
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Filling password field with selector: {self.password_selector}")
                
                # Проверяем наличие поля пароля
                password_exists = await self.browser.page.evaluate(f"!!document.querySelector('{self.password_selector}')")
                if not password_exists:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Password field not found with selector: {self.password_selector}")
                    raise Exception(f"Password field not found with selector: {self.password_selector}")
                
                # Ввод пароля с использованием JavaScript
                await self.browser.page.evaluate(f'''
                    const passwordInput = document.querySelector("{self.password_selector}");
                    passwordInput.value = "{self.password}";
                    passwordInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    passwordInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                ''')
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Password entered successfully")
                
                await asyncio.sleep(1)
                
                # Делаем скриншот для отладки после ввода данных
                await self.browser.page.screenshot({"path": "login_after_input.png"})
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Screenshot saved as login_after_input.png")
                
                # Поиск и нажатие кнопки входа
                await self.browser.page.evaluate('''
                    // Попробуем найти кнопку по разным атрибутам
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const loginButton = buttons.find(button => 
                        button.textContent.toLowerCase().includes('login') || 
                        button.textContent.toLowerCase().includes('sign in') ||
                        button.textContent.toLowerCase().includes('войти') ||
                        button.type === 'submit');
                    if (loginButton) {
                        console.log('Login button found, clicking...');
                        loginButton.click();
                    } else {
                        console.log('Login button not found');
                    }
                ''')
                
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Login button clicked")
                
                # Ожидание успешного входа
                await asyncio.sleep(5)
                
                # Делаем скриншот для отладки после нажатия кнопки
                await self.browser.page.screenshot({"path": "login_after_click.png"})
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Screenshot saved as login_after_click.png")
                
                # Проверяем, успешно ли вошли
                current_url = await self.browser.page.evaluate("window.location.href")
                if "chat" in current_url and "login" not in current_url:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Login successful!")
                    return True
                else:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Login might have failed, current URL: {current_url}")
                    # Продолжаем выполнение, возможно, мы все еще на странице входа
                
                return True
            else:
                # Использование стандартного метода, если селекторы не предоставлены
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] No custom selectors provided, using default login method")
                return await super().login_with_email_password()
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Failed to login with custom selectors: {e}")
            # Делаем скриншот для отладки
            try:
                await self.browser.page.screenshot({"path": "login_error.png"})
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [DEBUG] Error screenshot saved as login_error.png")
            except Exception as screenshot_error:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Failed to save error screenshot: {screenshot_error}")
            # Возвращаем False, чтобы показать, что вход не удался
            return False

async def main():
    try:
        print("Запуск скрипта с использованием авторизации через email/password с пользовательскими селекторами")
        
        # Селекторы, предоставленные пользователем
        email_selector = "#root > div > div._99ad066 > div > div > div.ds-sign-up-form__main > div > div:nth-child(2) > div.ds-form-item__content > div > input"
        password_selector = "#root > div > div._99ad066 > div > div > div.ds-sign-up-form__main > div > div:nth-child(3) > div.ds-form-item__content > div > input"
        
        # Используем модифицированный класс с пользовательскими селекторами
        api = CustomDeepSeek(
            email=os.getenv("EMAIL"),
            password=os.getenv("PASSWORD"),
            token=os.getenv("DEEPSEEK_CHAT_TOKEN"),
            chat_id=os.getenv("DEEPSEEK_CHAT_ID"),
            verbose=True,  # Выводить отладочные сообщения
            headless=False,  # Запускать Chrome в видимом режиме для отладки
            attempt_cf_bypass=True,  # Пытаться обойти защиту Cloudflare
            email_selector=email_selector,
            password_selector=password_selector
        )
        print("Инициализация API...")
        await api.initialize()
        print("API инициализирован успешно")
        
        # Отправка сообщения
        print("Отправка сообщения...")
        response = await api.send_message(
            "4*25",
            slow_mode=True,
            deepthink=False,
            search=False,
            slow_mode_delay=0.25
        )
        print(f"Ответ получен: {response.text}\nID чата: {response.chat_id}")

        # Регенерация последнего ответа
        print("Регенерация ответа...")
        new_response = await api.regenerate_response()
        print(f"Новый ответ: {new_response.text}\nID чата: {new_response.chat_id}")

        # Сброс чата
        print("Сброс чата...")
        await api.reset_chat()
        print("Чат сброшен")

        # Получение токена сеанса
        print("Получение токена сессии...")
        token = await api.retrieve_token()
        print(f"Токен сессии: {token}")

        # Выход из системы
        print("Выход из системы...")
        await api.logout()
        print("Выход выполнен")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        # Убедимся, что браузер закрыт даже при ошибке
        if 'api' in locals() and hasattr(api, 'browser') and api.browser:
            try:
                await api.logout()
                print("Выход из системы выполнен")
            except Exception as e:
                print(f"Ошибка при выходе: {e}")

if __name__ == '__main__':
    asyncio.run(main())