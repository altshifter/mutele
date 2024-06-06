from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import atexit

# Класс для управления браузером
class BrowserManager:
    _instance = None  # Единственный экземпляр класса (Singleton)
    _driver = None  # Экземпляр драйвера браузера

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
        return cls._instance

    # Метод для получения драйвера браузера
    def get_driver(self):
        if BrowserManager._driver is None:
            user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.4 Mobile/15E148 Safari/604.1'
            options = Options()
            options.add_argument('--headless')  # Запуск браузера в фоновом режиме
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=375,812')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'user-agent={user_agent}')
            service = Service(ChromeDriverManager().install())
            BrowserManager._driver = webdriver.Chrome(service=service, options=options)
        return BrowserManager._driver

    # Метод для закрытия драйвера браузера
    def close_driver(self):
        if BrowserManager._driver is not None:
            BrowserManager._driver.quit()
            BrowserManager._driver = None

# Закрытие браузера при выходе из программы
def close_browser():
    browser_manager = BrowserManager()
    browser_manager.close_driver()

# Регистрация функции для закрытия браузера при выходе из программы
atexit.register(close_browser)