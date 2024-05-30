import sqlite3
import logging
import config

# Функция для подключения к базе данных кеша
def cache_connect():
    return sqlite3.connect(config.CACHE_DB_FILE)  # Используем путь к файлу кеша из конфигурационного файла

# Функция для инициализации базы данных кеша
def init_cache_db():
    with cache_connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Функция для добавления записи в кеш
def add_to_cache(query, result):
    with cache_connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cache (query, result, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (query, str(result)))
        conn.commit()

# Функция для получения записи из кеша
def get_from_cache(query):
    with cache_connect() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT result FROM cache
            WHERE query = ? AND timestamp >= datetime('now', '-{config.CACHE_LIFETIME} seconds')
        ''', (query,))  # Используем время жизни кеша из конфигурационного файла
        result = cursor.fetchone()
        if result:
            logging.info(f"Cache result for query '{query}': {result}")
        return eval(result[0]) if result else None

# Функция для очистки старых записей из кеша
def rotate_cache():
    with cache_connect() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            DELETE FROM cache
            WHERE timestamp < datetime('now', '-{config.CACHE_LIFETIME} seconds')
        ''')  # Используем время жизни кеша из конфигурационного файла
        conn.commit()

# Инициализация базы данных кеша при запуске
init_cache_db()
# Очистка старых записей из кеша при запуске
rotate_cache()
