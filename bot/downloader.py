import yt_dlp
import os
import logging
import config
from utils import rotate_files, safe_filename, get_existing_file_path

# Функция для поиска музыки по ключевым словам
def search_music(keywords, search_amount=config.MAX_RESULTS):  # Используем максимальное количество результатов из конфигурационного файла
    try:
        ydl_opts = {
            'default_search': f'ytsearch{search_amount}',
            'noplaylist': True,
            'quiet': True,
            'dump-json': True,
            'no-check-certificate': True,
            'geo-bypass': True,
            'flat-playlist': True,
            'skip-download': True,
            'ignore-errors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(keywords, download=False)
            if not info or 'entries' not in info or not info['entries']:
                logging.error('Ничего не найдено.')
                return None
            # Фильтруем результаты по продолжительности
            filtered_entries = [{'title': e['title'], 'webpage_url': e['webpage_url'], 'duration': e['duration']} 
                                for e in info['entries'] if e.get('duration', 0) <= config.MAX_DURATION]  # Используем максимальную продолжительность из конфигурационного файла
        logging.info(f"Search results: {filtered_entries}")
        return filtered_entries
    except Exception as e:
        logging.error(f"Ошибка при поиске музыки: {e}")
        return None

# Функция для загрузки и конвертации музыки по URL
def download_and_convert_music(url):
    try:
        # Ротация старых файлов, чтобы не превышать лимит
        rotate_files(config.DOWNLOAD_DIR)  # Используем директорию загрузок из конфигурационного файла
        file_path, filename = get_existing_file_path(url)
        if file_path:
            return file_path, filename

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '256',
            }],
            'quiet': True,
            'outtmpl': '%(id)s.%(ext)s',  # Временный шаблон имени файла
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            temp_file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            title = safe_filename(info.get('title', 'Unknown Title'))
            new_file_path = os.path.join(config.DOWNLOAD_DIR, f'{title}.mp3')  # Используем директорию загрузок из конфигурационного файла
            if os.path.exists(temp_file_path):
                os.rename(temp_file_path, new_file_path)
                logging.info(f"Downloaded and converted music: {new_file_path}")
                return new_file_path, title
            else:
                logging.error(f'Downloaded file {temp_file_path} not found.')
                return None, None
    except Exception as e:
        logging.error(f"Ошибка при загрузке и конвертации музыки: {e}")
        return None, None

# Функция для получения информации о видео по URL
def get_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                logging.info(f"Video info: {info}")
                return {
                    'duration': info.get('duration', 0),
                    'title': info.get('title', 'Unknown Title')
                }
            else:
                logging.error('Failed to get video info')
                return None
    except Exception as e:
        logging.error(f"Ошибка при получении информации о видео: {e}")
        return None
