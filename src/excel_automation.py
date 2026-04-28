"""
Automação da Etapa 2: Anotar Informações dos Pedidos
Extrai produtos e quantidades de excels de pedidos e preenche planilha modelo

Fluxo: Lê Excel pedido → Extrai dados → Salva em modelo
Usando openpyxl para manipulação direta de arquivos (sem UI automation)
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import logging
import re
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
        
        for sheet_idx, sheet_name in enumerate(pedido_wb.sheetnames, 1):
            LOGGER.info(f"   [2.{sheet_idx}] Processando sheet: '{sheet_name}'")
            
            sheet = pedido_wb[sheet_name]
            
            # Encontrar colunas de produtos e quantidades
            col_produtos = self._encontrar_coluna_por_header(sheet, ["Produto", "Item", "Cod", "Código"])
            col_qtd = self._encontrar_coluna_por_header(sheet, ["Qtd", "Quantidade", "Qtd.", "QTD"])
            
            if col_produtos is None:
                LOGGER.warning(f"      ⚠️  Coluna de produtos não encontrada em '{sheet_name}'")
                col_produtos = 1  # Padrão: coluna A
            
            if col_qtd is None:
                LOGGER.warning(f"      ⚠️  Coluna de quantidades não encontrada em '{sheet_name}'")
                col_qtd = 2  # Padrão: coluna B
            
            # Extrair dados
            produtos = self._extrair_coluna(sheet, col_produtos, min_row=2)
            quantidades = self._extrair_coluna(sheet, col_qtd, min_row=2)
            
            todos_produtos.extend(produtos)
            todas_quantidades.extend(quantidades)
            
            LOGGER.info(f"      ✅ {len(produtos)} produtos, {len(quantidades)} quantidades")
        
        pedido_wb.close()
        
        # Preencher modelo
        LOGGER.info(f"   [3] Preenchendo modelo...")
        nome_saida = pedido_path.stem + " M.xlsx"
        caminho_saida = self.output_dir / nome_saida
        self._preencher_modelo(todos_produtos, todas_quantidades, caminho_saida)
        
        # Salvar com sufixo ' M'
        LOGGER.info(f"   [4] Salvando resultado...")
        LOGGER.info(f"      → {caminho_saida}")
        LOGGER.info(f"   ✅ Pedido processado com sucesso")
    
    # ============================================================================
    # FUNÇÕES AUXILIARES - MANIPULAÇÃO DE EXCEL
    # ============================================================================
    
    def _encontrar_coluna_por_header(self, sheet: Worksheet, headers: list[str]) -> Optional[int]:
        """Encontra coluna procurando pelos headers na primeira linha
        
        Args:
            sheet: Worksheet a processar
            headers: Lista de possíveis nomes de header
        
        Returns:
            Número da coluna (1-based) ou None se não encontrado
        """
        # Procurar na primeira linha
        for col in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=1, column=col)
            
            if cell.value is None:
                continue
            
            cell_value = str(cell.value).strip().lower()
            
            # Verificar se matches qualquer um dos headers
            for header in headers:
                if header.lower() in cell_value or cell_value in header.lower():
                    LOGGER.debug(f"      🔍 Header '{header}' encontrado na coluna {col}")
                    return col
        
        return None
    
    def _extrair_coluna(self, sheet: Worksheet, col_index: int, min_row: int = 2, 
                       max_row: Optional[int] = None) -> list[str]:
        """Extrai valores de uma coluna
        
        Args:
            sheet: Worksheet
            col_index: Número da coluna (1-based)
            min_row: Linha inicial
            max_row: Linha final (default: última linha com dados)
        
        Returns:
            Lista de valores (strings)
        """
        valores = []
        
        if max_row is None:
            max_row = sheet.max_row
        
        for row in range(min_row, max_row + 1):
            cell = sheet.cell(row=row, column=col_index)
            
            if cell.value is None:
                continue
            
            valor = str(cell.value).strip()
            
            if valor:  # Só adiciona se não vazio
                valores.append(valor)
        
        return valores
    
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
