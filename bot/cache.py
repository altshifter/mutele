import sqlite3
import logging
import config

# Функция для подключения к базе данных кеша
def cache_connect():
    return sqlite3.connect(config.CACHE_DB_FILE)

# Функция для инициализации базы данных кеша
def init_cache_db():
    with cache_connect() as conn:
        cursor = conn.cursor()
        # Создание таблицы кеша, если она не существует
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Функция для добавления результата в кеш
def add_to_cache(query, result):
    with cache_connect() as conn:
        cursor = conn.cursor()
        # Вставка запроса и результата в таблицу кеша
        cursor.execute('''
            INSERT INTO cache (query, result, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (query, str(result)))
        conn.commit()

# Функция для получения результата из кеша
def get_from_cache(query):
    with cache_connect() as conn:
        cursor = conn.cursor()
        # Получение результата из кеша, если он актуален
        cursor.execute(f'''
            SELECT result FROM cache
            WHERE query = ? AND timestamp >= datetime('now', '-{config.CACHE_LIFETIME} seconds')
        ''', (query,))
        result = cursor.fetchone()
        if result:
            logging.info(f"Cache result for query '{query}': {result}")
        return eval(result[0]) if result else None  # Возвращаем результат, если он найден

# Функция для очистки устаревших записей в кеше
def rotate_cache():
    with cache_connect() as conn:
        cursor = conn.cursor()
        # Удаление устаревших записей из таблицы кеша
        cursor.execute(f'''
            DELETE FROM cache
            WHERE timestamp < datetime('now', '-{config.CACHE_LIFETIME} seconds')
        ''')
        conn.commit()

# Инициализация базы данных кеша при запуске скрипта
init_cache_db()
rotate_cache()