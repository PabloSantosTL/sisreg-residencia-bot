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

class SisregResidenciaVerifier:
    def __init__(self, log: Callable[[str], None], timeout: int = 30):
        self.log = log
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def run(self, dt_inicio: str, dt_fim: str, usuario: str, senha: str) -> Tuple[bool, str]:
        _safe_log(self.log, "=== VERIFICAÇÃO DE RESIDÊNCIA - SISREG ===")

        registros = self._carregar_html_existente()

        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")

        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, self.timeout)

            if not self._login(usuario, senha):
                _safe_log(self.log, "Falha no login. Encerrando.")
                return False, HTML_FILE

            if not self._load_in_iframe("/cgi-bin/autorizador"):
                _safe_log(self.log, "Não foi possível carregar a área Autorizar.")
                return False, HTML_FILE

            _safe_log(self.log, f"Consultando período: {dt_inicio} à {dt_fim}")

            try:
                el_ini = self.wait.until(EC.visibility_of_element_located((By.ID, "dataInicial")))
                el_ini.clear()
                el_ini.send_keys(dt_inicio)
            except Exception as e:
                _safe_log(self.log, f"Erro ao inserir data inicial: {e}")
                return False, HTML_FILE

            try:
                el_fim = self.wait.until(EC.visibility_of_element_located((By.ID, "dataFinal")))
                el_fim.clear()
                el_fim.send_keys(dt_fim)
            except Exception as e:
                _safe_log(self.log, f"Erro ao inserir data final: {e}")
                return False, HTML_FILE

            try:
                btn_consultar = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='button' and @value='CONSULTAR']"))
                )
                btn_consultar.click()
                _safe_log(self.log, "Consulta realizada, aguardando resultados...")
            except Exception as e:
                _safe_log(self.log, f"Erro ao clicar em CONSULTAR: {e}")
                return False, HTML_FILE

            time.sleep(2)

            total_pages = self._get_total_pages()
            current_page = self._get_current_page()
            _safe_log(self.log, f"Total de páginas encontradas: {total_pages}")

            while True:
                _safe_log(self.log, f"--- Página {current_page} de {total_pages} ---")
                self._process_page(registros)

                if current_page >= total_pages:
                    _safe_log(self.log, "Última página processada.")
                    break

                if not self._go_next_page():
                    _safe_log(self.log, "Não foi possível avançar para próxima página. Encerrando paginação.")
                    break

                time.sleep(1)
                current_page = self._get_current_page()
                total_pages = self._get_total_pages()

            self._salvar_html_dinamico(registros)

            _safe_log(self.log, f"Processamento concluído. Total de fichas: {len(registros)}")
            _safe_log(self.log, f"Resultados salvos em '{HTML_FILE}'")
            return True, HTML_FILE

        except Exception as e:
            _safe_log(self.log, f"Erro durante execução: {e}")
            try:
                self._salvar_html_dinamico(registros)
            except Exception:
                pass
            return False, HTML_FILE

        finally:
            try:
                if self.driver:
                    self.driver.quit()
                _safe_log(self.log, "Navegador encerrado.")
            except Exception:
                pass

    def _login(self, usuario: str, senha: str) -> bool:
        _safe_log(self.log, "Acessando página de login...")
        assert self.driver and self.wait

        self.driver.get(START_URL)

        try:
            inp_user = self.wait.until(EC.visibility_of_element_located((By.ID, "usuario")))
            inp_user.clear()
            inp_user.send_keys(usuario)

            inp_pass = self.wait.until(EC.visibility_of_element_located((By.ID, "senha")))
            inp_pass.clear()
            inp_pass.send_keys(senha)

            btn_entrar = self.driver.find_element(By.XPATH, "//input[@type='button' and @value='entrar']")
            btn_entrar.click()

            try:
                self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "f_principal")))
                self.driver.switch_to.default_content()
            except TimeoutException:
                self.driver.switch_to.default_content()

            _safe_log(self.log, "Login realizado com sucesso!")
            return True

        except Exception as e:
            _safe_log(self.log, f"Erro no login: {e}")
            return False

    def _load_in_iframe(self, path: str) -> bool:
        assert self.driver and self.wait

        iframe_src = f"{BASE_URL}{path}"
        self.driver.switch_to.default_content()
        self.driver.execute_script(
            "var f = document.querySelector('iframe[name=\"f_principal\"]');"
            "if (!f) f = document.getElementById('f_main');"
            "if (f) { f.src = arguments[0]; }",
            iframe_src,
        )

        try:
            self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "f_principal")))
            time.sleep(1)
            return True
        except TimeoutException:
            self.driver.switch_to.default_content()
            _safe_log(self.log, "Timeout ao carregar iframe principal.")
            return False

    def _go_next_page(self) -> bool:
        assert self.driver

        try:
            next_btn = self.driver.find_element(
                By.XPATH,
                "//a[contains(@href,'exibirPagina')]/img[contains(@src,'seta_direita')]/..",
            )
            self.driver.execute_script("arguments[0].click();", next_btn)
            return True
        except Exception:
            try:
                cur = self._get_current_page()
                self.driver.execute_script("exibirPagina(arguments[0], arguments[1]);", cur, 12)
                return True
            except Exception as e:
                _safe_log(self.log, f"Falha ao avançar página: {e}")
                return False

    def _get_total_pages(self) -> int:
        assert self.driver
        try:
            input_el = self.driver.find_element(By.NAME, "txtPagina")
            parent = input_el.find_element(By.XPATH, "..")
            text = parent.text
            m = re.search(r"de\s+(\d+)", text)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return 1

    def _get_current_page(self) -> int:
        assert self.driver
        try:
            input_el = self.driver.find_element(By.NAME, "txtPagina")
            val = input_el.get_attribute("value")
            return int(val)
        except Exception:
            return 1

    def _process_page(self, registros: Dict[str, List[str]]) -> None:
        assert self.driver and self.wait

        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table_listagem")))
        except TimeoutException:
            _safe_log(self.log, "Tabela não encontrada nesta página.")
            return

        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.linha_selecionavel")
            _safe_log(self.log, f"Encontradas {len(rows)} fichas nesta página.")
        except Exception as e:
            _safe_log(self.log, f"Erro ao encontrar linhas: {e}")
            return

        itens: List[Dict[str, str]] = []

        for r in rows:
            try:
                tds = r.find_elements(By.TAG_NAME, "td")
                if len(tds) < 10:
                    continue

                code = tds[1].text.strip()
                central = tds[9].text.strip()

                if "TRES LAGOAS" in central.upper():
                    itens.append(
                        {
                            "codigo": code,
                            "central": central,
                            "paciente": tds[4].text.strip(),
                            "procedimento": tds[6].text.strip(),
                            "data_solicitacao": tds[2].text.strip(),
                        }
                    )

            except StaleElementReferenceException:
                continue
            except Exception as e:
                _safe_log(self.log, f"Erro ao processar linha: {e}")

        for item in itens:
            codigo = item["codigo"]

            if codigo in registros:
                _safe_log(self.log, f"Ficha {codigo} já processada, pulando...")
                continue

            try:
                _safe_log(self.log, f"Processando ficha {codigo} ({item.get('paciente','')})...")

                row_xpath = (
                    f"//tr[contains(@class,'linha_selecionavel') and .//td[2][normalize-space()='{codigo}']]"
                )
                row_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, row_xpath)))
                self.driver.execute_script("arguments[0].click();", row_el)
                time.sleep(0.3)

                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody.FichaCompleta")))
                    time.sleep(0.5)

                    paciente_ficha, _, status, municipio = self._analisar_ficha(codigo, item["paciente"])

                    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    registros[codigo] = [paciente_ficha, status, municipio, data_hora]
                    self._salvar_html_dinamico(registros)

                    self.driver.execute_script("history.back();")
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table_listagem")))
                    time.sleep(0.3)

                except TimeoutException:
                    _safe_log(self.log, f"Ficha {codigo} não carregou — marcada como não encontrada.")
                    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    registros[codigo] = [item["paciente"], "não encontrado", "", data_hora]
                    self._salvar_html_dinamico(registros)

                    try:
                        self.driver.execute_script("history.back();")
                        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table_listagem")))
                        time.sleep(0.3)
                    except Exception:
                        pass

            except Exception as e:
                _safe_log(self.log, f"Erro ao processar ficha {codigo}: {e}")
                data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                registros[codigo] = [item.get("paciente", ""), "erro", "", data_hora]
                try:
                    self._salvar_html_dinamico(registros)
                except Exception:
                    pass

                try:
                    self.driver.execute_script("history.back();")
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table_listagem")))
                    time.sleep(0.5)
                except Exception:
                    pass

    def _get_ficha_value(self, label: str) -> str:
        assert self.driver

        try:
            if "Município de Residência" in label:
                try:
                    el = self.driver.find_element(
                        By.XPATH,
                        "//tbody[@class='FichaCompleta']//tr[td/b[contains(normalize-space(.),'Município de Residência')]]"
                        "/following-sibling::tr[1]/td[last()]",
                    )
                    text = el.text.strip()
                    if text:
                        return text
                except Exception:
                    pass

            try:
                el = self.driver.find_element(
                    By.XPATH,
                    f"//tbody[@class='FichaCompleta']//td[b[contains(text(),'{label}')]]/../../following-sibling::tr[1]//td",
                )
                if el and el.text.strip():
                    return el.text.strip()
            except Exception:
                pass

            try:
                el2 = self.driver.find_element(
                    By.XPATH,
                    f"//tbody[@class='FichaCompleta']//td[b[contains(text(),'{label}')]]/following::td[1]",
                )
                if el2 and el2.text.strip():
                    return el2.text.strip()
            except Exception:
                pass

            try:
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{label}')]/following::td[1]")
                for elem in elements:
                    if elem.text.strip():
                        return elem.text.strip()
            except Exception:
                pass

            return ""
        except Exception:
            return ""

    def _get_nome_paciente_ficha(self) -> str:
        assert self.driver

        try:
            try:
                inputs = self.driver.find_elements(
                    By.XPATH,
                    "//tbody[@class='FichaCompleta']//input[("
                    "contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'paciente') or "
                    "contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'paciente') or "
                    "contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'nome') or "
                    "contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'nome'))]",
                )
                for inp in inputs:
                    try:
                        val = inp.get_attribute("value") or ""
                        if val and val.strip() and val.strip() != "---":
                            return val.strip()
                    except Exception:
                        continue
            except Exception:
                pass

            try:
                el = self.driver.find_element(
                    By.XPATH,
                    "//tbody[@class='FichaCompleta']//tr[td/b[contains(normalize-space(.),'Nome do Paciente')]]"
                    "/following-sibling::tr[1]//td[1]",
                )
                text = el.text.strip()
                if text and text != "---":
                    return text
            except Exception:
                pass

            try:
                el2 = self.driver.find_element(
                    By.XPATH,
                    "//tbody[@class='FichaCompleta']//td[b[contains(normalize-space(.),'Nome')]]/following::td[1]",
                )
                text2 = el2.text.strip()
                if text2 and text2 != "---":
                    return text2
            except Exception:
                pass

            try:
                el3 = self.driver.find_element(
                    By.XPATH,
                    "//*[contains(text(),'Nome do Paciente') or contains(text(),'Paciente')]/following::span[1]",
                )
                text3 = el3.text.strip()
                if text3 and text3 != "---":
                    return text3
            except Exception:
                pass

            try:
                tds = self.driver.find_elements(By.XPATH, "//tbody[@class='FichaCompleta']//tr//td")
                for td in tds:
                    txt = td.text.strip()
                    if txt and txt != "---" and len(txt) > 3:
                        digits = sum(c.isdigit() for c in txt)
                        if digits < len(txt) * 0.3:
                            return txt
            except Exception:
                pass

            return ""
        except Exception:
            return ""

    def _analisar_ficha(self, codigo_solicitacao: str, paciente_lista: str) -> Tuple[str, str, str, str]:
        try:
            municipio = self._get_ficha_value("Município de Residência:")

            paciente_ficha = self._get_nome_paciente_ficha()
            if not paciente_ficha:
                paciente_ficha = self._get_ficha_value("Nome do Paciente")
            if not paciente_ficha:
                paciente_ficha = paciente_lista

            if municipio:
                if municipio.strip().upper() == "TRES LAGOAS - MS":
                    return paciente_ficha, codigo_solicitacao, "coerente", municipio
                return paciente_ficha, codigo_solicitacao, "incoerente", municipio

            return paciente_ficha, codigo_solicitacao, "não encontrado", ""

        except Exception:
            return paciente_lista, codigo_solicitacao, "erro", ""

    def _carregar_html_existente(self) -> Dict[str, List[str]]:
        dados: Dict[str, List[str]] = {}
        if not os.path.exists(HTML_FILE):
            return dados

        try:
            with open(HTML_FILE, "r", encoding="utf-8") as f:
                conteudo = f.read()

            padrao = r"<tr><td>(.*?)</td><td>(.*?)</td><td(.*?)>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>"
            linhas = re.findall(padrao, conteudo)
            for nome, codigo, _, status, municipio, data_hora in linhas:
                dados[codigo] = [nome, status, municipio, data_hora]

            _safe_log(self.log, f"Carregados {len(dados)} registros anteriores.")
            return dados

        except Exception as e:
            _safe_log(self.log, f"Erro ao carregar HTML existente: {e}")
            return dados

    def _salvar_html_dinamico(self, dados: Dict[str, List[str]]) -> None:
        total = len(dados)
        coerentes = sum(1 for v in dados.values() if v[1] == "coerente")
        incoerentes = sum(1 for v in dados.values() if v[1] == "incoerente")
        nao_encontrados = sum(1 for v in dados.values() if v[1] == "não encontrado")
        erros = sum(1 for v in dados.values() if v[1] == "erro")

        html_head = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Verificação de Residência - TRES LAGOAS</title>
