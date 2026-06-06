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


STYLE = """
QMainWindow {
    background: transparent;
}

/* Карточки */
#Card {
    border-radius: 20px;
    border: 1px solid rgba(0,0,0,0.25);
}

/* Общие кнопки */
QPushButton {
    border-radius: 10px;
    border: 1px solid rgba(0,0,0,0.25);
    min-height: 35px;
    font-size: 14px;
    padding: 6px;
}

/* Hover */
QPushButton:hover {
    opacity: 0.9;
}

/* Основной акцент */
QPushButton#PrimaryAccent {
    font-weight: bold;
    font-size: 16px;
    min-height: 50px;
}

/* Вторичный акцент */
QPushButton#SecondaryAccent {
    font-weight: bold;
}

#TabButton {
    font-weight: 600;
}

#ActiveTab {
    font-weight: 700;
    border: 2px solid rgba(0,0,0,0.4);
}

/* Поля ввода */
QLineEdit, QTextEdit, QListWidget {
    border-radius: 8px;
    border: 1px solid rgba(0,0,0,0.25);
    padding: 6px;
}

/* TOOLTIP */
QToolTip {
    border-radius: 6px;
}

/* MENU */
QMenu {
    border: 1px solid rgba(0,0,0,0.2);
}

/* COMBOBOX */
QComboBox {
    border-radius: 6px;
    padding: 5px;
    border: 1px solid rgba(0,0,0,0.3);
}

QComboBox QAbstractItemView {
    selection-background-color: #FFC04B;
    selection-color: #000;
}
QPushButton#CloseBtn {
    background: transparent;
    border: 1px solid {theme['border']};
    color: {theme['text']};
    font-weight: bold;
}
QPushButton#ModeActive {
    background: {theme['accent']};
    color: {theme['accent_text']};
    font-weight: bold;
    border: 2px solid {theme['border']};
}

QPushButton#ModeActive:hover {
    background: {theme['selection_bg']};
}
QPushButton#CloseBtn:hover {
    background: {theme['selection_bg']};
    color: {theme['accent_text']};
}
QPushButton#SecondActive {
    background: #FFA500;
    color: black;
    font-weight: bold;
}
/* LIST */
QListWidget::item:selected {
    border-radius: 6px;
}
"""

