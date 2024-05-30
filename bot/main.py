from flask import Flask, request, jsonify, render_template, send_from_directory
import telebot
import logging
import config
from db import (db_add_user, db_add_search, db_add_download, load_chat_ids, db_get_all_tracks,
                db_get_downloaded_file, get_user_playlist, save_user_playlist, clear_user_playlist,
                db_get_user_requests, db_get_all_server_tracks)
from cache import get_from_cache, add_to_cache
from downloader import search_music, download_and_convert_music
from vk_downloader import search_music_vk
from soundcloud_downloader import search_music_soundcloud
from utils import is_youtube_url, sanitize, format_duration, trim_or_compress_title
from telebot import types

# Инициализация бота с использованием токена из конфигурационного файла
bot = telebot.TeleBot(config.BOT_TOKEN)
bot.set_webhook(url=config.WEBHOOK_URL)

# Настройка логирования
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)

# Инициализация Flask приложения
app = Flask(__name__, static_folder='static')

# Словари для хранения данных сессий
requests = {}
search_results = {}
user_platforms = {}

# Маршрут для главной страницы
@app.route('/')
def index():
    return render_template('index.html')

# Маршрут для обработки вебхуков от Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Error', 403

# Маршрут для поиска музыки
@app.route('/search', methods=['POST'])
def search():
    data = request.json
    chat_id = data.get('chat_id')
    query = data.get('query')
    platform = user_platforms.get(chat_id, 'youtube')

    if not chat_id or not query:
        return jsonify({'success': False, 'message': 'Missing chat_id or query'}), 400

    username = f'user_{chat_id}'

    # Если это ссылка на YouTube, проверяем и загружаем музыку
    if is_youtube_url(query):
        existing_file = db_get_downloaded_file(query)
        if existing_file:
            logging.info(f"File already exists for {query}: {existing_file}")
            send_music_web_app(chat_id, existing_file)
            return jsonify({'success': True, 'file_path': existing_file})
        else:
            file_path, real_name = download_and_convert_music(query)
            if file_path:
                db_add_download(chat_id, username, query, file_path, real_name)
                logging.info(f"Downloaded and converted {query}: {file_path}")
                send_music_web_app(chat_id, file_path)
                return jsonify({'success': True, 'file_path': file_path})
            else:
                return jsonify({'success': False, 'message': 'Failed to download track'})

    # Проверяем кэш
    cached_result = get_from_cache(query)
    if cached_result:
        logging.info(f'Using cached results for: {query}')
        search_results[username] = cached_result
        return jsonify({'success': True, 'results': cached_result})

    # Ищем музыку в зависимости от платформы
    if platform == 'youtube':
        results = search_music(query)
    elif platform == 'vk':
        results = search_music_vk(query, config.VK_ACCESS_TOKEN)
    elif platform == 'soundcloud':
        results = search_music_soundcloud(query, config.SOUNDCLOUD_CLIENT_ID)
    else:
        return jsonify({'success': False, 'message': 'Invalid platform specified'}), 400

    # Сохраняем результаты поиска и кэшируем их
    if results:
        search_results[username] = results
        add_to_cache(query, results)
        db_add_search(chat_id, query)
        return jsonify({'success': True, 'results': results})
    else:
        return jsonify({'success': False, 'message': 'No results found'})

# Маршрут для получения всех треков
@app.route('/tracks', methods=['GET'])
def get_tracks():
    tracks = db_get_all_tracks()
    return jsonify({'success': True, 'tracks': tracks})

# Маршрут для загрузки треков
@app.route('/download', methods=['POST'])
def download():
    data = request.json
    chat_id = data.get('chat_id')
    query = data.get('query')
    track_index = data.get('track_index')

    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400

    # Если это ссылка на YouTube, загружаем музыку
    if query and is_youtube_url(query):
        existing_file = db_get_downloaded_file(query)
        if existing_file:
            logging.info(f"File already exists for {query}: {existing_file}")
            return jsonify({'success': True, 'file_path': existing_file})
        else:
            file_path, real_name = download_and_convert_music(query)
            if file_path:
                db_add_download(chat_id, query, query, file_path, real_name)
                return jsonify({'success': True, 'file_path': file_path})
            else:
                return jsonify({'success': False, 'message': 'Failed to download track'}), 400
    elif track_index is not None:
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

# Маршрут для скачивания файлов
@app.route('/tracks/<path:filename>')
def download_file(filename):
    try:
        filename = filename.replace('%20', ' ')
        directory = config.DOWNLOAD_DIR
        logging.info(f"Serving file: {filename} from {directory}")
        return send_from_directory(directory, filename, as_attachment=False)
    except Exception as e:
        logging.error(f"Error serving file: {e}")
        return "File not found", 404

# Маршрут для отправки треков
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

# Маршрут для сохранения плейлиста пользователя
@app.route('/save_playlist', methods=['POST'])
def save_playlist():
    data = request.json
    chat_id = data.get('chat_id')
    tracks = data.get('tracks')

    if not chat_id or not tracks:
        return jsonify({'success': False, 'message': 'Missing chat_id or tracks'}), 400

    save_user_playlist(chat_id, tracks)
    return jsonify({'success': True})

# Маршрут для получения плейлиста пользователя
@app.route('/user_playlist', methods=['GET'])
def user_playlist():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400

    tracks = get_user_playlist(chat_id)
    return jsonify({'success': True, 'tracks': tracks})

