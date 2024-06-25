from flask import Flask, request, jsonify, render_template, send_from_directory
import telebot
import logging
import config
from db import (db_add_user, db_add_search, db_add_download, load_chat_ids, db_get_all_tracks,
                db_get_downloaded_file, get_user_playlist, save_user_playlist, clear_user_playlist,
                db_get_user_requests, db_get_all_server_tracks, clear_downloads_table)
from cache import get_from_cache, add_to_cache
from downloader import search_music, download_music, download_video_from_source
from utils import (parse_and_clean_url, sanitize, format_duration, trim_or_compress_title, get_existing_file_path, safe_filename, rotate_files)
from telebot import types
import atexit
from browser_manager import BrowserManager
from browser_manager import close_browser
import os

# Инициализация бота и веб-приложения
bot = telebot.TeleBot(config.BOT_TOKEN)  # Создание экземпляра бота с токеном из config.py
bot.set_webhook(url=config.WEBHOOK_URL)  # Установка вебхука для взаимодействия бота с сервером

# Настройка логирования
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)  # Конфигурация логирования

app = Flask(__name__, static_folder='static')  # Создание экземпляра Flask приложения, указание папки для статических файлов

# Словари для хранения запросов и результатов поиска
requests = {}
search_results = {}
user_platforms = {}

@app.route('/')
def index():
    return render_template('index.html')  # Рендеринг основной страницы веб-приложения (index.html)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])  # Обработка новых обновлений от Telegram
        return ''
    else:
        return 'Error', 403  # Возврат ошибки при неверном типе содержимого

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    chat_id = data.get('chat_id')  # Получение chat_id из запроса
    query = data.get('query')  # Получение поискового запроса из запроса
    platform = user_platforms.get(chat_id, 'youtube')  # Получение платформы для поиска (по умолчанию YouTube)

    if not chat_id or not query:
        return jsonify({'success': False, 'message': 'Missing chat_id or query'}), 400  # Проверка наличия chat_id и query

    username = f'user_{chat_id}'

    url_type, clean_url = parse_and_clean_url(query)  # Парсинг и очистка URL

    if url_type in ['youtube', 'youtube_music', 'youtube_shorts']:
        return handle_youtube_url(chat_id, clean_url, username, url_type)  # Обработка URL YouTube

    cached_result = get_from_cache(query)  # Проверка наличия результата в кеше
    if cached_result:
        logging.info(f'Using cached results for: {query}')
        search_results[username] = cached_result
        return jsonify({'success': True, 'results': cached_result})  # Возврат результата из кеша

    results = search_platform(platform, query)  # Поиск на указанной платформе
    if results:
        search_results[username] = results
        add_to_cache(query, results)  # Добавление результата в кеш
        db_add_search(chat_id, query)  # Добавление поиска в базу данных
        return jsonify({'success': True, 'results': results})
    else:
        return jsonify({'success': False, 'message': 'No results found'})  # Возврат сообщения об отсутствии результатов

@app.route('/tracks/<path:filename>')
def download_file(filename):
    try:
        filename = filename.replace('%20', ' ')
        directory = config.DOWNLOAD_DIR  # Директория для загрузки файлов
        logging.info(f"Serving file: {filename} from {directory}")
        return send_from_directory(directory, filename, as_attachment=False)  # Отправка файла из директории
    except Exception as e:
        logging.error(f"Error serving file: {e}")
        return "File not found", 404  # Возврат ошибки при отсутствии файла

