from flask import Flask, request, jsonify, render_template, send_from_directory
import telebot
import logging
import config
from db import (db_add_user, db_add_search, db_add_download, load_chat_ids, db_get_all_tracks,
                db_get_downloaded_file, get_user_playlist, save_user_playlist, clear_user_playlist,
                db_get_user_requests, db_get_all_server_tracks, clear_downloads_table)
from cache import get_from_cache, add_to_cache
from downloader import search_music, download_and_convert_music, get_video_info, download_video, download_video_from_source
from vk_downloader import search_music_vk
from soundcloud_downloader import search_music_soundcloud
from utils import is_youtube_url, sanitize, format_duration, trim_or_compress_title, is_valid_url, clean_youtube_url
from telebot import types
import atexit
from browser_manager import BrowserManager
from browser_manager import close_browser 

# Инициализация бота и веб-приложения
bot = telebot.TeleBot(config.BOT_TOKEN)
bot.set_webhook(url=config.WEBHOOK_URL)

# Настройка логирования
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)

app = Flask(__name__, static_folder='static')

# Словари для хранения запросов и результатов поиска
requests = {}
search_results = {}
user_platforms = {}

# Главная страница веб-приложения
@app.route('/')
def index():
    return render_template('index.html')

# Веб-хук для Telegram бота
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Error', 403

# Обработка поиска музыки
@app.route('/search', methods=['POST'])
def search():
    data = request.json
    chat_id = data.get('chat_id')
    query = data.get('query')
    platform = user_platforms.get(chat_id, 'youtube')

    if not chat_id or not query:
        return jsonify({'success': False, 'message': 'Missing chat_id or query'}), 400

    username = f'user_{chat_id}'

    # Проверка на наличие ссылки YouTube
    if is_youtube_url(query):
        return handle_youtube_url(chat_id, query, username)

    # Проверка кэша
    cached_result = get_from_cache(query)
    if cached_result:
        logging.info(f'Using cached results for: {query}')
        search_results[username] = cached_result
        return jsonify({'success': True, 'results': cached_result})

    # Поиск на выбранной платформе
    results = search_platform(platform, query)
    if results:
        search_results[username] = results
        add_to_cache(query, results)
        db_add_search(chat_id, query)
        return jsonify({'success': True, 'results': results})
    else:
        return jsonify({'success': False, 'message': 'No results found'})

# Обработка ссылки YouTube
def handle_youtube_url(chat_id, query, username):
    query = clean_youtube_url(query)
    existing_file = db_get_downloaded_file(query)
    if existing_file:
        logging.info(f"File already exists for {query}: {existing_file}")
        return jsonify({'success': True, 'file_path': existing_file})
    else:
        file_path, real_name = download_and_convert_music(query)
        if file_path:
            db_add_download(chat_id, username, query, file_path, real_name)
            logging.info(f"Downloaded and converted {query}: {file_path}")
            return jsonify({'success': True, 'file_path': file_path})
        else:
            return jsonify({'success': False, 'message': 'Failed to download track'})

# Поиск на различных платформах
def search_platform(platform, query):
    if platform == 'youtube':
        return search_music(query)
    elif platform == 'vk':
        return search_music_vk(query, config.VK_ACCESS_TOKEN)
    elif platform == 'soundcloud':
        return search_music_soundcloud(query, config.SOUNDCLOUD_CLIENT_ID)
    else:
        raise ValueError('Invalid platform specified')

# Получение всех треков из базы данных
@app.route('/tracks', methods=['GET'])
def get_tracks():
    tracks = db_get_all_tracks()
    return jsonify({'success': True, 'tracks': tracks})

# Обработка запроса на скачивание
@app.route('/download', methods=['POST'])
def download():
    data = request.json
    chat_id = data.get('chat_id')
    query = data.get('query')
    track_index = data.get('track_index')

    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400

    if query and is_youtube_url(query):
        return handle_youtube_url(chat_id, query, f'user_{chat_id}')
    elif track_index is not None:
        return handle_track_index(chat_id, track_index)

