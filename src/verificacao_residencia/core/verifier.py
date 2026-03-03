import os
import re
import base64
from datetime import datetime
from html import escape as html_escape
from typing import Callable, Dict, List, Tuple, Optional, Any

import requests

from .log import _safe_log


HTML_FILE = "verificacao_residencia.html"

API_SEARCH_URL = "https://sisreg-es.saude.gov.br/solicitacao-ambulatorial-ms-tres-lagoas/_search"

CNES_UNIDADES = [
    "9824111","6726747","3475298","2756900","2756927","6429343","2757176","9529500",
    "9430830","7638051","6288502","2757044","2757052","2757060","9390693","6343864",
    "2757079","2757087","2757095","9543333","9615946","2757109","2757117","2757125",
    "2757133","2757141","2757168","3453766"
]

MUN_ALVO = "TRES LAGOAS"
UF_ALVO = "MS"


SOURCE_FIELDS = [
    "codigo_solicitacao",
    "no_usuario",
    "nome_paciente",
    "municipio_paciente_residencia",
    "uf_paciente_residencia",
    "sigla_situacao"
]




def _norm(s: Any) -> str:
    return ("" if s is None else str(s)).strip()

def _upper(s: Any) -> str:
    return _norm(s).upper()

def _to_iso_date(dt_str: str) -> str:
    """
    Aceita:
      - YYYY-MM-DD
      - dd/mm/aaaa
      - dd/mm/yyyy
    Retorna YYYY-MM-DD
    """
    s = (dt_str or "").strip()
    if not s:
        return s

    
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s

    
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}"

    
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass

    
    return s

def _basic_auth_header(usuario: str, senha: str) -> str:
    pair = f"{usuario}:{senha}".encode("ascii", errors="ignore")
    b64 = base64.b64encode(pair).decode("ascii")
    return f"Basic {b64}"

def _slug_status(status: str) -> str:
    
    s = (status or "").lower().strip().replace(" ", "-")
    s = (
        s.replace("ã", "a")
         .replace("á", "a")
         .replace("é", "e")
         .replace("ê", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ô", "o")
         .replace("ú", "u")
         .replace("ç", "c")
    )
    return s




class SisregResidenciaVerifier:
    """
    Substitui Selenium por API.
    Mantém a mesma assinatura usada pelo runner/UI.
    """

    def __init__(self, log: Callable[[str], None], timeout: int = 30):
        self.log = log
        self.timeout = timeout

    def run(self, dt_inicio: str, dt_fim: str, usuario: str, senha: str) -> Tuple[bool, str]:
        _safe_log(self.log, "=== VERIFICAÇÃO DE RESIDÊNCIA - API ===")

        registros = self._carregar_html_existente()

        dt_ini_iso = _to_iso_date(dt_inicio)
        dt_fim_iso = _to_iso_date(dt_fim)

        _safe_log(self.log, f"Consultando período: {dt_ini_iso} à {dt_fim_iso}")
        _safe_log(self.log, f"CNES na query: {len(CNES_UNIDADES)}")

        headers = {
            "Authorization": _basic_auth_header(usuario, senha),
            "Content-Type": "application/json",
        }

        try:
            docs = self._fetch_all_docs(headers, dt_ini_iso, dt_fim_iso)
            _safe_log(self.log, f"Retornos da API: {len(docs)} solicitações")

            
            novos = 0
            for src in docs:
                codigo = _norm(src.get("codigo_solicitacao"))
                if not codigo:
                    continue

                if codigo in registros:
                    continue

                nome = _norm(src.get("no_usuario") or src.get("nome_paciente") or "")
                mun = _upper(src.get("municipio_paciente_residencia"))
                uf = _upper(src.get("uf_paciente_residencia"))

                data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                
                if not mun or not uf:
                    registros[codigo] = [nome, "não encontrado", "", data_hora]
                    novos += 1
                    continue

                
                if mun == MUN_ALVO and uf == UF_ALVO:
                    
                    
                    continue

                
                registros[codigo] = [nome, "incoerente", f"{mun} - {uf}", data_hora]
                novos += 1

                
                if novos % 50 == 0:
                    self._salvar_html_dinamico(registros)

            self._salvar_html_dinamico(registros)
            _safe_log(self.log, f"Processamento concluído. Total no HTML: {len(registros)} (novos: {novos})")
            _safe_log(self.log, f"Resultados salvos em '{HTML_FILE}'")
            return True, HTML_FILE

        except requests.HTTPError as e:
            _safe_log(self.log, f"HTTPError na API: {e} | resp: {getattr(e.response,'text', '')[:300]}")
            try:
                self._salvar_html_dinamico(registros)
            except Exception:
                pass
            return False, HTML_FILE

        except Exception as e:
            _safe_log(self.log, f"Erro durante execução (API): {e}")
            try:
                self._salvar_html_dinamico(registros)
            except Exception:
                pass
            return False, HTML_FILE

    
    
    
    def _fetch_all_docs(self, headers: Dict[str, str], dt_ini_iso: str, dt_fim_iso: str) -> List[Dict[str, Any]]:
        """
        Busca todos os hits do período.
        Seu PS usa size=800 sem paginação. Aqui eu faço paginação por `from`.
        Se o índice tiver limite alto de paginação, funciona. Se não, te explico o scroll depois.
        """
        size = 800
        offset = 0
        out: List[Dict[str, Any]] = []

        while True:
            body = {
                "size": size,
                "from": offset,
                "sort": [{"data_solicitacao": {"order": "desc"}}],
                "_source": SOURCE_FIELDS,
                "query": {
                    "bool": {
                        "must": [
                            {"terms": {"codigo_unidade_solicitante": CNES_UNIDADES}},
                            {"range": {"data_solicitacao": {"gte": dt_ini_iso, "lte": dt_fim_iso}}},
                        ],
                        "must_not": [
                            {"term": {"sigla_situacao": "D"}}
                        ]
                    }
                },
            }

            r = requests.post(API_SEARCH_URL, headers=headers, json=body, timeout=self.timeout)
            r.raise_for_status()

            data = r.json() or {}
            hits = (((data.get("hits") or {}).get("hits")) or [])
            batch = [h.get("_source") or {} for h in hits]

            out.extend(batch)
            _safe_log(self.log, f"API: offset={offset} recebeu={len(batch)} total={len(out)}")

            if len(batch) < size:
                break

            offset += size

            
            if offset > 200_000:
                _safe_log(self.log, "Guardrail: offset muito alto; parando paginação para evitar loop infinito.")
                break

        return out

    
    
    
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

            classe_status = _slug_status(status)

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