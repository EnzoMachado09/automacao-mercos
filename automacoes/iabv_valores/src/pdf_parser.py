from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

# Regex para prefixo CNPJ/CPF no início do nome (ex: "52.949.544 " ou "12.345.678/0001-99 ")
_CNPJ_PREFIX = re.compile(r"^\d[\d.\-/]+\s+")

# "Total da AC." pode aparecer com variações de espaço/pontuação
_TOTAL_AC_LABEL = re.compile(r"Total\s+da\s+AC\.", re.IGNORECASE)

# Número no formato brasileiro: 1.234,56 ou 1234,56
_BR_NUMBER = re.compile(r"[\d.,]+")


@dataclass
class PedidoInfo:
    pdf_path: Path
    nome_cliente_raw: str       # nome como veio no PDF (com prefixo CNPJ se houver)
    nome_cliente: str           # nome normalizado (sem prefixo, uppercase, sem acentos)
    valor: float
    numero_pedido: str


def normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return sem_acento.upper().strip()


def _strip_cnpj_prefix(nome: str) -> str:
    return _CNPJ_PREFIX.sub("", nome).strip()


def _deduplicar_nome(nome: str) -> str:
    """
    Remove a parte repetida que o pdfplumber extrai quando o PDF tem
    duas colunas na linha "Pessoa" (nome completo + fantasia).
    Ex: 'MAICON MONTEMEZZO MAICON MONTEMEZZO' -> 'MAICON MONTEMEZZO'
    Ex: 'POSTO DE MOLAS ZARICHTA LTDA POSTO DE MOLAS ZARIC' -> 'POSTO DE MOLAS ZARICHTA LTDA'
    Estratégia: se o primeiro token aparecer novamente mais à frente,
    trunca ali — esse ponto marca o início da coluna da direita.
    """
    words = nome.split()
    if len(words) < 2:
        return nome
    primeiro = words[0]
    for i in range(1, len(words)):
        if words[i] == primeiro:
            return " ".join(words[:i]).strip()
    return nome


def _parse_br_float(texto: str) -> float | None:
    """Converte '2.502,35' → 2502.35. Retorna None se não conseguir."""
    texto = texto.strip()
    # Remove separador de milhar (ponto), troca vírgula decimal por ponto
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


_COLUNA_GAP_MIN = 15  # pontos de espaço mínimo para considerar separação de colunas


def _extrair_pessoa(pagina) -> str | None:
    """
    Extrai o nome do cliente da linha 'Pessoa' usando coordenadas x/y.
    Detecta a separação entre colunas (nome legal | nome fantasia) pelo maior gap
    horizontal entre palavras consecutivas, e retorna apenas a coluna esquerda.
    """
    words = pagina.extract_words()
    pessoa_word = next(
        (w for w in words if w["text"].strip().lower() == "pessoa"), None
    )
    if not pessoa_word:
        return None

    pessoa_y = pessoa_word["top"]
    linha_words = sorted(
        [w for w in words if abs(w["top"] - pessoa_y) < 6 and w["text"].strip().lower() != "pessoa"],
        key=lambda w: w["x0"],
    )
    if not linha_words:
        return None

    # Calcula todos os gaps entre palavras consecutivas
    gaps = []
    for i in range(1, len(linha_words)):
        gap = linha_words[i]["x0"] - linha_words[i - 1]["x1"]
        gaps.append((gap, i))

    if gaps:
        max_gap, split_idx = max(gaps, key=lambda x: x[0])
        # Corta se o maior gap for significativamente maior que a média dos outros gaps
        # (indica separação de colunas, não apenas espaço entre palavras)
        if len(gaps) == 1:
            # Apenas um gap: corta se for maior que o limiar mínimo
            if max_gap > _COLUNA_GAP_MIN:
                linha_words = linha_words[:split_idx]
        else:
            outros_gaps = [g for g, _ in gaps if g != max_gap]
            media_outros = sum(outros_gaps) / len(outros_gaps) if outros_gaps else 0
            # Corta se o maior gap for pelo menos 2x a média dos outros E acima do mínimo
            if max_gap > _COLUNA_GAP_MIN and max_gap > media_outros * 2:
                linha_words = linha_words[:split_idx]

    return " ".join(w["text"] for w in linha_words)


