import { createPaginationButton, updatePagination } from './ui.js';

// Инициализация модуля плеера
export function initPlayer() {
    const elements = {
        playerButton: document.getElementById("playerButton"),
        playerDiv: document.getElementById("player"),
        closePlaylistButton: document.getElementById("closePlaylistButton"),
        playlistUl: document.getElementById("playlist"),
        playlistPaginationDiv: document.getElementById("playlistPagination"),
        audioPlayer: document.getElementById("audioPlayer"),
        userPlaylistButton: document.getElementById("userPlaylistButton"),
        userRequestsButton: document.getElementById("userRequestsButton"),
        allTracksButton: document.getElementById("allTracksButton"),
        userPlaylistDiv: document.getElementById("userPlaylistDiv"),
        userPlaylistUl: document.getElementById("userPlaylist"),
        editPlaylistButton: document.getElementById("editPlaylistButton"),
        savePlaylistButton: document.getElementById("savePlaylistButton"),
        searchSection: document.querySelector(".search-section"),
        filterInput: createInputElement("filterInput", "form-control", "Фильтр треков"),
        userPlaylistPaginationDiv: createDivElement("userPlaylistPagination"),
        editPlaylistPaginationDiv: createDivElement("editPlaylistPagination"),
        nowPlayingDiv: createDivElement("nowPlaying", "20px", "bold")
    };

    // Вставляем элементы в DOM
    elements.userPlaylistDiv.insertBefore(elements.filterInput, elements.userPlaylistUl);
    elements.userPlaylistDiv.appendChild(elements.userPlaylistPaginationDiv);
    elements.userPlaylistDiv.appendChild(elements.editPlaylistPaginationDiv);
    elements.playerDiv.appendChild(elements.nowPlayingDiv);

    let state = {
        playlistPage: 1,
        tracksPerPage: 9,
        editTracksPerPage: 9,
        allTracks: [],
        userPlaylist: [],
        userRequests: [],
        allServerTracks: [],
        userPlaylistPage: 1,
        editPlaylistPage: 1,
        currentTrackIndex: 0,
        selectedTracks: new Set(),
        trackOrder: [],
        currentPlaylist: [],
        activePlaylist: null,
        isEditing: false
    };

    // Добавляем обработчики событий
    elements.playerButton.addEventListener("click", togglePlayer);
    elements.userPlaylistButton.addEventListener("click", () => togglePlaylist('user_playlist', 'Твой плейлист', 'Твой плейлист'));
    elements.userRequestsButton.addEventListener("click", () => togglePlaylist('user_requests', 'Твои загрузки', 'Твои загрузки'));
    elements.allTracksButton.addEventListener("click", () => togglePlaylist('all_tracks', 'Все треки', 'Все треки'));
    elements.editPlaylistButton.addEventListener("click", editPlaylist);
    elements.savePlaylistButton.addEventListener("click", savePlaylist);
    elements.audioPlayer.addEventListener("ended", playNextTrack);
    elements.filterInput.addEventListener("input", filterTracksForEdit);
    elements.closePlaylistButton.addEventListener("click", closePlaylist);

    // Создание элемента ввода
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

    // Создание элемента div
    function createDivElement(id, marginTop = null, fontWeight = null) {
        const div = document.createElement('div');
        div.id = id;
        if (marginTop) div.style.marginTop = marginTop;
        if (fontWeight) div.style.fontWeight = fontWeight;
        return div;
    }

    // Переключение видимости плеера
    function togglePlayer() {
        if (elements.playerDiv.style.display === "block") {
            elements.playerDiv.style.display = "none";
            elements.searchSection.style.display = "block";
            elements.playerButton.textContent = "Открыть плеер";
            showAllButtons();
        } else {
            loadPlaylist('user_playlist', updateUserPlaylist);
            elements.playerDiv.style.display = "block";
            elements.searchSection.style.display = "none";
            elements.playerButton.textContent = "Закрыть плеер";
        }
    }

    // Переключение видимости плейлиста
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
                updateUserPlaylist(tracks);
                state.currentPlaylist = tracks;
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

    // Закрытие плейлиста
    function closePlaylist() {
        elements.userPlaylistDiv.style.display = "none";
        elements.closePlaylistButton.style.display = "none";
        elements.playerButton.style.display = "block";
        state.activePlaylist = null;
        state.isEditing = false;
        showAllButtons();
    }

    // Обновление текста кнопок
    function updateButtonText(buttonText, closeButtonText) {
        if (buttonText === 'Твой плейлист') {
            elements.userPlaylistButton.textContent = closeButtonText;
        } else if (buttonText === 'Твои загрузки') {
            elements.userRequestsButton.textContent = closeButtonText;
        } else if (buttonText === 'Все треки') {
            elements.allTracksButton.textContent = closeButtonText;
        }
    }

    // Скрытие всех кнопок, кроме указанной
    function hideAllButtonsExcept(exceptButton) {
        const buttons = [elements.userPlaylistButton, elements.userRequestsButton, elements.allTracksButton, elements.editPlaylistButton, elements.savePlaylistButton, elements.playerButton];
        buttons.forEach(button => {
            if (button !== exceptButton) button.style.display = 'none';
        });
    }

    // Показ всех кнопок
    function showAllButtons() {
        elements.userPlaylistButton.style.display = "block";
        elements.userRequestsButton.style.display = "block";
        elements.allTracksButton.style.display = "block";
        elements.playerButton.style.display = "block";
    }

    // Загрузка плейлиста с сервера
    function loadPlaylist(endpoint, callback) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        fetch(`/${endpoint}?chat_id=${chat_id}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    state.currentPlaylist = data.tracks;
                    state.userPlaylistPage = 1;
                    callback(data.tracks);
                } else {
                    elements.userPlaylistUl.innerHTML = `<li>${endpoint === 'user_playlist' ? 'Плейлист не найден.' : 'Запросы не найдены.'}</li>`;
                }
            })
            .catch(() => {
                elements.userPlaylistUl.innerHTML = `<li>Ошибка загрузки ${endpoint === 'user_playlist' ? 'плейлиста' : 'запросов'}.</li>`;
            });
    }

    // Обновление плейлиста пользователя в интерфейсе
    function updateUserPlaylist(tracks) {
        displayPlaylist(tracks);
    }

    // Отображение плейлиста
    function displayPlaylist(tracks) {
        elements.userPlaylistUl.innerHTML = '';

        if (tracks.length === 0) {
            elements.userPlaylistUl.innerHTML = '<li>Треки не найдены.</li>';
            elements.userPlaylistPaginationDiv.style.display = "none";
            return;
        }

        const startIndex = (state.userPlaylistPage - 1) * state.tracksPerPage;
        const endIndex = Math.min(startIndex + state.tracksPerPage, tracks.length);
        const tracksToDisplay = tracks.slice(startIndex, endIndex);

        tracksToDisplay.forEach((track, index) => {
            const item = createTrackListItem(track, startIndex, index);
            elements.userPlaylistUl.appendChild(item);
        });

        updatePagination(elements.userPlaylistPaginationDiv, state.userPlaylistPage, Math.ceil(tracks.length / state.tracksPerPage), (page) => {
            state.userPlaylistPage = page;
            displayPlaylist(tracks);
        });

        elements.userPlaylistPaginationDiv.style.display = (Math.ceil(tracks.length / state.tracksPerPage) > 1) ? "flex" : "none";
    }

    // Создание элемента списка треков
    function createTrackListItem(track, startIndex, index) {
        const item = document.createElement("li");
        const playIcon = createIconElement("/static/img/play.svg", "play-icon");
        const downloadIcon = createIconElement("/static/img/down.svg", "download-icon");

        item.textContent = track.title;
        item.classList.add("list-group-item", "d-flex", "justify-content-between", "align-items-center");

        item.addEventListener("click", () => {
            state.currentTrackIndex = startIndex + index;
            playTrack();
        });

        downloadIcon.addEventListener("click", (event) => {
            event.stopPropagation();
            sendTrackToChat(track);
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

    // Создание элемента иконки
    function createIconElement(src, className) {
        const icon = document.createElement("img");
        icon.src = src;
        icon.classList.add(className);
        return icon;
    }

    // Воспроизведение трека
    function playTrack() {
        const track = state.currentPlaylist[state.currentTrackIndex];
        let relativePath = track.path ? track.path.replace('/home/ubuntu/refinder/', '') : track.file_path.replace('/home/ubuntu/refinder/', '');
        const encodedPath = encodeURIComponent(relativePath).replace(/%20/g, ' ');
        elements.audioPlayer.src = `/tracks/${encodedPath}`;
        elements.audioPlayer.play();
        elements.nowPlayingDiv.textContent = `Сейчас играет: ${track.title}`;
    }

    // Воспроизведение следующего трека
    function playNextTrack() {
        if (state.currentTrackIndex < state.currentPlaylist.length - 1) {
            state.currentTrackIndex++;
            playTrack();
        } else {
            elements.nowPlayingDiv.textContent = 'Воспроизведение завершено';
        }
    }

    // Загрузка всех треков для редактирования
    function loadAllTracksForEdit() {
        fetch('/tracks')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    state.allTracks = data.tracks;
                    state.editPlaylistPage = 1;
                    filterTracksForEdit();
                } else {
                    elements.userPlaylistUl.innerHTML = '<li>Треки не найдены.</li>';
                }
            })
            .catch(() => {
                elements.userPlaylistUl.innerHTML = '<li>Ошибка загрузки треков.</li>';
            });
    }

    // Отображение треков для редактирования
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
            item.classList.add("list-group-item");
            elements.userPlaylistUl.appendChild(item);
        });

        updatePagination(elements.editPlaylistPaginationDiv, state.editPlaylistPage, Math.ceil(filteredTracks.length / state.editTracksPerPage), (page) => {
            state.editPlaylistPage = page;
            displayTracksForEdit();
        });

        elements.filterInput.style.display = "block";
        elements.editPlaylistButton.style.display = "none";
        elements.savePlaylistButton.style.display = "block";
    }

    // Создание чекбокса для треков
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

    // Отправка трека в чат
    function sendTrackToChat(track) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        const filePath = track.path ? track.path : track.file_path;

        fetch('/send_track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id, file_path: filePath })
        })
        .then(response => response.json())
        .catch(() => {});
    }

    // Сохранение плейлиста
    function savePlaylist() {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        const selectedTrackList = Array.from(state.selectedTracks).map(filePath => {
            const track = state.allTracks.find(track => track.file_path === filePath);
            return { title: track.title, path: track.file_path.replace('/home/ubuntu/refinder/', '') };
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

    // Фильтрация треков при редактировании
    function filterTracksForEdit() {
        displayTracksForEdit();
    }

    // Редактирование плейлиста
    function editPlaylist() {
        state.isEditing = true;
        loadAllTracksForEdit();
        elements.editPlaylistButton.style.display = "none";
        elements.savePlaylistButton.style.display = "block";
    }
}