// Ожидание загрузки всего содержимого DOM перед выполнением кода
document.addEventListener("DOMContentLoaded", function() {
    // Получение элементов DOM и создание необходимых элементов
    const elements = {
        playerButton: document.getElementById("playerButton"), // Кнопка для открытия/закрытия плеера
        playerDiv: document.getElementById("player"), // Контейнер для плеера
        closePlaylistButton: document.getElementById("closePlaylistButton"), // Кнопка для закрытия плейлиста
        playlistUl: document.getElementById("playlist"), // Список для отображения плейлиста
        playlistPaginationDiv: document.getElementById("playlistPagination"), // Контейнер для пагинации плейлиста
        audioPlayer: document.getElementById("audioPlayer"), // Аудиоплеер
        userPlaylistButton: document.getElementById("userPlaylistButton"), // Кнопка для отображения плейлиста пользователя
        userRequestsButton: document.getElementById("userRequestsButton"), // Кнопка для отображения запросов пользователя
        allTracksButton: document.getElementById("allTracksButton"), // Кнопка для отображения всех треков
        userPlaylistDiv: document.getElementById("userPlaylistDiv"), // Контейнер для плейлиста пользователя
        userPlaylistUl: document.getElementById("userPlaylist"), // Список для отображения треков пользователя
        editPlaylistButton: document.getElementById("editPlaylistButton"), // Кнопка для редактирования плейлиста
        savePlaylistButton: document.getElementById("savePlaylistButton"), // Кнопка для сохранения плейлиста
        searchSection: document.querySelector(".search-section"), // Секция поиска
        filterInput: createInputElement("filterInput", "input-field", "Фильтр треков"), // Поле для фильтрации треков
        userPlaylistPaginationDiv: createDivElement("userPlaylistPagination"), // Контейнер для пагинации плейлиста пользователя
        editPlaylistPaginationDiv: createDivElement("editPlaylistPagination"), // Контейнер для пагинации редактируемого плейлиста
        nowPlayingDiv: createDivElement("nowPlaying", "20px", "bold") // Контейнер для отображения текущего воспроизводимого трека
    };

    // Вставка элементов в DOM
    elements.userPlaylistDiv.insertBefore(elements.filterInput, elements.userPlaylistUl);
    elements.userPlaylistDiv.appendChild(elements.userPlaylistPaginationDiv);
    elements.userPlaylistDiv.appendChild(elements.editPlaylistPaginationDiv);
    elements.playerDiv.appendChild(elements.nowPlayingDiv);

    // Состояние приложения
    let state = {
        playlistPage: 1, // Текущая страница плейлиста
        tracksPerPage: 9, // Количество треков на странице
        editTracksPerPage: 9, // Количество треков на странице при редактировании
        allTracks: [], // Все доступные треки для редактирования
        userPlaylist: [], // Плейлист пользователя
        userRequests: [], // Запросы пользователя
        allServerTracks: [], // Все треки на сервере
        userPlaylistPage: 1, // Текущая страница плейлиста пользователя
        editPlaylistPage: 1, // Текущая страница редактируемого плейлиста
        currentTrackIndex: 0, // Индекс текущего воспроизводимого трека
        selectedTracks: new Set(), // Выбранные треки для редактирования
        trackOrder: [], // Порядок треков в редактируемом плейлисте
        currentPlaylist: [], // Текущий плейлист для воспроизведения
        activePlaylist: null, // Активный плейлист
        isEditing: false // Флаг редактирования
    };

    // Обработчики событий для кнопок и элементов
    elements.playerButton.addEventListener("click", togglePlayer); // Переключение видимости плеера
    elements.userPlaylistButton.addEventListener("click", () => togglePlaylist('user_playlist', 'Твой плейлист', 'Закрыть твой плейлист')); // Переключение на плейлист пользователя
    elements.userRequestsButton.addEventListener("click", () => togglePlaylist('user_requests', 'Твои загрузки', 'Закрыть Твои загрузки')); // Переключение на запросы пользователя
    elements.allTracksButton.addEventListener("click", () => togglePlaylist('all_tracks', 'Все треки', 'Закрыть все треки')); // Переключение на все треки
    elements.editPlaylistButton.addEventListener("click", editPlaylist); // Переключение в режим редактирования плейлиста
    elements.savePlaylistButton.addEventListener("click", savePlaylist); // Сохранение плейлиста
    elements.audioPlayer.addEventListener("ended", playNextTrack); // Воспроизведение следующего трека при завершении текущего
    elements.filterInput.addEventListener("input", filterTracksForEdit); // Фильтрация треков при редактировании
    elements.closePlaylistButton.addEventListener("click", closePlaylist); // Закрытие плейлиста

    // Функция для создания элемента ввода
    function createInputElement(id, className, placeholder) {
        const input = document.createElement("input");
        input.id = id;
        input.className = className;
        input.placeholder = placeholder;
        input.style.display = "none";
        input.style.width = "calc(100% - 10px)";
        input.style.maxWidth = "420px";
        return input;
    }

    // Функция для создания элемента div
    function createDivElement(id, marginTop = null, fontWeight = null) {
        const div = document.createElement('div');
        div.id = id;
        if (marginTop) div.style.marginTop = marginTop;
        if (fontWeight) div.style.fontWeight = fontWeight;
        return div;
    }

    // Функция для переключения видимости плеера
    function togglePlayer() {
        if (elements.playerDiv.style.display === "block") {
            elements.playerDiv.style.display = "none";
            elements.searchSection.style.display = "block";
            elements.playerButton.textContent = "Открыть плеер";
            showAllButtons();
        } else {
            loadPlaylist('user_playlist', updateUserPlaylist); // Загрузка плейлиста пользователя при открытии плеера
            elements.playerDiv.style.display = "block";
            elements.searchSection.style.display = "none";
            elements.playerButton.textContent = "Закрыть плеер";
        }
    }

    // Функция для переключения видимости плейлиста
    function togglePlaylist(endpoint, buttonText, closeButtonText) {
        if (state.activePlaylist === endpoint) {
            elements.userPlaylistDiv.style.display = "none";
            elements.closePlaylistButton.style.display = "none";
            elements.playerButton.style.display = "block";
            state.activePlaylist = null;
            state.isEditing = false;
            showAllButtons();
        } else {
            loadPlaylist(endpoint, (tracks) => {
                updateUserPlaylist(tracks); // Обновление плейлиста в интерфейсе
                state.currentPlaylist = tracks; // Обновление текущего плейлиста для воспроизведения
            });
            elements.userPlaylistDiv.style.display = "block";
            elements.closePlaylistButton.style.display = "block";
            elements.playerButton.style.display = "none";
            updateButtonText(buttonText, closeButtonText);
            hideAllButtonsExcept(elements[endpoint + 'Button']);
            state.activePlaylist = endpoint;
            state.isEditing = false;

            if (endpoint === 'user_playlist') {
                elements.editPlaylistButton.style.display = "block";
            } else {
                elements.editPlaylistButton.style.display = "none";
            }
        }
    }

    // Функция для закрытия плейлиста
    function closePlaylist() {
        elements.userPlaylistDiv.style.display = "none";
        elements.closePlaylistButton.style.display = "none";
        elements.playerButton.style.display = "block";
        state.activePlaylist = null;
        state.isEditing = false;
        showAllButtons();
    }

    // Функция для обновления текста кнопок
    function updateButtonText(buttonText, closeButtonText) {
        if (buttonText === 'Твой плейлист') {
            elements.userPlaylistButton.textContent = closeButtonText;
        } else if (buttonText === 'Твои загрузки') {
            elements.userRequestsButton.textContent = closeButtonText;
        } else if (buttonText === 'Все треки') {
            elements.allTracksButton.textContent = closeButtonText;
        }
    }

    // Функция для скрытия всех кнопок, кроме указанной
    function hideAllButtonsExcept(exceptButton) {
        const buttons = [elements.userPlaylistButton, elements.userRequestsButton, elements.allTracksButton, elements.editPlaylistButton, elements.savePlaylistButton, elements.playerButton];
        buttons.forEach(button => {
            if (button !== exceptButton) {
                button.style.display = 'none';
            }
        });
    }

    // Функция для показа всех кнопок
    function showAllButtons() {
        elements.userPlaylistButton.style.display = "block";
        elements.userRequestsButton.style.display = "block";
        elements.allTracksButton.style.display = "block";
        elements.playerButton.style.display = "block";
    }

    // Функция для загрузки плейлиста с сервера
    function loadPlaylist(endpoint, callback) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        fetch(`/${endpoint}?chat_id=${chat_id}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    state.currentPlaylist = data.tracks; // Обновление текущего плейлиста для воспроизведения
                    state.userPlaylistPage = 1;
                    callback(data.tracks); // Вызов функции обратного вызова с полученными треками
                } else {
                    elements.userPlaylistUl.innerHTML = `<li>${endpoint === 'user_playlist' ? 'Плейлист не найден.' : 'Запросы не найдены.'}</li>`;
                }
            })
            .catch(() => {
                elements.userPlaylistUl.innerHTML = `<li>Ошибка загрузки ${endpoint === 'user_playlist' ? 'плейлиста' : 'запросов'}.</li>`;
            });
    }

    // Функция для обновления плейлиста пользователя в интерфейсе
    function updateUserPlaylist(tracks) {
        displayPlaylist(tracks); // Отображение треков плейлиста
    }

    // Функция для отображения плейлиста
    function displayPlaylist(tracks) {
        elements.userPlaylistUl.innerHTML = '';

        if (tracks.length === 0) {
            elements.userPlaylistUl.innerHTML = '<li>Треки не найдены.</li>';
            return;
        }

        const startIndex = (state.userPlaylistPage - 1) * state.tracksPerPage;
        const endIndex = Math.min(startIndex + state.tracksPerPage, tracks.length);
        const tracksToDisplay = tracks.slice(startIndex, endIndex);

        tracksToDisplay.forEach((track, index) => {
            const item = createTrackListItem(track, startIndex, index); // Создание элемента списка треков
            elements.userPlaylistUl.appendChild(item);
        });

        updatePagination(tracks); // Обновление пагинации плейлиста

        if (state.activePlaylist === 'user_playlist') {
            elements.editPlaylistButton.style.display = "block";
        } else {
            elements.editPlaylistButton.style.display = "none";
        }
    }

    // Функция для создания элемента списка треков
    function createTrackListItem(track, startIndex, index) {
        const item = document.createElement("li");
        const playIcon = createIconElement("/static/img/play.svg", "play-icon");
        const downloadIcon = createIconElement("/static/img/down.svg", "download-icon");

        item.textContent = track.title;
        item.classList.add("track-item");

        item.addEventListener("click", () => {
            state.currentTrackIndex = startIndex + index;
            playTrack(); // Воспроизведение трека при клике
        });

        downloadIcon.addEventListener("click", (event) => {
            event.stopPropagation();
            sendTrackToChat(track); // Отправка трека в чат при клике на иконку загрузки
        });

        const iconsDiv = document.createElement("div");
        iconsDiv.style.display = "flex";
        iconsDiv.style.marginLeft = "auto";
        iconsDiv.appendChild(playIcon);
        iconsDiv.appendChild(downloadIcon);

        item.prepend(playIcon);
        item.appendChild(iconsDiv);
        return item;
    }

    // Функция для создания элемента иконки
    function createIconElement(src, className) {
        const icon = document.createElement("img");
        icon.src = src;
        icon.classList.add(className);
        return icon;
    }

    // Функция для обновления пагинации
    function updatePagination(tracks) {
        const paginationDiv = elements.userPlaylistPaginationDiv;
        paginationDiv.innerHTML = '';
        paginationDiv.style.display = "flex";
        paginationDiv.style.justifyContent = "center";

        const totalPages = Math.ceil(tracks.length / state.tracksPerPage);

        const prevButton = createPaginationButton('<<', state.userPlaylistPage === 1, () => {
            state.userPlaylistPage--;
            displayPlaylist(tracks); // Отображение предыдущей страницы треков
        });

        const nextButton = createPaginationButton('>>', state.userPlaylistPage === totalPages, () => {
            state.userPlaylistPage++;
            displayPlaylist(tracks); // Отображение следующей страницы треков
        });

        if (totalPages > 1) {
            paginationDiv.appendChild(prevButton);
            paginationDiv.appendChild(nextButton);
        }
    }

    // Функция для создания кнопки пагинации
    function createPaginationButton(text, disabled, clickHandler) {
        const button = document.createElement('button');
        button.textContent = text;
        button.className = 'pagination-button';
        button.disabled = disabled;
        button.addEventListener('click', clickHandler);
        return button;
    }

    // Функция для воспроизведения трека
    function playTrack() {
        const track = state.currentPlaylist[state.currentTrackIndex];
        let relativePath;

        // Проверка, из какого плейлиста воспроизводится трек
        if (state.activePlaylist === 'user_playlist') {
            relativePath = track.path.replace('/home/ubuntu/refinder/', ''); // Преобразование полного пути в относительный для пользовательского плейлиста
        } else {
            relativePath = track.file_path.replace('/home/ubuntu/refinder/', ''); // Преобразование полного пути в относительный для остальных плейлистов
        }

        const encodedPath = encodeURIComponent(relativePath).replace(/%20/g, ' '); // Кодирование пути для URL
        elements.audioPlayer.src = `/tracks/${encodedPath}`;
        elements.audioPlayer.play();
        elements.nowPlayingDiv.textContent = `Сейчас играет: ${track.title}`;
    }

    // Функция для воспроизведения следующего трека
    function playNextTrack() {
        if (state.currentTrackIndex < state.currentPlaylist.length - 1) {
            state.currentTrackIndex++;
            playTrack();
        } else {
            elements.nowPlayingDiv.textContent = 'Воспроизведение завершено';
        }
    }

    // Функция для загрузки всех треков для редактирования
    function loadAllTracksForEdit() {
        fetch('/tracks')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    state.allTracks = data.tracks; // Загрузка всех треков
                    state.editPlaylistPage = 1;
                    filterTracksForEdit(); // Фильтрация треков для редактирования
                } else {
                    elements.userPlaylistUl.innerHTML = '<li>Треки не найдены.</li>';
                }
            })
            .catch(() => {
                elements.userPlaylistUl.innerHTML = '<li>Ошибка загрузки треков.</li>';
            });
    }

    // Функция для отображения треков для редактирования
    function displayTracksForEdit() {
        const filter = elements.filterInput.value.toLowerCase();
        const filteredTracks = state.allTracks.filter(track => track.title.toLowerCase().includes(filter));

        elements.userPlaylistUl.innerHTML = '';
        const startIndex = (state.editPlaylistPage - 1) * state.editTracksPerPage;
        const endIndex = Math.min(startIndex + state.editTracksPerPage, filteredTracks.length);
        const tracksToDisplay = filteredTracks.slice(startIndex, endIndex);

        state.trackOrder = Array.from(state.selectedTracks);

        tracksToDisplay.forEach(track => {
            const item = document.createElement("li");
            const checkbox = createCheckbox(track);

            const checkboxLabel = document.createElement("label");
            const trackNumber = state.trackOrder.indexOf(track.file_path) + 1;
            checkboxLabel.textContent = checkbox.checked ? `${trackNumber}. ${track.title}` : `${track.title}`;
            checkboxLabel.prepend(checkbox);

            item.appendChild(checkboxLabel);
            elements.userPlaylistUl.appendChild(item);
        });

        updateEditPlaylistPagination(filteredTracks);
        elements.filterInput.style.display = "block";
        elements.editPlaylistButton.style.display = "none";
        elements.savePlaylistButton.style.display = "block";
    }

    // Функция для создания чекбокса для треков
    function createCheckbox(track) {
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = track.file_path;
        checkbox.checked = state.selectedTracks.has(track.file_path);

        checkbox.addEventListener("change", () => {
            if (checkbox.checked) {
                state.selectedTracks.add(track.file_path);
                state.trackOrder.push(track.file_path);
            } else {
                state.selectedTracks.delete(track.file_path);
                state.trackOrder = state.trackOrder.filter(path => path !== track.file_path);
            }
            displayTracksForEdit();
        });
        return checkbox;
    }

    // Функция для отправки трека в чат
    function sendTrackToChat(track) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        let filePath;

        // Проверка, из какого плейлиста отправляется трек
        if (state.activePlaylist === 'user_playlist') {
            filePath = track.path; // Использовать track.path для плейлиста "Твой плейлист"
        } else {
            filePath = track.file_path; // Использовать track.file_path для остальных плейлистов
        }

        fetch('/send_track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id, file_path: filePath })
        })
        .then(response => response.json())
        .catch(() => {});
    }

    // Функция для обновления пагинации редактируемого плейлиста
    function updateEditPlaylistPagination(tracks) {
        const paginationDiv = elements.editPlaylistPaginationDiv;
        paginationDiv.innerHTML = '';
        paginationDiv.style.display = "flex";
        paginationDiv.style.justifyContent = "center";

        const totalPages = Math.ceil(tracks.length / state.editTracksPerPage);

        const prevButton = createPaginationButton('<<', state.editPlaylistPage === 1, () => {
            state.editPlaylistPage--;
            displayTracksForEdit();
        });

        const nextButton = createPaginationButton('>>', state.editPlaylistPage === totalPages, () => {
            state.editPlaylistPage++;
            displayTracksForEdit();
        });

        if (totalPages > 1) {
            paginationDiv.appendChild(prevButton);
            paginationDiv.appendChild(nextButton);
        }
    }

    // Функция для сохранения плейлиста
    function savePlaylist() {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        const selectedTrackList = Array.from(state.selectedTracks).map(filePath => {
            const track = state.allTracks.find(track => track.file_path === filePath);
            return { title: track.title, path: track.file_path };
        });

        fetch('/save_playlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id, tracks: selectedTrackList })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                state.selectedTracks.clear();
                state.trackOrder = [];
                loadPlaylist('user_playlist', () => {
                    updateUserPlaylist(selectedTrackList);
                    state.currentPlaylist = selectedTrackList;
                });
                elements.editPlaylistButton.style.display = "block";
                elements.savePlaylistButton.style.display = "none";
                elements.filterInput.style.display = "none";
                elements.editPlaylistPaginationDiv.style.display = "none";
                elements.playerButton.style.display = "block";
                state.isEditing = false;
            }
        })
        .catch(() => {});
    }

    // Функция для фильтрации треков при редактировании
    function filterTracksForEdit() {
        displayTracksForEdit();
    }

    // Функция для редактирования плейлиста
    function editPlaylist() {
        state.isEditing = true;
        loadAllTracksForEdit();
        elements.editPlaylistButton.style.display = "none";
        elements.savePlaylistButton.style.display = "block";
    }
});