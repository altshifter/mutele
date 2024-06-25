import os
import re
import logging
import config

# Функция для удаления старых файлов в директории, если их количество превышает лимит
def rotate_files(directory, max_files=config.FILE_ROTATE):
    # Получаем список файлов в директории с расширением .mp3
    files = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.mp3')]
    # Удаляем файлы до тех пор, пока их количество не станет меньше или равно max_files
    while len(files) > max_files:
        oldest_file = min(files, key=os.path.getctime)  # Находим самый старый файл
        os.remove(oldest_file)  # Удаляем самый старый файл
        files.remove(oldest_file)
        logging.info(f'Удален старый файл: {oldest_file}')

# Функция для безопасного формирования имени файла
def safe_filename(filename):
    # Заменяем недопустимые символы пустой строкой и убираем лишние пробелы
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    safe_filename = re.sub(r'\s+', " ", safe_filename).strip()
    return safe_filename

# Функция для очистки URL от дополнительных параметров и определения типа URL
def parse_and_clean_url(url):
    url = url.split('&')[0]  # Удаление дополнительных параметров после знака "&"
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie|music\.youtube)\.(com|be)/.+$'
    )
    # Проверяем, соответствует ли URL шаблону YouTube
    if youtube_regex.match(url):
        if 'music.youtube' in url:
            return 'youtube_music', url
        elif 'youtube.com/shorts' in url or 'youtu.be' in url and '/shorts' in url:
            return 'youtube_shorts', url
        else:
            return 'youtube', url
    elif 'instagram' in url:
        return 'instagram', url
    elif 'tiktok' in url:
        return 'tiktok', url
    return None, url

# Функция для очистки текста от недопустимых символов
def sanitize(text):
    return re.sub(r'[^\w\s]', '', text).strip()

# Функция для форматирования продолжительности в секундах в формат "мм:сс"
def format_duration(seconds):
    minutes, sec = divmod(seconds, 60)
    return f"{minutes:02d}:{sec:02d}"

# Функция для проверки, существует ли файл по указанному URL
def get_existing_file_path(url):
    filename = safe_filename(url.split('/')[-1]) + '.mp3'
    file_path = os.path.join(config.DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        logging.info(f"File {file_path} already exists on server.")
        return file_path, filename
    return None, None

# Функция для сокращения или сжатия длинного заголовка до допустимой длины
def trim_or_compress_title(title, max_length=config.MAX_TITLE_LENGTH):
    if len(title) <= max_length:
        return title
    vowels = 'aeiouAEIOUаеёиоуыэюя'
    words = title.split()
    new_words = []
    for word in words:
        if len(word) <= 4:
            new_words.append(word)
            continue
        # Удаляем гласные из середины слова, если слово длинное
        num_vowels_to_compress = len([c for c in word[1:-1] if c in vowels]) * config.DROP_VOWELS // 100
        compressed_word = []
        vowels_count = 0
        compressed_word.append(word[0])
        for char in word[1:-1]:
            if vowels_count < num_vowels_to_compress and char in vowels:
                vowels_count += 1
                continue
            compressed_word.append(char)
        compressed_word.append(word[-1])
        new_words.append(''.join(compressed_word))
    return ' '.join(new_words)[:max_length-3] + '...'  # Возвращаем сокращенный заголовок