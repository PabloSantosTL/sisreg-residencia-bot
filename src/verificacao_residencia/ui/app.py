import sys, os, webbrowser
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QFormLayout,
    QFrame
)

from ..core.runner import run_verificacao_residencia

from .login_dialog import LoginDialog
from .main_window import MainWindow

def main():
    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        return

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
