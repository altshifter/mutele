# Настройки бота
ADMIN_USER_ID = 'tg_id'
BOT_TOKEN = 'TOKEN'
WEBHOOK_URL = 'https://domain/webhook'
WEB_APP_URL = 'https://domain'

# Настройки баз данных
DATABASE_FILE = 'telemusic.db'
CACHE_DB_FILE = 'cash.db'
PLAYLIST_DB_FILE = 'playlist.db'

# Настройки кеширования
CACHE_LIFETIME = 60*60*24*30*6  # Время жизни кеша в секундах (6 месяцев)

# Настройки скачивания
MAX_RESULTS = 30  # Максимальное количество результатов поиска
MAX_DURATION = 900  # Максимальная продолжительность трека в секундах (15 минут)
DOWNLOAD_DIR = "/home/ubuntu/refinder/"  # Директория для сохранения скачанных файлов

# Настройки утилит
FILE_ROTATE = 50  # Максимальное количество файлов в директории, после которого старые файлы будут удаляться
MAX_TITLE_LENGTH = 40  # Максимальная длина названия трека
DROP_VOWELS = 50  # Процент удаления гласных при сокращении длинных названий

# Настройки VK
VK_ACCESS_TOKEN = 'example'

# Настройки SoundCloud
SOUNDCLOUD_CLIENT_ID = 'example'

# Новая настройка
RESULTS_PAGES = 5  # Количество результатов на странице