def handle_youtube_url(chat_id, query, username, url_type):
    existing_file = db_get_downloaded_file(query)  # Проверка наличия файла в базе данных
    if existing_file:
        logging.info(f"File already exists for {query}: {existing_file}")
        return jsonify({'success': True, 'file_path': existing_file})  # Возврат пути к существующему файлу

    if url_type == 'youtube_music':
        file_path, real_name = download_music(query)  # Скачивание музыки с YouTube
        if file_path:
            db_add_download(chat_id, username, query, file_path, real_name)  # Добавление загрузки в базу данных
            logging.info(f"Downloaded and converted {query}: {file_path}")
            return jsonify({'success': True, 'file_path': file_path})
        else:
            return jsonify({'success': False, 'message': 'Failed to download track'})
    elif url_type == 'youtube_shorts':
        file_path = download_video_from_source(query, 'youtube_shorts')  # Скачивание видео с YouTube Shorts
        if file_path:
            with open(file_path, 'rb') as video:
                bot.send_video(chat_id, video)  # Отправка видео пользователю в чате
            return jsonify({'success': True, 'file_path': file_path})
        else:
            return jsonify({'success': False, 'message': 'Failed to download video'})
    else:
        keyboard = types.InlineKeyboardMarkup()
        music_button = types.InlineKeyboardButton(text="Скачать музыку", callback_data=f"download_music_{query}")
        video_button = types.InlineKeyboardButton(text="Скачать видео", callback_data=f"download_video_{query}")
        keyboard.add(music_button, video_button)
        bot.send_message(chat_id, "Вы можете скачать как видео так и отдельно музыку из Youtube", reply_markup=keyboard)  # Отправка сообщения с кнопками выбора
        return jsonify({'success': True})

def search_platform(platform, query):
    if platform == 'youtube':
        return search_music(query)  # Поиск музыки на YouTube
    elif platform == 'vk':
        return search_music_vk(query, config.VK_ACCESS_TOKEN)  # Поиск музыки на VK
    elif platform == 'soundcloud':
        return search_music_soundcloud(query, config.SOUNDCLOUD_CLIENT_ID)  # Поиск музыки на SoundCloud
    else:
        raise ValueError('Invalid platform specified')  # Ошибка при неверной платформе

@app.route('/tracks', methods=['GET'])
def get_tracks():
    tracks = db_get_all_tracks()  # Получение всех треков из базы данных
    return jsonify({'success': True, 'tracks': tracks})

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    chat_id = data.get('chat_id')
    query = data.get('query')
    track_index = data.get('track_index')

    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400  # Проверка наличия chat_id

    url_type, clean_url = parse_and_clean_url(query)
    if clean_url:
        return handle_youtube_url(chat_id, clean_url, f'user_{chat_id}', url_type)
    elif track_index is not None:
        return handle_track_index(chat_id, track_index)

def handle_track_index(chat_id, track_index):
    username = f'user_{chat_id}'
    if username not in search_results or track_index >= len(search_results[username]):
        return jsonify({'success': False, 'message': 'Invalid track index'}), 400  # Проверка корректности индекса трека

    url = search_results[username][track_index]['webpage_url']
    existing_file = db_get_downloaded_file(url)
    if existing_file:
        return jsonify({'success': True, 'file_path': existing_file})
    else:
        file_path, real_name = download_music(url)  # Скачивание музыки
        if file_path:
            db_add_download(chat_id, url, url, file_path, real_name)  # Добавление загрузки в базу данных
            return jsonify({'success': True, 'file_path': file_path})
        else:
            return jsonify({'success': False, 'message': 'Failed to download track'}), 400

@app.route('/send_track', methods=['POST'])
def send_track():
    data = request.json
    chat_id = data.get('chat_id')
    file_path = data.get('file_path')

    if not chat_id or not file_path:
        return jsonify({'success': False, 'message': 'Missing chat_id or file_path'}), 400  # Проверка наличия chat_id и пути к файлу

    try:
        send_music(chat_id, file_path)  # Отправка музыки пользователю
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error sending music: {e}")
        return jsonify({'success': False, 'message': 'Error sending music'}), 500

@app.route('/save_playlist', methods=['POST'])
def save_playlist():
    data = request.json
    chat_id = data.get('chat_id')
    tracks = data.get('tracks')

    if not chat_id or not tracks:
        return jsonify({'success': False, 'message': 'Missing chat_id or tracks'}), 400  # Проверка наличия chat_id и треков

    save_user_playlist(chat_id, tracks)  # Сохранение плейлиста пользователя
    return jsonify({'success': True})

@app.route('/user_playlist', methods=['GET'])
def user_playlist():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400  # Проверка наличия chat_id

    tracks = get_user_playlist(chat_id)  # Получение плейлиста пользователя
    return jsonify({'success': True, 'tracks': tracks})

@app.route('/clear_playlist', methods=['POST'])
def clear_playlist():
    try:
        chat_id = request.json.get('chat_id')
        clear_user_playlist(chat_id)  # Очистка плейлиста пользователя
        return jsonify(success=True)
    except Exception as e:
        print(f"Ошибка очистки плейлиста: {e}")
        return jsonify(success=False, message=str(e))