# Маршрут для очистки плейлиста пользователя
@app.route('/clear_playlist', methods=['POST'])
def clear_playlist():
    try:
        chat_id = request.json.get('chat_id')
        clear_user_playlist(chat_id)
        return jsonify(success=True)
    except Exception as e:
        logging.error(f"Ошибка очистки плейлиста: {e}")
        return jsonify(success=False, message=str(e))

# Маршрут для получения запросов пользователя
@app.route('/user_requests', methods=['GET'])
def user_requests():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({'success': False, 'message': 'Missing chat_id'}), 400

    tracks = db_get_user_requests(chat_id)
    return jsonify({'success': True, 'tracks': tracks})

# Маршрут для получения всех треков на сервере
@app.route('/all_tracks', methods=['GET'])
def all_tracks():
    try:
        tracks = db_get_all_server_tracks()
        return jsonify({'success': True, 'tracks': tracks})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Обработчик команды /start
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

    bot.send_message(chat_id, "Данный бот находится в разработке, установлена платформа YouTube. Предупреждение! Новый поиск может занять продолжительное время.")
    bot.send_message(chat_id, "Теперь вы можете открыть Web App для поиска музыки. Или воспользоваться inline режимом, отправив в чат имя исполнителя или название трека или ссылку на youtube.", reply_markup=keyboard)

# Обработчик callback-запросов для установки платформы. В разработке
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_platform_'))
def callback_set_platform(call):
    chat_id = call.message.chat.id

    user_platforms[chat_id] = 'youtube'

    keyboard = types.InlineKeyboardMarkup()
    web_app_button = types.InlineKeyboardButton(text="Открыть Web App", web_app=types.WebAppInfo(url=config.WEB_APP_URL))
    keyboard.add(web_app_button)

    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="null")
    bot.send_message(chat_id, "null.", reply_markup=keyboard)

# Обработчик команды /broadcast
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

# Функция для рассылки сообщений всем пользователям
def broadcast_message(text):
    chat_ids = load_chat_ids()
    for chat_id in chat_ids:
        try:
            bot.send_message(chat_id, text)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {chat_id}: {e}")

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def text(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username
    text_content = message.text.strip()
    logging.info(f"Received message from {username} (id: {user_id}): {text_content}")

    # Проверка, является ли сообщение ссылкой на YouTube
    if is_youtube_url(text_content):
        logging.info(f"Message is recognized as a YouTube URL: {text_content}")
        existing_file = db_get_downloaded_file(text_content)
        if existing_file:
            logging.info(f"File already exists for {text_content}: {existing_file}")
            send_music(chat_id, existing_file)
        else:
            file_path, real_name = download_and_convert_music(text_content)
            if file_path:
                db_add_download(user_id, username, text_content, file_path, real_name)
                send_music(chat_id, file_path)
            else:
                bot.send_message(chat_id, "Не удалось скачать трек.")
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

        if platform == 'youtube':
            results = search_music(keywords)
        elif platform == 'vk':
            results = search_music_vk(keywords, config.VK_ACCESS_TOKEN)
        elif platform == 'soundcloud':
            results = search_music_soundcloud(keywords, config.SOUNDCLOUD_CLIENT_ID)

        if results:
            requests[chat_id] = results
            add_to_cache(keywords, results)
            send_results_page(chat_id, results)
        else:
            bot.send_message(chat_id, "К сожалению, ничего не найдено. Попробуйте другой запрос.")

# Отправка результатов поиска с пагинацией
def send_results_page(chat_id, results, page=1, results_per_page=config.RESULTS_PAGES):
    total_pages = (len(results) + results_per_page - 1) // results_per_page
    page = max(1, min(page, total_pages))
    page_results = results[(page - 1) * results_per_page: page * results_per_page]
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(page_results, start=(page - 1) * results_per_page):
        duration = format_duration(item['duration']) if 'duration' in item else 'Unknown'
        title = trim_or_compress_title(item.get('title', 'Unknown Title'))
        button_text = f"{i + 1}. {title} [{duration}]"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=f'download_{i + 1}'))
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("<<", callback_data=f'page_{page-1}'))
    if page < total_pages:
        navigation_buttons.append(types.InlineKeyboardButton(">>", callback_data=f'page_{page+1}'))
    if navigation_buttons:
        keyboard.row(*navigation_buttons)
    bot.send_message(chat_id, "Выберите трек для скачивания:", reply_markup=keyboard)

# Обработчик callback-запросов для пагинации
@bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
def query_page(call):
    page_num = int(call.data.split('_')[1])
    chat_id = call.message.chat.id
    send_results_page(chat_id, requests[chat_id], page=page_num)

# Обработчик callback-запросов для скачивания треков
@bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))
def callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    username = call.from_user.username
    index = int(call.data.split('_')[1]) - 1
    url = requests[chat_id][index]['webpage_url']
    existing_file = db_get_downloaded_file(url)
    if existing_file:
        send_music(chat_id, existing_file)
    else:
        file_path, real_name = download_and_convert_music(url)
        if file_path:
            db_add_download(user_id, username, url, file_path, real_name)
            send_music(chat_id, file_path)
        else:
            bot.send_message(chat_id, "Не удалось скачать трек.")

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

# Запуск Flask приложения
if __name__ == '__main__':
    app.run(port=5000)
