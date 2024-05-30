document.addEventListener("DOMContentLoaded", function() {
    // Получение элементов DOM
    const playerButton = document.getElementById("playerButton");
    const playerDiv = document.getElementById("player");
    const playlistUl = document.getElementById("playlist");
    const playlistPaginationDiv = document.getElementById("playlistPagination");
    const audioPlayer = document.getElementById("audioPlayer");
    const userPlaylistButton = document.getElementById("userPlaylistButton");
    const userRequestsButton = document.getElementById("userRequestsButton");
    const allTracksButton = document.getElementById("allTracksButton");
    const userPlaylistDiv = document.getElementById("userPlaylistDiv");
    const userPlaylistUl = document.getElementById("userPlaylist");
    const editPlaylistButton = document.getElementById("editPlaylistButton");
    const savePlaylistButton = document.getElementById("savePlaylistButton");
    const searchSection = document.querySelector(".search-section");

    // Создание и настройка элементов фильтра и пагинации
    const filterInput = document.createElement("input");
    filterInput.id = "filterInput";
    filterInput.className = "input-field";
    filterInput.placeholder = "Фильтр треков";
    filterInput.style.display = "none";
    filterInput.style.width = "calc(100% - 10px)";
    filterInput.style.maxWidth = "420px";
    userPlaylistDiv.insertBefore(filterInput, userPlaylistUl);

    const userPlaylistPaginationDiv = document.createElement("div");
    const editPlaylistPaginationDiv = document.createElement("div");
    userPlaylistPaginationDiv.id = "userPlaylistPagination";
    userPlaylistDiv.appendChild(userPlaylistPaginationDiv);
    editPlaylistPaginationDiv.id = "editPlaylistPagination";
    userPlaylistDiv.appendChild(editPlaylistPaginationDiv);

    const nowPlayingDiv = document.createElement('div');
    nowPlayingDiv.id = 'nowPlaying';
    nowPlayingDiv.style.marginTop = '20px';
    nowPlayingDiv.style.fontWeight = 'bold';
    playerDiv.appendChild(nowPlayingDiv);

    // Переменные для управления состоянием плейлиста и плеера
    let playlistPage = 1;
    let tracksPerPage = 9;
    let editTracksPerPage = 9;
    let allTracks = [];
    let userPlaylist = [];
    let userRequests = [];
    let allServerTracks = [];
    let userPlaylistPage = 1;
    let editPlaylistPage = 1;
    let currentTrackIndex = 0;
    let selectedTracks = new Set();
    let trackOrder = [];

    // Обработчик кнопки открытия/закрытия плеера
    playerButton.addEventListener("click", function() {
        if (playerDiv.style.display === "block") {
            playerDiv.style.display = "none";
            searchSection.style.display = "block";
            playerButton.textContent = "Открыть плеер";
            showAllButtons();  // Показать все кнопки при закрытии плеера
        } else {
            loadUserPlaylist();
            playerDiv.style.display = "block";
            searchSection.style.display = "none";
            playerButton.textContent = "Закрыть плеер";
        }
    });

    // Обработчики кнопок для переключения между плейлистами и запросами
    userPlaylistButton.addEventListener("click", () => {
        toggleUserPlaylist();
    });

    userRequestsButton.addEventListener("click", () => {
        toggleUserRequests();
    });

    allTracksButton.addEventListener("click", () => {
        toggleAllTracks();
    });

    editPlaylistButton.addEventListener("click", () => {
        playerButton.style.display = "none";
        clearUserPlaylist(loadAllTracksForEdit);
    });

    savePlaylistButton.addEventListener("click", () => {
        saveUserPlaylist();
        playerButton.style.display = "block";
    });

    audioPlayer.addEventListener("ended", playNextTrack);

    filterInput.addEventListener("input", filterTracksForEdit);

    // Функция для отображения или скрытия плейлиста пользователя
    function toggleUserPlaylist() {
        if (userPlaylistDiv.style.display === "none" || userPlaylistDiv.style.display === "") {
            loadUserPlaylist();
            userPlaylistDiv.style.display = "block";
            userPlaylistButton.textContent = "Закрыть твой плейлист";
            userRequestsButton.style.display = "none";
            allTracksButton.style.display = "none";
            editPlaylistButton.style.display = "block"; // Показать кнопку редактирования
            savePlaylistButton.style.display = "none";
            filterInput.style.display = "none";
        } else {
            userPlaylistDiv.style.display = "none";
            userPlaylistButton.textContent = "Твой плейлист";
            showAllButtons();
        }
    }

    // Функция для отображения или скрытия запросов пользователя
    function toggleUserRequests() {
        if (userPlaylistDiv.style.display === "none" || userPlaylistDiv.style.display === "") {
            loadUserRequests();
            userPlaylistDiv.style.display = "block";
            userRequestsButton.textContent = "Закрыть Твои запросы";
            userPlaylistButton.style.display = "none";
            allTracksButton.style.display = "none";
            editPlaylistButton.style.display = "none";  // Скрыть кнопку редактирования
            savePlaylistButton.style.display = "none";
            filterInput.style.display = "none";
        } else {
            userPlaylistDiv.style.display = "none";
            userRequestsButton.textContent = "Твои запросы";
            showAllButtons();
        }
    }

    // Функция для отображения или скрытия всех треков на сервере
    function toggleAllTracks() {
        if (userPlaylistDiv.style.display === "none" || userPlaylistDiv.style.display === "") {
            loadAllServerTracks();
            userPlaylistDiv.style.display = "block";
            allTracksButton.textContent = "Закрыть все треки";
            userPlaylistButton.style.display = "none";
            userRequestsButton.style.display = "none";
            editPlaylistButton.style.display = "none";  // Скрыть кнопку редактирования
            savePlaylistButton.style.display = "none";
            filterInput.style.display = "none";
        } else {
            userPlaylistDiv.style.display = "none";
            allTracksButton.textContent = "Все треки";
            showAllButtons();
        }
    }

    // Функция для отображения всех кнопок управления
    function showAllButtons() {
        userPlaylistButton.style.display = "block";
        userRequestsButton.style.display = "block";
        allTracksButton.style.display = "block";
    }

    // Функция для загрузки плейлиста пользователя с сервера
    function loadUserPlaylist() {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;

        fetch(`/user_playlist?chat_id=${chat_id}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    userPlaylist = data.tracks;
                    userPlaylistPage = 1;
                    displayPlaylist(userPlaylist);
                } else {
                    userPlaylistUl.innerHTML = '<li>Плейлист не найден.</li>';
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                userPlaylistUl.innerHTML = '<li>Ошибка загрузки плейлиста.</li>';
            });
    }

    // Функция для загрузки запросов пользователя с сервера
    function loadUserRequests() {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;

        fetch(`/user_requests?chat_id=${chat_id}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    userRequests = data.tracks;
                    userPlaylistPage = 1;
                    displayPlaylist(userRequests);
                } else {
                    userPlaylistUl.innerHTML = '<li>Запросы не найдены.</li>';
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                userPlaylistUl.innerHTML = '<li>Ошибка загрузки запросов.</li>';
            });
    }

    // Функция для загрузки всех треков с сервера
    function loadAllServerTracks() {
        fetch(`/all_tracks`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    allServerTracks = data.tracks;
                    userPlaylistPage = 1;
                    displayPlaylist(allServerTracks);
                } else {
                    userPlaylistUl.innerHTML = '<li>Треки не найдены.</li>';
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                userPlaylistUl.innerHTML = '<li>Ошибка загрузки треков.</li>';
            });
    }

    // Функция для отображения плейлиста (общая)
    function displayPlaylist(tracks, isEditMode = false) {
        userPlaylistUl.innerHTML = '';

        if (tracks.length === 0) {
            userPlaylistUl.innerHTML = '<li>Треки не найдены.</li>';
            return;
        }

        const startIndex = (userPlaylistPage - 1) * tracksPerPage;
        const endIndex = Math.min(startIndex + tracksPerPage, tracks.length);
        const tracksToDisplay = tracks.slice(startIndex, endIndex);

        tracksToDisplay.forEach((track, index) => {
            const item = document.createElement("li");
            const playIcon = document.createElement("img");
            const downloadIcon = document.createElement("img");

            item.textContent = track.title;
            item.classList.add("track-item");

            if (!isEditMode) {
                item.addEventListener("click", () => {
                    currentTrackIndex = startIndex + index;
                    playTrack(track);
                });
            }

            playIcon.src = "/static/img/play.svg";
            playIcon.classList.add("play-icon");

            downloadIcon.src = "/static/img/down.svg";
            downloadIcon.classList.add("download-icon");

            downloadIcon.addEventListener("click", (event) => {
                event.stopPropagation();
                sendTrackToChat(track.path);
            });

            const iconsDiv = document.createElement("div");
            iconsDiv.style.display = "flex";
            iconsDiv.style.marginLeft = "auto";
            iconsDiv.appendChild(playIcon);
            iconsDiv.appendChild(downloadIcon);

            item.prepend(playIcon);
            item.appendChild(iconsDiv);
            userPlaylistUl.appendChild(item);
        });

        if (isEditMode) {
            updateUserPlaylistPaginationForEdit();
        } else {
            updateGeneralPagination(tracks);
        }
    }

    // Функция для обновления пагинации (общая)
    function updateGeneralPagination(tracks) {
        userPlaylistPaginationDiv.innerHTML = '';

        const totalPages = Math.ceil(tracks.length / tracksPerPage);

        const prevButton = document.createElement('button');
        prevButton.textContent = 'Предыдущая';
        prevButton.disabled = userPlaylistPage === 1;
        prevButton.addEventListener('click', () => {
            userPlaylistPage--;
            displayPlaylist(tracks);
        });

        const nextButton = document.createElement('button');
        nextButton.textContent = 'Следующая';
        nextButton.disabled = userPlaylistPage === totalPages;
        nextButton.addEventListener('click', () => {
            userPlaylistPage++;
            displayPlaylist(tracks);
        });

        if (totalPages > 1) {
            userPlaylistPaginationDiv.appendChild(prevButton);
            userPlaylistPaginationDiv.appendChild(nextButton);
        }
    }

    // Функция для воспроизведения трека
    function playTrack(track) {
        const encodedTitle = encodeURIComponent(track.path.split('/').pop()).replace(/%20/g, ' ');
        audioPlayer.src = `/tracks/${encodedTitle}`;
        audioPlayer.play();
        nowPlayingDiv.textContent = `Сейчас играет: ${track.title}`;
    }

    // Функция для воспроизведения следующего трека
    function playNextTrack() {
        if (currentTrackIndex < userPlaylist.length - 1) {
            currentTrackIndex++;
            playTrack(userPlaylist[currentTrackIndex]);
        } else {
            nowPlayingDiv.textContent = 'Воспроизведение завершено';
        }
    }

    // Функция для загрузки всех треков для редактирования
    function loadAllTracksForEdit() {
        fetch('/tracks')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    allTracks = data.tracks;
                    editPlaylistPage = 1;
                    displayTracksForEdit();
                } else {
                    userPlaylistUl.innerHTML = '<li>Треки не найдены.</li>';
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                userPlaylistUl.innerHTML = '<li>Ошибка загрузки треков.</li>';
            });
    }

    // Функция для отображения треков для редактирования
    function displayTracksForEdit() {
        const filter = filterInput.value.toLowerCase();
        const filteredTracks = allTracks.filter(track => track.title.toLowerCase().includes(filter));
        
        userPlaylistUl.innerHTML = '';
        const startIndex = (editPlaylistPage - 1) * editTracksPerPage;
        const endIndex = Math.min(startIndex + editTracksPerPage, filteredTracks.length);
        const tracksToDisplay = filteredTracks.slice(startIndex, endIndex);

        trackOrder = Array.from(selectedTracks);

        tracksToDisplay.forEach(track => {
            const item = document.createElement("li");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.value = track.file_path;

            checkbox.checked = selectedTracks.has(track.file_path);

            checkbox.addEventListener("change", () => {
                if (checkbox.checked) {
                    selectedTracks.add(track.file_path);
                    trackOrder.push(track.file_path);
                } else {
                    selectedTracks.delete(track.file_path);
                    trackOrder = trackOrder.filter(path => path !== track.file_path);
                }
                displayTracksForEdit();
            });

            const checkboxLabel = document.createElement("label");
            const trackNumber = trackOrder.indexOf(track.file_path) + 1;
            checkboxLabel.textContent = checkbox.checked ? `${trackNumber}. ${track.title}` : `${track.title}`;
            checkboxLabel.prepend(checkbox);

            item.appendChild(checkboxLabel);
            userPlaylistUl.appendChild(item);
        });

        updateUserPlaylistPaginationForEdit();
        filterInput.style.display = "block";
        editPlaylistButton.style.display = "none";
        savePlaylistButton.style.display = "block";
    }

    // Функция для обновления пагинации для редактирования плейлиста
    function updateUserPlaylistPaginationForEdit() {
        editPlaylistPaginationDiv.innerHTML = '';
        editPlaylistPaginationDiv.style.display = "flex";
        editPlaylistPaginationDiv.style.justifyContent = "center";

        const totalPages = Math.ceil(allTracks.length / editTracksPerPage);

        const prevButton = document.createElement('button');
        prevButton.textContent = 'Предыдущая';
        prevButton.disabled = editPlaylistPage === 1;
        prevButton.addEventListener('click', () => {
            editPlaylistPage--;
            displayTracksForEdit();
        });

        const nextButton = document.createElement('button');
        nextButton.textContent = 'Следующая';
        nextButton.disabled = editPlaylistPage === totalPages;
        nextButton.addEventListener('click', () => {
            editPlaylistPage++;
            displayTracksForEdit();
        });

        if (totalPages > 1) {
            editPlaylistPaginationDiv.appendChild(prevButton);
            editPlaylistPaginationDiv.appendChild(nextButton);
        }
    }

    // Функция для сохранения плейлиста пользователя
    function saveUserPlaylist() {
        selectedTracks = new Set(Array.from(selectedTracks).filter(track => allTracks.some(t => t.file_path === track)));

        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;
        const selectedTrackList = Array.from(selectedTracks).map(filePath => {
            const track = allTracks.find(track => track.file_path === filePath);
            return {
                title: track.title,
                path: track.file_path
            };
        });

        fetch('/save_playlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ chat_id, tracks: selectedTrackList })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                selectedTracks.clear();
                trackOrder = [];
                loadUserPlaylist();
                editPlaylistButton.style.display = "block";
                savePlaylistButton.style.display = "none";
                filterInput.style.display = "none";
                editPlaylistPaginationDiv.style.display = "none";
                playerButton.style.display = "block";
            } else {
                console.error('Ошибка сохранения плейлиста:', data.message);
            }
        })
        .catch(error => {
            console.error('Ошибка сохранения плейлиста:', error);
        });
    }

    // Функция для очистки плейлиста пользователя
    function clearUserPlaylist(callback) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;

        fetch('/clear_playlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ chat_id })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                selectedTracks.clear();
                trackOrder = [];
                Array.from(document.querySelectorAll("#userPlaylistDiv input[type=checkbox]")).forEach(checkbox => {
                    checkbox.checked = false;
                });
                if (callback) {
                    callback();
                }
            } else {
                console.error('Ошибка очистки плейлиста:', data.message);
            }
        })
        .catch(error => {
            console.error('Ошибка очистки плейлиста:', error);
        });
    }

    // Функция для отправки трека в чат
    function sendTrackToChat(filePath) {
        const chat_id = Telegram.WebApp.initDataUnsafe.user.id;

        fetch('/send_track', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ chat_id, file_path: filePath })
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

    // Функция для фильтрации треков при редактировании
    function filterTracksForEdit() {
        displayTracksForEdit();
    }
});
