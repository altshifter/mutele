document.addEventListener("DOMContentLoaded", function() {
    // Получаем элементы DOM
    const searchButton = document.getElementById("searchButton");
    const spinner = document.getElementById("spinner");

    // Создаем и настраиваем элемент для уведомлений
    const notificationDiv = document.createElement('div');
    notificationDiv.id = 'notification';
    notificationDiv.style.position = 'fixed';
    notificationDiv.style.bottom = '20px';
    notificationDiv.style.right = '20px';
    notificationDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    notificationDiv.style.color = 'white';
    notificationDiv.style.padding = '10px';
    notificationDiv.style.borderRadius = '5px';
    notificationDiv.style.display = 'none';  // Скрываем уведомление по умолчанию
    document.body.appendChild(notificationDiv);

    // Функция для отображения уведомлений
    function showNotification(message) {
        notificationDiv.textContent = message;
        notificationDiv.style.display = 'block';  // Показываем уведомление
        setTimeout(() => {
            notificationDiv.style.display = 'none';  // Скрываем уведомление через 3 секунды
        }, 3000);
    }

    // Функция для сброса состояния поиска
    function resetSearchState() {
        isSearching = false;
        searchButton.disabled = false;  // Активируем кнопку поиска
        searchInput.disabled = false;  // Активируем поле ввода поиска
        searchButton.textContent = "Поиск";  // Восстанавливаем текст кнопки
        searchInput.value = '';  // Очищаем поле ввода поиска
        resultsDiv.innerHTML = '';  // Очищаем результаты поиска
        paginationDiv.innerHTML = '';  // Очищаем пагинацию
    }
});