@app.route('/user_requests', methods=['GET'])
def user_requests():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400  # Проверка наличия chat_id

    tracks = db_get_user_requests(chat_id)  # Получение запросов пользователя
    return jsonify({'success': True, 'tracks': tracks})

@app.route('/all_tracks', methods=['GET'])
def all_tracks():
    try:
        tracks = db_get_all_server_tracks()  # Получение всех треков на сервере
        return jsonify({'success': True, 'tracks': tracks})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download_video_direct', methods=['POST'])
def download_video_direct():
    data = request.json
    chat_id = data.get('chat_id')
    url = data.get('url')

    if not chat_id or not url:
        return jsonify({'success': False, 'message': 'Missing chat_id or url'}), 400  # Проверка наличия chat_id и URL

    try:
        source = 'youtube'
        if 'instagram' in url:
            source = 'instagram'
        elif 'shorts' in url:
            source = 'youtube_shorts'
        
        file_path = download_video_from_source(url, source)  # Скачивание видео с источника
        if file_path:
            with open(file_path, 'rb') as video:
                bot.send_video(chat_id, video)  # Отправка видео пользователю
            return jsonify({'success': True, 'file_path': file_path})
        else:
            return jsonify({'success': False, 'message': 'Не удалось скачать видео.'}), 500
    except Exception as e:
        logging.error(f"Error in download_video_direct: {e}")
        return jsonify({'success': False, 'message': 'Произошла ошибка при обработке запроса.'}), 500

@app.route('/webapp_download', methods=['POST'])
def webapp_download():
    data = request.json
    chat_id = data.get('chat_id')
    query = data.get('query')

    if not chat_id or not query:
        return jsonify({'success': False, 'message': 'Missing chat_id or query'}), 400  # Проверка наличия chat_id и запроса

    url_type, clean_url = parse_and_clean_url(query)
    try:
        if url_type in ['youtube', 'youtube_music']:
            file_path, real_name = download_music(clean_url)  # Скачивание музыки
            if file_path:
                db_add_download(chat_id, query, clean_url, file_path, real_name)  # Добавление загрузки в базу данных
                return jsonify({'success': True, 'file_path': file_path})
            else:
                return jsonify({'success': False, 'message': 'Failed to download track'})
        elif url_type == 'youtube_shorts':
            file_path = download_video_from_source(clean_url, 'youtube_shorts')  # Скачивание видео
            if file_path:
                return jsonify({'success': True, 'file_path': file_path})
            else:
                return jsonify({'success': False, 'message': 'Failed to download video'})
        else:
            return jsonify({'success': False, 'message': 'Unsupported URL type'})
    except Exception as e:
        logging.error(f"Error in webapp_download: {e}")
        return jsonify({'success': False, 'message': 'Произошла ошибка при обработке запроса.'})

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id  # Получение user_id пользователя
    username = message.from_user.username  # Получение имени пользователя
    chat_id = message.chat.id  # Получение chat_id чата
    db_add_user(user_id, username)  # Добавление пользователя в базу данных

    user_platforms[chat_id] = 'youtube'  # Установка платформы YouTube по умолчанию

    keyboard = types.InlineKeyboardMarkup()
    web_app_button = types.InlineKeyboardButton(text="Открыть Web App", web_app=types.WebAppInfo(url=config.WEB_APP_URL))
    keyboard.add(web_app_button)

    bot.send_message(chat_id, "Данный бот находится в разработке, установлена платформа YouTube.")
    bot.send_message(chat_id, "Теперь вы можете открыть Web App для поиска музыки. Или воспользоваться inline режимом, отправив в чат имя исполнителя или название трека или ссылку на youtube.", reply_markup=keyboard)  # Отправка приветственного сообщения с кнопкой Web App

@bot.message_handler(commands=['broadcast'])
def handle_broadcast_command(message):
    if str(message.from_user.id) == config.ADMIN_USER_ID:
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            broadcast_message(args[1])  # Отправка сообщения всем пользователям
            bot.reply_to(message, "Сообщение отправлено всем пользователям.")
        else:
            bot.reply_to(message, "Пожалуйста, укажите текст сообщения после команды.")
    else:
        bot.reply_to(message, "У вас нет прав использовать эту команду.")  # Проверка прав администратора

