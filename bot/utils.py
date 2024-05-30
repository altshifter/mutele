import os
import re
import logging
import config

# Функция для ротации файлов в директории, чтобы не превышать заданное количество файлов
def rotate_files(directory, max_files=config.FILE_ROTATE):  # Используем максимальное количество файлов из конфигурационного файла
    files = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.mp3')]
    while len(files) > max_files:
        oldest_file = min(files, key=os.path.getctime)
        os.remove(oldest_file)
        files.remove(oldest_file)
        logging.info(f'Удален старый файл: {oldest_file}')

# Функция для безопасного создания имени файла (без недопустимых символов)
def safe_filename(filename):
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    safe_filename = re.sub(r'\s+', " ", safe_filename).strip()
    return safe_filename

# Функция для проверки, является ли URL ссылкой на YouTube
def is_youtube_url(url):
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/.+$'
    )
    return youtube_regex.match(url) is not None

# Функция для очистки текста от недопустимых символов
def sanitize(text):
    return re.sub(r'[^\w\s]', '', text).strip()

# Функция для форматирования продолжительности в секундах в формат "MM:SS"
def format_duration(seconds):
    minutes, sec = divmod(seconds, 60)
    return f"{minutes:02d}:{sec:02d}"

# Функция для сокращения или сжатия длинного заголовка до допустимой длины
def trim_or_compress_title(title, max_length=config.MAX_TITLE_LENGTH):  # Используем максимальную длину заголовка из конфигурационного файла
    if len(title) <= max_length:
        return title
    vowels = 'aeiouAEIOUаеёиоуыэюя'
    words = title.split()
    new_words = []
    for word in words:
        if len(word) <= 4:
            new_words.append(word)
            continue
        num_vowels_to_compress = len([c for c in word[1:-1] if c in vowels]) * config.DROP_VOWELS // 100  # Используем процент удаления гласных из конфигурационного файла
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
    return ' '.join(new_words)[:max_length-3] + '...'

# Функция для получения пути к существующему файлу по URL
def get_existing_file_path(url):
    filename = safe_filename(url.split('/')[-1]) + '.mp3'
    file_path = os.path.join(config.DOWNLOAD_DIR, filename)  # Используем директорию загрузок из конфигурационного файла
    if os.path.exists(file_path):
        logging.info(f"File {file_path} already exists on server.")
        return file_path, filename
    return None, None
