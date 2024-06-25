import pytube
import os
import logging
import config
import requests
import time
from utils import rotate_files, safe_filename, get_existing_file_path, parse_and_clean_url
from selenium.webdriver.common.by import By
from browser import BrowserManager, close_browser
import atexit
import requests
from typing import Optional, List, Dict
import subprocess

# Класс для хранения метаданных YouTube видео
class YouTubeMetadata:
    def __init__(self, metadata_rows: List[Dict]):
        # Инициализация словаря метаданных из списка строк
        self.metadata = {row['title']['simpleText']: row['contents'][0]['simpleText'] for row in metadata_rows}

# Функция для получения метаданных YouTube видео
def get_metadata(video: pytube.YouTube) -> Optional<YouTubeMetadata]:
    try:
        video_data = requests.get(f"https://www.youtube.com/watch?v={video.video_id}").text
        initial_data_start = video_data.find('ytInitialData =') + len('ytInitialData =')
        initial_data_end = video_data.find('};', initial_data_start) + 1
        initial_data = json.loads(video_data[initial_data_start:initial_data_end])
        metadata_rows = initial_data["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"][1]["videoSecondaryInfoRenderer"]["metadataRowContainer"]["metadataRowContainerRenderer"]["rows"]
        metadata_rows = filter(lambda x: "metadataRowRenderer" in x.keys(), metadata_rows)
        metadata_rows = [x["metadataRowRenderer"] for x in metadata_rows]
        return YouTubeMetadata(metadata_rows)  # Возвращаем метаданные как экземпляр YouTubeMetadata
    except Exception as e:
        logging.error(f"Error fetching metadata: {e}")
        return None

# Изменить рабочий каталог на директорию с правами записи
os.chdir("/home/ubuntu/refinder/wdm_cache")

# Инициализация BrowserManager
browser_manager = BrowserManager()
browser = browser_manager.get_driver()

# Функция для поиска музыки на YouTube
def search_music(keywords, search_amount=config.MAX_RESULTS):
    try:
        search = pytube.Search(keywords)
        results = search.results[:search_amount]
        # Фильтрация результатов по максимальной длительности трека
        filtered_entries = [{'title': video.title, 'webpage_url': video.watch_url, 'duration': video.length} 
                            for video in results if video.length <= config.MAX_DURATION]
        logging.info(f"Search results (pytube): {filtered_entries}")
        return filtered_entries
    except Exception as e:
        logging.error(f"Ошибка при поиске музыки: {e}")
        return None

# Функция для скачивания видео с различных платформ
def download_video_from_source(url: str, source: str) -> str:
    try:
        if source == 'youtube_music':
            return download_music(url)[0]
        elif source in ['youtube', 'youtube_shorts']:
            yt = pytube.YouTube(url)
            # Получаем все прогрессивные потоки с расширением mp4
            streams = yt.streams.filter(progressive=True, file_extension='mp4')
            
            # Сортируем потоки по убыванию разрешения
            streams = sorted(streams, key=lambda s: int(s.resolution[:-1]) if s.resolution else 0, reverse=True)

            best_stream = None
            for stream in streams:
                if int(stream.resolution[:-1]) <= 1080 and stream.filesize <= 50 * 1024 * 1024:
                    best_stream = stream
                    break

            if not best_stream:
                logging.error(f"No suitable video stream found for {source} within size limit.")
                return None
            
            # Скачиваем видео
            file_path = best_stream.download(output_path=config.DOWNLOAD_DIR)
            logging.info(f"Downloaded video from {source}: {file_path}")
            return file_path
        elif source == 'instagram':
            video_url = get_instagram_video_url(url)
            if video_url:
                file_path = f"{config.DOWNLOAD_DIR}/instagram_video.mp4"
                download_video_file(video_url, file_path)
                logging.info(f"Downloaded video from Instagram: {file_path}")
                return file_path
            else:
                logging.error("Failed to retrieve Instagram video URL.")
                return None
        elif source == 'tiktok':
            file_path = download_tiktok_video(url)
            logging.info(f"Downloaded video from TikTok: {file_path}")
            return file_path
    except Exception as e:
        logging.error(f"Error downloading video from {source}: {e}")
        return None

# Функция для скачивания музыки с YouTube
def download_music(url):
    try:
        rotate_files(config.DOWNLOAD_DIR)  # Удаление старых файлов, если их количество превышает лимит
        file_path, filename = get_existing_file_path(url)
        if file_path:
            return file_path, filename  # Если файл уже существует, возвращаем путь к нему

        video = pytube.YouTube(url)
        audio_stream = video.streams.filter(only_audio=True).first()
        if not audio_stream:
            logging.error('Audio stream not found.')
            return None, None

        # Скачивание аудиопотока
        temp_file_path = audio_stream.download(output_path=config.DOWNLOAD_DIR, filename=f'{video.video_id}_audio.mp4')

        # Получение метаданных
        metadata = get_metadata(video)
        if metadata and 'Artist' in metadata.metadata and 'Song' in metadata.metadata:
            artist = metadata.metadata['Artist']
            song = metadata.metadata['Song']
            title = f"{artist} - {song}"
        else:
            title = safe_filename(video.title)

        new_file_path = os.path.join(config.DOWNLOAD_DIR, f'{title}.mp3')

        # Переименование файла в окончательное имя
        os.rename(temp_file_path, new_file_path)

        logging.info(f"Downloaded and saved music (pytube): {new_file_path}")
        return new_file_path, title
    except Exception as e:
        logging.error(f"Ошибка при загрузке музыки с pytube: {e}")
        return None, None
        
# Функция для скачивания видеофайла по URL
def download_video_file(video_url, file_path):
    try:
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logging.info(f"Video downloaded to: {file_path}")
    except Exception as e:
        logging.error(f"Error downloading video file: {e}")
        return None

# Функция для получения URL видео из Instagram
def get_instagram_video_url(instagram_url):
    try:
        browser.get(instagram_url)
        time.sleep(5)
        video_element = browser.find_element(By.XPATH, "//video")
        video_url = video_element.get_attribute("src")
        return video_url
    except Exception as e:
        logging.error(f"Error downloading Instagram video: {e}")
        return None

# Функция для скачивания видео с TikTok
def download_tiktok_video(tiktok_url):
    try:
        browser.get(tiktok_url)
        time.sleep(10)

        video_elements = browser.find_elements(By.TAG_NAME, 'video')
        if not video_elements:
            logging.error("Video elements not found.")
            return None

        video_url = None
        for video in video_elements:
            src = video.get_attribute('src')
            if src:
                video_url = src
                break

        if not video_url:
            logging.error("Video URL not found.")
            return None

        response = requests.get(video_url, stream=True)
        if response.status_code != 200:
            logging.error(f"Failed to download video, status code: {response.status_code}")
            return None

        file_path = f"{config.DOWNLOAD_DIR}/tiktok_video.mp4"
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logging.info(f"Video downloaded to: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Error downloading TikTok video with Selenium: {e}")
        return None

# Закрытие браузера при завершении работы
atexit.register(close_browser)