@bot.message_handler(commands=['drop_downloads'])
def handle_drop_downloads_command(message):
    if str(message.from_user.id) == config.ADMIN_USER_ID:
        clear_downloads_table()  # Очистка таблицы загрузок
        bot.reply_to(message, "Таблица downloads очищена.")
    else:
        bot.reply_to(message, "У вас нет прав использовать эту команду.")  # Проверка прав администратора

def broadcast_message(text):
    chat_ids = load_chat_ids()  # Загрузка всех chat_id пользователей
    for chat_id in chat_ids:
        try:
            bot.send_message(chat_id, text)  # Отправка сообщения каждому пользователю
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {chat_id}: {e}")

@bot.message_handler(content_types=['text'])
def text(message):
    if message.text.startswith('/'):
        return  # Игнорирование команд

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username
    text_content = message.text.strip()
    logging.info(f"Received message from {username} (id: {user_id}): {text_content}")

    url_type, clean_url = parse_and_clean_url(text_content)
    if url_type:
        if url_type == 'youtube_music':
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path, real_name = download_music(clean_url)  # Скачивание музыки с YouTube
            if file_path:
                db_add_download(chat_id, username, clean_url, file_path, real_name)  # Добавление загрузки в базу данных
                send_music(chat_id, file_path)  # Отправка музыки пользователю
            else:
                bot.send_message(chat_id, "Не удалось скачать музыку.")
        elif url_type == 'youtube_shorts':
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path = download_video_from_source(clean_url, 'youtube_shorts')  # Скачивание видео с YouTube Shorts
            if file_path:
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)  # Отправка видео пользователю
            else:
                bot.send_message(chat_id, "Не удалось скачать видео.")
        elif url_type == 'youtube':
            keyboard = types.InlineKeyboardMarkup()
            music_button = types.InlineKeyboardButton(text="Скачать музыку", callback_data=f"download_music_{clean_url}")
            video_button = types.InlineKeyboardButton(text="Скачать видео", callback_data=f"download_video_{clean_url}")
            keyboard.add(music_button, video_button)
            bot.send_message(chat_id, "Вы можете скачать как видео так и отдельно музыку из Youtube", reply_markup=keyboard)  # Отправка сообщения с кнопками выбора
        elif url_type == 'instagram':
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path = get_instagram_video_url(clean_url)  # Получение видео URL с Instagram
            if file_path:
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)  # Отправка видео пользователю
        elif url_type == 'tiktok':
            bot.send_message(chat_id, "Файл скачивается и будет отправлен.")
            file_path = download_video_from_source(clean_url, 'tiktok')  # Скачивание видео с TikTok
            if file_path:
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video)  # Отправка видео пользователю
        else:
            keyboard = types.InlineKeyboardMarkup()
            bot.send_message(chat_id, "Неопознанная ссылка", reply_markup=keyboard)  # Обработка неизвестной ссылки
    else:
        keywords = sanitize(text_content)
        cached_result = get_from_cache(keywords)  # Проверка наличия результата в кеше
        if (cached_result):
            logging.info(f'Using cached results for: {keywords}')
            requests[chat_id] = cached_result
            send_results_page(chat_id, cached_result)
            return

        db_add_search(user_id, keywords)  # Добавление поиска в базу данных
        platform = user_platforms.get(chat_id, 'youtube')
        results = search_platform(platform, keywords)  # Поиск на указанной платформе

        if results:
            requests[chat_id] = results
            add_to_cache(keywords, results)  # Добавление результата в кеш
            send_results_page(chat_id, results)
        else:
            bot.send_message(chat_id, "К сожалению, ничего не найдено. Попробуйте другой запрос.")

