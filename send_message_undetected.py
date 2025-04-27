# Скрипт для отправки сообщения в DeepSeek с использованием DEEPSEEK_CHAT_ID и DEEPSEEK_CHAT_TOKEN
# с помощью undetected-chromedriver для обхода защиты Cloudflare
import os
import asyncio
from dotenv import load_dotenv
import time
import traceback
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Загрузка переменных окружения из файла .env
load_dotenv()

class DeepSeekUndetected:
    def __init__(self, token=None, chat_id=None, email=None, password=None, verbose=True, headless=False):
        self.token = token
        self.chat_id = chat_id
        self.email = email
        self.password = password
        self.verbose = verbose
        self.headless = headless
        self.driver = None
        self.base_url = "https://chat.deepseek.com"

    def initialize(self):
        # Инициализация браузера с undetected-chromedriver
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        
        # Добавляем аргументы для обхода защиты от автоматизации
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        
        try:
            self.driver = uc.Chrome(options=options)
            
            # Открываем страницу чата
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] Открываем страницу DeepSeek...")
            self.driver.get(self.base_url)
            time.sleep(5)  # Ждем загрузки страницы
            
            # Проверяем, что страница загрузилась успешно
            if "deepseek" not in self.driver.title.lower():
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Ошибка: Не удалось загрузить страницу DeepSeek")
                return False
            
            # Проверяем, нужно ли авторизоваться через форму логина
            if self.email and self.password:
                try:
                    # Проверяем, находимся ли мы на странице логина
                    login_elements = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="email"]')
                    if login_elements:
                        if self.verbose:
                            print(f"[{time.strftime('%H:%M:%S')}] Обнаружена страница логина, вводим учетные данные...")
                        
                        # Находим поле для ввода email
                        email_input = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
                        )
                        email_input.clear()
                        email_input.send_keys(self.email)
                        
                        # Находим поле для ввода пароля
                        password_input = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
                        )
                        password_input.clear()
                        password_input.send_keys(self.password)
                        
                        # Находим кнопку логина и нажимаем её
                        login_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))
                        )
                        login_button.click()
                        
                        # Ждем загрузки страницы после авторизации
                        time.sleep(5)
                        
                        if self.verbose:
                            print(f"[{time.strftime('%H:%M:%S')}] Учетные данные введены, ожидаем авторизации...")
                except Exception as login_error:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Ошибка при вводе учетных данных: {login_error}")
                    traceback.print_exc()
                    return False
            # Если есть токен, пытаемся авторизоваться через него
            elif self.token:
                try:
                    self.driver.add_cookie({
                        'name': 'userToken',
                        'value': self.token,
                        'domain': 'chat.deepseek.com',
                        'path': '/',
                    })
                    
                    # Перезагружаем страницу
                    self.driver.refresh()
                    time.sleep(5)  # Ждем загрузки страницы после авторизации
                except Exception as cookie_error:
                    if self.verbose:
                        print(f"[{time.strftime('%H:%M:%S')}] Ошибка установки cookie: {cookie_error}")
                    traceback.print_exc()
                    return False
            else:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Ошибка: Не предоставлены данные для авторизации (токен или email/пароль)")
                return False
            
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
                    time.sleep(3)  # Ждем загрузки чата
                    
                    # Проверяем доступность указанной страницы чата
                    current_url = self.driver.current_url
                    if self.chat_id not in current_url:
                        if self.verbose:
                            print(f"[{time.strftime('%H:%M:%S')}] Ошибка: Не удалось перейти в указанный чат. Возможно, вы не авторизованы или чат недоступен.")
                            print(f"[{time.strftime('%H:%M:%S')}] Текущий URL: {current_url}")
                        return False
                
                return True
            except TimeoutException:
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Не удалось войти с использованием токена")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка инициализации: {e}")
            traceback.print_exc()
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            return False

    def send_message(self, message, deepthink=False, search=False, slow_mode=True, slow_mode_delay=0.25, timeout=120):
        try:
            # Проверяем, что мы на странице чата
            current_url = self.driver.current_url
            if not current_url.startswith(self.base_url):
                self.driver.get(f"{self.base_url}/chat/{self.chat_id}")
                time.sleep(2)  # Ждем загрузки страницы
            
            # Находим текстовое поле для ввода сообщения
            textbox = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea'))
            )
            
            # Вводим сообщение
            if slow_mode:
                for char in message:
                    textbox.send_keys(char)
                    time.sleep(slow_mode_delay)
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
                            
                            time.sleep(1)
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
                    
                    time.sleep(1)
                
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

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
                if self.verbose:
                    print(f"[{time.strftime('%H:%M:%S')}] Браузер закрыт")
        except Exception as e:
            if self.verbose:
                print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Ошибка закрытия ресурсов: {e}")
            traceback.print_exc()

