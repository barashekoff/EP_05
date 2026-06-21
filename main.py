import sys
import re
import json
import math
import numpy as np
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QEvent, QRegularExpression, QSettings
from PyQt6.QtGui import QFont, QAction, QRegularExpressionValidator, QShortcut, QKeySequence
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

# Стили для оформления интерфейса
STYLE = """
QMainWindow {
    background: transparent;}

/* Карточки, левая и правая панели */
#Card {
    border-radius: 20px;
    border: 1px solid rgba(0,0,0,0.25);}

/* Общие кнопки */
QPushButton {
    border-radius: 10px;
    border: 1px solid rgba(0,0,0,0.25);
    min-height: 35px;
    font-size: 14px;
    padding: 6px;}

/* Hover, при наведении на элементы курсором мыши */
QPushButton:hover {
    opacity: 0.9;}

/* Основной акцент для кнопки = */
QPushButton#PrimaryAccent {
    font-weight: bold;
    font-size: 16px;
    min-height: 50px;}

/* Вторичный акцент для кнопок C и DEL */
QPushButton#SecondaryAccent {
    font-weight: bold;}
    
/* Стиль для кнопок неактивных вкладок */
#TabButton {
    font-weight: 600;}

#ActiveTab {
    font-weight: 700;
    border: 2px solid rgba(0,0,0,0.4);}

/* Стиль для полей ввода, текстовых полей и списков */
QLineEdit, QTextEdit, QListWidget {
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.25);
    padding: 6px;}

/* Всплывающие подсказки */
QToolTip {
    border-radius: 6px;}

/* Контекстные меню */
QMenu {
    border: 1px solid rgba(0,0,0,0.2);}

/* Выпадающие списки */
QComboBox {
    border-radius: 6px;
    padding: 5px;
    border: 1px solid rgba(0,0,0,0.3);}

/* Раскрывающийся список выпадающего меню */
QComboBox QAbstractItemView {
    selection-background-color: #FFC04B;
    selection-color: #000;}

/* Стиль для активной кнопки DEG/RAD */    
QPushButton#ModeActive {
    background: {theme['accent']};
    color: {theme['accent_text']};
    font-weight: bold;
    border: 2px solid {theme['border']};}
/* При наведении на активную кнопку DEG/RAD */
QPushButton#ModeActive:hover {
    background: {theme['selection_bg']};}
/* Кнопка 2nd в активном состоянии */
QPushButton#SecondActive {
    background: #FFA500;
    color: black;
    font-weight: bold;}    
/* Выбранный элемент в списке истории */
QListWidget::item:selected {
    border-radius: 6px;}
"""

# Словарь. Цветовые темы: светлая, тёмная, зелёная, синяя
THEMES = {
    "light": {
        "bg": "#FFFFFF",  # фон окна
        "card": "#E0E0E0",  # фон карточек
        "input_bg": "#FFFFFF",  # фон полей ввода
        "btn_default": "#E0E0E0",  # обычные кнопки
        "special_btn_bg": "#D9D9D9",  # важные кнопки (C, DEL, =)
        "text": "#000000",  # цвет текста
        "border": "#B0B0B0"  # цвет границ
    },
    "dark": {
        "bg": "#565656",
        "card": "#2B2B2B",
        "input_bg": "#E0E0E0",
        "btn_default": "#848484",
        "special_btn_bg": "#565656",
        "text": "#FFFFFF",
        "border": "#444444"
    },
    "green": {
        "bg": "#445C3F",
        "card": "#AAB992",
        "input_bg": "#FFFFFF",
        "btn_default": "#CCD5B5",
        "special_btn_bg": "#7D936C",
        "text": "#000000",
        "border": "#6C805C"
    },
    "blue": {
        "bg": "#395886",
        "card": "#B1C9EF",
        "input_bg": "#FFFFFF",
        "btn_default": "#8AAEE0",
        "special_btn_bg": "#638ECB",
        "text": "#000000",
        "border": "#5373A1"
    }
}

def safe_eval(expr, angle_mode): # безопасное вычисление
    if not expr.strip():
        raise ValueError("Введите выражение!")

    expr = expr.replace("^", "**") # ^ → ** для возведения в степень

    if expr.count(")") > expr.count("("):
        raise ValueError("Лишняя закрывающая скобка")

    expr = re.sub(r'(?<!\d)\.(?!\d)', '0.', expr) # .5 будет 0.5, добавляет ноль перед точкой

    if expr and expr[0] in "+*/": # защита от кривых операторов в начале, добавляем 0
        expr = "0" + expr

    if expr and expr[-1] in "+-*/":  # защита от кривых операторов в конце, добавляем 0
        expr += "0"

    if "0**0" in expr: # 0**0
        raise ValueError("0⁰ — неопределенность")

    if re.search(r"0\*\*-\d+", expr): # 0**-число
        raise ValueError("Деление на ноль")

    if expr.count("(") != expr.count(")"): # проверка баланса скобок
        raise ValueError("Незакрытая скобка")

    if re.search(r"[a-zA-Z]+", expr) and not re.search(r"(sin|cos|tan|log|ln|sqrt|exp)", expr):
        raise ValueError("Недопустимые символы")

    # функции для кнопок
    def mod(x, y):
        return x % y

    def sin(x):
        return math.sin(math.radians(x) if angle_mode == "DEG" else x)

    def cos(x):
        return math.cos(math.radians(x) if angle_mode == "DEG" else x)

    def tan(x):
        if angle_mode == "DEG" and x % 180 == 90:
            raise ValueError("Тангенс не определен")
        return math.tan(math.radians(x) if angle_mode == "DEG" else x)

    def asin(x):
        if x < -1 or x > 1:
            raise ValueError("Аргумент должен быть от -1 до 1")
        result = math.asin(x)
        if angle_mode == "DEG":
            result = math.degrees(result)
        return result

    def acos(x):
        if x < -1 or x > 1:
            raise ValueError("Аргумент должен быть от -1 до 1")
        result = math.acos(x)
        if angle_mode == "DEG":
            result = math.degrees(result)
        return result

    def atan(x):
        result = math.atan(x)
        if angle_mode == "DEG":
            result = math.degrees(result)
        return result

    def sqrt(x):
        if x < 0:
            raise ValueError("Корень из отрицательного числа")
        return math.sqrt(x)

    def log(x): # десятичный логарифм
        if x <= 0:
            raise ValueError("Логарифм от нуля или отрицательного числа")
        return math.log10(x)

    def ln(x): # натуральный логарифм
        if x <= 0:
            raise ValueError("Логарифм от нуля или отрицательного числа")
        return math.log(x)

    try: # перехват исключений, вычисляет выражение в безопасном окружении
        result = eval(expr, {
            "__builtins__": {}, # запрет к встроенным функциям
            "sin": sin, "cos": cos, "tan": tan,
            "asin": asin, "acos": acos, "atan": atan,
            "sqrt": sqrt, "log": log, "ln": ln,
            "abs": abs,
            "exp": math.exp, "pi": math.pi, "e": math.e,
            "mod": mod,})
        if abs(result) > 1e308: # проверка переполнения (слишком большое число)
            raise OverflowError
        return result

    except ZeroDivisionError: # перехват различных ошибок
        raise ValueError("Деление на ноль невозможно")
    except OverflowError:
        raise ValueError("Переполнение")
    except Exception:
        raise ValueError("Ошибка выражения")

