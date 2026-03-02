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

class Worker(QThread):
    log_sig = Signal(str)
    done_sig = Signal(bool, str)

    def __init__(self, dt_ini, dt_fim, sis_user, sis_pass):
        super().__init__()
        self.dt_ini = dt_ini
        self.dt_fim = dt_fim
        self.sis_user = sis_user
        self.sis_pass = sis_pass

    def run(self):
        def log(msg):
            self.log_sig.emit(msg)

        ok, html_path = run_verificacao_residencia(
            self.dt_ini, self.dt_fim,
            self.sis_user, self.sis_pass,
            log=log
        )
        self.done_sig.emit(ok, html_path)
