import sys
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QCalendarWidget, QTimeEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QStyledItemDelegate, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from plyer import notification


class Task:
    def __init__(self, name, priority, datetime_str):
        self.name = name
        self.priority = priority
        self.datetime_str = datetime_str
        self.notified = False  

    def to_dict(self):
        return {"name": self.name, "priority": self.priority, "datetime": self.datetime_str, "notified": self.notified}

    @staticmethod
    def from_dict(data):
        task = Task(data["name"], data["priority"], data["datetime"])
        task.notified = data.get("notified", False)
        return task


class QueueManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def remove_task(self, index):
        if 0 <= index < len(self.tasks):
            del self.tasks[index]

    def save_tasks(self, filepath="tasks.json"):
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump([task.to_dict() for task in self.tasks], file, ensure_ascii=False, indent=4)

    def load_tasks(self, filepath="tasks.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                self.tasks = [Task.from_dict(data) for data in json.load(file)]
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            self.tasks = []


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Симулятор задач и очередей")
        self.setGeometry(100, 100, 800, 600)

        self.manager = QueueManager()
        self.manager.load_tasks()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.init_add_task_tab()
        self.init_task_list_tab()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_deadlines)
        self.timer.start(1000)

        self.update_task_table()

    def init_add_task_tab(self):
        self.add_task_tab = QWidget()
        layout = QVBoxLayout(self.add_task_tab)

        self.name_input = QLineEdit()
        layout.addWidget(QLabel("Название задачи:"))
        layout.addWidget(self.name_input)

        self.priority_input = QComboBox()
        self.priority_input.addItems(["Низкий", "Средний", "Высокий"])
        layout.addWidget(QLabel("Приоритет задачи:"))
        layout.addWidget(self.priority_input)

        self.date_input = QCalendarWidget()
        self.date_input.setGridVisible(True)
        layout.addWidget(QLabel("Дата выполнения:"))
        layout.addWidget(self.date_input)

        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        layout.addWidget(QLabel("Время выполнения (часы:минуты):"))
        layout.addWidget(self.time_input)

        self.add_task_button = QPushButton("Добавить задачу")
        self.add_task_button.clicked.connect(self.add_task)
        layout.addWidget(self.add_task_button)

        self.tabs.addTab(self.add_task_tab, "Добавить задачу")

    def init_task_list_tab(self):
        self.task_list_tab = QWidget()
        layout = QVBoxLayout(self.task_list_tab)

        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["", "Название", "Приоритет", "Время"])
        layout.addWidget(self.task_table)

        
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Удалить выбранные задачи")
        self.delete_button.clicked.connect(self.delete_selected_tasks)
        button_layout.addWidget(self.delete_button, alignment=Qt.AlignmentFlag.AlignRight)  
        layout.addLayout(button_layout)
        self.tabs.addTab(self.task_list_tab, "Список задач")

    def add_task(self):
        name = self.name_input.text()
        priority = self.priority_input.currentText()
        date = self.date_input.selectedDate().toString("yyyy-MM-dd")
        time = self.time_input.time().toString("HH:mm")

        if not name:
            QMessageBox.warning(self, "Ошибка", "Название задачи не может быть пустым!")
            return

        datetime_str = f"{date} {time}"
        task = Task(name, priority, datetime_str)
        self.manager.add_task(task)
        self.update_task_table()
        self.name_input.clear()

    def delete_selected_tasks(self):
        selected_rows = []
        for row in range(self.task_table.rowCount()):
            checkbox_item = self.task_table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                selected_rows.append(row)

       
        for row in sorted(selected_rows, reverse=True):
            task_name_item = self.task_table.item(row, 1) 
            if task_name_item:
                task_name = task_name_item.text()
                task_to_remove = None
                for task in self.manager.tasks:
                    if task.name == task_name:
                        task_to_remove = task
                        break
                if task_to_remove:
                    self.manager.tasks.remove(task_to_remove)

        self.update_task_table()

    def update_task_table(self):
        check_states = {}
        for row in range(self.task_table.rowCount()):
            checkbox_item = self.task_table.item(row, 0)
            if checkbox_item:
                task_name_item = self.task_table.item(row, 1)
                if task_name_item:
                    task_name = task_name_item.text()
                    check_states[task_name] = checkbox_item.checkState()

        self.task_table.setRowCount(0)

        tasks_by_day = {}
        for task in self.manager.tasks:
            task_date = datetime.strptime(task.datetime_str, "%Y-%m-%d %H:%M").date()
            tasks_by_day.setdefault(task_date, []).append(task)

        sorted_dates = sorted(tasks_by_day.keys())

        priority_order = {"Высокий": 1, "Средний": 2, "Низкий": 3}

        row_index = 0
        for task_date in sorted_dates:
            day_of_week = task_date.strftime("%A, %d %B").capitalize()
            self.task_table.insertRow(row_index)
            header_item = QTableWidgetItem(day_of_week)
            header_item.setFlags(Qt.ItemIsEnabled)
            header_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setSpan(row_index, 0, 1, 4)
            self.task_table.setItem(row_index, 0, header_item)
            row_index += 1

            
            sorted_tasks = sorted(tasks_by_day[task_date], key=lambda t: priority_order[t.priority])

            for task in sorted_tasks:
                self.task_table.insertRow(row_index)

                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                checkbox.setCheckState(check_states.get(task.name, Qt.Unchecked))
                self.task_table.setItem(row_index, 0, checkbox)

                self.task_table.setItem(row_index, 1, QTableWidgetItem(task.name))
                self.task_table.setItem(row_index, 2, QTableWidgetItem(task.priority))

                task_time = datetime.strptime(task.datetime_str, "%Y-%m-%d %H:%M").strftime("%H:%M")
                self.task_table.setItem(row_index, 3, QTableWidgetItem(task_time))
                row_index += 1

    def check_deadlines(self):
        current_time = datetime.now()
        for task in self.manager.tasks[:]:
            task_time = datetime.strptime(task.datetime_str, "%Y-%m-%d %H:%M")
            time_diff = task_time - current_time

            if timedelta(0) < time_diff <= timedelta(minutes=30) and not task.notified:
                if time_diff <= timedelta(minutes=1):
                    notification.notify(
                        title="Напоминание",
                        message=f"Задача '{task.name}' закочится через  1 минуту!",
                        timeout=5
                    )
                    task.notified = True
                elif time_diff <= timedelta(minutes=15):
                    notification.notify(
                        title="Напоминание",
                        message=f"Задача '{task.name}' закочится через  15 минут!",
                        timeout=5
                    )
                    task.notified = True
                elif time_diff <= timedelta(minutes=30):
                    notification.notify(
                        title="Напоминание",
                        message=f"Задача '{task.name}' закочится через  30 минут!",
                        timeout=5
                    )
                    task.notified = True

            elif time_diff <= timedelta(seconds=0):
                if not task.notified:
                    notification.notify(
                        title="Задача завершена",
                        message=f"Задача '{task.name}' истекла!",
                        timeout=5
                    )
                    task.notified = True

        self.manager.save_tasks()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())