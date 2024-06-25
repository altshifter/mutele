# Mutele
**Music Telegram Bot**  
*(REfinder on steroids)*

Мьютель - телеграм бот для поиска и загрузки музыки из (пока что только) YouTube, с плеером скачанной музыки через веб-приложение.

## Основные функции

### Inline режим (в чате Телеграм):
- **Поиск по ключевым словам**: Бот выдаст список треков, при выборе трека он отправляется в чат в формате MP3.
- **Отправка по прямой ссылке**: При отправке ссылки на YouTube видео, бот запрашивает  аудио или видео. Аудио - отправляет в чат. Видео - отправляет видео по ссылке в чат.
- **Отправка youtube shorts**
- **Отправка instagram reels** - пока сломано

### Режим Web App:
- **Поиск**: Повторяет функционал inline режима.
- **Музыкальный плеер**: Возможность составить собственный плейлист и доступ к двум встроенным плейлистам (треков, скачанных пользователем и всех треков на сервере).

---

# Mutele
**Music Telegram Bot**  
*(REfinder on steroids)*

Search, download, and send MP3s from YouTube + music player (web app)

## Features

### Inline Mode:
- **Search from keywords**: Show results based on keywords; clicking a result downloads, and sends the MP3.
- **Search from YouTube URL**: Enter a YouTube URL, and the bot will download, convert, and send the MP3.

### Web Mode:
- **Search**: Mirrors the inline mode functionality.
- **Music Player**: Includes a custom playlist feature and two built-in playlists (user's downloaded tracks and all tracks on the server).




структура проекта: 
bot/
├── main.py
├── downloader.py
├── db.py
├── utils.py
├── cache.py
├── browser.py
├── telemusic.db
├── cash.db
├── playlist.db
├── config.py
├── templates/
│	└── index.html
└───static/
	├── player.js
	├── bot.js
	├── style.css
	├── main.js
	├── ui.js
	└── img/
		├── play.svg
		└── down.svg

описание файлов, серверная часть:
main.py - основное тело бота, там распологаются все вызовы, диалоги, кнопки и flask маршруты.
downloader.py - модуль где располагаются скрипты работы с pytube и запросы к selenium.
db.py - модуль для работы с базой данных. инициализация, запись, выгрузка итд
utils.py - модуль для вспомогательных функций, например проверки ссылок, санитаризация итд.
cache.py - модуль кеширования, там хранится кеш поиска, для избежания повторов поиска.
browser.py - модуль содержащий параметры selenium для запуска браузера.
config.py - модуль содержащий все глобальные переменные, токен бота, пути файлов, и остальные изменяемые параметры.
telemusic.db - файл бд где хранится информация о пользователях, поисках, и скачанных файлов.
cash.db - файл бд кеша поиска музыки.

описание файлов, веб часть:
playlist.db - файл бд пользовательского плейлиста.
index.html - основная страница, запускает модули js и отображается в telegram web app.
player.js - модуль плеера, содержит плейлисты и сам плеер, служит для воспроизведения треков из web app.
bot.js - модуль поиска, транслирует запросы из web части в бекграунд, возвращает результат.
style.css - стили веб части проекта.
main.js - содержит запускаемые модули js.
ui.js - эффекты для js. (возможно надо ликвидировать).
play.svg - иконка воспроизведения.
down.svg - иконка загрузки.

