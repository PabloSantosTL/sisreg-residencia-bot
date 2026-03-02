import os
import re
import time
from datetime import datetime
from html import escape as html_escape
from typing import Callable, Dict, List, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


BASE_URL = "https://sisregiii.saude.gov.br"
START_URL = f"{BASE_URL}/cgi-bin/index#"
HTML_FILE = "verificacao_residencia.html"

from .log import _safe_log
from .verifier import SisregResidenciaVerifier

def run_verificacao_residencia(
    dt_inicio: str,
    dt_fim: str,
    usuario_sisreg: str,
    senha_sisreg: str,
    log: Callable[[str], None] = lambda s: None,
) -> Tuple[bool, str]:
    return SisregResidenciaVerifier(log=log).run(dt_inicio, dt_fim, usuario_sisreg, senha_sisreg)
