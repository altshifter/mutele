import { createPaginationButton, updatePagination } from './ui.js';

// Инициализация модуля бота
export function initBot() {
    // Получение элементов из DOM
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const downloadVideoButton = document.getElementById("downloadVideoButton");
    const resultsDiv = document.getElementById("results");
    const paginationDiv = document.getElementById("pagination");
    const spinner = document.getElementById("spinner");

    // Инициализация переменных состояния
    let currentPage = 1;
    let resultsPerPage = 5;
    let allResults = [];
    let searchQuery = '';
    let isSearching = false;
    let isDownloading = false;

    // Обработчик изменения ввода в поле поиска
    searchInput.addEventListener("input", function() {
        const url = searchInput.value.trim();
        if (isVideoUrl(url)) {
            searchButton.style.display = isInstagramUrl(url) ? "none" : "block";
            downloadVideoButton.style.display = "block";
        } else {
            searchButton.style.display = "block";
            downloadVideoButton.style.display = "none";
        }
    });

    // Обработчик кнопки поиска
    searchButton.addEventListener("click", function() {
        searchQuery = searchInput.value.trim();
        if (searchQuery && !isSearching && !isDownloading) {
            if (isVideoUrl(searchQuery)) {
                handleRequest('/webapp_download', searchQuery);
            } else {
                handleRequest('/search', searchQuery);
            }
        }
    });

    // Обработчик кнопки скачивания видео
    downloadVideoButton.addEventListener("click", function() {
        searchQuery = searchInput.value.trim();
        if (searchQuery && !isSearching && !isDownloading && isVideoUrl(searchQuery)) {
            disableUserInput();
            showNotification('Видео загружается...');
            fetch('/download_video_direct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: Telegram.WebApp.initDataUnsafe.user.id, url: searchQuery })
            })
            .then(response => response.json())
            .then(data => {
                enableUserInput();
                showNotification(data.success ? 'Видео отправлено.' : 'Не удалось скачать видео.');
            })
            .catch(() => {
                enableUserInput();
                showNotification('Произошла ошибка при скачивании видео.');
            });
        }
    });

    // Проверяет, является ли введенный URL ссылкой на видео
    function isVideoUrl(url) {
        const videoRegex = /^(https?:\/\/)?(www\.)?((youtube|youtu|youtube-nocookie)\.(com|be)|instagram\.com)\/.+$/;
        return videoRegex.test(url);
    }

    // Проверяет, является ли введенный URL ссылкой на Instagram
    function isInstagramUrl(url) {
        const instagramRegex = /^(https?:\/\/)?(www\.)?instagram\.com\/.+$/;
        return instagramRegex.test(url);
    }

    // Обработка запроса к серверу
    function handleRequest(endpoint, query) {
        if (endpoint === '/webapp_download') {
            isDownloading = true;
        } else {
            isSearching = true;
        }

        disableUserInput();
        spinner.style.display = "block";

        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: Telegram.WebApp.initDataUnsafe.user.id, query })
        })
        .then(response => response.json())
        .then(data => {
            spinner.style.display = "none";
            if (endpoint === '/search') {
                processSearchResults(data);
            } else {
                processDownloadResults(data);
            }
            resetState(endpoint);
        })
        .catch(error => {
            showNotification('Произошла ошибка при обработке запроса.');
            resetState(endpoint);
        });
    }

    // Обработка результатов поиска
    function processSearchResults(data) {
        if (data.success) {
            allResults = data.results;
            currentPage = 1;
            displayResults();
        } else {
            showNotification('Произошла ошибка при обработке запроса.');
        }
    }

    // Обработка результатов скачивания
    function processDownloadResults(data) {
        if (data.success) {
            if (data.file_path) {
                sendTrackToChat(data.file_path);
            } else {
                showNotification('Трек загружается...');
            }
        } else {
            showNotification('Не удалось загрузить трек.');
        }
    }

    // Отображение результатов поиска
    function displayResults() {
        resultsDiv.innerHTML = '';
        const startIndex = (currentPage - 1) * resultsPerPage;
        const endIndex = Math.min(startIndex + resultsPerPage, allResults.length);
        const resultsToDisplay = allResults.slice(startIndex, endIndex);

        resultsToDisplay.forEach((result, index) => {
            const item = document.createElement("div");
            item.className = "result-item list-group-item";
            item.textContent = `${result.title} [${formatDuration(result.duration)}]`;
            item.addEventListener("click", () => downloadTrack(result.webpage_url));
            resultsDiv.appendChild(item);
        });

        updatePagination(paginationDiv, currentPage, Math.ceil(allResults.length / resultsPerPage), (page) => {
            currentPage = page;
            displayResults();
        });
    }

    // Форматирование продолжительности трека
    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const sec = seconds % 60;
        return `${minutes}:${sec < 10 ? '0' : ''}${sec}`;
    }

    // Скачивание трека
    function downloadTrack(url) {
        if (isDownloading) {
            showNotification('Файл еще загружается...');
            return;
        }
        isDownloading = true;
        disableUserInput();
        showNotification('Трек загружается...');
        fetch('/webapp_download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: Telegram.WebApp.initDataUnsafe.user.id, query: url })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.file_path) {
                    sendTrackToChat(data.file_path);
                } else {
                    showNotification('Трек загружается...');
                }
            } else {
                showNotification('Не удалось загрузить трек.');
            }
            resetState('/webapp_download');
        })
        .catch(() => {
            showNotification('Произошла ошибка при загрузке трека.');
            resetState('/webapp_download');
        });
    }

    // Отправка трека в чат
    function sendTrackToChat(filePath) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        fetch('/send_track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id, file_path: filePath })
        })
        .then(response => response.json())
        .then(data => {
            showNotification(data.success ? 'Трек отправлен.' : 'Ошибка отправки трека в чат.');
            isDownloading = false;
            enableUserInput();
        })
        .catch(() => {
            showNotification('Ошибка отправки трека в чат.');
            isDownloading = false;
            enableUserInput();
        });
    }

    // Отключение пользовательского ввода
    function disableUserInput() {
        searchButton.disabled = true;
        searchInput.disabled = true;
        downloadVideoButton.disabled = true;
    }

    // Включение пользовательского ввода
    function enableUserInput() {
        searchButton.disabled = false;
        searchInput.disabled = false;
        downloadVideoButton.disabled = false;
        searchButton.textContent = "Поиск";
        searchInput.value = '';
    }

    // Сброс состояния после выполнения запроса
    function resetState(endpoint) {
        if (endpoint === '/webapp_download') {
            isDownloading = false;
        } else {
            isSearching = false;
        }
        enableUserInput();
    }

    // Показ уведомлений
    function showNotification(message) {
        const notificationDiv = document.createElement('div');
        notificationDiv.id = 'notification';
        notificationDiv.className = 'notification';
        notificationDiv.textContent = message;
        document.body.appendChild(notificationDiv);
        setTimeout(() => {
            document.body.removeChild(notificationDiv);
        }, 4000);
    }
}