def _extrair_total_ac(paginas: list) -> float | None:
    """
    Extrai o valor de 'Total da AC.' percorrendo as tabelas do PDF.
    O valor fica na última coluna da linha que contém o label.
    """
    for pagina in paginas:
        # Tenta extrair via tabelas (mais preciso para PDFs tabulares)
        tabelas = pagina.extract_tables()
        for tabela in tabelas:
            for i, linha in enumerate(tabela):
                celulas = [str(c or "").strip() for c in linha]
                linha_str = " ".join(celulas)
                if _TOTAL_AC_LABEL.search(linha_str):
                    # Próxima linha deve ter os valores; tenta pegar o último valor numérico
                    if i + 1 < len(tabela):
                        proxima = [str(c or "").strip() for c in tabela[i + 1]]
                        for celula in reversed(proxima):
                            if _BR_NUMBER.search(celula):
                                valor = _parse_br_float(celula)
                                if valor is not None:
                                    return valor
                    # Tenta na mesma linha (label e valor na mesma linha, colunas diferentes)
                    for celula in reversed(celulas):
                        if celula and not _TOTAL_AC_LABEL.search(celula):
                            valor = _parse_br_float(celula)
                            if valor is not None:
                                return valor

        # Fallback: extração por texto puro
        texto = pagina.extract_text() or ""
        linhas = texto.splitlines()
        for i, linha in enumerate(linhas):
            if _TOTAL_AC_LABEL.search(linha):
                # Tenta encontrar número após o label na mesma linha
                apos_label = _TOTAL_AC_LABEL.split(linha, maxsplit=1)[-1]
                numeros = _BR_NUMBER.findall(apos_label)
                if numeros:
                    valor = _parse_br_float(numeros[-1])
                    if valor is not None:
                        return valor
                # Tenta na linha seguinte
                if i + 1 < len(linhas):
                    numeros = _BR_NUMBER.findall(linhas[i + 1])
                    if numeros:
                        valor = _parse_br_float(numeros[-1])
                        if valor is not None:
                            return valor

    return None


def _extrair_numero_pedido(texto: str) -> str:
    """Extrai o número do pedido (ex: 'IA2026/521858')."""
    match = re.search(r"N[uú]mero[:\s]+(\S+)", texto, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def parsear_pdf(pdf_path: Path) -> PedidoInfo | None:
    """
    Lê um PDF de pedido IABV e retorna as informações estruturadas.
    Retorna None se não conseguir extrair os campos obrigatórios.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return None

            pagina1 = pdf.pages[0]
            nome_raw = _extrair_pessoa(pagina1)
            if not nome_raw:
                return None

            total = _extrair_total_ac(pdf.pages)
            if total is None:
                return None

            texto_pagina1 = pagina1.extract_text() or ""
            numero = _extrair_numero_pedido(texto_pagina1)
            nome_sem_prefixo = _strip_cnpj_prefix(nome_raw)

            return PedidoInfo(
                pdf_path=pdf_path,
                nome_cliente_raw=nome_raw,
                nome_cliente=normalizar(nome_sem_prefixo),
                valor=total,
                numero_pedido=numero,
            )
    except Exception:
        return None


def parsear_pasta(pasta: Path) -> tuple[list[PedidoInfo], list[Path]]:
    """
    Processa todos os PDFs em uma pasta.
    Retorna (pedidos_ok, pdfs_com_erro).
    """
    pdfs = sorted(pasta.glob("*.pdf"))
    pedidos: list[PedidoInfo] = []
    erros: list[Path] = []

    for pdf_path in pdfs:
        info = parsear_pdf(pdf_path)
        if info is not None:
            pedidos.append(info)
        else:
            erros.append(pdf_path)

    return pedidos, erros