# цветовые темы: светлая, тёмная, зелёная, синяя
THEMES = {
    "light": {
        "bg": "#FFFFFF",          # фон окна
        "card": "#E0E0E0",        # фон карточек
        "input_bg": "#FFFFFF",    # фон полей ввода
        "btn_default": "#E0E0E0", # обычные кнопки
        "special_btn_bg": "#D9D9D9", # важные кнопки (C, DEL, =)
        "text": "#000000", # цвет текста
        "border": "#B0B0B0" # цвет границ
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

def safe_eval(expr, angle_mode):
    # безопасное вычисление выражения с поддержкой тригонометрии и логарифмов
    if not expr.strip():
        raise ValueError("Введите выражение!")

    # ^ → ** для возведения в степень
    expr = expr.replace("^", "**")

    # проверка лишних закрывающих скобок (быстрая защита)
    if expr.count(")") > expr.count("("):
        raise ValueError("Лишняя закрывающая скобка")

    # чистка точек (аккуратно, чтобы не ломать числа)
    expr = re.sub(r'(?<!\d)\.(?!\d)', '0.', expr)

    # защита от кривых операторов в начале/конце, добавляем 0
    if expr and expr[0] in "+*/":
        expr = "0" + expr

    if expr and expr[-1] in "+-*/":
        expr += "0"

    # специальные случаи степени
    if "0**0" in expr:
        raise ValueError("0⁰ — неопределенность")

    if re.search(r"0\*\*-\d+", expr):
        raise ValueError("Деление на ноль")

    # проверка скобок
    if expr.count("(") != expr.count(")"):
        raise ValueError("Незакрытая скобка")

    # запрещенные символы
    if re.search(r"[a-zA-Z]+", expr) and not re.search(r"(sin|cos|tan|log|ln|sqrt|exp)", expr):
        raise ValueError("Недопустимые символы")

    def mod(x, y):
        return x % y

    # функции
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


    def sqrt(x):
        if x < 0:
            raise ValueError("Корень из отрицательного числа")
        return math.sqrt(x)

    def log(x):
        if x <= 0:
            raise ValueError("Логарифм от нуля или отрицательного числа")
        return math.log10(x)

    def ln(x):
        if x <= 0:
            raise ValueError("Логарифм от нуля или отрицательного числа")
        return math.log(x)

    try:
        result = eval(expr, {
            "__builtins__": {},
            "sin": sin, "cos": cos, "tan": tan,
            "asin": asin, "acos": acos, "atan": math.atan,
            "sqrt": sqrt, "log": log, "ln": ln,
            "abs": abs,
            "exp": math.exp, "pi": math.pi, "e": math.e,
            "mod": mod,
        })

        if abs(result) > 1e308:
            raise OverflowError

        return result

    except ZeroDivisionError:
        raise ValueError("Деление на ноль невозможно")
    except OverflowError:
        raise ValueError("Переполнение")
    except Exception:
        raise ValueError("Ошибка выражения")


# noinspection PyUnresolvedReferences
class EngineeringApp(QMainWindow):
    # главное окно инженерного калькулятора
    def __init__(self):
        super().__init__()

        # сохранение темы и режима углов при выключении
        self.prefs = QSettings("MyCompany", "CalculatorApp")
        self.setWindowTitle("Инженерный калькулятор")

        # загрузка сохраненных параметров
        self.angle_mode = self.prefs.value("angle_mode", "RAD")
        self.saved_theme = self.prefs.value("theme_color", "light")

        self.last_focused_input = None # последнее активное поле ввода
        self.memory = 0.0 # ячейка памяти (упрощённая)
        self.second_func = False  # режим 2nd (обратные функции)
        self.btn_2nd = None  # для хранения кнопки 2nd
        self.history_file = "history.json"

        # запрет символов
        self.num_val = QRegularExpressionValidator(QRegularExpression(r"^-?\d*\.?\d*$"))
        self.math_val = QRegularExpressionValidator(QRegularExpression(r"[0-9.+\-*/()%^]*"))

        self.init_ui()
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
        self.shortcut_select.activated.connect(self.main_display.selectAll)
        self.apply_theme_color(self.saved_theme)
        self.showMaximized()
        self.update_clear_button()

        # переопределяем метод вставки из буфера обмена для контроля нечисловых букв
        def custom_paste():
            clipboard_text = QApplication.clipboard().text()
            # оставляем только цифры, математические операторы, скобки и точки
            filtered_text = re.sub(r'[^0-9.+\-*/()^%a-zA-Z]', '', clipboard_text)
            # если текст содержал запрещенные буквы (русские буквы, спецсимволы), пишем предупреждение
            if len(filtered_text) != len(clipboard_text):
                self.error_label.setText("Недопустимые символы очищены")
            self.insert_text(filtered_text)

        self.main_display.paste = custom_paste

    def load_history(self):
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.hist_list.addItem(item)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # noinspection PyTypeChecker
    def save_history(self):
        data = [self.hist_list.item(i).text() for i in range(self.hist_list.count())]
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # noinspection PyTypeChecker
    def clear_history(self):
        self.hist_list.clear()
        with open(self.history_file, "w") as f:
            json.dump([], f)

    def update_clear_button(self):
        for btn in self.findChildren(QPushButton):
            if btn.text() in ["C"]:
                if self.main_display.text() == "0":
                    btn.setText("C")

    def init_ui(self):
        # создание интерфейса: левая панель с кнопками, правая с режимами
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # левая панель, калькулятор
        self.left_card = QFrame(central)
        self.left_card.setObjectName("Card")
        left_vbox = QVBoxLayout(self.left_card)

        top_row = QHBoxLayout()
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(50, 50)
        self.settings_btn.clicked.connect(self.open_params)

        self.trig_btn = QPushButton("Тригонометрия")
        self.trig_btn.setFixedHeight(50)
        trig_menu = QMenu(self)
        trig_menu.setStyleSheet("""
        QMenu {
            background: #FFFFFF;
            border: 1px solid #999;
        }
        QMenu::item:selected {
            background-color: #FFC04B;
            color: #000000;
        }
        """)
        # функции с проверкой 2nd
        def make_handler(func_name):
            def handler():
                if self.second_func and func_name in ['sin', 'cos', 'tan']:
                    # если 2nd включён, вставляем обратную функцию
                    self.insert_text("a" + func_name + "(")
                    self.second_func = False
                    self.btn_2nd.setText("2nd")
                    self.btn_2nd.setObjectName("")
                    self.btn_2nd.setStyleSheet("")
                    self.trig_btn.setText("Тригонометрия")
                else:
                    self.insert_text(func_name + "(")

            return handler
        for f in ['sin', 'cos', 'tan', 'asin', 'acos', 'atan']:
            a = QAction(f, self)
            # для asin, acos, atan не нужно преобразование
            if f in ['asin', 'acos', 'atan']:
                a.triggered.connect(lambda ch, func=f: self.insert_text(func + "("))
            else:
                a.triggered.connect(make_handler(f))
            trig_menu.addAction(a)

        self.trig_btn.setMenu(trig_menu)

        top_row.addWidget(self.settings_btn)
        top_row.addWidget(self.trig_btn)
        top_row.addStretch()
        left_vbox.addLayout(top_row)

        self.main_display = QLineEdit("0")
        self.main_display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.main_display.setFixedHeight(80)
        self.main_display.setFont(QFont("Inter", 24))
        self.main_display.setValidator(self.math_val)
        self.main_display.installEventFilter(self)
        left_vbox.addWidget(self.main_display)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 12px;")
        left_vbox.addWidget(self.error_label)

        # noinspection PyArgumentList
        grid = QGridLayout()
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

        for r, row in enumerate(buttons):
            for c, text in enumerate(row):
                btn = QPushButton(text)
                if text in tips: btn.setToolTip(tips[text])
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                if text in ['C', 'DEL']:
                    btn.setObjectName("SecondaryAccent")
                elif text == '=':
                    btn.setObjectName("PrimaryAccent")
                btn.clicked.connect(lambda ch, t=text: self.on_calc_click(t))
                if text == "2nd":
                    self.btn_2nd = btn
                grid.addWidget(btn, r, c)
        left_vbox.addLayout(grid, stretch=1)
        main_layout.addWidget(self.left_card, 2)

        # правая панель, вкладки
        self.right_card = QFrame(central)
        self.right_card.setObjectName("Card")
        right_vbox = QVBoxLayout(self.right_card)

        self.tabs_nav = QHBoxLayout()
        self.tab_buttons = []
        for i, name in enumerate(["История", "Матрицы", "График"]):
            b = QPushButton(name)
            b.clicked.connect(lambda ch, idx=i: self.switch_tab(idx))
            self.tabs_nav.addWidget(b)
            self.tab_buttons.append(b)
        right_vbox.addLayout(self.tabs_nav)

        self.stack = QStackedWidget(central)
        self.stack.addWidget(self.ui_history())
        self.stack.addWidget(self.ui_matrix())
        self.stack.addWidget(self.ui_graph())
        right_vbox.addWidget(self.stack)

        self.switch_tab(0)
        main_layout.addWidget(self.right_card, 3)

    def memory_store(self):
        try:
            val = float(safe_eval(self.main_display.text(), self.angle_mode))
            self.memory_value = val
        except Exception:
            self.main_display.setText("Ошибка синтаксиса")

    def memory_plus(self):
        try:
            val = float(safe_eval(self.main_display.text(), self.angle_mode))
            if not hasattr(self, 'memory_value') or self.memory_value is None:
                self.memory_value = 0.0
            self.memory_value += val
        except Exception:
            self.main_display.setText("Ошибка синтаксиса")

    def memory_minus(self):
        try:
            val = float(safe_eval(self.main_display.text(), self.angle_mode))
            if not hasattr(self, 'memory_value') or self.memory_value is None:
                self.memory_value = 0.0
            self.memory_value -= val
        except Exception:
            self.main_display.setText("Ошибка синтаксиса")

    def memory_recall(self):
        # ТЗ: извлечение из пустой памяти (MR без сохранения) – вывод 0
        if not hasattr(self, 'memory_value') or self.memory_value is None:
            self.main_display.setText("0")
        else:
            self.main_display.setText(str(round(self.memory_value, 8)))

    def memory_clear(self):
        self.memory_value = None

    def insert_asin(self):
        # очищаем 0 или ошибку перед вставкой
        current = self.main_display.text()
        if current in ["0", "Ошибка", "Введите выражение!", "Ошибка синтаксиса"]:
            self.main_display.setText("")
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

    def on_calc_click(self, t):
        # обработка 2nd
        if t == "2nd":
            self.second_func = not self.second_func
            if self.second_func:
                self.btn_2nd.setText("2nd ON")
                self.btn_2nd.setObjectName("SecondActive")
                self.btn_2nd.style().unpolish(self.btn_2nd)
                self.btn_2nd.style().polish(self.btn_2nd)
            else:
                self.btn_2nd.setText("2nd")
                self.btn_2nd.setObjectName("")
                self.btn_2nd.setStyleSheet("")
            return

        # не сбрасываем поле, если в нём есть математические функции
        """if self.main_display.text() not in ["0"] and not re.match(r"^[0-9.+\-*/()^a-zA-Z\s]*$",
                                                                  self.main_display.text()):
            self.main_display.setText("0")"""

        if t == "DEL":
            txt = self.main_display.text()
            self.main_display.setText(txt[:-1] if len(txt) > 1 else "0")
        elif t == "C":
            # полный сброс
            self.main_display.setText("0")
            self.memory = 0.0
            self.error_label.setText("")
        elif t == "=":
            self.calculate_main()
        elif t == "MS":
            self.memory = float(self.main_display.text().replace("Ошибка", "0") or 0)
        elif t == "MR":
            if self.memory == 0:
                self.error_label.setText("Память пуста")
                return
            self.insert_text(str(self.memory))
        elif t == "MC":
            self.memory = 0.0
        elif t == "M+":
            self.memory += float(self.main_display.text().replace("Ошибка", "0") or 0)
        elif t == "M-":
            self.memory -= float(self.main_display.text().replace("Ошибка", "0") or 0)
        elif t == "n!":
            self.apply_factorial()
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
                self.second_func = False
                self.trig_btn.setText("Тригонометрия")
                self.trig_btn.setStyleSheet("")
                self.insert_text("sqrt(")
            else:
                # обычный режим: берём число на экране и вычисляем корень
                try:
                    val = float(self.main_display.text())
                    if val < 0:
                        self.error_label.setText("Корень из отрицательного")
                        return
                    result = math.sqrt(val)
                    self.hist_list.addItem(f"√({val}) = {result}")
                    self.save_history()
                    self.main_display.setText(str(result))
                except Exception:
                    self.main_display.setText("Ошибка")
        elif t == "sin":
            if self.second_func:
                self.insert_asin()
                self.second_func = False
                self.trig_btn.setText("Тригонометрия")
            else:
                self.insert_text("sin(")
        elif t == "cos":
            if self.second_func:
                self.insert_acos()
                self.second_func = False
                self.trig_btn.setText("Тригонометрия")
            else:
                self.insert_text("cos(")
        elif t == "tan":
            if self.second_func:
                self.insert_atan()
                self.second_func = False
                self.trig_btn.setText("Тригонометрия")
            else:
                self.insert_text("tan(")
        elif t == "π":
            self.insert_text("3.14159")
        elif t == "e":
            self.insert_text("2.71828")
        else:
            self.insert_text(t)
        self.update_clear_button()

    def apply_factorial(self):
        try:
            val = int(safe_eval(self.main_display.text(), self.angle_mode))
            if val < 0:
                raise ValueError("Факториал отрицательного")
            res = math.factorial(val)
            self.hist_list.addItem(f"{val}! = {res}")
            self.save_history()
            self.main_display.setText(str(res))
        except Exception as e:
            self.main_display.setText(str(e))

    def toggle_sign(self):
        current = self.main_display.text()
        try:
            val = float(current)
            result = -val
            self.main_display.setText(str(result))
        except Exception:
            # Если не число, добавляем минус в начало
            if current.startswith('-'):
                self.main_display.setText(current[1:])
            else:
                self.main_display.setText('-' + current)

    def calculate_main(self):
        # вычисление выражения с обработкой всех ошибок
        raw = self.main_display.text().strip()

        # преобразуем 5mod(2) → 5 % 2
        raw = re.sub(r'(\d+)mod\((\d+)\)', r'\1 % \2', raw)

        # пустой ввод
        if not raw or raw == "0" or raw == "Введите выражение":
            self.main_display.setText("Введите выражение!")
            return

        # автоматическое добавление нуля для операторов в начале/конце
        operators = ["+", "-", "*", "/", "%", "^"]
        if raw[0] in operators and raw[0] != "-":
            raw = "0" + raw
        if raw[-1] in operators:
            raw = raw + "0"

        # проверка скобок с выводом ошибки прямо в поле ввода
        if raw.count("(") > raw.count(")"):
            self.main_display.setText("Незакрытая скобка")
            return
        if raw.count(")") > raw.count("("):
            self.main_display.setText("Лишняя закрывающая скобка")
            return

        try:
            # пре-валидация специфичных математических ситуаций из ТЗ
            if "0^0" in raw or "0^(0)" in raw:
                self.main_display.setText("0⁰ – неопределённость")
                return

            if re.search(r'0\^\(-\d', raw) or "0^-" in raw:
                self.main_display.setText("Деление на ноль")
                return

            if "tan" in raw:
                match = re.search(r'tan\(([^)]+)\)', raw)
                if match:
                    arg = float(safe_eval(match.group(1), self.angle_mode))
                    if self.angle_mode == "DEG" and (abs(arg % 180) == 90):
                        self.main_display.setText("Тангенс не определён для 90°")
                        return
                    elif self.angle_mode == "RAD" and np.isclose(abs(arg % np.pi), np.pi / 2):
                        self.main_display.setText("Тангенс не определён для 90°")
                        return

            if "asin" in raw or "acos" in raw:
                match = re.search(r'(asin|acos)\(([^)]+)\)', raw)
                if match:
                    val = float(safe_eval(match.group(2), self.angle_mode))
                    if val < -1.0 or val > 1.0:
                        self.main_display.setText("Аргумент должен быть от -1 до 1")
                        return

            if "log" in raw or "ln" in raw:
                match = re.search(r'(log|ln)\(([^)]+)\)', raw)
                if match:
                    val = float(safe_eval(match.group(2), self.angle_mode))
                    if val <= 0:
                        self.main_display.setText("Логарифм от нуля или отрицательного числа")
                        return

            # вычисление выражения через ваш safe_eval
            raw_eval = re.sub(r'(\d+)\^\(', r'\1**(', raw)
            raw_eval = raw_eval.replace("^", "**")
            res = safe_eval(raw_eval, self.angle_mode)

            # сохранение в историю и вывод результата
            formatted = str(round(res, 8))
            self.hist_list.addItem(f"{raw} = {formatted}")
            self.save_history()

            self.main_display.setText(formatted)
            self.error_label.setText("")
            self.main_display.setStyleSheet("")

        # все математические ошибки выводятся в текстовое поле ввода
        except ZeroDivisionError:
            self.main_display.setText("Деление на ноль невозможно")
        except OverflowError:
            self.main_display.setText("Переполнение")
        except ValueError as e:
            if "math domain error" in str(e) or "negative number" in str(e):
                self.main_display.setText("Корень из отрицательного числа")
            else:
                self.main_display.setText("Ошибка синтаксиса")
        except Exception:
            self.main_display.setText("Ошибка синтаксиса")

    def set_buttons_enabled(self, enabled: bool):
        try:
            for btn in self.findChildren(QPushButton):
                if btn.text() in ["=", "C", "DEL", "MC", "MR", "MS", "M+", "M-"]:
                    continue
                btn.setEnabled(enabled)
        except Exception as e:
            self.error_label.setText(str(e))

    # разделы
    def ui_history(self):
        w = QWidget()
        l = QVBoxLayout(w)
        # noinspection PyArgumentList
        self.hist_list = QListWidget()

        # копирование ответа по двойному клику
        self.hist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.hist_list.customContextMenuRequested.connect(self.history_menu)
        self.hist_list.itemDoubleClicked.connect(self.copy_history_item)
        l.addWidget(self.hist_list)
        btn = QPushButton("Очистить историю")
        btn.clicked.connect(self.clear_history)
        l.addWidget(btn)
        return w

    def history_menu(self, pos):
        item = self.hist_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        insert_act = menu.addAction("Вставить")
        copy_act = menu.addAction("Копировать")
        del_act = menu.addAction("Удалить")

        action = menu.exec(self.hist_list.mapToGlobal(pos))

        if action == insert_act:
            text = item.text()

            if "=" in text:
                result = text.split("=")[1].strip()
            else:
                result = text

            self.main_display.setText(result)
        elif action == copy_act:
            text = item.text()

            if "=" in text:
                result = text.split("=")[1].strip()
            else:
                result = text

            QApplication.clipboard().setText(result)
        elif action == del_act:
            self.hist_list.takeItem(self.hist_list.row(item))

    def copy_history_item(self, item):
        text = item.text()
        if "=" in text:
            result = text.split("=")[1].strip()

            current = self.main_display.text()

            if current in ["", "0", "Ошибка"]:
                self.main_display.setText(result)
            else:
                self.main_display.setText(current + result)

    def ui_matrix(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("<b>Матрица A</b>"))
        # noinspection PyArgumentList
        self.dim_a = QComboBox()
        self.dim_a.addItems(["2x2", "2x3", "3x2", "3x3"])
        self.dim_a.currentIndexChanged.connect(self.update_matrix_grid)
        l.addWidget(self.dim_a)
        # noinspection PyArgumentList
        self.grid_a_layout = QGridLayout()
        l.addLayout(self.grid_a_layout)

        l.addWidget(QLabel("<b>Матрица B</b>"))
        # noinspection PyArgumentList
        self.dim_b = QComboBox()
        self.dim_b.addItems(["2x2", "2x3", "3x2", "3x3"])
        self.dim_b.currentIndexChanged.connect(self.update_matrix_grid)
        l.addWidget(self.dim_b)
        # noinspection PyArgumentList
        self.grid_b_layout = QGridLayout()
        l.addLayout(self.grid_b_layout)

        # выбор всех операций
        # noinspection PyArgumentList
        self.m_op = QComboBox()
        self.m_op.addItems([
            "Сложение (A+B)",
            "Вычитание (A-B)",
            "Умножение (A*B)",
            "Транспонирование (A)",
            "Транспонирование (B)",
            "Детерминант (A)",
            "Детерминант (B)"
        ])
        l.addWidget(self.m_op)

        btn = QPushButton("Вычислить")
        btn.setObjectName("PrimaryAccent")
        btn.clicked.connect(self.solve_matrix)
        l.addWidget(btn)

        self.m_expl = QTextEdit()
        self.m_expl.setFont(QFont("Courier New", 12))
        self.m_expl.setReadOnly(True)
        self.m_expl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        l.addWidget(self.m_expl)
        self.update_matrix_grid()
        return w

    @staticmethod
    def format_matrix(m):
        if isinstance(m, np.ndarray):
            # выравнивание по столбцам
            str_rows = [[f"{v:.3g}" for v in row] for row in m]
            col_widths = [max(len(row[i]) for row in str_rows) for i in range(len(str_rows[0]))]

            rows = []
            for row in str_rows:
                formatted = "  ".join(val.rjust(col_widths[i]) for i, val in enumerate(row))
                rows.append(formatted)

            # ДВЕ БОЛЬШИЕ СКОБКИ
            result = []
            for i, row in enumerate(rows):
                if i == 0:
                    result.append("⎛ " + row + " ⎞")
                elif i == len(rows) - 1:
                    result.append("⎝ " + row + " ⎠")
                else:
                    result.append("⎜ " + row + " ⎟")

            return "\n".join(result)

        return str(round(m, 5))

    def update_matrix_grid(self):
        for g in [self.grid_a_layout, self.grid_b_layout]:
            while g.count(): g.takeAt(0).widget().deleteLater()

        def fill(dim, layout):
            r, c = int(dim[0]), int(dim[2])
            for i in range(r):
                for j in range(c):
                    e = QLineEdit()
                    e.setPlaceholderText("0")
                    e.setFixedWidth(40)
                    e.setValidator(self.num_val)
                    layout.addWidget(e, i, j)

        fill(self.dim_a.currentText(), self.grid_a_layout)
        fill(self.dim_b.currentText(), self.grid_b_layout)

    def solve_matrix(self):
        try:
            def get_matrix(layout, dim):
                r, c = int(dim[0]), int(dim[2])
                vals = []
                for i in range(layout.count()):
                    val = layout.itemAt(i).widget().text()
                    vals.append(float(val) if val else 0.0)
                return np.array(vals).reshape(r, c)

            a = get_matrix(self.grid_a_layout, self.dim_a.currentText())
            b = get_matrix(self.grid_b_layout, self.dim_b.currentText())
            op = self.m_op.currentText()
            res = None

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
                if b.shape[0] != b.shape[1]:
                    raise ValueError("Матрица B должна быть квадратной")
                res = np.linalg.det(b)
            elif "Детерминант (A)" in op:
                res = np.linalg.det(a)
            else:
                res = a.T

            if res is None:
                raise ValueError("Не выбрана операция")

            self.m_expl.setText(self.format_matrix(res))
        except Exception as e:
            self.m_expl.setText(str(e))

    def ui_graph(self):
        w = QWidget()
        l = QVBoxLayout(w)

        # поле ввода
        self.g_in = QLineEdit()
        self.g_in.setPlaceholderText("Введите выражение")
        self.g_in.installEventFilter(self)  # отслеживаем клик для удаления ошибок

        row = QHBoxLayout()
        label = QLabel("F(x) =")
        label.setStyleSheet("font-weight: bold;")
        row.addWidget(label)
        row.addWidget(self.g_in)
        l.addLayout(row)

        # диапазоны
        self.xmin = QLineEdit()
        self.xmax = QLineEdit()
        self.ymin = QLineEdit()
        self.ymax = QLineEdit()

        # задаем дефолтные значения через подсказки (placeholder)
        self.xmin.setPlaceholderText("-10")
        self.xmax.setPlaceholderText("10")
        self.ymin.setPlaceholderText("-10")
        self.ymax.setPlaceholderText("10")

        # принудительно регистрируем фильтр кликов (событий) для автоматической очистки
        self.xmin.installEventFilter(self)
        self.xmax.installEventFilter(self)
        self.ymin.installEventFilter(self)
        self.ymax.installEventFilter(self)

        # включаем запрет букв
        self.xmin.setValidator(self.num_val)
        self.xmax.setValidator(self.num_val)
        self.ymin.setValidator(self.num_val)
        self.ymax.setValidator(self.num_val)

        # X
        x_row = QHBoxLayout()
        x_row.addWidget(QLabel("X: от"))
        x_row.addWidget(self.xmin)
        x_row.addWidget(QLabel("до"))
        x_row.addWidget(self.xmax)
        l.addLayout(x_row)

        # Y
        y_row = QHBoxLayout()
        y_row.addWidget(QLabel("Y: от"))
        y_row.addWidget(self.ymin)
        y_row.addWidget(QLabel("до"))
        y_row.addWidget(self.ymax)
        l.addLayout(y_row)

        self.fig = plt.Figure()
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        l.addWidget(self.canvas)

        btn = QPushButton("Построить")
        btn.clicked.connect(self.draw_graph)
        l.addWidget(btn)

        return w

    def draw_graph(self):
        if self.ax is None or self.canvas is None:
            return
        try:
            expr = self.g_in.text().strip()

            if not expr:
                self.g_in.setText("Введите выражение!")
                return

            xmin = float(self.xmin.text() or -10)
            xmax = float(self.xmax.text() or 10)
            ymin = float(self.ymin.text() or -10)
            ymax = float(self.ymax.text() or 10)

            x = np.linspace(xmin, xmax, 1000)

            safe_dict = {
                "np": np,
                "x": x,
                "sin": np.sin, "cos": np.cos, "tan": np.tan,
                "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
                "log": np.log10, "ln": np.log, "sqrt": np.sqrt,
                "exp": np.exp, "abs": np.abs
            }

            # поддержка слитного умножения (3x -> 3*x)
            expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)
            expr = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', expr)
            expr = re.sub(r'(\))(\d)', r'\1*\2', expr)
            expr = re.sub(r'(\d)(\()', r'\1*\2', expr)

            expr = expr.replace("^", "**")
            try:
                y = eval(expr, {"__builtins__": {}}, safe_dict)
            except Exception:
                self.g_in.setToolTip("Ошибка в выражении")
                return

            # если это число → делаем массив
            y = np.asarray(y, dtype=float)

            if y.ndim == 0:
                y = np.full_like(x, y)

            y = np.where(np.isfinite(y), y, np.nan)

            if np.all(np.isnan(y)):
                self.g_in.setText("Функция не определена")
                return

            self.ax.clear()

            # ИЗНАЧАЛЬНАЯ СЕТКА И ШАГ 1x1 С КООРДИНАТАМИ
            self.ax.set_xticks(np.arange(xmin, xmax + 1, 1))
            self.ax.set_yticks(np.arange(ymin, ymax + 1, 1))
            self.ax.grid(True, linestyle='--', linewidth=0.5)

            # оси
            self.ax.axhline(0, linewidth=1.5)
            self.ax.axvline(0, linewidth=1.5)

            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)

            if abs(xmax - xmin) > 100:
                self.g_in.setText("Слишком большой диапазон")
                return

            self.ax.plot(x, y, linewidth=2)
            if xmin >= xmax or ymin >= ymax:
                self.g_in.setText("Неверный диапазон")
                return

            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)

            self.ax.set_ylabel("Y", loc="top", rotation=0)
            # координаты смещения: -0.05 уводит букву влево от оси Y, 1.02 приподнимает над графиком
            self.ax.yaxis.set_label_coords(-0.05, 1.02)

            self.canvas.draw()

            # скрываем рамки
            for spine in self.ax.spines.values():
                spine.set_visible(False)

            # оси со стрелками
            self.ax.annotate('', xy=(xmax, 0), xytext=(xmin, 0),
                             arrowprops=dict(arrowstyle='->', linewidth=1.5))

            self.ax.annotate('', xy=(0, ymax), xytext=(0, ymin),
                             arrowprops=dict(arrowstyle='->', linewidth=1.5))
            # подписи осей у стрелок
            self.ax.text(xmax, 0, "x", ha='right', va='bottom')
            self.ax.text(0, ymax, "y", ha='left', va='top')
            self.ax.set_aspect('auto', adjustable='box')
            self.g_in.textEdited.connect(self.clear_graph_error)
            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(e)
            if self.g_in is not None:
                self.g_in.setText(str(e))
                self.g_in.setStyleSheet("border: 2px solid red;")

    def clear_graph_error(self):
        self.g_in.setStyleSheet("")

    # ПАРАМЕТРЫ
    def open_params(self):
        d = QDialog(self)
        theme = THEMES.get(self.saved_theme, THEMES["light"])

        # установка фона параметров и скруглений для окон
        d.setStyleSheet(f"""
            QDialog {{ 
                background-color: {theme['bg']}; 
            }}
            QLabel {{ 
                color: {theme['text']}; 
                font-family: Inter;
            }}
        """)
        d.setFixedSize(360, 420)
        d.setWindowTitle("Параметры")
        l = QVBoxLayout(d)

        # ПАРАМЕТРЫ
        title_label = QLabel("<b>ПАРАМЕТРЫ</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title_label)

        l.addWidget(QLabel("Цветовая тема:"))

        # выбор цветовой темы с помощью выпадающего списка
        # noinspection PyArgumentList
        self.theme_select = QComboBox()
        self.theme_select.addItems(["Светлая", "Темная", "Зеленая", "Синяя"])

        # установка текущего значения в комбобоксе
        mapping = {"light": 0, "dark": 1, "green": 2, "blue": 3}
        rev_mapping = {0: "light", 1: "dark", 2: "green", 3: "blue"}
        self.theme_select.setCurrentIndex(mapping.get(self.saved_theme, 0))

        # функция смены темы «на лету» без закрытия окна параметров
        def on_theme_changed(index):
            chosen_key = rev_mapping.get(index, "light")
            self.apply_theme_color(chosen_key)
            # динамически обновляем подложку текущего окна параметров
            new_theme = THEMES[chosen_key]
            d.setStyleSheet(
                f"QDialog {{ background-color: {new_theme['bg']}; }} QLabel {{ color: {new_theme['text']}; }}")

        self.theme_select.currentIndexChanged.connect(on_theme_changed)
        l.addWidget(self.theme_select)

        # выбор измерений
        l.addSpacing(10)
        l.addWidget(QLabel("Выбор измерений:"))
        h_m = QHBoxLayout()
        for m in ["DEG", "RAD"]:
            b = QPushButton(m)
            # стили полностью управляются через apply_theme_color динамически
            b.clicked.connect(lambda ch, mode=m: self.update_meas(mode))
            h_m.addWidget(b)
        l.addLayout(h_m)

        # СВЕДЕНИЯ
        l.addSpacing(15)
        info_label = QLabel("<b>СВЕДЕНИЯ</b>")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(info_label)

        version_label = QLabel("Приложение разработано на Python, версия 0.1")
        l.addWidget(version_label)

        l.addSpacing(15)
        # кнопка Закрыть (попадает под правило TallBtn — высокая, жирная)
        btn = QPushButton("Закрыть")
        btn.setObjectName("TallBtn")
        btn.clicked.connect(d.accept)
        l.addWidget(btn)

        # принудительно обновляем стили созданных внутри диалога кнопок
        self.apply_theme_color(self.saved_theme)

        d.exec()

    def apply_theme_color(self, theme_name):
        if theme_name not in THEMES:
            theme_name = "light"

        theme = THEMES[theme_name]
        self.saved_theme = theme_name

        # блокируем сигналы, чтобы избежать критического вылета 0xC0000409
        self.blockSignals(True)

        for btn in self.findChildren(QPushButton):
            t = btn.text()
            if t in ["Построить", "Вычислить", "Закрыть", "Очистить историю"]:
                btn.setObjectName("TallBtn")
            elif t in ["История", "Матрицы", "График"]:
                if btn.objectName() != "ActiveTab":
                    btn.setObjectName("TabButton")
            elif t in ["C", "DEL", "=", "Тригонометрия"]:
                btn.setObjectName("SpecialBtn")
            elif t in ["DEG", "RAD"]:
                if t == self.angle_mode:
                    btn.setObjectName("ModeActive")
                else:
                    btn.setObjectName("ModeInactive")

            # принудительно заставляем Qt обновить стили элемента
            btn.style().unpolish(btn)
            btn.style().polish(btn)


        self.setStyleSheet(f"""
            QMainWindow {{ background: {theme['bg']}; }}
            #Card {{ background: {theme['card']}; border-radius: 12px; border: 1px solid {theme['border']}; }}
            * {{ color: {theme['text']}; font-family: Inter; }}

            /* Скругленные кнопки */
            QPushButton {{
                background: {theme['btn_default']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                min-height: 35px;
            }}
            QPushButton#DefaultBtn {{ background: {theme['btn_default']}; }}
            QPushButton#SpecialBtn {{ background: {theme['special_btn_bg']}; }}

            QPushButton#ActiveTab {{
                background: {theme['special_btn_bg']};
                font-weight: bold;
                border: 2px solid {theme['text']};
            }}

            /* Кнопки Очистить историю, Вычислить, Построить увеличены */
            QPushButton#TallBtn {{
                background: {theme['special_btn_bg']};
                font-weight: bold;
                min-height: 48px;
                min-width: 170px;
                font-size: 14px;
            }}

            /* Выделение кнопок измерения под цвет фона панели */
            QPushButton#ModeActive {{
                background: {theme['card']};
                border: 2px solid {theme['text']};
                font-weight: bold;
            }}

            /* Поля ввода калькулятора, выражений графиков, истории, ввода и решения матриц */
            QLineEdit, QTextEdit, QListWidget {{
                background: {theme['input_bg']};
                color: #000000 !important; /* Строго чёрный текст для читаемости на белом фоне */
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 5px;
            }}
            QLineEdit::placeholder {{
                color: #888888;
            }}

            /* Увеличенный выпадающий список Тригонометрия (в закрытом состоянии) */
            QComboBox {{
                background: {theme['special_btn_bg']};
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 4px;
                min-width: 180px;
                color: {theme['text']} !important; /* ИСПРАВЛЕНИЕ: белый текст для названия закрытого списка */
            }}

            /* Раскрывающийся список (Тригонометрия, Действия в истории) — светлый фон, чёрный текст */
            QComboBox QAbstractItemView {{
                background: {theme['input_bg']};
                border-radius: 6px;
                border: 1px solid {theme['border']};
                color: #000000 !important; /* строго чёрный текст элементов при раскрытии */
            }}
            QComboBox QAbstractItemView::item {{
                color: #000000 !important;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: rgba(0, 0, 0, 0.1);
                color: #000000 !important;
            }}

            /* Контекстное меню при ПКМ (Вставить, Копировать, Удалить) — светлый фон, чёрный текст */
            QMenu {{
                background: {theme['input_bg']} !important;
                border: 1px solid {theme['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                background: transparent;
                color: #000000 !important; /* чёрный текст для пунктов контекстного меню */
            }}
            QMenu::item:selected {{
                background-color: rgba(0, 0, 0, 0.1);
                color: #000000 !important;
            }}
        """)

        # принудительно применяем цвет текста для диапазонов графика, если они существуют
        if hasattr(self, 'xmin') and self.xmin:
            for field in [self.xmin, self.xmax, self.ymin, self.ymax]:
                if field:
                    field.setStyleSheet(f"background: {theme['special_btn_bg']}; color: #000000; border-radius: 8px;")

        self.prefs.setValue("theme_color", theme_name) # сохраняем настройку
        self.blockSignals(False) # возвращаем сигналы

    def update_meas(self, mode):
        self.angle_mode = mode
        self.prefs.setValue("angle_mode", mode)

        # перевызываем обновление стилей, чтобы переразметить ModeActive / ModeInactive кнопки
        self.apply_theme_color(self.saved_theme)

        # перерисовываем диалоговое окно параметров, если оно открыто
        sender_btn = self.sender()
        if sender_btn:
            parent_dialog = sender_btn.window()
            if isinstance(parent_dialog, QDialog):
                theme = THEMES[self.saved_theme]
                parent_dialog.setStyleSheet(
                    f"QDialog {{ background-color: {theme['bg']}; }} QLabel {{ color: {theme['text']}; }}")

    def insert_text(self, text):
        target = self.last_focused_input if self.last_focused_input else self.main_display
        current = target.text()

        if self.second_func:
            target.setText(current + text)
            self.second_func = False
            self.trig_btn.setText("Тригонометрия")
            self.trig_btn.setStyleSheet("")
            self.update_clear_button()
            self.set_buttons_enabled(True)
            return

        # очистка дефолтного нуля или старых ошибок перед вводом нового текста
        if current in ["0", "Ошибка", "Введите выражение!", "Ошибка синтаксиса"]:
            current = ""

        # два оператора подряд — заменяем старый оператор на самый последний введенный
        operators = ["+", "-", "*", "/", "%", "^"]
        if text.strip() in operators and current and current[-1] in operators:
            current = current[:-1]

        # точка без цифр — автоматическое добавление нуля ("0.")
        if text == ".":
            if not current or current[-1] in ["+", "-", "*", "/", "(", ")", "%", "^"]:
                text = "0."
            else:
                # несколько точек в одном числе — игнорируем ввод второй точки
                last_number = re.split(r'[+\-*/()^%]', current)[-1]
                if "." in last_number:
                    return

        # стандартная вставка и сброс состояния интерфейса
        target.setText(current + text)
        self.error_label.setText("")
        self.main_display.setStyleSheet("")
        self.update_clear_button()
        self.set_buttons_enabled(True)

    def switch_tab(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.tab_buttons):
            btn.setObjectName("ActiveTab" if i == idx else "TabButton")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.FocusIn and isinstance(obj, QLineEdit):
            self.last_focused_input = obj
            txt = obj.text().strip()

            # расширенный список ошибок, включая ошибки графиков
            if txt in ["0", "Ошибка", "Ошибка синтаксиса", "Функция не определена", "Введите выражение",
                       "Введите выражение!", "Неверный диапазон", "Слишком большой диапазон",
                       "Деление на ноль невозможно", "Переполнение", "Корень из отрицательного числа",
                       "Логарифм от нуля или отрицательного числа", "0 ⁰  – неопределённость",
                       "Деление на ноль", "Тангенс не определён для 90°",
                       "Аргумент должен быть от -1 до 1", "Незакрытая скобка", "Лишняя закрывающая скобка"]:
                obj.clear()

                # если это поле ввода графика (g_in), сбрасываем его красную рамку к дефолтной теме
                if hasattr(self, 'g_in') and obj == self.g_in:
                    obj.setStyleSheet("")

            # предотвращает вылет приложения при старте
            elif hasattr(self, 'xmin') and self.xmin and obj in [self.xmin, self.xmax, self.ymin, self.ymax]:
                if txt in ["-10", "10"]:
                    obj.clear()

        return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = EngineeringApp()
    # noinspection PyUnresolvedReferences
    ex.show()
    sys.exit(app.exec())