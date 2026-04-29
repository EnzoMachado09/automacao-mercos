"""
Automação da Etapa 2: Anotar Informações dos Pedidos
Extrai produtos e quantidades de excels de pedidos e preenche planilha modelo

Fluxo: Lê Excel pedido → Extrai dados → Salva em modelo
Usando openpyxl para manipulação direta de arquivos (sem UI automation)
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import json
import logging
import re
from datetime import datetime
from typing import Optional

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

LOGGER = logging.getLogger(__name__)


@dataclass
class ExcelPaths:
    """Caminhos para automação direta de arquivos Excel"""
    modelo_path: Path  # Caminho do Excel modelo (template)
    pedidos_input_dir: Path  # Diretório com arquivos de pedidos .xlsx (entrada)
    output_dir: Path  # Diretório de saída para arquivos preenchidos


class ExcelAutomation:
    """Automação de preenchimento de Excel modelo com dados de pedidos
    
    Usa openpyxl para manipulação direta de arquivos:
    1. Itera arquivos .xlsx na pasta de pedidos
    2. Para cada pedido: extrai dados
    3. Preenche modelo e salva com sufixo ' M'
    """
    
    def __init__(self, paths: ExcelPaths):
        self.modelo_path = Path(paths.modelo_path)
        self.pedidos_input_dir = Path(paths.pedidos_input_dir)
        self.output_dir = Path(paths.output_dir)
        self.pedido_count = 0
        
        # Validar caminhos
        if not self.modelo_path.exists():
            raise FileNotFoundError(f"❌ Modelo não encontrado: {self.modelo_path}")
        if not self.pedidos_input_dir.is_dir():
            raise NotADirectoryError(f"❌ Diretório de pedidos não encontrado: {self.pedidos_input_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        LOGGER.info(f"✅ Automação Etapa 2 inicializada (openpyxl)")
        LOGGER.info(f"   Modelo: {self.modelo_path}")
        LOGGER.info(f"   Entrada (pedidos): {self.pedidos_input_dir}")
        LOGGER.info(f"   Saída: {self.output_dir}")
    
    def run(self) -> None:
        """Processa todos os arquivos .xlsx na pasta de pedidos"""
        LOGGER.info("=" * 70)
        LOGGER.info("🚀 INICIANDO AUTOMAÇÃO ETAPA 2 - EXTRAÇÃO DE DADOS")
        LOGGER.info("=" * 70)
        
        # Listar arquivos .xlsx de entrada (ignora os já gerados com sufixo " M.xlsx")
        pedidos = sorted(
            p for p in self.pedidos_input_dir.glob("*.xlsx")
            if not p.stem.endswith(" M")
        )
        
        if not pedidos:
            LOGGER.warning(f"⚠️  Nenhum arquivo .xlsx encontrado em {self.pedidos_input_dir}")
            return
        
        LOGGER.info(f"📂 {len(pedidos)} arquivo(s) de pedido encontrado(s)")
        
        # Processar cada pedido
        for pedido_path in pedidos:
            try:
                self.pedido_count += 1
                LOGGER.info(f"\n{'='*70}")
                LOGGER.info(f"📋 PEDIDO {self.pedido_count}/{len(pedidos)}: {pedido_path.name}")
                LOGGER.info(f"{'='*70}")
                
                self._processar_pedido(pedido_path)
                
            except Exception as e:
                LOGGER.error(f"❌ Erro ao processar {pedido_path.name}: {e}")
                continue
        
        LOGGER.info(f"\n{'='*70}")
        LOGGER.info(f"✅ AUTOMAÇÃO CONCLUÍDA - {self.pedido_count} pedido(s) processado(s)")
        LOGGER.info(f"{'='*70}\n")
    
    def _processar_pedido(self, pedido_path: Path) -> None:
        """Processa um único arquivo de pedido:
        1. Extrai dados (produtos e quantidades)
        2. Preenche modelo
        3. Salva com sufixo ' M'
        """
        LOGGER.info(f"   [1] Abrindo pedido...")
        
        try:
            pedido_wb = load_workbook(pedido_path, data_only=True)
        except Exception as e:
            raise Exception(f"Não conseguiu abrir {pedido_path}: {e}")
        
        # Extrair dados de todas as sheets do pedido
        todos_produtos = []
        todas_quantidades = []
        col_produtos_referencia: Optional[int] = None
        col_qtd_referencia: Optional[int] = None

        for sheet_idx, sheet_name in enumerate(pedido_wb.sheetnames, 1):
            LOGGER.info(f"   [2.{sheet_idx}] Processando sheet: '{sheet_name}'")

            sheet = pedido_wb[sheet_name]

            # Localizar linha de header e colunas de código e qtd
            resultado = self._encontrar_linha_e_colunas(sheet)

            if resultado is not None:
                row_header, col_produtos, col_qtd = resultado
                data_start_row = row_header + 1
                # Guarda as colunas da primeira sheet com header para reusar nas seguintes
                col_produtos_referencia = col_produtos
                col_qtd_referencia = col_qtd
            elif col_produtos_referencia is not None:
                # Sheets seguintes sem header: reutiliza as colunas já identificadas
                LOGGER.info(
                    f"      ℹ️  Sem header em '{sheet_name}', "
                    f"reutilizando colunas da página anterior "
                    f"(código={col_produtos_referencia}, qtd={col_qtd_referencia})"
                )
                col_produtos = col_produtos_referencia
                col_qtd = col_qtd_referencia
                data_start_row = 1
            else:
                LOGGER.warning(f"      ⚠️  Sem header e sem referência anterior em '{sheet_name}', pulando sheet")
                continue

            # Extrair pares código+quantidade
            produtos, quantidades = self._extrair_produtos(
                sheet, data_start_row, col_produtos, col_qtd
            )

            todos_produtos.extend(produtos)
            todas_quantidades.extend(quantidades)

            LOGGER.info(f"      ✅ {len(produtos)} produtos, {len(quantidades)} quantidades")
        
        # Extrair metadados (cliente e data) da primeira sheet
        metadados = {"cliente": None, "data_pedido": None}
        try:
            primeira_sheet = pedido_wb[pedido_wb.sheetnames[0]]
            metadados = self._extrair_metadados(primeira_sheet)
        except Exception as e:
            LOGGER.warning(f"      ⚠️  Não foi possível extrair metadados: {e}")

        pedido_wb.close()

        # Preencher modelo
        LOGGER.info(f"   [3] Preenchendo modelo...")
        nome_saida = pedido_path.stem + " M.xlsx"
        caminho_saida = self.output_dir / nome_saida
        self._preencher_modelo(todos_produtos, todas_quantidades, caminho_saida)

        # Salvar metadados em JSON ao lado do M.xlsx
        try:
            caminho_json = self.output_dir / (pedido_path.stem + " M.json")
            metadados["arquivo_xlsx"] = nome_saida
            metadados["gerado_em"] = datetime.now().isoformat(timespec="seconds")
            caminho_json.write_text(json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8")
            LOGGER.info(f"      ✅ Metadados salvos: cliente={metadados['cliente']}, data={metadados['data_pedido']}")
        except Exception as e:
            LOGGER.warning(f"      ⚠️  Não foi possível salvar metadados JSON: {e}")

        LOGGER.info(f"   [4] Salvando resultado...")
        LOGGER.info(f"      → {caminho_saida}")
        LOGGER.info(f"   ✅ Pedido processado com sucesso")
    
    # ============================================================================
    # FUNÇÕES AUXILIARES - MANIPULAÇÃO DE EXCEL
    # ============================================================================

    def _extrair_metadados(self, sheet: Worksheet) -> dict:
        """Extrai nome do cliente e data do pedido varrendo a planilha por labels.

        Regras:
        - "Pessoa" → valor à direita = nome do cliente
        - "Data" (exato, não "Data Ent.") → valor à direita = data do pedido
        """
        cliente = None
        data_pedido = None

        for row in range(1, sheet.max_row + 1):
            for col in range(1, sheet.max_column + 1):
                val = sheet.cell(row=row, column=col).value
                if val is None:
                    continue
                texto = str(val).strip().lower()

                if texto == "pessoa" and cliente is None:
                    vizinho = sheet.cell(row=row, column=col + 1).value
                    if vizinho:
                        cliente = str(vizinho).strip()

                if texto == "data" and data_pedido is None:
                    vizinho = sheet.cell(row=row, column=col + 1).value
                    if vizinho:
                        data_str = str(vizinho).strip()
                        # Aceita tanto string "DD/MM/AAAA" quanto objeto date/datetime do openpyxl
                        if hasattr(vizinho, "strftime"):
                            data_str = vizinho.strftime("%d/%m/%Y")
                        data_pedido = data_str

                if cliente and data_pedido:
                    return {"cliente": cliente, "data_pedido": data_pedido}

        return {"cliente": cliente, "data_pedido": data_pedido}

    # Formatos aceitos: nnnn | nnnn-nn | nnnn-ln | nnnn-l | llnnnn | nnnnln | nnnn-n
    _CODIGO_RE = re.compile(
        r'^[A-Za-z]{0,2}\d{3,6}([A-Za-z]\d?)?(-(\d{1,2}[A-Za-z]?|[A-Za-z]\d*))?$'
    )

    @staticmethod
    def _is_codigo(valor: str) -> bool:
        return bool(ExcelAutomation._CODIGO_RE.match(valor.strip()))

    def _encontrar_linha_e_colunas(
        self, sheet: Worksheet
    ) -> Optional[tuple[int, int, int]]:
        """Localiza a linha de header da tabela de produtos e as colunas de código e qtd.

        Estratégia: varre as linhas procurando uma que tenha simultaneamente
        um header de produto (col A geralmente) e um header de quantidade.
        Retorna (row_header, col_codigo, col_qtd) ou None.
        """
        HEADERS_PRODUTO = {"produto", "item", "cod", "código", "cód"}
        HEADERS_QTD = {"qtd", "qtd.", "quantidade", "qtd..", "quant"}

        for row in range(1, sheet.max_row + 1):
            col_cod_encontrada = None
            col_qtd_encontrada = None

            for col in range(1, sheet.max_column + 1):
                val = sheet.cell(row=row, column=col).value
                if val is None:
                    continue
                texto = str(val).strip().lower()

                if col_cod_encontrada is None:
                    for h in HEADERS_PRODUTO:
                        if texto == h or texto.startswith(h):
                            col_cod_encontrada = col
                            break

                if col_qtd_encontrada is None:
                    for h in HEADERS_QTD:
                        if texto == h or texto.startswith(h):
                            col_qtd_encontrada = col
                            break

            if col_cod_encontrada and col_qtd_encontrada:
                LOGGER.info(
                    f"      🔍 Header na linha {row}: "
                    f"código=col {col_cod_encontrada}, qtd=col {col_qtd_encontrada}"
                )
                return (row, col_cod_encontrada, col_qtd_encontrada)

        return None

    def _detectar_colunas_por_conteudo(
        self, sheet: Worksheet
    ) -> tuple[Optional[int], Optional[int]]:
        """Detecta colunas de código e quantidade contando valores válidos em cada coluna.

        Usada quando a sheet não tem linha de header (páginas 2+ do pedido).
        Retorna (col_codigo, col_qtd). A coluna com mais códigos válidos vira código;
        a com mais números que NÃO são códigos vira quantidade.
        """
        contagem_cod: dict[int, int] = {}
        contagem_qtd: dict[int, int] = {}

        for col in range(1, sheet.max_column + 1):
            c_cod = 0
            c_qtd = 0
            for row in range(1, sheet.max_row + 1):
                val = sheet.cell(row=row, column=col).value
                if val is None:
                    continue
                texto = str(val).strip()
                if self._is_codigo(texto):
                    c_cod += 1
                else:
                    try:
                        float(texto.replace(',', '.'))
                        c_qtd += 1
                    except ValueError:
                        pass
            contagem_cod[col] = c_cod
            contagem_qtd[col] = c_qtd

        col_cod = max(contagem_cod, key=contagem_cod.get) if any(contagem_cod.values()) else None
        # Para quantidade, exclui a coluna já escolhida como código
        contagem_qtd_filtrado = {c: v for c, v in contagem_qtd.items() if c != col_cod}
        col_qtd = max(contagem_qtd_filtrado, key=contagem_qtd_filtrado.get) if any(contagem_qtd_filtrado.values()) else None

        LOGGER.info(f"      🔍 Colunas detectadas por conteúdo: código={col_cod}, qtd={col_qtd}")
        return col_cod, col_qtd

    def _extrair_produtos(
        self, sheet: Worksheet, data_start_row: int, col_cod: int, col_qtd: int
    ) -> tuple[list[str], list[str]]:
        """Extrai pares (código, quantidade) a partir de data_start_row.

        Para quando encontra uma linha cujo valor na coluna de código não
        corresponde a um código de produto válido (indica fim da tabela).
        Linhas com código vazio são ignoradas.
        """
        codigos: list[str] = []
        qtds: list[str] = []

        for row in range(data_start_row, sheet.max_row + 1):
            val_cod = sheet.cell(row=row, column=col_cod).value

            if val_cod is None:
                continue

            cod_str = str(val_cod).strip()

            if not self._is_codigo(cod_str):
                continue  # linha sem código válido (descrição continuada, totais, etc.)

            val_qtd = sheet.cell(row=row, column=col_qtd).value
            if val_qtd is not None:
                try:
                    # Converte 16,00 → 16 (inteiro)
                    qtd_num = float(str(val_qtd).replace(',', '.'))
                    qtd_str = str(int(qtd_num)) if qtd_num == int(qtd_num) else str(qtd_num)
                except (ValueError, TypeError):
                    qtd_str = str(val_qtd).strip()
            else:
                qtd_str = ""

            codigos.append(cod_str)
            qtds.append(qtd_str)

        return codigos, qtds
    
    def _preencher_modelo(self, produtos: list[str], quantidades: list[str], caminho_saida: Path) -> None:
        """Preenche modelo com produtos e quantidades
        
        Args:
            produtos: Lista de produtos
            quantidades: Lista de quantidades
        """
        try:
            modelo_wb = load_workbook(self.modelo_path)
            modelo_sheet = modelo_wb.active
            
            # Limpar dados antigos (de A2 em diante)
            self._limpar_coluna(modelo_sheet, col=1, start_row=2)  # Coluna A
            self._limpar_coluna(modelo_sheet, col=2, start_row=2)  # Coluna B
            
            # Preencher produtos (coluna A)
            for idx, produto in enumerate(produtos, start=2):
                modelo_sheet.cell(row=idx, column=1).value = produto
            
            # Preencher quantidades (coluna B)
            for idx, qtd in enumerate(quantidades, start=2):
                modelo_sheet.cell(row=idx, column=2).value = qtd
            
            # Salvar cópia preenchida no destino de saída
            modelo_wb.save(caminho_saida)
            modelo_wb.close()
            
            LOGGER.info(f"      ✅ Modelo preenchido com {len(produtos)} produtos")
            
        except Exception as e:
            LOGGER.error(f"      ❌ Erro ao preencher modelo: {e}")
            raise
    
    def _limpar_coluna(self, sheet: Worksheet, col: int, start_row: int = 2, 
                       end_row: Optional[int] = None) -> None:
        """Limpa uma coluna
        
        Args:
            sheet: Worksheet
            col: Número da coluna (1-based)
            start_row: Linha inicial
            end_row: Linha final (default: max_row)
        """
        if end_row is None:
            end_row = sheet.max_row
        
        for row in range(start_row, end_row + 1):
            sheet.cell(row=row, column=col).value = None
