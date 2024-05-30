document.addEventListener("DOMContentLoaded", function() {
    // Получаем элементы DOM
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const resultsDiv = document.getElementById("results");
    const paginationDiv = document.getElementById("pagination");
    const spinner = document.getElementById("spinner");

    // Переменные для управления состоянием поиска и загрузки
    let currentPage = 1;
    let resultsPerPage = 5;
    let allResults = [];
    let searchQuery = '';
    let isSearching = false;
    let isDownloading = false;

    // Событие ввода в поле поиска для изменения текста кнопки
    searchInput.addEventListener("input", function() {
        if (isYouTubeUrl(searchInput.value.trim())) {
            searchButton.textContent = "Скачать";
        } else {
            searchButton.textContent = "Поиск";
        }
    });

    // Событие нажатия кнопки поиска
    searchButton.addEventListener("click", function() {
        searchQuery = searchInput.value.trim();
        if (searchQuery && !isSearching) {
            if (isYouTubeUrl(searchQuery)) {
                downloadYouTube(searchQuery);
            } else {
                searchMusic(searchQuery);
            }
        }
    });

    // Функция для проверки, является ли URL ссылкой на YouTube
    function isYouTubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/.+$/;
        return youtubeRegex.test(url);
    }

    // Функция для поиска музыки по запросу
    function searchMusic(query) {
        isSearching = true;
        searchButton.disabled = true;
        searchInput.disabled = true;
        searchButton.textContent = "Поиск...";
        spinner.style.display = "block";

        fetch('/search', {
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
            if (data.success) {
                allResults = data.results;
                currentPage = 1;
                displayResults();
            } else {
                showNotification('Произошла ошибка при обработке запроса.');
            }
            isSearching = false;
            searchButton.disabled = false;
            searchInput.disabled = false;
        })
        .catch(error => {
            console.error('Ошибка:', error);
            showNotification('Произошла ошибка при обработке запроса.');
            isSearching = false;
            searchButton.disabled = false;
            searchInput.disabled = false;
        });
    }

    // Функция для загрузки и конвертации YouTube видео
    function downloadYouTube(url) {
        isSearching = true;
        searchButton.disabled = true;
        searchInput.disabled = true;
        searchButton.textContent = "Поиск...";
        spinner.style.display = "block";

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
            spinner.style.display = "none";
            if (data.success) {
                if (data.file_path) {
                    sendTrackToChat(data.file_path);
                } else {
                    showNotification('Трек загружается...');
                }
            } else {
                showNotification('Не удалось загрузить трек.');
            }
            resetSearchState();
        })
        .catch(error => {
            console.error('Ошибка:', error);
            showNotification('Произошла ошибка при загрузке трека.');
            resetSearchState();
        });

        // Показ уведомления через 10 секунд
        setTimeout(() => {
            showNotification('Трек загружается');
            resetSearchState();
            isDownloading = false;
        }, 10000);
    }

    // Функция для сброса состояния поиска
    function resetSearchState() {
        isSearching = false;
        searchButton.disabled = false;
        searchInput.disabled = false;
        searchButton.textContent = "Поиск";
        searchInput.value = ''; // Очистка поля ввода
    }

    // Функция для отображения результатов поиска
    function displayResults() {
        resultsDiv.innerHTML = '';
        const startIndex = (currentPage - 1) * resultsPerPage;
        const endIndex = Math.min(startIndex + resultsPerPage, allResults.length);
        const resultsToDisplay = allResults.slice(startIndex, endIndex);

        resultsToDisplay.forEach((result, index) => {
            const item = document.createElement("div");
            item.className = "result-item";
            item.textContent = `${result.title} [${formatDuration(result.duration)}]`;
            item.addEventListener("click", () => downloadTrack(startIndex + index));
            resultsDiv.appendChild(item);
        });

        updatePagination();
    }

    // Функция для обновления пагинации
    function updatePagination() {
        paginationDiv.innerHTML = '';

        const totalPages = Math.ceil(allResults.length / resultsPerPage);

        const prevButton = document.createElement('button');
        prevButton.textContent = 'Предыдущая';
        prevButton.disabled = currentPage === 1;
        prevButton.addEventListener('click', () => {
            currentPage--;
            displayResults();
        });

        const nextButton = document.createElement('button');
        nextButton.textContent = 'Следующая';
        nextButton.disabled = currentPage === totalPages;
        nextButton.addEventListener('click', () => {
            currentPage++;
            displayResults();
        });

        paginationDiv.appendChild(prevButton);
        paginationDiv.appendChild(nextButton);
    }

    // Функция для форматирования продолжительности в секундах в формат "MM:SS"
    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const sec = seconds % 60;
        return `${minutes}:${sec < 10 ? '0' : ''}${sec}`;
    }

    // Функция для загрузки трека
    function downloadTrack(index) {
        if (isDownloading) {
            showNotification('Файл еще загружается...');
            return;
        }
        isDownloading = true;
        fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: Telegram.WebApp.initDataUnsafe.user.id,
                track_index: index
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
            isDownloading = false;
        })
        .catch(error => {
            console.error('Ошибка:', error);
            showNotification('Произошла ошибка при загрузке трека.');
            isDownloading = false;
        });

        // Показ уведомления через 10 секунд
        setTimeout(() => {
            showNotification('Трек загружается');
            resetSearchState();
            isDownloading = false;
        }, 10000);
    }

    // Функция для отправки трека в чат
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
                console.log('Трек отправлен в чат');
            } else {
                console.error('Ошибка отправки трека в чат:', data.message);
            }
        })
        .catch(error => {
            console.error('Ошибка отправки трека в чат:', error);
        });
    }

    // Функция для показа уведомлений
    function showNotification(message) {
        const notificationDiv = document.createElement('div');
        notificationDiv.id = 'notification';
        notificationDiv.style.position = 'fixed';
        notificationDiv.style.bottom = '20px';
        notificationDiv.style.right = '20px';
        notificationDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        notificationDiv.style.color = 'white';
        notificationDiv.style.padding = '10px';
        notificationDiv.style.borderRadius = '5px';
        notificationDiv.textContent = message;
        document.body.appendChild(notificationDiv);
        setTimeout(() => {
            document.body.removeChild(notificationDiv);
        }, 3000);
    }
});