def main():
    # Получение данных авторизации из переменных окружения
    token = os.getenv('DEEPSEEK_CHAT_TOKEN')
    chat_id = os.getenv('DEEPSEEK_CHAT_ID')
    email = os.getenv('DEEPSEEK_EMAIL')
    password = os.getenv('DEEPSEEK_PASSWORD')
    
    # Проверяем наличие необходимых данных для авторизации
    if (not token or not chat_id) and (not email or not password):
        print("Ошибка: Не найдены данные для авторизации в .env файле")
        print("Необходимо указать либо DEEPSEEK_CHAT_TOKEN и DEEPSEEK_CHAT_ID, либо DEEPSEEK_EMAIL и DEEPSEEK_PASSWORD")
        return
    
    # Выводим информацию о используемых данных
    if token and chat_id:
        print(f"[{time.strftime('%H:%M:%S')}] Используем CHAT_ID: {chat_id}")
        print(f"[{time.strftime('%H:%M:%S')}] Используем TOKEN: {token[:10]}...{token[-10:]}")
    
    if email and password:
        print(f"[{time.strftime('%H:%M:%S')}] Используем EMAIL: {email}")
        print(f"[{time.strftime('%H:%M:%S')}] Используем PASSWORD: {'*' * len(password)}")
    
    # Создание экземпляра браузера
    browser = DeepSeekUndetected(token=token, chat_id=chat_id, email=email, password=password, verbose=True, headless=False)
    
    try:
        # Инициализация браузера
        print(f"[{time.strftime('%H:%M:%S')}] Инициализация браузера и проверка авторизации...")
        success = browser.initialize()
        if not success:
            print(f"[{time.strftime('%H:%M:%S')}] Ошибка: Не удалось инициализировать браузер или авторизоваться")
            print(f"[{time.strftime('%H:%M:%S')}] Проверьте правильность токена и ID чата в .env файле")
            return
        
        # Проверка доступности конкретной страницы
        test_chat_url = "https://chat.deepseek.com/a/chat/s/71cf0476-c07b-4032-bb40-751467e0a29a"
        test_chat_id = "71cf0476-c07b-4032-bb40-751467e0a29a"
        
        print(f"[{time.strftime('%H:%M:%S')}] Проверка доступности страницы: {test_chat_url}")
        
        # Сохраняем текущий chat_id
        original_chat_id = browser.chat_id
        
        # Временно меняем chat_id для проверки
        browser.chat_id = test_chat_id
        
        # Переходим на тестовую страницу
        browser.driver.get(test_chat_url)
        time.sleep(3)  # Ждем загрузки страницы
        
        # Проверяем URL после перехода
        current_url = browser.driver.current_url
        if test_chat_id in current_url:
            print(f"[{time.strftime('%H:%M:%S')}] Успешно! Страница {test_chat_url} доступна.")
            print(f"[{time.strftime('%H:%M:%S')}] Вы успешно авторизованы в DeepSeek.")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Ошибка: Страница {test_chat_url} недоступна.")
            print(f"[{time.strftime('%H:%M:%S')}] Возможно, вы не авторизованы или у вас нет доступа к этому чату.")
            print(f"[{time.strftime('%H:%M:%S')}] Текущий URL: {current_url}")
            return
        
        # Возвращаем исходный chat_id
        browser.chat_id = original_chat_id
        
        # Возвращаемся в исходный чат
        if original_chat_id:
            browser.driver.get(f"{browser.base_url}/chat/{original_chat_id}")
            time.sleep(2)  # Ждем загрузки страницы
        
        # Отправка тестового сообщения
        message = "Привет! Это тестовое сообщение, отправленное с использованием DEEPSEEK_CHAT_TOKEN и DEEPSEEK_CHAT_ID через undetected-chromedriver."
        print(f"\nОтправляемое сообщение: {message}")
        
        response = browser.send_message(
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
        browser.close()

# Запуск приложения
if __name__ == '__main__':
    main()