# Обработка индекса трека для скачивания
def handle_track_index(chat_id, track_index):
    username = f'user_{chat_id}'
    if username not in search_results or track_index >= len(search_results[username]):
        return jsonify({'success': False, 'message': 'Invalid track index'}), 400

    url = search_results[username][track_index]['webpage_url']
    existing_file = db_get_downloaded_file(url)
    if existing_file:
        return jsonify({'success': True, 'file_path': existing_file})
    else:
        file_path, real_name = download_and_convert_music(url)
        if file_path:
            db_add_download(chat_id, url, url, file_path, real_name)
            return jsonify({'success': True, 'file_path': file_path})
        else:
            return jsonify({'success': False, 'message': 'Failed to download track'}), 400

# Отправка трека пользователю
@app.route('/send_track', methods=['POST'])
def send_track():
    data = request.json
    chat_id = data.get('chat_id')
    file_path = data.get('file_path')

    if not chat_id or not file_path:
        return jsonify({'success': False, 'message': 'Missing chat_id or file_path'}), 400

    try:
        send_music(chat_id, file_path)
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error sending music: {e}")
        return jsonify({'success': False, 'message': 'Error sending music'}), 500

# Сохранение плейлиста пользователя
@app.route('/save_playlist', methods=['POST'])
def save_playlist():
    data = request.json
    chat_id = data.get('chat_id')
    tracks = data.get('tracks')

    if not chat_id or not tracks:
        return jsonify({'success': False, 'message': 'Missing chat_id or tracks'}), 400

    save_user_playlist(chat_id, tracks)
    return jsonify({'success': True})

# Получение плейлиста пользователя
@app.route('/user_playlist', methods=['GET'])
def user_playlist():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400

    tracks = get_user_playlist(chat_id)
    return jsonify({'success': True, 'tracks': tracks})

# Очистка плейлиста пользователя
@app.route('/clear_playlist', methods=['POST'])
def clear_playlist():
    try:
        chat_id = request.json.get('chat_id')
        clear_user_playlist(chat_id)
        return jsonify(success=True)
    except Exception as e:
        print(f"Ошибка очистки плейлиста: {e}")
        return jsonify(success=False, message=str(e))

# Получение всех запросов пользователя
@app.route('/user_requests', methods=['GET'])
def user_requests():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400

    tracks = db_get_user_requests(chat_id)
    return jsonify({'success': True, 'tracks': tracks})

# Получение всех треков с сервера
@app.route('/all_tracks', methods=['GET'])
def all_tracks():
    try:
        tracks = db_get_all_server_tracks()
        return jsonify({'success': True, 'tracks': tracks})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Прямое скачивание видео
@app.route('/download_video_direct', methods=['POST'])
def download_video_direct():
    data = request.json
    chat_id = data.get('chat_id')
    url = data.get('url')

    if not chat_id or not url:
        return jsonify({'success': False, 'message': 'Missing chat_id or url'}), 400

    try:
        source = 'youtube'
        if 'instagram' in url:
            source = 'instagram'
        elif 'shorts' in url:
            source = 'youtube_shorts'
        
        file_path = download_video_from_source(url, source)
        if file_path:
            with open(file_path, 'rb') as video:
                bot.send_video(chat_id, video)
            return jsonify({'success': True, 'file_path': file_path})
        else:
            return jsonify({'success': False, 'message': 'Не удалось скачать видео.'}), 500
    except Exception as e:
        logging.error(f"Error in download_video_direct: {e}")
        return jsonify({'success': False, 'message': 'Произошла ошибка при обработке запроса.'}), 500
        
# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    db_add_user(user_id, username)

    user_platforms[chat_id] = 'youtube'

    keyboard = types.InlineKeyboardMarkup()
    web_app_button = types.InlineKeyboardButton(text="Открыть Web App", web_app=types.WebAppInfo(url=config.WEB_APP_URL))
    keyboard.add(web_app_button)

    bot.send_message(chat_id, "Данный бот находится в разработке, установлена платформа YouTube.")
    bot.send_message(chat_id, "Теперь вы можете открыть Web App для поиска музыки. Или воспользоваться inline режимом, отправив в чат имя исполнителя или название трека или ссылку на youtube.", reply_markup=keyboard)

