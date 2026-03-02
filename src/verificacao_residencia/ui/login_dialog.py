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
