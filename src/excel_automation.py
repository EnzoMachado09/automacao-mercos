"""
Automação da Etapa 2: Anotar Informações dos Pedidos
Extrai produtos e quantidades de excels de pedidos e preenche planilha modelo
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import logging
import re
import time

import pyautogui
import openpyxl
from openpyxl.utils import get_column_letter

LOGGER = logging.getLogger(__name__)


@dataclass
class ExcelCoordinates:
    """Coordenadas necessárias para automação de Excel"""
    excel_taskbar_left: tuple[int, int] | None = None  # Ícone Excel modelo na taskbar
    excel_taskbar_right: tuple[int, int] | None = None  # Ícone Excel pedido na taskbar
    folder_window_coords: tuple[int, int] | None = None  # Janela da pasta de pedidos
    
    # Será preenchido pelo usuário


class ExcelAutomation:
    """Automação de preenchimento de Excel modelo com dados de pedidos"""
    
    def __init__(self, pedidos_folder: Path, modelo_path: Path, coords: ExcelCoordinates):
        self.pedidos_folder = Path(pedidos_folder)
        self.modelo_path = Path(modelo_path)
        self.coords = coords
        self.current_file: Path | None = None
        self.current_sheet = None
        self.collected_items: list[str] = []  # Produtos
        self.collected_quantities: list[str] = []  # Quantidades
        
        LOGGER.info(f"🗂️  Pasta de pedidos: {self.pedidos_folder}")
        LOGGER.info(f"📊 Planilha modelo: {self.modelo_path}")
    
    def run(self) -> None:
        """Executa automação completa da Etapa 2"""
        LOGGER.info("=" * 60)
        LOGGER.info("🚀 Iniciando Etapa 2: Anotar Informações dos Pedidos")
        LOGGER.info("=" * 60)
        
        # Listar arquivos Excel da pasta
        excel_files = sorted(self.pedidos_folder.glob("*.xlsx"))
        if not excel_files:
            LOGGER.error(f"❌ Nenhum arquivo Excel encontrado em {self.pedidos_folder}")
            return
        
        LOGGER.info(f"📁 Encontrados {len(excel_files)} arquivos de pedidos")
        for idx, file in enumerate(excel_files, 1):
            LOGGER.info(f"   {idx}. {file.name}")
        
        # Processar cada pedido
        for idx, pedido_file in enumerate(excel_files, 1):
            try:
                LOGGER.info(f"\n{'='*60}")
                LOGGER.info(f"📄 Processando pedido {idx}/{len(excel_files)}: {pedido_file.name}")
                LOGGER.info(f"{'='*60}")
                
                self.process_pedido(pedido_file)
                
                # Salvar modelo após cada pedido
                self.save_modelo()
                
                # Avançar para próximo (exceto no último)
                if idx < len(excel_files):
                    self.advance_to_next_file()
                    time.sleep(1)
            
            except Exception as e:
                LOGGER.error(f"❌ Erro ao processar {pedido_file.name}: {e}", exc_info=True)
                continue
        
        LOGGER.info(f"\n{'='*60}")
        LOGGER.info("✅ Etapa 2 concluída!")
        LOGGER.info(f"{'='*60}")
    
    def process_pedido(self, pedido_file: Path) -> None:
        """Processa um arquivo de pedido completo (todas as páginas)"""
        self.current_file = pedido_file
        self.collected_items = []
        self.collected_quantities = []
        
        # Etapa 1: Abrir primeiro pedido em Excel
        LOGGER.info(f"📂 Abrindo: {pedido_file.name}")
        pyautogui.press("enter")
        time.sleep(10)  # Delay para Excel abrir
        
        # Processar cada página do pedido
        page = 1
        while True:
            try:
                LOGGER.info(f"\n📄 Página {page} do pedido")
                
                if page == 1:
                    # Página 1: Usar headers "Produto" e "Qtd."
                    self._process_page_1()
                else:
                    # Páginas 2+: Pattern matching
                    self._process_page_n(page)
                
                # Verificar se tem mais página
                if not self._has_next_page():
                    LOGGER.info("✅ Fim do pedido (última página)")
                    break
                
                self._go_to_next_page()
                page += 1
            
            except Exception as e:
                LOGGER.error(f"❌ Erro ao processar página {page}: {e}", exc_info=True)
                break
        
        LOGGER.info(f"📊 Pedido completo:")
        LOGGER.info(f"   Itens coletados: {len(self.collected_items)}")
        LOGGER.info(f"   Quantidades coletadas: {len(self.collected_quantities)}")
    
    def _process_page_1(self) -> None:
        """Processa página 1 com headers 'Produto' e 'Qtd.'"""
        LOGGER.info("   Página 1: Usando headers 'Produto' e 'Qtd.'")
        
        # Etapa 2: Identificar coluna de produtos
        products_col = self._find_column_by_header("Produto")
        LOGGER.info(f"   Coluna 'Produto' encontrada: {products_col}")
        
        # Etapa 3: Copiar produtos
        items = self._extract_column_data(products_col)
        LOGGER.info(f"   ✅ Copiados {len(items)} produtos")
        self.collected_items.extend(items)
        
        # Etapa 7: Identificar coluna de quantidades
        qty_col = self._find_column_by_header("Qtd.")
        LOGGER.info(f"   Coluna 'Qtd.' encontrada: {qty_col}")
        
        # Etapa 7: Copiar quantidades
        quantities = self._extract_column_data(qty_col)
        LOGGER.info(f"   ✅ Copiadas {len(quantities)} quantidades")
        self.collected_quantities.extend(quantities)
    
    def _process_page_n(self, page: int) -> None:
        """Processa página 2+ usando pattern matching"""
        LOGGER.info(f"   Página {page}: Usando pattern matching (produtos em A, quantidades em D)")
        
        # Etapa 13: Copiar coluna inteira de itens (coluna A)
        items = self._extract_column_data_pattern("products")
        LOGGER.info(f"   ✅ Copiados {len(items)} produtos (padrão)")
        self.collected_items.extend(items)
        
        # Etapa 17: Copiar coluna de quantidades (detectar via padrão)
        quantities = self._extract_column_data_pattern("quantities")
        LOGGER.info(f"   ✅ Copiadas {len(quantities)} quantidades (padrão)")
        self.collected_quantities.extend(quantities)
    
    def _find_column_by_header(self, header_text: str) -> int:
        """Encontra a coluna pela célula header (ex: 'Produto', 'Qtd.')
        Retorna índice da coluna (1-based)"""
        LOGGER.debug(f"   🔍 Procurando coluna com header: '{header_text}'")
        
        # TODO: Usar pyautogui para ler valores da tela
        # Por enquanto, placeholder que será preenchido
        
        LOGGER.warning(f"   ⚠️  Função _find_column_by_header precisa de implementação com OCR/pattern matching")
        return 1  # Placeholder
    
    def _extract_column_data(self, col_index: int, skip_rows: int = 1) -> list[str]:
        """Extrai dados de uma coluna começando após o header
        
        Args:
            col_index: Índice da coluna (1-based)
            skip_rows: Linhas a pular após header (padrão: 1)
        
        Returns:
            Lista de valores não-vazios
        """
        LOGGER.debug(f"   📋 Extraindo dados da coluna {col_index}")
        
        # TODO: Copiar dados para clipboard usando pyautogui
        # pyautogui.hotkey('ctrl', 'c')
        # return read_from_clipboard()
        
        LOGGER.warning(f"   ⚠️  Função _extract_column_data precisa de implementação")
        return []  # Placeholder
    
    def _extract_column_data_pattern(self, data_type: str) -> list[str]:
        """Extrai dados usando pattern matching
        
        Args:
            data_type: "products" (padrão: nnnn ou nnnn-n etc) ou "quantities" (padrão: n,00)
        
        Returns:
            Lista de valores que matcham o padrão
        """
        LOGGER.debug(f"   🔎 Extraindo {data_type} por pattern matching")
        
        if data_type == "products":
            # Padrão: 4-6 caracteres, números e letras, com formatos como "nnnn", "nnnn-n", "nnnn-ln"
            pattern = r"^\d{4}(?:[-]\d{1,2})?(?:[-]\w{1,2})?$"
        elif data_type == "quantities":
            # Padrão: números com ",00" no final (ex: "10,00", "1000,00")
            pattern = r"^\d+(?:\.\d+)?[,]\d{2}$"
        else:
            LOGGER.error(f"❌ data_type desconhecido: {data_type}")
            return []
        
        # TODO: Implementar extração com pattern matching
        # - Ler célula por célula
        # - Validar contra padrão
        # - Acumular valores válidos
        
        LOGGER.warning(f"   ⚠️  Função _extract_column_data_pattern precisa de implementação")
        return []  # Placeholder
    
    def _has_next_page(self) -> bool:
        """Verifica se há mais páginas (abas) no Excel"""
        LOGGER.debug(f"   ❓ Verificando se há próxima página...")
        
        # TODO: Contar abas/sheets do arquivo atual
        # ou usar Page Down para ver se há mais conteúdo
        
        LOGGER.warning(f"   ⚠️  Função _has_next_page precisa de implementação")
        return False  # Placeholder
    
    def _go_to_next_page(self) -> None:
        """Navega para a próxima página/aba do Excel"""
        LOGGER.debug(f"   ➡️  Avançando para próxima página...")
        
        # TODO: Pressionar Ctrl+Page Down ou clicar na aba seguinte
        # pyautogui.hotkey('ctrl', 'pagedown')
        
        LOGGER.warning(f"   ⚠️  Função _go_to_next_page precisa de implementação")
    
    def switch_to_modelo(self) -> None:
        """Muda para a aba do Excel modelo (esquerda na taskbar)"""
        LOGGER.debug(f"   🔄 Trocando para Excel modelo...")
        
        if not self.coords.excel_taskbar_left:
            LOGGER.error("❌ Coordenada excel_taskbar_left não configurada")
            return
        
        pyautogui.click(self.coords.excel_taskbar_left[0], self.coords.excel_taskbar_left[1])
        time.sleep(1)
    
    def switch_to_pedido(self) -> None:
        """Muda para a aba do Excel pedido (direita na taskbar)"""
        LOGGER.debug(f"   🔄 Trocando para Excel pedido...")
        
        if not self.coords.excel_taskbar_right:
            LOGGER.error("❌ Coordenada excel_taskbar_right não configurada")
            return
        
        pyautogui.click(self.coords.excel_taskbar_right[0], self.coords.excel_taskbar_right[1])
        time.sleep(1)
    
    def paste_to_modelo(self, data_type: str, column: str) -> None:
        """Cola dados no Excel modelo
        
        Args:
            data_type: "products" ou "quantities"
            column: "A" ou "B"
        """
        LOGGER.info(f"   📌 Colando {data_type} na coluna {column}...")
        
        self.switch_to_modelo()
        
        # Etapa 5/9: Verificar se coluna está vazia, se não limpar
        self._clear_column_if_needed(column)
        
        # Encontrar primeira célula vazia
        first_empty_row = self._find_first_empty_row(column)
        LOGGER.info(f"   Primeira linha vazia em {column}: {first_empty_row}")
        
        # Colar dados
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2)
        
        LOGGER.info(f"   ✅ Dados colados em {column}")
    
    def _clear_column_if_needed(self, column: str) -> None:
        """Limpa coluna a partir da linha 2 se houver dados"""
        LOGGER.debug(f"   🧹 Verificando se coluna {column} precisa limpeza...")
        
        # TODO: Selecionar a partir de linha 2 e deletar se houver dados
        # Usar Ctrl+Shift+End para selecionar até o final
        
        LOGGER.warning(f"   ⚠️  Função _clear_column_if_needed precisa de implementação")
    
    def _find_first_empty_row(self, column: str) -> int:
        """Encontra a primeira linha vazia em uma coluna
        
        Returns:
            Número da linha (1-based)
        """
        LOGGER.debug(f"   🔍 Procurando primeira célula vazia em coluna {column}...")
        
        # TODO: Usar Ctrl+Down para navegar até célula vazia
        
        LOGGER.warning(f"   ⚠️  Função _find_first_empty_row precisa de implementação")
        return 2  # Placeholder
    
    def save_modelo(self) -> None:
        """Salva o Excel modelo com sufixo ' M'"""
        LOGGER.info(f"💾 Salvando Excel modelo...")
        
        # Etapa 23: Pressionar F12 para salvar
        pyautogui.press("f12")
        time.sleep(1)
        
        # Etapa 25-26: Nome do arquivo + sufixo " M"
        if self.current_file:
            filename = self.current_file.stem  # Remove .xlsx
            new_name = f"{filename} M"
            
            LOGGER.info(f"   Nome do arquivo: '{new_name}'")
            
            # TODO: Digitar novo nome na caixa de salvamento
            # pyautogui.write(new_name, interval=0.05)
            
            LOGGER.warning(f"   ⚠️  Função save_modelo precisa de implementação (digitar nome e clicar OK)")
        
        time.sleep(2)
    
    def advance_to_next_file(self) -> None:
        """Avança para o próximo arquivo na pasta (Etapa 29)"""
        LOGGER.info(f"   ⬇️  Avançando para próximo pedido...")
        
        if not self.coords.folder_window_coords:
            LOGGER.error("❌ Coordenada folder_window_coords não configurada")
            return
        
        # Clicar na janela da pasta
        pyautogui.click(self.coords.folder_window_coords[0], self.coords.folder_window_coords[1])
        time.sleep(0.5)
        
        # Pressionar seta para baixo
        pyautogui.press("down")
        time.sleep(1)
        
        LOGGER.info(f"   ✅ Próximo arquivo selecionado")


def main():
    """Função de teste/exemplo"""
    import sys
    from .config import default_config_path
    
    # Placeholders para teste
    pedidos_folder = Path("E:/Automações/Automação Mercos/pedidos_excel")
    modelo_path = Path("E:/Automações/Automação Mercos/modelo.xlsx")
    
    coords = ExcelCoordinates(
        excel_taskbar_left=(0, 0),  # TODO: Preencher com coordenadas reais
        excel_taskbar_right=(0, 0),  # TODO: Preencher com coordenadas reais
        folder_window_coords=(0, 0),  # TODO: Preencher com coordenadas reais
    )
    
    automation = ExcelAutomation(pedidos_folder, modelo_path, coords)
    automation.run()


if __name__ == "__main__":
    main()
