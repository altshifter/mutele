// Инициализация модуля UI
export function initUI() {
    const searchButton = document.getElementById("searchButton"); // Получение элемента кнопки поиска из DOM
    const spinner = document.getElementById("spinner"); // Получение элемента индикатора загрузки из DOM

    // Создание элемента уведомления и добавление его в DOM
    const notificationDiv = document.createElement('div');
    notificationDiv.id = 'notification';
    notificationDiv.style.position = 'fixed';
    notificationDiv.style.bottom = '20px';
    notificationDiv.style.right = '20px';
    notificationDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    notificationDiv.style.color = 'white';
    notificationDiv.style.padding = '10px';
    notificationDiv.style.borderRadius = '5px';
    notificationDiv.style.display = 'none';
    document.body.appendChild(notificationDiv);

    // Функция для отображения уведомлений
    function showNotification(message) {
        notificationDiv.textContent = message;
        notificationDiv.style.display = 'block';
        setTimeout(() => {
            notificationDiv.style.display = 'none';
        }, 3000);
    }

    // Функция для сброса состояния поиска
    function resetSearchState() {
        isSearching = false;
        searchButton.disabled = false;
        searchInput.disabled = false;
        searchButton.textContent = "Поиск";
        searchInput.value = '';
        resultsDiv.innerHTML = '';
        paginationDiv.innerHTML = '';
    }
}

// Функция для создания кнопки пагинации
export function createPaginationButton(text, disabled, clickHandler) {
    const button = document.createElement('button'); // Создание элемента кнопки
    button.textContent = text; // Установка текста кнопки
    button.className = 'btn btn-secondary'; // Установка класса кнопки
    button.disabled = disabled; // Установка состояния кнопки (активная/неактивная)
    button.addEventListener('click', clickHandler); // Добавление обработчика клика на кнопку
    return button; // Возвращение созданной кнопки
}

// Функция для обновления пагинации
export function updatePagination(paginationDiv, currentPage, totalPages, onPageChange) {
    paginationDiv.innerHTML = ''; // Очистка содержимого элемента пагинации
    paginationDiv.style.display = "flex"; // Установка стиля отображения flex
    paginationDiv.style.justifyContent = "center"; // Центрирование содержимого

    // Создание кнопки "Назад"
    const prevButton = createPaginationButton('<<', currentPage === 1, () => {
        onPageChange(currentPage - 1); // Переход на предыдущую страницу при клике
    });

    // Создание кнопки "Вперед"
    const nextButton = createPaginationButton('>>', currentPage === totalPages, () => {
        onPageChange(currentPage + 1); // Переход на следующую страницу при клике
    });

    // Добавление кнопок в элемент пагинации
    paginationDiv.appendChild(prevButton);
    paginationDiv.appendChild(nextButton);
}