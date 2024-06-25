import { initBot } from './bot.js'; // Импорт функции инициализации модуля бота из bot.js
import { initPlayer } from './player.js'; // Импорт функции инициализации модуля плеера из player.js
import { initUI } from './ui.js'; // Импорт функции инициализации модуля пользовательского интерфейса из ui.js

// Инициализация модулей после загрузки DOM
document.addEventListener("DOMContentLoaded", function() {
    initBot(); // Инициализация функционала бота
    initPlayer(); // Инициализация плеера
    initUI(); // Инициализация пользовательского интерфейса
});