# Инициализация
# noinspection PyUnresolvedReferences
class EngineeringApp(QMainWindow):
    # главное окно инженерного калькулятора
    def __init__(self): # конструктор класса, вызывается при создании объекта
        super().__init__()

        # сохранение темы и режима углов при выключении
        self.prefs = QSettings("MyCompany", "CalculatorApp")
        self.setWindowTitle("Инженерный калькулятор")

        # загрузка сохраненных параметров
        self.angle_mode = self.prefs.value("angle_mode", "RAD")
        self.saved_theme = self.prefs.value("theme_color", "light")

        self.last_focused_input = None  # последнее активное поле ввода
        self.memory_value = None  # ячейка памяти
        self.second_func = False  # флаг режима 2nd (обратные функции)
        self.btn_2nd = None  # для хранения кнопки 2nd
        self.history_file = "history.json"

        # запрет символов
        self.num_val = QRegularExpressionValidator(QRegularExpression(r"^-?\d*\.?\d*$")) # разрешены только цифры, точка, минус
        self.math_val = QRegularExpressionValidator(QRegularExpression(r"[0-9.+\-*/()%^]*")) # разрешены цифры, операторы, скобки, точка

        self.init_ui() # метод создания интерфейса
        self.load_history()

        self.shortcut_copy = QShortcut(QKeySequence("Ctrl+C"), self)
        self.shortcut_copy.activated.connect(lambda: QApplication.clipboard().setText(self.main_display.text()))

        self.shortcut_paste = QShortcut(QKeySequence("Ctrl+V"), self)
        self.shortcut_paste.activated.connect(lambda: self.insert_text(QApplication.clipboard().text()))

        self.shortcut_clear = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut_clear.activated.connect(lambda: self.main_display.setText("0"))

        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(lambda: self.on_calc_click("MS"))
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(lambda: self.on_calc_click("M-"))
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(lambda: self.on_calc_click("M+"))
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(lambda: self.on_calc_click("MR"))

        self.shortcut_select = QShortcut(QKeySequence("Ctrl+A"), self)
        self.shortcut_select.activated.connect(self.main_display.selectAll) # подключение напрямую к методу поля ввода

        self.apply_theme_color(self.saved_theme) # применение темы ко всему интерфейсу, передает сохраненную тему
        self.showMaximized()  # главное окно открывается на весь экран

        self._inserting = False  # флаг защиты от рекурсии

        # переопределяем метод вставки из буфера обмена для контроля нечисловых букв
        def custom_paste():
            clipboard_text = QApplication.clipboard().text()
            # оставляем только цифры, математические операторы, скобки и точки
            filtered_text = re.sub(r'[^0-9.+\-*/()^%a-zA-Z]', '', clipboard_text)
            # если текст содержал запрещенные буквы (русские буквы, спецсимволы), пишем предупреждение
            if len(filtered_text) != len(clipboard_text):
                self.error_label.setText("Недопустимые символы очищены")
            current = self.main_display.text() # текущий текст из поля ввода
            if current in ["0", "Ошибка", "Введите выражение!", "Ошибка синтаксиса"]:
                current = ""
            self.main_display.setText(current + filtered_text) # отфильтрованный текст в конец поля ввода
            self.error_label.setText("")
            self.main_display.setStyleSheet("") # если была красная рамка
        self.main_display.paste = custom_paste

    def load_history(self):
        try:
            with open(self.history_file, "r", encoding="utf-8") as f: # открываем файл для чтения
                data = json.load(f) # читаем файл и преобразуем в список
                for item in data:
                    self.hist_list.addItem(item) # добавляем каждую запись в виджет списка
        except (FileNotFoundError, json.JSONDecodeError):
            pass # игнор ошибки

    # noinspection PyTypeChecker
    def save_history(self):
        data = [self.hist_list.item(i).text() for i in range(self.hist_list.count())] # элементы списка истории в текст
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2) # разрешает русские буквы и делает отступы

    # noinspection PyTypeChecker
    def clear_history(self):
        self.hist_list.clear() # удаляет все элементы списка на экране
        with open(self.history_file, "w") as f:
            json.dump([], f)

    def init_ui(self):
        # создание интерфейса: левая панель с кнопками, правая с режимами
        central = QWidget() # в виджет будут вкладываться все элементы
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central) # создает горизонтальный компоновщик для главного окна

        # левая панель, калькулятор
        self.left_card = QFrame(central)
        self.left_card.setObjectName("Card") # для применения стилей
        left_vbox = QVBoxLayout(self.left_card) # вертикальный компоновщик (сверху вниз)

        top_row = QHBoxLayout() # горизонтальный компоновщик для верхней строки
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(50, 50)
        self.settings_btn.clicked.connect(self.open_params)

        self.trig_btn = QPushButton("Тригонометрия")
        self.trig_btn.setFixedHeight(50)
        trig_menu = QMenu(self) # объект меню, выпадающее из кнопки
        trig_menu.setStyleSheet("""
        QMenu {
            background: #FFFFFF;
            border: 1px solid #999;}
        QMenu::item:selected {
            background-color: #FFC04B;
            color: #000000;}""")

        def make_handler(func_name): # возвращает обработчик для конкретной функции
            def handler():
                if self.second_func and func_name in ['sin', 'cos', 'tan']:
                    # если 2nd включён, вставляем обратную функцию
                    self.insert_text("a" + func_name + "(")
                    self.second_func = False
                    self.btn_2nd.setText("2nd")
                    self.btn_2nd.setObjectName("") # убираем стиль активной кнопки
                    self.btn_2nd.setStyleSheet("")
                    self.trig_btn.setText("Тригонометрия")
                else:
                    self.insert_text(func_name + "(")
            return handler

        for f in ['sin', 'cos', 'tan', 'asin', 'acos', 'atan']:
            a = QAction(f, self) # пункт меню с названием функции
            # для asin, acos, atan не нужно преобразование
            if f in ['asin', 'acos', 'atan']:
                a.triggered.connect(lambda ch, func=f: self.insert_text(func + "("))
            else: # для проверки режима 2nd
                a.triggered.connect(make_handler(f))
            trig_menu.addAction(a) # добавляет пункт в меню
        self.trig_btn.setMenu(trig_menu) # привязывает меню к кнопке

        top_row.addWidget(self.settings_btn) # кнопка параметров в верхнюю строку слева
        top_row.addWidget(self.trig_btn) # кнопка тригонометрии рядом
        top_row.addStretch() # упругий пробел, т.е. выталкивает все влево
        left_vbox.addLayout(top_row) # добавляет эту строку в вертикальный компоновщик левой панели

        self.main_display = QLineEdit("0") # поле ввода
        self.main_display.setAlignment(Qt.AlignmentFlag.AlignRight) # по правому краю
        self.main_display.setFixedHeight(80)
        self.main_display.setFont(QFont("Inter", 24))
        self.main_display.setValidator(self.math_val)
        self.main_display.installEventFilter(self) # обработка кликов и фокуса
        left_vbox.addWidget(self.main_display) # добавление поля ввода в левую панель

        self.error_label = QLabel("") # текстовая метка для ошибок
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        left_vbox.addWidget(self.error_label)

        # noinspection PyArgumentList
        grid = QGridLayout() # сетка кнопок
        buttons = [
            ['MC', 'MR', 'M+', 'M-', 'MS'], ['2nd', 'π', 'e', 'C', 'DEL'],
            ['x²', '1/x', '|x|', 'exp', 'mod'], ['2√x', '(', ')', 'n!', '/'],
            ['x^y', '7', '8', '9', '*'], ['10^x', '4', '5', '6', '-'],
            ['log', '1', '2', '3', '+'], ['ln', '+/-', '0', '.', '=']]

        # подсказки (ToolTips)
        tips = {
            'MC': 'MC (Memory Clear) — Очистить память',
            'MR': 'MR (Memory Recall) — Вставить число из памяти',
            'M+': 'M+ (Memory Add) — Прибавить к числу в памяти',
            'M-': 'M- (Memory Subtract) — Вычесть из числа в памяти',
            'MS': 'MS (Memory Store) — Сохранить число в память',
            'C': 'C (Clear) — Очистить поле ввода',
            'DEL': 'DEL (Delete) — Удалить последний символ'}

        for r, row in enumerate(buttons): # r - номер строки, row - список кнопок в строке
            for c, text in enumerate(row): # c - номер столбца, text - текст кнопки
                btn = QPushButton(text)
                if text in tips: btn.setToolTip(tips[text]) # добавляет подсказку
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # кнопка заполняет всю ячейку
                if text in ['C', 'DEL']:
                    btn.setObjectName("SecondaryAccent")
                elif text == '=':
                    btn.setObjectName("PrimaryAccent")
                btn.clicked.connect(lambda ch, t=text: self.on_calc_click(t)) # вызывается метод с текстом кнопки
                if text == "2nd":
                    self.btn_2nd = btn # сохраняет ссылку на кнопку для изменения стиля
                grid.addWidget(btn, r, c) # добавляет кнопку в сетку на позицию
        left_vbox.addLayout(grid, stretch=1) # добавляет сетку с кнопками в л.пн и занимает все св. место
        main_layout.addWidget(self.left_card, 2) # доб л.пн в гл.компн., шире правой

        # правая панель, вкладки
        self.right_card = QFrame(central)
        self.right_card.setObjectName("Card")
        right_vbox = QVBoxLayout(self.right_card) # верт.компн для пр.пн

        self.tabs_nav = QHBoxLayout() # гор.кмп для кнопок вкладок
        self.tab_buttons = []
        for i, name in enumerate(["История", "Матрицы", "График"]):
            b = QPushButton(name) # кнопка вкладки
            b.clicked.connect(lambda ch, idx=i: self.switch_tab(idx))
            self.tabs_nav.addWidget(b) # добавляет кнопку в строку
            self.tab_buttons.append(b) # и сохраняет в список
        right_vbox.addLayout(self.tabs_nav) # доб строку вкладок в пр.пн

        self.stack = QStackedWidget(central) # виджет показывает одну страницу
        self.stack.addWidget(self.ui_history())
        self.stack.addWidget(self.ui_matrix())
        self.stack.addWidget(self.ui_graph())
        right_vbox.addWidget(self.stack) # доб стек в пр.пн

        self.switch_tab(0) # активирует первую вкладку
        main_layout.addWidget(self.right_card, 3) # доб пр.пн в гл.компн, шире левой

    # работа с памятью
    def memory_store(self):
        text = self.main_display.text().strip() # берет текст и убирает пробелы по краям
        if not text or text in ["0", "Ошибка", "Ошибка синтаксиса", "Введите выражение!"]:
            self.error_label.setText("Нет значения для сохранения")
            return
        try:
            val = float(safe_eval(text, self.angle_mode)) # вычисл выражение и преобразует в число с плав.точкой
            self.memory_value = val
            self.error_label.setText("Сохранено в память")
        except Exception:
            self.main_display.setText("Ошибка синтаксиса")

    def memory_plus(self):
        text = self.main_display.text().strip()
        if not text or text in ["0", "Ошибка", "Ошибка синтаксиса", "Введите выражение!"]:
            self.error_label.setText("Нет значения для операции")
            return
        try:
            val = float(safe_eval(text, self.angle_mode)) # вычисляет текущее выражение
            if not hasattr(self, 'memory_value') or self.memory_value is None:
                self.memory_value = 0.0 # если нет памяти создаем ее с нулем
            self.memory_value += val
            self.error_label.setText("Добавлено к памяти")
        except Exception:
            self.main_display.setText("Ошибка синтаксиса")

    def memory_minus(self):
        text = self.main_display.text().strip()
        if not text or text in ["0", "Ошибка", "Ошибка синтаксиса", "Введите выражение!"]:
            self.error_label.setText("Нет значения для операции")
            return
        try:
            val = float(safe_eval(text, self.angle_mode))
            if not hasattr(self, 'memory_value') or self.memory_value is None:
                self.memory_value = 0.0
            self.memory_value -= val
            self.error_label.setText("Вычтено из памяти")
        except Exception:
            self.main_display.setText("Ошибка синтаксиса")

    def memory_recall(self): # вспомнить из памяти
        # извлечение из пустой памяти (MR без сохранения) – вывод 0
        if not hasattr(self, 'memory_value') or self.memory_value is None:
            self.main_display.setText("0")
        else:
            self.main_display.setText(str(round(self.memory_value, 8))) # округляет до 8 знаков

    def memory_clear(self):
        self.memory_value = None

    # методы вставки обратных тригонометрических функций
    def insert_asin(self):
        current = self.main_display.text() # текущий текст из поля ввода
        if current in ["0", "Ошибка", "Введите выражение!", "Ошибка синтаксиса"]:
            self.main_display.setText("") # очищаем 0 или ошибку перед вставкой
        self.insert_text("asin(")

    def insert_acos(self):
        current = self.main_display.text()
        if current in ["0", "Ошибка", "Введите выражение!", "Ошибка синтаксиса"]:
            self.main_display.setText("")
        self.insert_text("acos(")

    def insert_atan(self):
        current = self.main_display.text()
        if current in ["0", "Ошибка", "Введите выражение!", "Ошибка синтаксиса"]:
            self.main_display.setText("")
        self.insert_text("atan(")

    def on_calc_click(self, t): # обработчик нажатий на кнопки
        # обработка 2nd
        if t == "2nd": # если нажата кнопка
            self.second_func = not self.second_func # переключает флаг режима
            if self.second_func:
                self.btn_2nd.setText("2nd ON")
                self.btn_2nd.setObjectName("SecondActive") # стиль активной кнопки
                self.btn_2nd.style().unpolish(self.btn_2nd) # убирает старые стили (сбрасывает кеш)
                self.btn_2nd.style().polish(self.btn_2nd)
            else:
                self.btn_2nd.setText("2nd")
                self.btn_2nd.setObjectName("") # убирает спец. стиль
                self.btn_2nd.setStyleSheet("") # сбрасывает стили
            return

        if t in ["MS", "MR", "M+", "M-", "MC"]: # защита от спама кнопок памяти
            import time
            if not hasattr(self, '_last_memory_click_time'): # сущ ли переменная для хранения t послед.клика
                self._last_memory_click_time = 0
            current_time = time.time() # текущее время в секундах
            if current_time - self._last_memory_click_time < 0.3:  # если с прош. клика прошло 300 мс
                return # игнор нажатия
            self._last_memory_click_time = current_time # запоминает время текущ.клика

        if t == "DEL":
            txt = self.main_display.text() # текущий текст из поля
            self.main_display.setText(txt[:-1] if len(txt) > 1 else "0") # берет все кроме последнего символа
        elif t == "C": # полный сброс
            self.main_display.setText("0")
            self.memory_value = None # очистка памяти
            self.error_label.setText("") # очистка сообщений об ошибке
        elif t == "=":
            self.calculate_main() # вызов метода вычисления выражения
        elif t == "MS":
            try:
                val = float(self.main_display.text()) # преобразует текст в число с плав. точкой
                self.memory_value = val # сохраняет в память
            except ValueError:
                self.error_label.setText("Нет значения для сохранения")
        elif t == "MR":
            if self.memory_value is None or self.memory_value == 0:
                self.error_label.setText("Память пуста")
                return
            self.insert_text(str(self.memory_value)) # вставка значения из памяти в поле
        elif t == "MC":
            self.memory_value = None
        elif t == "M+":
            if self.memory_value is None:
                self.memory_value = 0.0 # если пуста то 0
            try:
                val = float(self.main_display.text().replace("Ошибка", "0") or 0) # берет текст поля и заменяет ошибка на 0
                self.memory_value += val
                self.error_label.setText(f"В памяти: {round(self.memory_value, 8)}") # текущее значение округ до 8
            except ValueError:
                self.error_label.setText("Нет значения для операции")
        elif t == "M-":
            if self.memory_value is None:
                self.memory_value = 0.0
            try:
                val = float(self.main_display.text().replace("Ошибка", "0") or 0)
                self.memory_value -= val
                self.error_label.setText(f"В памяти: {round(self.memory_value, 8)}")
            except ValueError:
                self.error_label.setText("Нет значения для операции")
        elif t == "n!":
            self.apply_factorial() # вызов метода вычисления факториала
        elif t == "x²":
            self.insert_text("^2")
        elif t == "x^y":
            self.insert_text("^(")
        elif t == "10^x":
            self.insert_text("10^(")
        elif t == "+/-":
            self.toggle_sign()
        elif t == "log":
            self.insert_text("log(")
        elif t == "ln":
            self.insert_text("ln(")
        elif t == "|x|":
            self.insert_text("abs(")
        elif t == "mod":
            self.insert_text("mod(")
        elif t == "exp":
            self.insert_text("exp(")
        elif t == "1/x":
            self.insert_text("1/(")
        elif t == "2√x":
            # если 2nd активна, то просто вставляем sqrt со скобкой без вычислений
            if self.second_func:
                self.second_func = False # выключает режим
                self.trig_btn.setText("Тригонометрия")
                self.trig_btn.setStyleSheet("") # сброс стилей
                self.insert_text("sqrt(")
            else:
                # обычный режим: берём число на экране и вычисляем корень
                try:
                    val = float(self.main_display.text()) # преобразует текст из поля в число
                    if val < 0:
                        self.error_label.setText("Корень из отрицательного")
                        return
                    result = math.sqrt(val) # вычисляет корень
                    self.hist_list.addItem(f"√({val}) = {result}") # добавляет в историю
                    self.save_history() # сохраняет историю
                    self.main_display.setText(str(result)) # вывод результата
                except Exception:
                    self.main_display.setText("Ошибка")
        elif t == "sin":
            if self.second_func:
                self.insert_asin() # вставка арксинуса
                self.second_func = False # выкл режима
                self.trig_btn.setText("Тригонометрия")
            else:
                self.insert_text("sin(")
        elif t == "cos":
            if self.second_func:
                self.insert_acos() # вставка аркосинуса
                self.second_func = False
                self.trig_btn.setText("Тригонометрия")
            else:
                self.insert_text("cos(")
        elif t == "tan":
            if self.second_func:
                self.insert_atan() # вставка арктангенса
                self.second_func = False
                self.trig_btn.setText("Тригонометрия")
            else:
                self.insert_text("tan(")
        elif t == "π":
            self.insert_text("3.14159")
        elif t == "e":
            self.insert_text("2.71828")
        else:
            self.insert_text(t) # вставка текста кнопки в поле ввода

    def apply_factorial(self): # вычисление факториала
        text = self.main_display.text().strip() # берет текст и убирает пробелы по краям
        if not text or text in ["0", "Ошибка", "Ошибка синтаксиса", "Введите выражение!"]:
            self.main_display.setText("Введите число")
            return
        try: # перехват ошибок
            val = int(float(safe_eval(text, self.angle_mode))) # вычисляет выраж, сначала преобразует в число с плав.точкой, затем в целое
            if val < 0:
                self.main_display.setText("Факториал только для неотрицательных")
                return
            res = math.factorial(val) # вычисление факториала
            self.hist_list.addItem(f"{val}! = {res}") # сохраняет в историю как 5! = 120
            self.save_history()
            self.main_display.setText(str(res))
        except ValueError: # не удалось преобразовать в целое число, например 2.5
            self.main_display.setText("Введите целое число")
        except Exception:
            self.main_display.setText("Ошибка вычисления факториала")

    def get_grid_step(self, min_val, max_val): # автоматическое определение оптимального шага сетки
        range_val = max_val - min_val # вычисляет ширину диапазона
        # базовые шаги для разных масштабов
        if range_val <= 15:
            step = 1 # шаг сетки
        elif range_val <= 30:
            step = 2
        elif range_val <= 60:
            step = 5
        elif range_val <= 120:
            step = 10
        elif range_val <= 300:
            step = 20
        elif range_val <= 600:
            step = 50
        else:
            step = 100
        # округляем min и max до ближайших значений, кратных шагу
        start = math.floor(min_val / step) * step
        end = math.ceil(max_val / step) * step
        return step, start, end # возвращает шаг округленный мин и макс

    def toggle_sign(self): # смена знака числа
        current = self.main_display.text() # текущий текст из поля
        if not current or current in ["Ошибка", "Ошибка синтаксиса", "Введите выражение!"]:
            self.main_display.setText("0")
            return
        try:
            val = float(current)
            result = -val
            result_str = str(result) # обратно в строку
            if '.' in result_str: # убирает лишние нули в конце, 2.500 будет 2.5
                result_str = result_str.rstrip('0').rstrip('.')
            self.main_display.setText(result_str)
        except Exception:
            if current.startswith('-'): # текст с минуса
                self.main_display.setText(current[1:]) # убирает этот минус
            else:
                self.main_display.setText('-' + current)

    def calculate_main(self): # метод вычисления выражения
        raw = self.main_display.text().strip() # убираем пробелы по краям у текста
        self.error_label.setText("") # очищаем ошибки перед новым вычислением
        self.main_display.setStyleSheet("") # очистка красной рамки

        if len(raw) > 200:
            self.main_display.setText("Слишком длинное выражение")
            return

        raw = re.sub(r'(\d+)mod\((\d+)\)', r'\1 % \2', raw) # преобразуем 5mod(2) → 5 % 2

        if not raw or raw == "0" or raw == "Введите выражение":
            self.main_display.setText("Введите выражение!")
            return

        # автоматическое добавление нуля для операторов в начале/конце
        operators = ["+", "-", "*", "/", "%", "^"] # список операторов
        if raw[0] in operators and raw[0] != "-": # если начинается с оператора кроме минуса
            raw = "0" + raw
        if raw[-1] in operators: # если заканчивается оператором
            raw = raw + "0"

        if raw.count("(") > raw.count(")"): # проверка скобок с выводом ошибки прямо в поле ввода
            self.main_display.setText("Незакрытая скобка")
            return
        if raw.count(")") > raw.count("("):
            self.main_display.setText("Лишняя закрывающая скобка")
            return

        try: # пре-валидация специфичных математических ситуаций
            if "0^0" in raw or "0^(0)" in raw:
                self.main_display.setText("0⁰ – неопределённость")
                return

            if re.search(r'0\^\(-\d', raw) or "0^-" in raw:
                self.main_display.setText("Деление на ноль")
                return

            if "tan" in raw:
                match = re.search(r'tan\(([^)]+)\)', raw) # ищет конструкцию tan(число)
                if match: # вычисляет аргумент (число внутри скобок)
                    arg = float(safe_eval(match.group(1), self.angle_mode))
                    if self.angle_mode == "DEG" and (abs(arg % 180) == 90):
                        self.main_display.setText("Тангенс не определён для 90°")
                        return
                    elif self.angle_mode == "RAD" and np.isclose(abs(arg % np.pi), np.pi / 2):
                        self.main_display.setText("Тангенс не определён для 90°")
                        return

            if "asin" in raw or "acos" in raw:
                match = re.search(r'(asin|acos)\(([^)]+)\)', raw) # ищет asin(число), acos(число)
                if match: # вычисляет аргумент (число внутри скобок)
                    val = float(safe_eval(match.group(2), self.angle_mode))
                    if val < -1.0 or val > 1.0:
                        self.main_display.setText("Аргумент должен быть от -1 до 1")
                        return

            if "log" in raw or "ln" in raw:
                match = re.search(r'(log|ln)\(([^)]+)\)', raw) # log(число) ln(число)
                if match:
                    val = float(safe_eval(match.group(2), self.angle_mode))
                    if val <= 0:
                        self.main_display.setText("Логарифм от нуля или отрицательного числа")
                        return

            raw_eval = re.sub(r'(\d+)\^\(', r'\1**(', raw) # заменяет конструкцию число^( на число**(
            raw_eval = raw_eval.replace("^", "**") # замена оставшихся знаков
            res = safe_eval(raw_eval, self.angle_mode) # вычисление выражения через safe_eval

            # сохранение в историю и вывод результата
            formatted = str(round(res, 8)) # окр результат до 8 знаков после запятой и в строку преобразует
            self.hist_list.addItem(f"{raw} = {formatted}") # добавляет запись в формате выражение = результат
            self.save_history()
            self.main_display.setText(formatted) # вывод результата в поле ввода
            self.error_label.setText("")
            self.main_display.setStyleSheet("") # очистка красной рамки

        # обработка ошибок, вывод понятных сообщений
        except ZeroDivisionError:
            self.main_display.setText("Деление на ноль невозможно")
        except OverflowError:
            self.main_display.setText("Переполнение")
        except ValueError as e: # перехват ошибок значений
            error_msg = str(e)
            if "Деление на ноль невозможно" in error_msg:
                self.main_display.setText("Деление на ноль невозможно")
            elif "Корень из отрицательного числа" in error_msg:
                self.main_display.setText("Корень из отрицательного числа")
            elif "Логарифм от нуля" in error_msg or "Логарифм от нуля или отрицательного числа" in error_msg:
                self.main_display.setText("Логарифм от нуля или отрицательного числа")
            elif "Тангенс не определен" in error_msg:
                self.main_display.setText("Тангенс не определён для 90°")
            elif "0⁰" in error_msg:
                self.main_display.setText("0⁰ – неопределённость")
            elif "Аргумент должен быть от -1 до 1" in error_msg:
                self.main_display.setText("Аргумент должен быть от -1 до 1")
            elif "Переполнение" in error_msg:
                self.main_display.setText("Переполнение")
            elif "Введите выражение" in error_msg:
                self.main_display.setText("Введите выражение!")
            elif "Незакрытая скобка" in error_msg:
                self.main_display.setText("Незакрытая скобка")
            else:
                self.main_display.setText("Ошибка синтаксиса")
        except Exception: # общее сообщение об ошибке
            self.main_display.setText("Ошибка синтаксиса")

    # разделы
    def ui_history(self): # метод создания вкладки История
        w = QWidget() # виджет контейнер для вкладки
        l = QVBoxLayout(w) # вертикальный компоновщик для вкладки
        # noinspection PyArgumentList
        self.hist_list = QListWidget() # виджет списка для отображения истории

        self.hist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu) # режим контекстного меню пользовательское
        self.hist_list.customContextMenuRequested.connect(self.history_menu) # при клике ПКМ вызывается метод
        self.hist_list.itemDoubleClicked.connect(self.copy_history_item) # при двойном клике
        l.addWidget(self.hist_list) # добавляет список в вертикальный компоновщик
        btn = QPushButton("Очистить историю")
        btn.clicked.connect(self.clear_history)
        l.addWidget(btn)
        return w

    def history_menu(self, pos): # контекстное меню истории
        item = self.hist_list.itemAt(pos) # элемент списка, на который кликнули
        if not item: # мимо элемента
            return

        menu = QMenu(self) # контекстное меню
        insert_act = menu.addAction("Вставить") # добавить пункт
        copy_act = menu.addAction("Копировать")
        del_act = menu.addAction("Удалить")

        action = menu.exec(self.hist_list.mapToGlobal(pos)) # показывает меню в позиции клика
        if action == insert_act: # если выбрали вставить
            text = item.text() # берет текст записи
            if "=" in text:
                result = text.split("=")[1].strip() # берет только результат
            else:
                result = text
            self.main_display.setText(result) # в поле ввода вставка
        elif action == copy_act:
            text = item.text()
            if "=" in text:
                result = text.split("=")[1].strip()
            else:
                result = text
            QApplication.clipboard().setText(result) # копирует результат в буфер обмена
        elif action == del_act:
            self.hist_list.takeItem(self.hist_list.row(item))

    def copy_history_item(self, item): # двойной клик по истории
        text = item.text() # берет текст записи
        if "=" in text:
            result = text.split("=")[1].strip()
            current = self.main_display.text() # берет текущий текст из поля ввода
            if current in ["", "0", "Ошибка"]:
                self.main_display.setText(result) # замена содержимого поля на результат
            else:
                self.main_display.setText(current + result)

    def ui_matrix(self): # вкладка матрицы
        w = QWidget() # виджет контейнер
        l = QVBoxLayout(w) # вертикальный компоновщик

        l.addWidget(QLabel("<b>Матрица A</b>"))
        # noinspection PyArgumentList
        self.dim_a = QComboBox() # выпадающий список для выбора размерности матрицы а
        self.dim_a.addItems(["2x2", "2x3", "3x2", "3x3"])
        self.dim_a.currentIndexChanged.connect(self.update_matrix_grid) # изменяет сетку ввода при изменении выбора
        l.addWidget(self.dim_a) # добавляет список в компоновщик
        # noinspection PyArgumentList
        self.grid_a_layout = QGridLayout() # сеточный компоновщик для ввода элементов матрицы а
        l.addLayout(self.grid_a_layout)

        l.addWidget(QLabel("<b>Матрица B</b>"))
        # noinspection PyArgumentList
        self.dim_b = QComboBox()
        self.dim_b.addItems(["2x2", "2x3", "3x2", "3x3"])
        self.dim_b.currentIndexChanged.connect(self.update_matrix_grid)
        l.addWidget(self.dim_b)
        # noinspection PyArgumentList
        self.grid_b_layout = QGridLayout() # сеточный компоновщик для ввода элементов матрицы б
        l.addLayout(self.grid_b_layout)

        # noinspection PyArgumentList
        self.m_op = QComboBox()
        self.m_op.addItems([ # выбор всех операций
            "Сложение (A+B)",
            "Вычитание (A-B)",
            "Умножение (A*B)",
            "Транспонирование (A)",
            "Транспонирование (B)",
            "Детерминант (A)",
            "Детерминант (B)"])
        l.addWidget(self.m_op)

        btn = QPushButton("Вычислить")
        btn.setObjectName("PrimaryAccent") # стиль акцентной кнопки
        btn.clicked.connect(self.solve_matrix)
        l.addWidget(btn)

        self.m_expl = QTextEdit() # текстовое поле для вывода результата
        self.m_expl.setFont(QFont("Courier New", 12))
        self.m_expl.setReadOnly(True)
        self.m_expl.setFocusPolicy(Qt.FocusPolicy.NoFocus) # клик по полю не переключает на него внимание
        l.addWidget(self.m_expl)
        self.update_matrix_grid() # сразу создает сетки ввода для матриц
        return w

    @staticmethod # декоратор, метод не требует доступа к экземпляру класса
    def format_matrix(m): # метод принимающий матрицу
        if isinstance(m, np.ndarray): # является ли аргумент массивом NumPy
            str_rows = [[f"{v:.3g}" for v in row] for row in m] # преобразует все числа в строки с 3 значащими цифрами
            col_widths = [max(len(row[i]) for row in str_rows) for i in range(len(str_rows[0]))] # макс.ширина столбцов

            rows = [] # список для строк
            for row in str_rows: # выравнивает каждое значение по правому краю и объединяет с двумя пробелами
                formatted = "  ".join(val.rjust(col_widths[i]) for i, val in enumerate(row))
                rows.append(formatted)

            result = []
            for i, row in enumerate(rows): # перебор строк с индексом
                if i == 0:
                    result.append("⎛ " + row + " ⎞")
                elif i == len(rows) - 1:
                    result.append("⎝ " + row + " ⎠")
                else:
                    result.append("⎜ " + row + " ⎟")
            return "\n".join(result) # объединяет строки с переносами
        return str(round(m, 5)) # округляет и возвращает как строку

    def update_matrix_grid(self): # перестроение сеток матриц
        for g in [self.grid_a_layout, self.grid_b_layout]: # элементы 2х компоновщиков
            while g.count(): g.takeAt(0).widget().deleteLater() # удаляет первый элемент и его виджет

        def fill(dim, layout): # заполнение сетки
            r, c = int(dim[0]), int(dim[2]) # 2х2 r=2 c=2
            for i in range(r):
                for j in range(c):
                    e = QLineEdit() # поле для элемента матрицы
                    e.setPlaceholderText("0")
                    e.setFixedWidth(40)
                    e.setValidator(self.num_val)
                    layout.addWidget(e, i, j) # поле в сетку на позицию (строка, столбец)
        fill(self.dim_a.currentText(), self.grid_a_layout) # текст и расположение
        fill(self.dim_b.currentText(), self.grid_b_layout)

    def solve_matrix(self): # вычисление матричных операций
        try:
            def get_matrix(layout, dim): # для чтения матрицы из сетки
                r, c = int(dim[0]), int(dim[2])
                vals = [] # для элементов
                for i in range(layout.count()): # перебор всех полей в сетке
                    val = layout.itemAt(i).widget().text() # берет текст из каждого поля
                    vals.append(float(val) if val else 0.0)
                return np.array(vals).reshape(r, c) # преобразует список в массив и меняет форму на r c
            a = get_matrix(self.grid_a_layout, self.dim_a.currentText()) # чтение матриц
            b = get_matrix(self.grid_b_layout, self.dim_b.currentText())
            op = self.m_op.currentText() # берет выбранную операцию
            res = None # переменная для результата

            if "Сложение" in op:
                if a.shape != b.shape:
                    raise ValueError("Размеры матриц должны совпадать для сложения")
                res = a + b
            elif "Вычитание" in op:
                if a.shape != b.shape:
                    raise ValueError("Размеры матриц должны совпадать для вычитания")
                res = a - b
            elif "Умножение" in op:
                if a.shape[1] != b.shape[0]:
                    raise ValueError("Нельзя умножить матрицы! Число столбцов A ≠ числу строк B")
                res = np.dot(a, b)
            elif "Транспонирование (A)" in op:
                res = a.T
            elif "Транспонирование (B)" in op:
                res = b.T
            elif "Детерминант (B)" in op:
                if b.shape[0] != b.shape[1]: # число строк не равно числу столбцов
                    raise ValueError("Матрица B должна быть квадратной")
                res = np.linalg.det(b)
            elif "Детерминант (A)" in op:
                res = np.linalg.det(a)
            else:
                res = a.T # по умолчанию транспонирует А
            if res is None:
                raise ValueError("Не выбрана операция")
            self.m_expl.setText(self.format_matrix(res)) # форматирует результат и вывод в поле
        except Exception as e:
            self.m_expl.setText(str(e))

    def ui_graph(self): # вкладка график
        w = QWidget() # виджет контейнер
        l = QVBoxLayout(w) # вертикальный компоновщик для вкладки

        self.g_in = QLineEdit() # поле ввода
        self.g_in.setPlaceholderText("Введите выражение") # подсказка
        self.g_in.installEventFilter(self)  # отслеживаем клик для удаления ошибок
        self.g_in.textEdited.connect(self.clear_graph_error) # убирает красную рамку ошибки при вводе текста

        row = QHBoxLayout() # горизонтальный комп-к для строки
        label = QLabel("F(x) =")
        label.setStyleSheet("font-weight: bold;")
        row.addWidget(label) # добавляет метку в строку
        row.addWidget(self.g_in) # добавляет поле ввода в строку
        l.addLayout(row)

        self.xmin = QLineEdit() # диапазон, поле для мин значения по оси Х
        self.xmax = QLineEdit()
        self.ymin = QLineEdit()
        self.ymax = QLineEdit()

        self.xmin.setPlaceholderText("-10") # задаем дефолтные значения через подсказки (placeholder)
        self.xmax.setPlaceholderText("10")
        self.ymin.setPlaceholderText("-10")
        self.ymax.setPlaceholderText("10")

        self.xmin.installEventFilter(self) # принудительно регистрируем фильтр кликов (событий) для автоматической очистки
        self.xmax.installEventFilter(self)
        self.ymin.installEventFilter(self)
        self.ymax.installEventFilter(self)

        self.xmin.setValidator(self.num_val) # включаем валидатор, запрет букв
        self.xmax.setValidator(self.num_val)
        self.ymin.setValidator(self.num_val)
        self.ymax.setValidator(self.num_val)

        x_row = QHBoxLayout() # горизонт.комп-к для строки Х
        x_row.addWidget(QLabel("X: от"))
        x_row.addWidget(self.xmin)
        x_row.addWidget(QLabel("до"))
        x_row.addWidget(self.xmax)
        l.addLayout(x_row) # добавляет строку в вертик.комп-к

        y_row = QHBoxLayout() # горизонт.комп-к для строки Y
        y_row.addWidget(QLabel("Y: от"))
        y_row.addWidget(self.ymin)
        y_row.addWidget(QLabel("до"))
        y_row.addWidget(self.ymax)
        l.addLayout(y_row) # добавляет строку в вертик.комп-к

        self.fig = plt.Figure() # холст для графика, пустой объект
        self.ax = self.fig.add_subplot(111) # добавляет оси на холст (1 строка, 1 столбец, первый график)
        self.canvas = FigureCanvas(self.fig) # виджет для встраивания графика
        l.addWidget(self.canvas) # добавляет графическую область в вертикальный компоновщик

        btn = QPushButton("Построить")
        btn.clicked.connect(self.draw_graph)
        l.addWidget(btn)
        return w

    def draw_graph(self): # построение графика
        if self.ax is None or self.canvas is None: # сущ ли оси и холст для защиты от ошибок
            return
        try:
            expr = self.g_in.text().strip() # берет текст функции из поля ввода и убирает пробелы
            if not expr:
                self.g_in.setText("Введите выражение!")
                return

            xmin = float(self.xmin.text() or -10) # текст из поля Xmin,
            xmax = float(self.xmax.text() or 10) # если пусто — подставляет -10, преобразует в число
            ymin = float(self.ymin.text() or -10)
            ymax = float(self.ymax.text() or 10)

            if xmin >= xmax:  # защита от некорректных диапазонов
                self.g_in.setText("Xmin должно быть меньше Xmax")
                return
            if ymin >= ymax:
                self.g_in.setText("Ymin должно быть меньше Ymax")
                return
            if xmax - xmin < 0.001: # иначе шаг будет слишком мелким
                self.g_in.setText("Диапазон X слишком маленький")
                return

            x = np.linspace(xmin, xmax, 1000) # массив из 1000 точек

            safe_dict = { # расширенные функции и переменные для безопасного вычисления
                "np": np, # разрешает доступ к библиотеке numpy
                "x": x,
                "sin": np.sin, "cos": np.cos, "tan": np.tan,
                "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
                "log": np.log10, "ln": np.log, "sqrt": np.sqrt,
                "exp": np.exp, "abs": np.abs}

            # поддержка слитного умножения
            expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr) # 3х 3*х
            expr = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', expr) # x3 x*3
            expr = re.sub(r'(\))(\d)', r'\1*\2', expr) # )3 )*3
            expr = re.sub(r'(\d)(\()', r'\1*\2', expr)# 3( 3*(
            expr = expr.replace("^", "**")
            try:
                y = eval(expr, {"__builtins__": {}}, safe_dict) # вычисляет в безопасном окружении (без встр.функций)
            except Exception as e:
                self.g_in.setText("Ошибка в выражении")
                self.g_in.setStyleSheet("border: 2px solid red;")
                return

            # обработка результата
            y = np.asarray(y, dtype=float) # если это число, то делаем массив
            if y.ndim == 0: # результат — одно число (а не массив)
                y = np.full_like(x, y) # создаем массив, повторяем число для всех точек х
            y = np.where(np.isfinite(y), y, np.nan) # замена бесконечности на Nan (не число)
            if np.all(np.isnan(y)):
                self.g_in.setText("Функция не определена")
                return

            self.ax.clear() # очистка осей

            x_step, x_start, x_end = self.get_grid_step(xmin, xmax) # шаг сетки для оси х
            y_step, y_start, y_end = self.get_grid_step(ymin, ymax) # шаг сетки для оси y

            # устанавливаем деления с автоматическим шагом
            self.ax.set_xticks(np.arange(x_start, x_end + x_step, x_step))
            self.ax.set_yticks(np.arange(y_start, y_end + y_step, y_step))
            self.ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.7) # вкл сетку

            self.ax.axhline(0, linewidth=1.5) # рисует горизонт.ось на уровне y =0
            self.ax.axvline(0, linewidth=1.5) # рисует вертик.ось на уровне x =0

            self.ax.spines['top'].set_visible(False) # скрывает верхнюю рамку
            self.ax.spines['right'].set_visible(False) # скрывает правую рамку

            if abs(xmax - xmin) > 100:
                self.g_in.setText("Слишком большой диапазон")
                return
            self.ax.plot(x, y, linewidth=2) # строит график функции
            if xmin >= xmax or ymin >= ymax:
                self.g_in.setText("Неверный диапазон")
                return

            self.ax.set_xlim(xmin, xmax) # устанавливает пределы отображения по оси X
            self.ax.set_ylim(ymin, ymax)

            self.ax.set_ylabel("Y", loc="top", rotation=0) # подпись вверху оси без поворота
            # координаты смещения: -0.05 уводит букву влево от оси Y, 1.02 приподнимает над графиком
            self.ax.yaxis.set_label_coords(-0.05, 1.02)
            self.canvas.draw() # перерисовывает график, отображает изменения

            for spine in self.ax.spines.values(): # перебор всех рамок и их скрытие
                spine.set_visible(False)

            # оси со стрелками
            self.ax.annotate('', xy=(xmax, 0), xytext=(xmin, 0),
                             arrowprops=dict(arrowstyle='->', linewidth=1.5))
            # рисует стрелку вдоль оси X от xmin до xmax
            self.ax.annotate('', xy=(0, ymax), xytext=(0, ymin),
                             arrowprops=dict(arrowstyle='->', linewidth=1.5))

            self.ax.text(xmax, 0, "x", ha='right', va='bottom') # подписи осей у стрелок
            self.ax.text(0, ymax, "y", ha='left', va='top')
            self.ax.set_aspect('auto', adjustable='box') # устанавливает автоматическое соотношение сторон
            self.fig.tight_layout() # убирает лишние отступы
            self.canvas.draw()
        except Exception as e:
            print(e)
            if self.g_in is not None: # если поле ввода существует
                self.g_in.setText(str(e))
                self.g_in.setStyleSheet("border: 2px solid red;")

    def clear_graph_error(self): # очистка ошибок в поле графика при вводе текста
        self.g_in.setStyleSheet("") # убираем красную рамку
        current_text = self.g_in.text() # берем текст из поля
        if current_text in ["Ошибка в выражении", "Введите выражение!",
                            "Функция не определена", "Xmin должно быть меньше Xmax",
                            "Ymin должно быть меньше Ymax", "Диапазон X слишком маленький",
                            "Слишком большой диапазон", "Неверный диапазон"]:
            self.g_in.clear()

    def open_params(self): # окно параметров
        d = QDialog(self) # всплывающее окно с привязкой к гл.окну
        theme = THEMES.get(self.saved_theme, THEMES["light"])

        # установка фона параметров и скруглений для окон
        d.setStyleSheet(f"""
            QDialog {{ 
                background-color: {theme['bg']}; }}
            QLabel {{ 
                color: {theme['text']}; 
                font-family: Inter;}}""") # шрифт для всех меток
        d.setFixedSize(360, 420)
        d.setWindowTitle("Параметры")
        l = QVBoxLayout(d) # вертик.комп-к для окна

        title_label = QLabel("<b>ПАРАМЕТРЫ</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # выравнивание по центру
        l.addWidget(title_label)

        l.addWidget(QLabel("Цветовая тема:"))

        # noinspection PyArgumentList
        self.theme_select = QComboBox() # выбор цветовой темы с помощью выпадающего списка
        self.theme_select.addItems(["Светлая", "Темная", "Зеленая", "Синяя"])

        mapping = {"light": 0, "dark": 1, "green": 2, "blue": 3} # словарь для перевода названия темы в индекс
        rev_mapping = {0: "light", 1: "dark", 2: "green", 3: "blue"}
        self.theme_select.setCurrentIndex(mapping.get(self.saved_theme, 0)) # устан. текущ.выбран.элемент в списке

        # функция смены темы «на лету» без закрытия окна параметров
        def on_theme_changed(index):
            chosen_key = rev_mapping.get(index, "light") # тема по индексу
            self.apply_theme_color(chosen_key) # применяем ко всему приложению
            new_theme = THEMES[chosen_key] # получаем цвета новой темы
            # без перезапуска обновляет фон и цвет текста в окне
            d.setStyleSheet(
                f"QDialog {{ background-color: {new_theme['bg']}; }} QLabel {{ color: {new_theme['text']}; }}")

        self.theme_select.currentIndexChanged.connect(on_theme_changed) # вызов функции при выборе новой темы
        l.addWidget(self.theme_select) # добавляем список в комп-к

        # выбор измерений
        l.addSpacing(10) # вертик.отступ
        l.addWidget(QLabel("Выбор измерений:"))
        h_m = QHBoxLayout() # горзионт.комп-к для кнопок DEG/RAD
        for m in ["DEG", "RAD"]:
            b = QPushButton(m) # кнопка с названием измерений
            b.clicked.connect(lambda ch, mode=m: self.update_meas(mode)) # функция с нужным режимом
            h_m.addWidget(b)
        l.addLayout(h_m)

        # сведения
        l.addSpacing(15)
        info_label = QLabel("<b>СВЕДЕНИЯ</b>")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(info_label)

        version_label = QLabel("Приложение разработано на Python, версия 0.1")
        l.addWidget(version_label)

        l.addSpacing(15)
        btn = QPushButton("Закрыть")
        btn.setObjectName("TallBtn") # стиль высокой кнопки
        btn.clicked.connect(d.accept) # accept - успешное завершение
        l.addWidget(btn)

        # принудительно обновляем стили созданных внутри диалога кнопок
        self.apply_theme_color(self.saved_theme)
        d.exec() # запуск диалог.окна

    def apply_theme_color(self, theme_name): # применение цветовой темы
        if theme_name not in THEMES:
            theme_name = "light"

        theme = THEMES[theme_name]
        self.saved_theme = theme_name # сохраняет название темы в переменную объекта

        # массовое обновление стилей. блокируем сигналы (события), чтобы избежать критического вылета 0xC0000409
        self.blockSignals(True)

        for btn in self.findChildren(QPushButton): # все кнопки на интерфейсе
            t = btn.text()
            if t in ["Построить", "Вычислить", "Закрыть", "Очистить историю"]:
                btn.setObjectName("TallBtn") # высокие, жирные кнопки
            elif t in ["История", "Матрицы", "График"]:
                if btn.objectName() != "ActiveTab":
                    btn.setObjectName("TabButton") # обычный стиль вкладки
            elif t in ["C", "DEL", "=", "Тригонометрия"]:
                btn.setObjectName("SpecialBtn")
            elif t in ["DEG", "RAD"]:
                if t == self.angle_mode: # текст совпадает с текущим режимом
                    btn.setObjectName("ModeActive")
                else:
                    btn.setObjectName("ModeInactive") # стиль неактивной кнопки
            btn.style().unpolish(btn) # убирает старые стили
            btn.style().polish(btn)

        # применяет стили ко всему интерфейсу
        self.setStyleSheet(f"""
            QMainWindow {{ background: {theme['bg']}; }}
            #Card {{ background: {theme['card']}; border-radius: 12px; border: 1px solid {theme['border']}; }}
            * {{ color: {theme['text']}; font-family: Inter; }}

            /* Скругленные кнопки */
            QPushButton {{
                background: {theme['btn_default']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                min-height: 35px;}}
            QPushButton#DefaultBtn {{ background: {theme['btn_default']}; }}
            QPushButton#SpecialBtn {{ background: {theme['special_btn_bg']}; }}

            QPushButton#ActiveTab {{
                background: {theme['special_btn_bg']};
                font-weight: bold;
                border: 2px solid {theme['text']};}}

            /* Кнопки Очистить историю, Вычислить, Построить увеличены */
            QPushButton#TallBtn {{
                background: {theme['special_btn_bg']};
                font-weight: bold;
                min-height: 48px;
                min-width: 170px;
                font-size: 14px;}}

            /* Выделение кнопок измерения под цвет фона панели */
            QPushButton#ModeActive {{
                background: {theme['card']};
                border: 2px solid {theme['text']};
                font-weight: bold;}}

            /* Поля ввода калькулятора, выражений графиков, истории, ввода и решения матриц */
            QLineEdit, QTextEdit, QListWidget {{
                background: {theme['input_bg']};
                color: #000000 !important; /* Строго чёрный текст для читаемости на белом фоне */
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 5px;}}
            QLineEdit::placeholder {{
                color: #888888;}}

            /* Увеличенный выпадающий список Тригонометрия (в закрытом состоянии) */
            QComboBox {{
                background: {theme['special_btn_bg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 4px;
                min-width: 180px;
                color: {theme['text']} !important; /* белый текст для названия закрытого списка */}}

            /* Раскрывающийся список (Тригонометрия, Действия в истории) — светлый фон, чёрный текст */
            QComboBox QAbstractItemView {{
                background: {theme['input_bg']};
                border-radius: 6px;
                border: 1px solid {theme['border']};
                color: #000000 !important; /* строго чёрный текст элементов при раскрытии */}}
            QComboBox QAbstractItemView::item {{
                color: #000000 !important;}}
            QComboBox QAbstractItemView::item:selected {{
                background-color: rgba(0, 0, 0, 0.1);
                color: #000000 !important;}}

            /* Контекстное меню при ПКМ (Вставить, Копировать, Удалить) — светлый фон, чёрный текст */
            QMenu {{
                background: {theme['input_bg']} !important;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 4px;}}
            QMenu::item {{
                background: transparent;
                color: #000000 !important; /* чёрный текст для пунктов контекстного меню */}}
            QMenu::item:selected {{
                background-color: rgba(0, 0, 0, 0.1);
                color: #000000 !important;}}
        """)

        # принудительно применяем цвет текста для диапазонов графика, если они существуют
        if hasattr(self, 'xmin') and self.xmin: # сущ ли поля диапазонов графика
            for field in [self.xmin, self.xmax, self.ymin, self.ymax]:
                if field:
                    field.setStyleSheet(f"background: {theme['special_btn_bg']}; color: #000000; border-radius: 8px;")

        self.prefs.setValue("theme_color", theme_name)  # сохраняем выбранную тему в настройки
        self.blockSignals(False)  # возвращаем сигналы

    def update_meas(self, mode): # обновление режима углов
        self.angle_mode = mode # установка нового режима (DEG или RAD)
        self.prefs.setValue("angle_mode", mode) # сохраняет режим в настройки
        self.apply_theme_color(self.saved_theme) # переприменяет тему, чтобы обновить стиль кнопок
        sender_btn = self.sender() # кнопка, которая вызвала метод
        if sender_btn:
            parent_dialog = sender_btn.window() # получает родительское окно (диалог параметров)
            if isinstance(parent_dialog, QDialog):
                theme = THEMES[self.saved_theme]
                parent_dialog.setStyleSheet(
                    f"QDialog {{ background-color: {theme['bg']}; }} QLabel {{ color: {theme['text']}; }}")

    def insert_text(self, text): # вставка текста в поле ввода
        if self._inserting: # защита от рекурсии
            return # вставка уже идёт — выходит
        self._inserting = True # флаг, что началась вставка
        try:
            current = self.main_display.text() # текущий текст из поля ввода
            if len(current) > 100 and text not in ["C", "DEL", "="]: # и вставляется не управляющая кнопка
                self.error_label.setText("Достигнут лимит символов")
                return
            # если есть активное поле, то вставляет туда, иначе в главный дисплей
            target = self.last_focused_input if self.last_focused_input else self.main_display
            current = target.text() # текст из целевого поля

            if self.second_func:
                target.setText(current + text)
                self.second_func = False
                self.trig_btn.setText("Тригонометрия")
                self.trig_btn.setStyleSheet("") # сбрасывает стили кнопки
                return

            # очистка дефолтного нуля или старых ошибок перед вводом нового текста
            if current in ["0", "Ошибка", "Введите выражение!", "Ошибка синтаксиса"]:
                current = ""

            operators = ["+", "-", "*", "/", "%", "^"] # список операторов
            # два оператора подряд, то заменяем старый оператор на самый последний введенный
            if text.strip() in operators and current and current[-1] in operators:
                current = current[:-1] # удаляет старый оператор

            # точка без цифр, автоматическое добавление нуля ("0.")
            if text == ".":
                if not current or current[-1] in ["+", "-", "*", "/", "(", ")", "%", "^"]:
                    text = "0."
                else: # если после цифры, то находим последнее число в выражении
                    last_number = re.split(r'[+\-*/()^%]', current)[-1]
                    if "." in last_number: # если уже есть точка, то игнор
                        return

            # стандартная вставка и сброс состояния интерфейса
            target.setText(current + text) # вставляет текст в поле
            self.error_label.setText("")
            self.main_display.setStyleSheet("") # убирает красную рамку
        finally:
            self._inserting = False # снимает флаг защиты от рекурсии

    def switch_tab(self, idx): # переключение вкладок
        self.stack.setCurrentIndex(idx) # переключает стековый виджет на страницу с индексом idx
        for i, btn in enumerate(self.tab_buttons): # перебор всех кнопкок вкладок
            btn.setObjectName("ActiveTab" if i == idx else "TabButton") # если индекс совпал, то активной делает
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def eventFilter(self, obj, event): # фильтр событий
        # если событие — получение фокуса и объект — поле ввода
        if event.type() == QEvent.Type.FocusIn and isinstance(obj, QLineEdit):
            self.last_focused_input = obj # запоминает активное поле
            txt = obj.text().strip() # берёт текст из поля и убирает пробелы

            # расширенный список ошибок, очистка
            if txt in ["0", "Ошибка", "Ошибка синтаксиса", "Функция не определена", "Введите выражение",
                       "Введите выражение!", "Неверный диапазон", "Слишком большой диапазон",
                       "Деление на ноль невозможно", "Переполнение", "Корень из отрицательного числа",
                       "Логарифм от нуля или отрицательного числа", "0 ⁰  – неопределённость",
                       "Деление на ноль", "Тангенс не определён для 90°",
                       "Аргумент должен быть от -1 до 1", "Незакрытая скобка", "Лишняя закрывающая скобка",
                       "Недопустимые символы", "Недопустимые символы очищены",
                       "Ошибка выражения", "Слишком длинное выражение",
                       "Ошибка в выражении", "Xmin должно быть меньше Xmax",
                       "Ymin должно быть меньше Ymax", "Диапазон X слишком маленький",
                       "Введите число", "Факториал только для неотрицательных",
                       "Введите целое число", "Ошибка вычисления факториала"]:
                obj.clear()

                # если это поле ввода графика (g_in), то сбрасываем его красную рамку
                if hasattr(self, 'g_in') and obj == self.g_in:
                    obj.setStyleSheet("")

            # если объект — одно из полей диапазона графика
            elif hasattr(self, 'xmin') and self.xmin and obj in [self.xmin, self.xmax, self.ymin, self.ymax]:
                if txt in ["-10", "10"]:
                    obj.clear() # очистка значений по умолчанию при вводе
        # вызывает родительскую версию метода, чтобы остальные события обрабатывались как обычно
        return super().eventFilter(obj, event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = EngineeringApp()
    # noinspection PyUnresolvedReferences
    ex.show()
    sys.exit(app.exec())