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

def _safe_log(log: Callable[[str], None], msg: str) -> None:
    try:
        if callable(log):
            log(str(msg))
    except Exception:
        pass
