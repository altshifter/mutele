import sqlite3
import config

# Функция для подключения к базе данных
def db_connect(db_file=config.DATABASE_FILE):
    return sqlite3.connect(db_file)

# Функция для инициализации базы данных
def init_db():
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                keywords TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                file_path TEXT NOT NULL,
                real_name TEXT NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                path TEXT NOT NULL,
                order_num INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

# Функция для выполнения запроса к базе данных
def execute_query(query, params=(), db_file=config.DATABASE_FILE):
    with db_connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

# Функция для выполнения запроса и получения всех результатов
def fetch_all(query, params=(), db_file=config.DATABASE_FILE):
    with db_connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

# Функция для добавления пользователя в базу данных
def db_add_user(user_id, username):
    query = 'INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)'
    execute_query(query, (user_id, username))

# Функция для добавления запроса в историю поиска
def db_add_search(user_id, keywords):
    query = '''
        INSERT INTO search_history (user_id, keywords, date)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    '''
    execute_query(query, (user_id, keywords))

# Функция для добавления записи о скачивании в базу данных
def db_add_download(user_id, username, url, file_path, real_name):
    query = '''
        INSERT INTO downloads (user_id, url, file_path, real_name, date)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    '''
    execute_query(query, (user_id, url, file_path, real_name))

# Функция для получения пути к скачанному файлу
def db_get_downloaded_file(url):
    query = 'SELECT file_path FROM downloads WHERE url = ?'
    rows = fetch_all(query, (url,))
    return rows[0][0] if rows else None

# Функция для загрузки идентификаторов чатов
def load_chat_ids():
    query = 'SELECT id FROM users'
    rows = fetch_all(query)
    return [row[0] for row in rows]

# Функция для получения всех треков из базы данных
def db_get_all_tracks():
    query = 'SELECT real_name, file_path FROM downloads'
    rows = fetch_all(query)
    return [{'title': row[0], 'file_path': row[1]} for row in rows]

# Функция для получения плейлиста пользователя
def get_user_playlist(user_id):
    query = '''
        SELECT title, path FROM user_playlists WHERE user_id = ? ORDER BY order_num ASC
    '''
    rows = fetch_all(query, (user_id,))
    return [{'title': row[0], 'path': row[1]} for row in rows]

# Функция для сохранения плейлиста пользователя
def save_user_playlist(user_id, tracks):
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_playlists WHERE user_id = ?', (user_id,))
        cursor.executemany('''
            INSERT INTO user_playlists (user_id, title, path, order_num) VALUES (?, ?, ?, ?)
        ''', [(user_id, track['title'], track['path'], index + 1) for index, track in enumerate(tracks)])
        conn.commit()

# Функция для очистки плейлиста пользователя
def clear_user_playlist(user_id):
    query = 'DELETE FROM user_playlists WHERE user_id = ?'
    execute_query(query, (user_id,))

# Функция для получения всех запросов пользователя
def db_get_user_requests(user_id):
    query = 'SELECT real_name, file_path FROM downloads WHERE user_id = ?'
    rows = fetch_all(query, (user_id,))
    return [{'title': row[0], 'file_path': row[1]} for row in rows]

# Функция для получения всех треков с сервера
def db_get_all_server_tracks():
    query = 'SELECT real_name, file_path FROM downloads'
    rows = fetch_all(query)
    return [{'title': row[0], 'file_path': row[1]} for row in rows]

# Функция для очистки таблицы скачиваний
def clear_downloads_table():
    query = 'DELETE FROM downloads'
    execute_query(query)

# Инициализация базы данных при запуске скрипта
init_db()