# Команда /broadcast для рассылки сообщений
@bot.message_handler(commands=['broadcast'])
def handle_broadcast_command(message):
    if str(message.from_user.id) == config.ADMIN_USER_ID:
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            broadcast_message(args[1])
            bot.reply_to(message, "Сообщение отправлено всем пользователям.")
        else:
            bot.reply_to(message, "Пожалуйста, укажите текст сообщения после команды.")
    else:
        bot.reply_to(message, "У вас нет прав использовать эту команду.")
        
# Команда /drop_downloads для очистки таблицы downloads
@bot.message_handler(commands=['drop_downloads'])
def handle_drop_downloads_command(message):
    if str(message.from_user.id) == config.ADMIN_USER_ID:
        clear_downloads_table()
        bot.reply_to(message, "Таблица downloads очищена.")
        print("Таблица downloads очищена")
    else:
        bot.reply_to(message, "У вас нет прав использовать эту команду.")

# Функция для рассылки сообщений
def broadcast_message(text):
    chat_ids = load_chat_ids()
    for chat_id in chat_ids:
        try:
            bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {chat_id}: {e}")

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def text(message):
    if message.text.startswith('/'):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username
    text_content = message.text.strip()
    logging.info(f"Received message from {username} (id: {user_id}): {text_content}")

    url_type = is_valid_url(text_content)
    if url_type:
        if url_type == 'youtube':
            keyboard = types.InlineKeyboardMarkup()
            clean_url = clean_youtube_url(text_content)
            music_button = types.InlineKeyboardButton(text="Скачать музыку", callback_data=f"download_music_{clean_url}")
            video_button = types.InlineKeyboardButton(text="Скачать видео", callback_data=f"download_video_{clean_url}")
            keyboard.add(music_button, video_button)
            logging.debug(f"Generated buttons with callback data: download_music_{clean_url}, download_video_{clean_url}")
            bot.send_message(chat_id, "Вы можете скачать как видео так и отдельно музыку из Youtube", reply_markup=keyboard)
        elif url_type == 'youtube_shorts':
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path = download_video_from_source(text_content, 'youtube_shorts')
            if file_path:
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)
            else:
                bot.send_message(chat_id, "Не удалось скачать видео.")
        elif url_type == 'instagram':
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path = download_video_from_source(text_content, 'instagram')
            if file_path:
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)
            else:
                bot.send_message(chat_id, "Не удалось скачать видео.")
        elif url_type == 'tiktok':
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path = download_video_from_source(text_content, 'tiktok')
            if file_path:
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)
            else:
                bot.send_message(chat_id, "Не удалось скачать видео.")
        else:
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path = download_video_from_source(text_content, url_type)
            if file_path:
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)
            else:
                bot.send_message(chat_id, "Не удалось скачать видео.")
    else:
        keywords = sanitize(text_content)
        cached_result = get_from_cache(keywords)
        if cached_result:
            logging.info(f"Using cached results for: {keywords}")
            requests[chat_id] = cached_result
            send_results_page(chat_id, cached_result)
            return

        db_add_search(user_id, keywords)
        platform = user_platforms.get(chat_id, 'youtube')
        results = search_platform(platform, keywords)

        if results:
            requests[chat_id] = results
            add_to_cache(keywords, results)
            send_results_page(chat_id, results)
        else:
            bot.send_message(chat_id, "К сожалению, ничего не найдено. Попробуйте другой запрос.")

