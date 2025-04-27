# Кастомная реализация класса DeepSeek для правильной авторизации
# на основе документации из DeepSeekBrowserReadme.md
# с улучшенным обходом Cloudflare защиты

import os
import asyncio
import aiohttp
import time
import traceback
import undetected_chromedriver as uc  # Используем undetected_chromedriver для обхода Cloudflare
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import random  # Для добавления случайных задержек

class CustomDeepSeek:
    def __init__(self, email=None, password=None, token=None, chat_id=None, verbose=True, headless=False, chrome_args=None, attempt_cf_bypass=True):
        self.email = email
        self.password = password
        self.token = token
        self.chat_id = chat_id
        self.verbose = verbose
        self.headless = headless
        self.chrome_args = chrome_args or []
        self.attempt_cf_bypass = attempt_cf_bypass
        self.driver = None
        self.session = None
        self.base_url = "https://chat.deepseek.com"

    async def initialize(self):
        # Инициализация браузера с использованием undetected_chromedriver
        try:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Инициализация браузера...")
            
            # Настраиваем опции для undetected_chromedriver
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
            
            # Добавляем аргументы для обхода защиты от автоматизации
            if self.attempt_cf_bypass:
                options.add_argument('--disable-blink-features=AutomationControlled')
                # Добавляем случайный user-agent для лучшего обхода защиты
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                ]
                options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            # Добавляем пользовательские аргументы Chrome
            for arg in self.chrome_args:
                options.add_argument(arg)
            
            # Инициализируем undetected_chromedriver
            self.driver = uc.Chrome(options=options)
            
            # Устанавливаем таймаут для страницы
            self.driver.set_page_load_timeout(60)
            
            # Инициализация aiohttp сессии
            self.session = aiohttp.ClientSession()
            
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Браузер успешно инициализирован")
            
            # Выполняем авторизацию в зависимости от предоставленных данных
            if self.email and self.password:
                await self.login_with_email_password()
            elif self.token:
                await self.login_with_token()
            else:
                raise ValueError("Either email/password or token must be provided")
            
            return True
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка при инициализации браузера: {e}")
            traceback.print_exc()
            return False

    async def login_with_email_password(self):
        try:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Открываем страницу входа...")
            
            # Добавляем случайную задержку перед открытием страницы для имитации человеческого поведения
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Открываем страницу входа
            self.driver.get(f"{self.base_url}/login")
            
            # Ждем появления формы входа
            try:
                # Добавляем случайную задержку перед вводом данных
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Пробуем разные селекторы для поля email
                email_selectors = [
                    "input[type='email']",
                    "input[placeholder*='email']",
                    "input[name*='email']",
                    "#root input[type='email']",
                    "div.ds-form-item__content input[type='email']"
                ]
                
                email_input = None
                for selector in email_selectors:
                    try:
                        email_input = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if email_input:
                            break
                    except:
                        continue
                
                if not email_input:
                    raise TimeoutException("Не удалось найти поле для ввода email")
                
                # Пробуем разные селекторы для поля пароля
                password_selectors = [
                    "input[type='password']",
                    "input[placeholder*='password']",
                    "input[name*='password']",
                    "#root input[type='password']",
                    "div.ds-form-item__content input[type='password']"
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        password_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if password_input:
                            break
                    except:
                        continue
                
                if not password_input:
                    raise NoSuchElementException("Не удалось найти поле для ввода пароля")
                
                # Вводим учетные данные с имитацией человеческого ввода
                email_input.clear()
                for char in self.email:
                    email_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
                password_input.clear()
                for char in self.password:
                    password_input.send_keys(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Ввели email и пароль")
                
                # Добавляем случайную задержку перед нажатием кнопки
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Пробуем разные селекторы для кнопки входа
                login_button_selectors = [
                    "button[type='submit']",
                    "button.ds-button--primary",
                    "button.ds-sign-up-form__register-button",
                    "button[aria-label='Login']",
                    "div.ds-button--block"
                ]
                
                login_button = None
                for selector in login_button_selectors:
                    try:
                        login_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if login_button:
                            break
                    except:
                        continue
                
                if not login_button:
                    raise TimeoutException("Не удалось найти кнопку входа")
                
                login_button.click()
                
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Нажали кнопку входа")
                
                # Ждем успешного входа с увеличенным таймаутом
                await asyncio.sleep(random.uniform(3.0, 5.0))
                
                # Проверяем успешность входа с несколькими селекторами
                profile_selectors = [
                    'div[data-testid="profile-button"]',
                    'button[aria-label="User settings"]',
                    'div.user-avatar',
                    'div.user-profile'
                ]
                
                login_success = False
                for selector in profile_selectors:
                    try:
                        WebDriverWait(self.driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        login_success = True
                        break
                    except:
                        continue
                
                if login_success:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Успешно вошли в систему")
                    return True
                else:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Не удалось подтвердить успешный вход")
                    # Делаем скриншот для диагностики
                    self.driver.save_screenshot('login_error.png')
                    print("Скриншот ошибки сохранен в 'login_error.png'")
                    return False
                
            except TimeoutException as te:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Не удалось найти форму входа: {te}")
                self.driver.save_screenshot('login_timeout_error.png')
                print("Скриншот ошибки таймаута сохранен в 'login_timeout_error.png'")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка входа: {e}")
            traceback.print_exc()
            self.driver.save_screenshot('login_exception_error.png')
            print("Скриншот ошибки исключения сохранен в 'login_exception_error.png'")
            return False

    async def login_with_token(self):
        if not self.token:
            raise ValueError("Token is required for token-based authentication")
        
        try:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Выполняем вход с использованием токена...")
            
            # Добавляем случайную задержку перед открытием страницы
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Открываем страницу чата
            self.driver.get(self.base_url)
            
            # Ждем загрузки страницы
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # Устанавливаем cookie с токеном
            try:
                self.driver.add_cookie({
                    'name': 'userToken',
                    'value': self.token,
                    'domain': 'chat.deepseek.com',
                    'path': '/',
                })
                
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Установили cookie с токеном")
            except Exception as cookie_error:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Ошибка при установке cookie: {cookie_error}")
                # Если не удалось установить cookie, пробуем войти с email/password
                if self.email and self.password:
                    return await self.login_with_email_password()
                raise
            
            # Перезагружаем страницу
            self.driver.refresh()
            
            # Ждем успешного входа с увеличенным таймаутом
            await asyncio.sleep(random.uniform(3.0, 5.0))
            
            # Проверяем успешность входа с несколькими селекторами
            profile_selectors = [
                'div[data-testid="profile-button"]',
                'button[aria-label="User settings"]',
                'div.user-avatar',
                'div.user-profile'
            ]
            
            login_success = False
            for selector in profile_selectors:
                try:
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    login_success = True
                    break
                except:
                    continue
            
            if login_success:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Успешно вошли в систему с использованием токена")
                return True
            else:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Не удалось войти с использованием токена")
                self.driver.save_screenshot('token_login_error.png')
                print("Скриншот ошибки входа с токеном сохранен в 'token_login_error.png'")
                
                # Пробуем войти с email/password
                if self.email and self.password:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Пробуем войти с использованием email/password...")
                    return await self.login_with_email_password()
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка входа с токеном: {e}")
            traceback.print_exc()
            self.driver.save_screenshot('token_exception_error.png')
            print("Скриншот ошибки исключения сохранен в 'token_exception_error.png'")
            return False

    async def send_message(self, message, deepthink=False, search=False, slow_mode=True, slow_mode_delay=0.25, timeout=120):
        try:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Отправка сообщения...")
            
            # Проверяем, что мы на странице чата
            current_url = self.driver.current_url
            if not current_url.startswith(self.base_url):
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Переходим на страницу чата...")
                self.driver.get(self.base_url)
                await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # Пробуем разные селекторы для текстового поля
            textbox_selectors = [
                'textarea',
                'div[contenteditable="true"]',
                'div[role="textbox"]',
                'div.chat-input textarea'
            ]
            
            textbox = None
            for selector in textbox_selectors:
                try:
                    textbox = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if textbox:
                        break
                except:
                    continue
            
            if not textbox:
                raise TimeoutException("Не удалось найти текстовое поле для ввода сообщения")
            
            # Очищаем текстовое поле перед вводом
            textbox.clear()
            
            # Добавляем случайную задержку перед вводом
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Вводим сообщение с имитацией человеческого ввода
            if slow_mode:
                for char in message:
                    textbox.send_keys(char)
                    # Добавляем случайную задержку для более естественного ввода
                    await asyncio.sleep(slow_mode_delay * random.uniform(0.8, 1.2))
            else:
                textbox.send_keys(message)
            
            # Добавляем случайную задержку перед нажатием кнопки отправки
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Пробуем разные селекторы для кнопки отправки
            send_button_selectors = [
                'button[aria-label="Send message"]',
                'button.send-button',
                'button[type="submit"]',
                'svg[data-icon="paper-plane"]',
                'div.chat-input button'
            ]
            
            send_button = None
            for selector in send_button_selectors:
                try:
                    send_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if send_button:
                        break
                except:
                    continue
            
            if not send_button:
                raise TimeoutException("Не удалось найти кнопку отправки сообщения")
            
            # Нажимаем кнопку отправки
            send_button.click()
            
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Сообщение отправлено, ожидаем ответа...")
            
            # Ждем ответа с периодическим выводом статуса
            start_time = time.time()
            response_text = ""
            deepthink_content = ""
            deepthink_duration = 0
            last_status_time = start_time
            
            # Проверяем наличие опций DeepThink и Search, если они запрошены
            if deepthink or search:
                try:
                    # Ищем и активируем опцию DeepThink, если запрошена
                    if deepthink:
                        deepthink_selectors = [
                            'div[role="button"] span:contains("DeepThink")',
                            'button:contains("DeepThink")',
                            'div.deepthink-button'
                        ]
                        
                        for selector in deepthink_selectors:
                            try:
                                deepthink_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for element in deepthink_elements:
                                    if "DeepThink" in element.text and "active" not in element.get_attribute("class"):
                                        element.click()
                                        if self.verbose:
                                            print(f"[{time.strftime('%H:%M:%S')}] Активировали опцию DeepThink")
                                        break
                            except:
                                continue
                    
                    # Ищем и активируем опцию Search, если запрошена
                    if search:
                        search_selectors = [
                            'div[role="button"] span:contains("Search")',
                            'button:contains("Search")',
                            'div.search-button'
                        ]
                        
                        for selector in search_selectors:
                            try:
                                search_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for element in search_elements:
                                    if "Search" in element.text and "active" not in element.get_attribute("class"):
                                        element.click()
                                        if self.verbose:
                                            print(f"[{time.strftime('%H:%M:%S')}] Активировали опцию Search")
                                        break
                            except:
                                continue
                except Exception as option_error:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Ошибка при активации опций: {option_error}")
            
            # Ожидаем появления ответа с улучшенной обработкой
            while time.time() - start_time < timeout:
                try:
                    # Если прошло больше 10 секунд с последнего вывода статуса, выводим текущий статус
                    current_time = time.time()
                    if current_time - last_status_time > 10:
                        if self.verbose:
                            print(f"[{time.strftime('%H:%M:%S')}] Ожидаем ответ... Прошло {int(current_time - start_time)} секунд")
                        last_status_time = current_time
                    
                    # Проверяем наличие DeepThink, если он был запрошен
                    if deepthink and deepthink_duration == 0:
                        deepthink_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="deepthink"]')
                        if deepthink_elements:
                            deepthink_content = deepthink_elements[0].text
                            if not deepthink_content.endswith('...') and not deepthink_content.endswith('…'):
                                deepthink_duration = time.time() - start_time
                                if self.verbose:
                                    print(f"[{time.strftime('%H:%M:%S')}] DeepThink завершен за {deepthink_duration:.2f} секунд")
                    
                    # Ищем последний ответ от бота с использованием разных селекторов
                    response_selectors = [
                        'div[data-message-author-role="assistant"]',
                        'div.assistant-message',
                        'div.message-content.assistant',
                        'div[class*="message"][class*="assistant"]'
                    ]
                    
                    for selector in response_selectors:
                        response_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if response_elements:
                            last_response = response_elements[-1]
                            current_text = last_response.text
                            
                            # Проверяем, завершен ли ответ
                            if current_text and not current_text.endswith('...') and not current_text.endswith('…'):
                                # Проверяем, есть ли индикатор загрузки
                                loading_indicators = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="loading"]')
                                if not loading_indicators:
                                    response_text = current_text
                                    if self.verbose:
                                        print(f"[{time.strftime('%H:%M:%S')}] Получен полный ответ")
                                    break
                            
                            # Обновляем текущий текст ответа
                            response_text = current_text
                    
                    # Если получен полный ответ, выходим из цикла
                    if response_text and not response_text.endswith('...') and not response_text.endswith('…'):
                        break
                    
                except Exception as e:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Ошибка при получении ответа: {e}")
                
                # Добавляем небольшую задержку между проверками
                await asyncio.sleep(1)
            
            # Если время ожидания истекло, но ответ не получен полностью
            if time.time() - start_time >= timeout and (not response_text or response_text.endswith('...') or response_text.endswith('…')):
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Таймаут ожидания ответа. Возвращаем частичный ответ.")
            
            # Создаем объект ответа
            response = type('Response', (), {
                'text': response_text,
                'deepthink_content': deepthink_content,
                'deepthink_duration': deepthink_duration
            })
            
            return response
            
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка при отправке сообщения: {e}")
            traceback.print_exc()
            # Делаем скриншот для диагностики
            try:
                self.driver.save_screenshot('send_message_error.png')
                print("Скриншот ошибки сохранен в 'send_message_error.png'")
            except:
                pass
            raise

    async def close(self):
        try:
            if self.driver:
                self.driver.quit()
            if self.session:
                await self.session.close()
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка при закрытии ресурсов: {e}")