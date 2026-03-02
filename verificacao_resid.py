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

from verificador_residencia_core import run_verificacao_residencia


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


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(580, 480)

        self._drag_pos = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(18)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        title_wrap = QVBoxLayout()
        title = QLabel("Central de Regulação")
        title.setObjectName("title")

        subtitle = QLabel("Acesso restrito • Sistema auditável")
        subtitle.setObjectName("subtitle")

        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)

        btn_min = QPushButton("–")
        btn_min.setObjectName("winBtn")
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QPushButton("×")
        btn_close.setObjectName("winBtnClose")
        btn_close.clicked.connect(self.reject)

        top_layout.addLayout(title_wrap)
        top_layout.addStretch()
        top_layout.addWidget(btn_min)
        top_layout.addWidget(btn_close)

        card_layout.addLayout(top_layout)
        card_layout.addSpacing(10)

        lbl_user = QLabel("Usuário")
        lbl_user.setObjectName("label")

        self.user = QLineEdit()
        self.user.setObjectName("input")
        self.user.setPlaceholderText("Digite seu usuário institucional")

        card_layout.addWidget(lbl_user)
        card_layout.addWidget(self.user)

        lbl_pass = QLabel("Senha")
        lbl_pass.setObjectName("label")

        pass_layout = QHBoxLayout()

        self.pw = QLineEdit()
        self.pw.setObjectName("input")
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("Digite sua senha")

        self.toggle_btn = QPushButton("👁")
        self.toggle_btn.setObjectName("toggle")
        self.toggle_btn.clicked.connect(self.toggle_password)

        pass_layout.addWidget(self.pw)
        pass_layout.addWidget(self.toggle_btn)

        card_layout.addSpacing(4)
        card_layout.addWidget(lbl_pass)
        card_layout.addLayout(pass_layout)

        card_layout.addSpacing(30)

        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(14)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_login = QPushButton("Entrar")
        self.btn_login.setObjectName("btnPrimary")
        self.btn_login.clicked.connect(self.try_login)

        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_login)

        card_layout.addLayout(button_layout)
        card_layout.addStretch()

        root.addWidget(self.card)

        self.user.returnPressed.connect(self.try_login)
        self.pw.returnPressed.connect(self.try_login)

        self.setStyleSheet("""
        QDialog { background: transparent; }

        QFrame#card {
            background: #0f172a;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.08);
        }

        QLabel#title {
            color: white;
            font-size: 20px;
            font-weight: 900;
        }

        QLabel#subtitle {
            color: rgba(255,255,255,0.6);
            font-size: 12px;
        }

        QLabel#label {
            color: rgba(255,255,255,0.85);
            font-size: 13px;
            font-weight: 700;
        }

        QLineEdit#input {
            background: #1e293b;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 14px;
            padding: 16px;
            font-size: 14px;
            color: white;
        }

        QLineEdit#input:focus {
            border: 1px solid #6366f1;
        }

        QPushButton#toggle {
            background: #1e293b;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 14px;
            padding: 14px;
            font-size: 16px;
            color: white;
            min-width: 48px;
        }

        QPushButton#btnPrimary {
            background: #6366f1;
            border-radius: 14px;
            padding: 14px;
            font-size: 14px;
            font-weight: 800;
            color: white;
        }

        QPushButton#btnPrimary:hover {
            background: #4f46e5;
        }

        QPushButton#btnSecondary {
            background: #334155;
            border-radius: 14px;
            padding: 14px;
            font-size: 14px;
            font-weight: 800;
            color: white;
        }

        QPushButton#btnSecondary:hover {
            background: #475569;
        }

        QPushButton#winBtn {
            background: #334155;
            border-radius: 10px;
            padding: 6px 10px;
            font-size: 14px;
            color: white;
        }

        QPushButton#winBtnClose {
            background: #7f1d1d;
            border-radius: 10px;
            padding: 6px 10px;
            font-size: 14px;
            color: white;
        }

        QLabel#error {
            color: #fecaca;
            background: rgba(239,68,68,0.2);
            border-radius: 12px;
            padding: 10px;
            font-size: 12px;
        }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def toggle_password(self):
        if self.pw.echoMode() == QLineEdit.Password:
            self.pw.setEchoMode(QLineEdit.Normal)
        else:
            self.pw.setEchoMode(QLineEdit.Password)

    def try_login(self):
        user = self.user.text().strip()
        pw = self.pw.text().strip()

        if not user or not pw:
            self.error_label.setText("Preencha usuário e senha.")
            self.error_label.setVisible(True)
            return

        if user == "admin" and pw == "admin":
            self.accept()
        else:
            self.error_label.setText("Usuário ou senha inválidos.")
            self.error_label.setVisible(True)


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
