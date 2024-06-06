import pytube
import os
import logging
import config
import requests
import time
from utils import rotate_files, safe_filename, get_existing_file_path, clean_youtube_url
from browser_manager import BrowserManager
from selenium.webdriver.common.by import By
from TikTokApi import TikTokApi

# Функция для поиска музыки на YouTube
def search_music(keywords, search_amount=config.MAX_RESULTS):
    try:
        search = pytube.Search(keywords)  # Выполнение поиска по ключевым словам
        results = search.results[:search_amount]  # Ограничение количества результатов
        # Фильтрация результатов и формирование списка
        filtered_entries = [{'title': video.title, 'webpage_url': video.watch_url, 'duration': video.length} 
                            for video in results if video.length <= config.MAX_DURATION]
        logging.info(f"Search results (pytube): {filtered_entries}")
        return filtered_entries
    except Exception as e:
        logging.error(f"Ошибка при поиске музыки: {e}")
        return None

# Функция для скачивания и конвертации музыки с YouTube
def download_and_convert_music(url):
    try:
        rotate_files(config.DOWNLOAD_DIR)  # Вращение файлов для управления дисковым пространством
        file_path, filename = get_existing_file_path(url)
        if file_path:
            return file_path, filename

        video = pytube.YouTube(url)
        audio_stream = video.streams.filter(only_audio=True).first()  # Поиск аудиопотока
        if not audio_stream:
            logging.error('Audio stream not found.')
            return None, None

        temp_file_path = audio_stream.download(filename=f'{video.video_id}.mp4')  # Скачивание аудио в формате mp4
        title = safe_filename(video.title)
        new_file_path = os.path.join(config.DOWNLOAD_DIR, f'{title}.mp3')

        temp_mp3_path = os.path.join(config.DOWNLOAD_DIR, f'{video.video_id}.mp3')
        command = f'ffmpeg -i "{temp_file_path}" -vn -ab 256k -ar 44100 -y "{temp_mp3_path}"'  # Команда для конвертации
        logging.info(f'Running command: {command}')
        os.system(command)
        os.rename(temp_mp3_path, new_file_path)
        os.remove(temp_file_path)
        logging.info(f"Downloaded and converted music (pytube): {new_file_path}")
        return new_file_path, title
    except Exception as e:
        logging.error(f"Ошибка при загрузке и конвертации музыки с pytube: {e}")
        return None, None

# Функция для получения информации о видео
def get_video_info(url):
    try:
        yt = pytube.YouTube(clean_youtube_url(url))
        qualities = []
        for stream in yt.streams.filter(progressive=True, file_extension='mp4'):
            if stream.resolution not in qualities and int(stream.resolution[:-1]) <= 1080:
                qualities.append(stream.resolution)
        return {'title': yt.title, 'qualities': qualities}
    except Exception as e:
        print(f"Error fetching video info: {e}")
        return {'title': '', 'qualities': []}

# Функция для скачивания видео с YouTube
def download_video(url):
    try:
        rotate_files(config.DOWNLOAD_DIR)  # Вращение файлов для управления дисковым пространством
        file_path, filename = get_existing_file_path(url)
        if file_path:
            logging.debug(f"File already exists on server: {file_path}")
            return file_path, filename

        video = pytube.YouTube(url)
        stream = video.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if not stream:
            logging.error('Video stream not found.')
            return None, None

        temp_file_path = stream.download(filename=f'{video.video_id}.mp4')  # Скачивание видео
        title = safe_filename(video.title)
        new_file_path = os.path.join(config.DOWNLOAD_DIR, f'{title}.mp4')
        os.rename(temp_file_path, new_file_path)

        logging.info(f"Downloaded video (pytube): {new_file_path}")
        return new_file_path, title
    except Exception as e:
        logging.error(f"Error downloading video with pytube: {e}")
        return None, None

# Функция для скачивания видео с различных платформ
def download_video_from_source(url: str, source: str) -> str:
    try:
        if source == 'youtube' or source == 'youtube_shorts':
            yt = pytube.YouTube(url)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            filename = stream.download(output_path=config.DOWNLOAD_DIR)
            logging.info(f"Downloaded video from {source}: {filename}")
            return filename
        elif source == 'instagram':
            video_url = get_instagram_video_url(url)
            if video_url:
                file_path = f"{config.DOWNLOAD_DIR}/instagram_video.mp4"
                download_video_file(video_url, file_path)
                return file_path
            else:
                return None
        elif source == 'tiktok':
            file_path = download_tiktok_video(url)
            return file_path
    except Exception as e:
        logging.error(f"Error downloading video from {source}: {e}")
        return None

# Функция для получения URL видео с Instagram
def get_instagram_video_url(instagram_url):
    try:
        browser_manager = BrowserManager()
        browser = browser_manager.get_driver()
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
        browser_manager = BrowserManager()
        browser = browser_manager.get_driver()
        browser.get(tiktok_url)
        time.sleep(10)  # Дать больше времени для загрузки страницы и видео

        # Проверка всех видеоэлементов на странице
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

# Функция для скачивания файла видео по URL
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