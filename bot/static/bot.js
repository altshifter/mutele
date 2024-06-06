document.addEventListener("DOMContentLoaded", function() {
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const resultsDiv = document.getElementById("results");
    const paginationDiv = document.getElementById("pagination");
    const spinner = document.getElementById("spinner");

    // Добавление новой кнопки "Скачать видео"
    const downloadVideoButton = document.createElement("button");
    downloadVideoButton.className = "button";
    downloadVideoButton.style.display = "none";
    downloadVideoButton.textContent = "Скачать видео";
    searchButton.parentNode.insertBefore(downloadVideoButton, searchButton.nextSibling);

    // Инициализация переменных состояния
    let currentPage = 1;
    let resultsPerPage = 5;
    let allResults = [];
    let searchQuery = '';
    let isSearching = false;
    let isDownloading = false;

    // Обработчик ввода текста в поле поиска
    searchInput.addEventListener("input", function() {
        if (isVideoUrl(searchInput.value.trim())) {
            const url = searchInput.value.trim();
            if (isInstagramUrl(url)) {
                searchButton.style.display = "none";
            } else {
                searchButton.textContent = "Скачать аудио";
                searchButton.style.display = "block";
            }
            downloadVideoButton.style.display = "block";
        } else {
            searchButton.textContent = "Поиск";
            searchButton.style.display = "block";
            downloadVideoButton.style.display = "none";
        }
    });

    // Обработчик нажатия на кнопку поиска
    searchButton.addEventListener("click", function() {
        searchQuery = searchInput.value.trim();
        if (searchQuery && !isSearching && !isDownloading) {
            if (isVideoUrl(searchQuery)) {
                handleRequest('/download', searchQuery);
            } else {
                handleRequest('/search', searchQuery);
            }
        }
    });

    // Обработчик нажатия на кнопку скачивания видео
    downloadVideoButton.addEventListener("click", function() {
        searchQuery = searchInput.value.trim();
        if (searchQuery && !isSearching && !isDownloading && isVideoUrl(searchQuery)) {
            disableUserInput();
            showNotification('Видео загружается...');
            fetch('/download_video_direct', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    chat_id: Telegram.WebApp.initDataUnsafe.user.id,
                    url: searchQuery
                })
            })
            .then(response => response.json())
            .then(data => {
                enableUserInput();
                if (data.success) {
                    showNotification('Видео отправлено.');
                } else {
                    showNotification('Не удалось скачать видео.');
                }
            })
            .catch(() => {
                enableUserInput();
                showNotification('Произошла ошибка при скачивании видео.');
            });
        }
    });

    // Функция для проверки, является ли URL видео
    function isVideoUrl(url) {
        const videoRegex = /^(https?:\/\/)?(www\.)?((youtube|youtu|youtube-nocookie)\.(com|be)|instagram\.com)\/.+$/;
        return videoRegex.test(url);
    }

    // Функция для проверки, является ли URL Instagram
    function isInstagramUrl(url) {
        const instagramRegex = /^(https?:\/\/)?(www\.)?instagram\.com\/.+$/;
        return instagramRegex.test(url);
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

    // Выполнение запроса к серверу
    function handleRequest(endpoint, query) {
        if (endpoint === '/download') {
            isDownloading = true;
        } else {
            isSearching = true;
        }

        disableUserInput();
        spinner.style.display = "block";

        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: Telegram.WebApp.initDataUnsafe.user.id,
                query: query
            })
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
            showNotification('Error occurred: ' + error);
            showNotification('Произошла ошибка при обработке запроса.');
            resetState(endpoint);
        });
    }

    // Функция для получения доступных качеств видео
    function fetchVideoQualities(query) {
        disableUserInput();
        spinner.style.display = "block";

        fetch('/video_info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: query
            })
        })
        .then(response => response.json())
        .then(data => {
            spinner.style.display = "none";
            if (data.success) {
                displayVideoQualities(data.qualities);
            } else {
                showNotification('Не удалось получить информацию о видео.');
                enableUserInput();
            }
        })
        .catch(() => {
            showNotification('Произошла ошибка при получении информации о видео.');
            enableUserInput();
        });
    }

    // Отображение доступных качеств видео
    function displayVideoQualities(qualities) {
        resultsDiv.innerHTML = '';
        qualities.forEach((quality, index) => {
            const button = document.createElement("button");
            button.className = "button";
            button.textContent = quality;
            button.addEventListener("click", () => downloadVideo(quality));
            resultsDiv.appendChild(button);
        });
    }

    // Скачивание видео выбранного качества
    function downloadVideo(quality) {
        disableUserInput();
        spinner.style.display = "block";

        fetch('/download_video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: Telegram.WebApp.initDataUnsafe.user.id,
                url: searchQuery,
                quality: quality
            })
        })
        .then(response => response.json())
        .then(data => {
            spinner.style.display = "none";
            if (data.success) {
                sendTrackToChat(data.file_path);
            } else {
                showNotification('Не удалось скачать видео.');
            }
            enableUserInput();
        })
        .catch(() => {
            showNotification('Произошла ошибка при скачивании видео.');
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

    // Сброс состояния поиска и скачивания
    function resetState(endpoint) {
        if (endpoint === '/download') {
            isDownloading = false;
        } else {
            isSearching = false;
        }
        enableUserInput();
    }

    // Отображение результатов поиска
    function displayResults() {
        resultsDiv.innerHTML = '';
        const startIndex = (currentPage - 1) * resultsPerPage;
        const endIndex = Math.min(startIndex + resultsPerPage, allResults.length);
        const resultsToDisplay = allResults.slice(startIndex, endIndex);

        resultsToDisplay.forEach((result, index) => {
            const item = document.createElement("div");
            item.className = "result-item";
            item.textContent = `${result.title} [${formatDuration(result.duration)}]`;
            item.addEventListener("click", () => downloadTrack(result.webpage_url));
            resultsDiv.appendChild(item);
        });

        updatePagination();
    }

    // Обновление пагинации
    function updatePagination() {
        paginationDiv.innerHTML = '';

        const totalPages = Math.ceil(allResults.length / resultsPerPage);

        const prevButton = createPaginationButton('<<', currentPage === 1, () => {
            currentPage--;
            displayResults();
        });

        const nextButton = createPaginationButton('>>', currentPage === totalPages, () => {
            currentPage++;
            displayResults();
        });

        paginationDiv.appendChild(prevButton);
        paginationDiv.appendChild(nextButton);
    }

    // Создание кнопки пагинации
    function createPaginationButton(text, disabled, clickHandler) {
        const button = document.createElement('button');
        button.textContent = text;
        button.className = 'pagination-button';
        button.disabled = disabled;
        button.addEventListener('click', clickHandler);
        return button;
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
        fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: Telegram.WebApp.initDataUnsafe.user.id,
                query: url
            })
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
            resetState('/download');
        })
        .catch(() => {
            showNotification('Произошла ошибка при загрузке трека.');
            resetState('/download');
        });
    }

    // Отправка трека в чат
    function sendTrackToChat(filePath) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;

        fetch('/send_track', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: chat_id,
                file_path: filePath
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Трек отправлен.');
            } else {
                showNotification('Ошибка отправки трека в чат.');
            }
        })
        .catch(() => {
            showNotification('Ошибка отправки трека в чат.');
        });
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
        }, 4000);  // Увеличиваем время показа уведомления до 4 секунд
    }
});