<style>
 body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
 h1 { color: #333; text-align: center; }
 .stats { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
 .stat-item { display: inline-block; margin-right: 30px; font-size: 16px; }
 .stat-number { font-weight: bold; font-size: 24px; display: block; }
 table { border-collapse: collapse; width: 100%; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
         border-radius: 8px; overflow: hidden; }
 th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #e0e0e0; }
 th { background-color: #2c3e50; color: white; font-weight: 600; cursor: pointer; position: relative; }
 th:hover { background-color: #34495e; }
 tr:hover { background-color: #f8f9fa; }
 .coerente { color: #27ae60; font-weight: bold; }
 .incoerente { color: #e74c3c; font-weight: bold; }
 .nao-encontrado { color: #f39c12; font-weight: bold; }
 .erro { color: #7f8c8d; font-weight: bold; }
 #search { padding: 12px 15px; width: 100%; margin-bottom: 20px; border: 2px solid #ddd;
           border-radius: 6px; font-size: 16px; box-sizing: border-box; }
 #search:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
 .last-update { text-align: right; color: #7f8c8d; font-size: 14px; margin-top: 10px; }
</style>
<script>
function searchTable() {
  var input = document.getElementById("search");
  var filter = input.value.toUpperCase();
  var table = document.getElementById("resultsTable");
  var tr = table.getElementsByTagName("tr");
  for (var i = 1; i < tr.length; i++) {
    var tds = tr[i].getElementsByTagName("td");
    var show = false;
    for (var j = 0; j < tds.length; j++) {
      if (tds[j].innerHTML.toUpperCase().indexOf(filter) > -1) { show = true; break; }
    }
    tr[i].style.display = show ? "" : "none";
  }
}
function sortTable(n) {
  var table = document.getElementById("resultsTable");
  var rows = Array.from(table.rows).slice(1);
  var isAsc = table.getAttribute("data-sort-dir") === "asc";
  var sortCol = parseInt(table.getAttribute("data-sort-col"));
  if (sortCol >= 0) {
    var prevTh = table.rows[0].cells[sortCol];
    prevTh.innerHTML = prevTh.innerHTML.replace(' ▲','').replace(' ▼','');
  }
  rows.sort(function(a,b){
    var x = a.cells[n].innerText;
    var y = b.cells[n].innerText;
    if (n === 1) {
      var numX = parseInt(x.replace(/[^0-9]/g,'')); var numY = parseInt(y.replace(/[^0-9]/g,''));
      if (!isNaN(numX) && !isNaN(numY)) return isAsc ? numX-numY : numY-numX;
    }
    if (n === 4) {
      var dx = parseDate(x); var dy = parseDate(y);
      if (dx && dy) return isAsc ? dx-dy : dy-dx;
    }
    return isAsc ? x.localeCompare(y) : y.localeCompare(x);
  });
  rows.forEach(function(row){ table.tBodies[0].appendChild(row); });
  var th = table.rows[0].cells[n];
  th.innerHTML = th.innerHTML + (isAsc ? ' ▼' : ' ▲');
  table.setAttribute("data-sort-col", n);
  table.setAttribute("data-sort-dir", isAsc ? "desc" : "asc");
}
function parseDate(dateStr){
  var parts = dateStr.split(/[\\/ :]/);
  if (parts.length >= 5) return new Date(parts[2], parts[1]-1, parts[0], parts[3], parts[4]).getTime();
  return null;
}
function exportToCSV(){
  var table = document.getElementById("resultsTable");
  var rows = table.getElementsByTagName("tr");
  var csv = [];
  for (var i=0;i<rows.length;i++){
    var row=[], cols=rows[i].querySelectorAll("td, th");
    for (var j=0;j<cols.length;j++){
      row.push('"' + cols[j].innerText.replace(/"/g,'""') + '"');
    }
    csv.push(row.join(","));
  }
  var csvString = csv.join("\\n");
  var blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  var link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = 'verificacao_residencia.csv';
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
</script>
</head>
<body>
<h1>Verificação de Residência - TRES LAGOAS</h1>
<div class="stats">
  <div class="stat-item"><span class="stat-number" id="totalCount">""" + str(total) + """</span>Total verificadas</div>
  <div class="stat-item"><span class="stat-number" id="coerenteCount" style="color:#27ae60">""" + str(coerentes) + """</span>Coerentes</div>
  <div class="stat-item"><span class="stat-number" id="incoerenteCount" style="color:#e74c3c">""" + str(incoerentes) + """</span>Incoerentes</div>
  <div class="stat-item"><span class="stat-number" id="naoEncontradoCount" style="color:#f39c12">""" + str(nao_encontrados) + """</span>Não encontrados</div>
  <button onclick="exportToCSV()" style="float:right;background:white;color:#2c3e50;border:none;
          padding:8px 15px;border-radius:4px;cursor:pointer;font-weight:bold;">Exportar CSV</button>
</div>
<input type="text" id="search" onkeyup="searchTable()" placeholder="Buscar por nome, código, município ou status...">
<table id="resultsTable" data-sort-col="-1" data-sort-dir="asc">
<thead>
<tr>
  <th onclick="sortTable(0)">Nome do Paciente</th>
  <th onclick="sortTable(1)">Código</th>
  <th onclick="sortTable(2)">Status</th>
  <th onclick="sortTable(3)">Município Residência</th>
  <th onclick="sortTable(4)">Data/Hora Verificação</th>
</tr>
</thead>
<tbody>
"""

        html_rows = ""
        for codigo, valores in sorted(dados.items(), key=lambda x: x[0], reverse=True):
            nome, status, municipio, data_hora = valores

            nome_h = html_escape(nome or "")
            codigo_h = html_escape(codigo or "")
            status_h = html_escape(status or "")
            municipio_h = html_escape(municipio or "")
            data_hora_h = html_escape(data_hora or "")

            classe_status = (
                (status or "")
                .lower()
                .replace(" ", "-")
                .replace("ã", "a")
                .replace("á", "a")
                .replace("é", "e")
                .replace("ê", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ô", "o")
                .replace("ú", "u")
                .replace("ç", "c")
            )

            html_rows += (
                f"<tr><td>{nome_h}</td><td>{codigo_h}</td>"
                f"<td class=\"{classe_status}\">{status_h}</td>"
                f"<td>{municipio_h}</td><td>{data_hora_h}</td></tr>\n"
            )

        html_footer = """</tbody>
</table>
<div class="last-update">
  Última atualização: """ + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + """
</div>
</body>
</html>"""

        html_completo = html_head + html_rows + html_footer

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html_completo)

        _safe_log(
            self.log,
            f"HTML atualizado: {total} fichas (✓ {coerentes} | ✗ {incoerentes} | ? {nao_encontrados} | ! {erros})",
        )