# Отправка страницы с результатами поиска
def send_results_page(chat_id, results, page=1, results_per_page=config.RESULTS_PAGES):  # Переместили RESULTS_PAGES в config.py
    total_pages = (len(results) + results_per_page - 1) // results_per_page
    page = max(1, min(page, total_pages))
    page_results = results[(page - 1) * results_per_page: page * results_per_page]
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(page_results, start=(page - 1) * results_per_page):
        duration = format_duration(item['duration']) if 'duration' in item else 'Unknown'
        title = trim_or_compress_title(item.get('title', 'Unknown Title'))
        button_text = f"{i + 1}. {title} [{duration}]"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=f'download_music_{item["webpage_url"]}'))  # Изменение здесь
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("<<", callback_data=f'page_{page-1}'))
    if page < total_pages:
        navigation_buttons.append(types.InlineKeyboardButton(">>", callback_data=f'page_{page+1}'))
    if navigation_buttons:
        keyboard.row(*navigation_buttons)
    bot.send_message(chat_id, "Выберите трек для скачивания:", reply_markup=keyboard)

# Обработчик для переключения страниц
@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def query_page(call):
    page_num = int(call.data.split('_')[1])
    chat_id = call.message.chat.id
    send_results_page(chat_id, requests[chat_id], page=page_num)

# Обработчик для всех callback_query для отладки
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    logging.debug(f"Callback query data: {call.data}")
    # Проверка и вызов конкретных обработчиков в зависимости от данных
    if call.data.startswith('download_video_'):
        download_video_callback(call)
    elif call.data.startswith('download_music_'):
        download_music_callback(call)

# Callback для скачивания видео
def download_video_callback(call):
    logging.debug("download_video_ callback triggered")
    chat_id = call.message.chat.id
    try:
        url = call.data.split('download_video_')[1]
        logging.debug(f"Extracted URL for download video: {url}")
        existing_file = db_get_downloaded_file(url)
        if existing_file:
            logging.debug(f"File already exists: {existing_file}")
            with open(existing_file, 'rb') as video:
                bot.send_video(chat_id, video)
        else:
            file_path = download_video_from_source(url, 'youtube')
            if file_path:
                logging.debug(f"Video downloaded to path: {file_path}")
                db_add_download(chat_id, url, url, file_path, file_path)
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)
            else:
                logging.error("Failed to download video.")
                bot.send_message(chat_id, "Не удалось скачать видео.")
    except Exception as e:
        logging.error(f"Error in download_video_callback: {e}")
        bot.send_message(chat_id, "Произошла ошибка при обработке запроса.")

# Callback для скачивания музыки
def download_music_callback(call):
    logging.debug("download_music_ callback triggered")
    chat_id = call.message.chat.id
    try:
        url = call.data.split('download_music_')[1]
        logging.debug(f"Extracted URL for download music: {url}")
        existing_file = db_get_downloaded_file(url)
        if existing_file:
            logging.debug(f"File already exists: {existing_file}")
            send_music(chat_id, existing_file)
        else:
            file_path, real_name = download_and_convert_music(url)
            logging.debug(f"Downloaded and converted music: {file_path}, {real_name}")
            if file_path:
                db_add_download(chat_id, url, url, file_path, real_name)
                send_music(chat_id, file_path)
            else:
                bot.send_message(chat_id, "Не удалось скачать музыку.")
    except Exception as e:
        logging.error(f"Error in download_music_callback: {e}")
        bot.send_message(chat_id, "Произошла ошибка при обработке запроса.")

# Функция для отправки музыки пользователю
def send_music(chat_id, filename):
    logging.info(f'Начинаем отправку музыки в чат {chat_id} по имени файла: {filename}')
    with open(filename, 'rb') as audio:
        bot.send_audio(chat_id, audio)
    logging.info(f'Отправили музыку в чат {chat_id} по имени файла: {filename}')
    
# Функция для отправки музыки через Web App
def send_music_web_app(chat_id, filename):
    logging.info(f'Начинаем отправку музыки для Web App в чат {chat_id} по имени файла: {filename}')
    with open(filename, 'rb') as audio:
        bot.send_audio(chat_id, audio)
    logging.info(f'Отправили музыку для Web App в чат {chat_id} по имени файла: {filename}')

# Регистрация функции для закрытия браузера при выходе
atexit.register(close_browser)

# Запуск приложения
if __name__ == '__main__':
    app.run(port=5000)