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

from .worker import Worker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robôs SISREG - Central de Regulação")
        self.setMinimumSize(900, 600)

        central = QWidget()
        root = QVBoxLayout()

        header = QLabel("Verificação de Residência (Três Lagoas)")
        header.setStyleSheet("font-size: 22px; font-weight: 800;")
        root.addWidget(header)

        form = QFormLayout()
        self.sis_user = QLineEdit()
        self.sis_user.setPlaceholderText("Usuário do SISREG")
        self.sis_pass = QLineEdit()
        self.sis_pass.setPlaceholderText("Senha do SISREG")
        self.sis_pass.setEchoMode(QLineEdit.Password)

        self.dt_ini = QLineEdit()
        self.dt_ini.setPlaceholderText("dd/mm/aaaa")
        self.dt_fim = QLineEdit()
        self.dt_fim.setPlaceholderText("dd/mm/aaaa")

        form.addRow("Usuário SISREG:", self.sis_user)
        form.addRow("Senha SISREG:", self.sis_pass)
        form.addRow("Data inicial:", self.dt_ini)
        form.addRow("Data final:", self.dt_fim)
        root.addLayout(form)

        actions = QHBoxLayout()
        self.btn_run = QPushButton("Iniciar verificação")
        self.btn_run.clicked.connect(self.start)
        actions.addWidget(self.btn_run)

        self.btn_open = QPushButton("Abrir HTML")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_html)
        actions.addWidget(self.btn_open)

        root.addLayout(actions)

        self.logbox = QTextEdit()
        self.logbox.setReadOnly(True)
        root.addWidget(self.logbox)

        central.setLayout(root)
        self.setCentralWidget(central)

        self.html_path = None
        self.worker = None

        self.setStyleSheet("""
            QMainWindow { background: #0b0b0f; color: #eaeaea; }
            QLabel { color: #eaeaea; }
            QLineEdit {
                background: #151521; border: 1px solid #2a2a3a;
                padding: 10px; border-radius: 10px; color: #eaeaea;
            }
            QPushButton {
                background: #10b981; padding: 10px; border-radius: 10px;
                color: #06110c; font-weight: 800;
            }
            QPushButton:disabled { background: #1f2937; color: #9ca3af; }
            QTextEdit {
                background: #0f1220; border: 1px solid #2a2a3a;
                border-radius: 10px; padding: 10px; color: #eaeaea;
                font-family: Consolas, monospace;
            }
        """)

    def log(self, msg):
        self.logbox.append(msg)

    def start(self):
        dt_ini = self.dt_ini.text().strip()
        dt_fim = self.dt_fim.text().strip()
        su = self.sis_user.text().strip()
        sp = self.sis_pass.text().strip()

        if not (dt_ini and dt_fim and su and sp):
            QMessageBox.warning(self, "Campos obrigatórios", "Preencha usuário/senha do SISREG e datas.")
            return

        self.btn_run.setEnabled(False)
        self.btn_open.setEnabled(False)
        self.logbox.clear()
        self.log("Iniciando...")

        self.worker = Worker(dt_ini, dt_fim, su, sp)
        self.worker.log_sig.connect(self.log)
        self.worker.done_sig.connect(self.done)
        self.worker.start()

    def done(self, ok, html_path):
        self.btn_run.setEnabled(True)
        self.html_path = html_path
        self.btn_open.setEnabled(True)

        if ok:
            QMessageBox.information(self, "Concluído", "Processamento concluído com sucesso.")
        else:
            QMessageBox.warning(self, "Finalizado com erro", "A execução terminou com erro. Veja os logs.")

    def open_html(self):
        if self.html_path and os.path.exists(self.html_path):
            webbrowser.open(os.path.abspath(self.html_path))
        else:
            QMessageBox.warning(self, "Arquivo não encontrado", "HTML não localizado.")