def send_results_page(chat_id, results, page=1, results_per_page=config.RESULTS_PAGES):
    total_pages = (len(results) + results_per_page - 1) // results_per_page
    page = max(1, min(page, total_pages))
    page_results = results[(page - 1) * results_per_page: page * results_per_page]
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(page_results, start=(page - 1) * results_per_page):
        duration = format_duration(item['duration']) if 'duration' in item else 'Unknown'
        title = trim_or_compress_title(item.get('title', 'Unknown Title'))
        button_text = f"{i + 1}. {title} [{duration}]"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=f'download_music_{item["webpage_url"]}'))
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("<<", callback_data=f'page_{page-1}'))
    if page < total_pages:
        navigation_buttons.append(types.InlineKeyboardButton(">>", callback_data=f'page_{page+1}'))
    if navigation_buttons:
        keyboard.row(*navigation_buttons)
    bot.send_message(chat_id, "Выберите трек для скачивания:", reply_markup=keyboard)  # Отправка страницы с результатами поиска

@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def query_page(call):
    page_num = int(call.data.split('_')[1])
    chat_id = call.message.chat.id
    send_results_page(chat_id, requests[chat_id], page=page_num)  # Обработка пагинации результатов поиска

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    logging.debug(f"Callback query data: {call.data}")
    if call.data.startswith('download_video_'):
        download_video_callback(call)  # Обработка загрузки видео
    elif call.data.startswith('download_music_'):
        download_music_callback(call)  # Обработка загрузки музыки

def download_video_callback(call):
    logging.debug("download_video_callback triggered")
    chat_id = call.message.chat.id
    try:
        url = call.data.split('download_video_')[1]
        logging.debug(f"Extracted URL for download video: {url}")
        existing_file = db_get_downloaded_file(url)
        if existing_file:
            logging.debug(f"File already exists: {existing_file}")
            file_size = os.path.getsize(existing_file)
            if file_size > 50 * 1024 * 1024:
                bot.send_message(chat_id, "Файл превышает ограничение в 50 МБ и не может быть отправлен через Telegram.")  # Ограничение размера файла
                return
            with open(existing_file, 'rb') as video:
                bot.send_video(chat_id, video, supports_streaming=True)  # Отправка видео пользователю
        else:
            file_path = download_video_from_source(url, 'youtube')  # Скачивание видео с YouTube
            if file_path:
                logging.debug(f"Video downloaded to path: {file_path}")
                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:
                    bot.send_message(chat_id, "Файл превышает ограничение в 50 МБ и не может быть отправлен через Telegram.")  # Ограничение размера файла
                    return
                db_add_download(chat_id, url, url, file_path, file_path)  # Добавление загрузки в базу данных
                with open(file_path, 'rb') as video:
                    bot.send_video(chat_id, video, supports_streaming=True)  # Отправка видео пользователю
            else:
                logging.error("Failed to download video.")
                bot.send_message(chat_id, "Не удалось скачать видео.")
    except Exception as e:
        logging.error(f"Error in download_video_callback: {e}")
        bot.send_message(chat_id, "Произошла ошибка при обработке запроса.")

def download_music_callback(call):
    logging.debug("download_music_ callback triggered")
    chat_id = call.message.chat.id
    try:
        url = call.data.split('download_music_')[1]
        logging.debug(f"Extracted URL for download music: {url}")
        existing_file = db_get_downloaded_file(url)
        if existing_file:
            logging.debug(f"File already exists: {existing_file}")
            send_music(chat_id, existing_file)  # Отправка музыки пользователю
        else:
            file_path, real_name = download_music(url)  # Скачивание музыки с YouTube
            logging.debug(f"Downloaded and converted music: {file_path, real_name}")
            if file_path:
                db_add_download(chat_id, url, url, file_path, real_name)  # Добавление загрузки в базу данных
                send_music(chat_id, file_path)  # Отправка музыки пользователю
            else:
                bot.send_message(chat_id, "Не удалось скачать музыку.")
    except Exception as e:
        logging.error(f"Error in download_music_callback: {e}")
        bot.send_message(chat_id, "Произошла ошибка при обработке запроса.")

def send_music(chat_id, filename):
    logging.info(f'Начинаем отправку музыки в чат {chat_id} по имени файла: {filename}')
    with open(filename, 'rb') as audio:
        bot.send_audio(chat_id, audio)  # Отправка аудио пользователю
    logging.info(f'Отправили музыку в чат {chat_id} по имени файла: {filename}')

atexit.register(close_browser)  # Регистрация функции закрытия браузера при завершении программы

if __name__ == '__main__':
    app.run(port=3001)  # Запуск Flask приложения на порту 3001