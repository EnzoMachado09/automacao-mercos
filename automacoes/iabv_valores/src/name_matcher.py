from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

# Colunas do Excel
COL_NOME = 1       # A — RAZÃO SOCIAL
COL_2024 = 2       # B
COL_2025 = 3       # C
COL_2026 = 4       # D
COL_ALIASES = 7    # G

LINHA_HEADER = 4
LINHA_DADOS_INICIO = 5
LINHA_TOTAL = 241

ANO_PARA_COLUNA = {"2024": COL_2024, "2025": COL_2025, "2026": COL_2026}


def normalizar(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return sem_acento.upper().strip()


@dataclass
class EntradaCliente:
    linha: int
    nome_original: str
    nome_norm: str
    aliases: list[str] = field(default_factory=list)  # já normalizados


@dataclass
class ResultadoMatch:
    entrada: EntradaCliente
    nome_pdf: str           # nome que veio do PDF
    tipo: str               # "exato", "alias", "substring", "fuzzy"
    score: float            # 1.0 para exato/alias, ratio para fuzzy, 0.9 para substring


def _aliases_de_celula(valor: str | None) -> list[str]:
    if not valor:
        return []
    return [normalizar(a) for a in valor.split("|") if a.strip()]


def construir_lookup(ws) -> list[EntradaCliente]:
    """Lê as linhas de dados do Excel e monta a lista de clientes para matching."""
    entradas: list[EntradaCliente] = []
    for linha in range(LINHA_DADOS_INICIO, LINHA_TOTAL):
        nome_cell = ws.cell(row=linha, column=COL_NOME).value
        if not nome_cell or not str(nome_cell).strip():
            continue
        nome_str = str(nome_cell)
        alias_cell = ws.cell(row=linha, column=COL_ALIASES).value
        entradas.append(EntradaCliente(
            linha=linha,
            nome_original=nome_str,
            nome_norm=normalizar(nome_str),
            aliases=_aliases_de_celula(str(alias_cell) if alias_cell else None),
        ))
    return entradas


_TOKENS_GENERICOS = {
    "LTDA", "ME", "SA", "SS", "EIRELI", "EPP", "DE", "DO", "DA", "DOS", "DAS",
    "E", "EM", "COM", "O", "A", "OS", "AS",
}


def _compartilha_token_distintivo(nome1: str, nome2: str) -> bool:
    """
    Garante que os dois nomes compartilham ao menos um token não-genérico.
    Evita fuzzy matches como TORKER -> WIEBBELLING por terem
    'DISTRIBUIDORA DE PECAS AUTOMOTIVAS LTDA' em comum.
    """
    def tokens(n: str) -> set[str]:
        return {t for t in n.split() if t not in _TOKENS_GENERICOS}

    return bool(tokens(nome1) & tokens(nome2))


def _contem_como_palavra(curto: str, longo: str) -> bool:
    """Verifica se 'curto' aparece como sequência completa de tokens em 'longo'."""
    tokens_curto = curto.split()
    tokens_longo = longo.split()
    if not tokens_curto:
        return False
    # Todos os tokens do nome curto devem estar no nome longo
    return all(t in tokens_longo for t in tokens_curto)


def encontrar_match(
    nome_pdf_norm: str,
    entradas: list[EntradaCliente],
    limiar_fuzzy: float = 0.75,
) -> ResultadoMatch | None:
    """
    Tenta casar nome_pdf_norm contra as entradas do Excel.
    Ordem de prioridade: exato → alias → substring → fuzzy.
    """

    # 1. Exato
    for entrada in entradas:
        if entrada.nome_norm == nome_pdf_norm:
            return ResultadoMatch(entrada, nome_pdf_norm, "exato", 1.0)

    # 2. Alias exato
    for entrada in entradas:
        if nome_pdf_norm in entrada.aliases:
            return ResultadoMatch(entrada, nome_pdf_norm, "alias", 1.0)

    # 3. Substring bidirecional (nome Excel contido no PDF ou vice-versa)
    matches_substring: list[tuple[EntradaCliente, float]] = []
    for entrada in entradas:
        curto, longo = sorted([entrada.nome_norm, nome_pdf_norm], key=len)
        if _contem_como_palavra(curto, longo):
            score = len(curto) / max(len(longo), 1)
            matches_substring.append((entrada, score))

    if matches_substring:
        melhor, score = max(matches_substring, key=lambda x: x[1])
        return ResultadoMatch(melhor, nome_pdf_norm, "substring", round(score, 3))

    # 4. Fuzzy (difflib — sem dependência extra)
    melhor_ratio = 0.0
    melhor_entrada: EntradaCliente | None = None
    for entrada in entradas:
        candidatos = [entrada.nome_norm] + entrada.aliases
        for candidato in candidatos:
            ratio = difflib.SequenceMatcher(None, nome_pdf_norm, candidato).ratio()
            if ratio > melhor_ratio:
                melhor_ratio = ratio
                melhor_entrada = entrada

    if (
        melhor_entrada is not None
        and melhor_ratio >= limiar_fuzzy
        and _compartilha_token_distintivo(nome_pdf_norm, melhor_entrada.nome_norm)
    ):
        return ResultadoMatch(melhor_entrada, nome_pdf_norm, "fuzzy", round(melhor_ratio, 3))

    return None
