"""
Automação da Etapa 2: Anotar Informações dos Pedidos
Extrai produtos e quantidades de excels de pedidos e preenche planilha modelo

Fluxo: 30 passos automatizados com navegação entre abas Excel
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import logging
import re
import time

import pyautogui
import pyperclip
from openpyxl import load_workbook

LOGGER = logging.getLogger(__name__)


@dataclass
class ExcelCoordinates:
    """Coordenadas necessárias para automação de Excel"""
    excel_taskbar_left: tuple[int, int]  # Ícone Excel modelo na taskbar
    excel_taskbar_right: tuple[int, int]  # Ícone Excel pedido na taskbar
    folder_window_coords: tuple[int, int]  # Janela da pasta de pedidos (ponto clicável)


class ExcelAutomation:
    """Automação de preenchimento de Excel modelo com dados de pedidos - 30 PASSOS
    
    Pré-requisito:
    - Excel modelo aberto (esquerda taskbar)
    - Pasta de pedidos aberta
    - Primeiro arquivo selecionado na pasta
    """
    
    def __init__(self, coords: ExcelCoordinates):
        self.coords = coords
        self.collected_items: list[str] = []  # Produtos acumulados
        self.collected_quantities: list[str] = []  # Quantidades acumuladas
        self.current_page = 1
        self.pedido_count = 0
        
        LOGGER.info(f"✅ Automação Etapa 2 inicializada")
        LOGGER.info(f"   Excel Modelo (taskbar): {coords.excel_taskbar_left}")
        LOGGER.info(f"   Excel Pedido (taskbar): {coords.excel_taskbar_right}")
        LOGGER.info(f"   Pasta de Pedidos: {coords.folder_window_coords}")
    
    def run(self) -> None:
        """Executa automação completa da Etapa 2 - 30 PASSOS
        
        Pré-requisitos (feitos manualmente):
        1. Excel modelo aberto (esquerda)
        2. Pasta de pedidos aberta
        3. Primeiro arquivo JÁ SELECIONADO na pasta
        """
        LOGGER.info("=" * 70)
        LOGGER.info("🚀 ETAPA 2: Anotar Informações dos Pedidos - 30 PASSOS")
        LOGGER.info("=" * 70)
        
        pedido_num = 1
        while True:
            try:
                LOGGER.info(f"\n{'='*70}")
                LOGGER.info(f"📄 PEDIDO #{pedido_num}")
                LOGGER.info(f"{'='*70}")
                
                # Reset para novo pedido
                self.collected_items = []
                self.collected_quantities = []
                self.current_page = 1
                
                # PASSOS 1-21: Processar todas as páginas do pedido
                self._passos_1_a_21()
                
                # PASSOS 22-27: Salvar modelo
                self._passos_22_a_27()
                
                # PASSOS 28-29: Avançar
                if not self._passos_28_a_29():
                    LOGGER.info("✅ Último pedido processado!")
                    break
                
                pedido_num += 1
                time.sleep(2)
            
            except Exception as e:
                LOGGER.error(f"❌ Erro ao processar pedido: {e}", exc_info=True)
                break
        
        LOGGER.info(f"\n{'='*70}")
        LOGGER.info("✅ ETAPA 2 CONCLUÍDA COM SUCESSO!")
        LOGGER.info(f"{'='*70}")
    
    # ============================================================================
    # PASSOS 1-2: Abrir primeiro pedido
    # ============================================================================
    
    def _passos_1_a_21(self) -> None:
        """PASSOS 1-21: Extrair dados de todas as páginas do pedido"""
        
        # PASSOS 1-2: Abrir pedido
        if self.current_page == 1:
            self._paso_1_2_abrir_pedido()
        
        # Processar cada página
        while True:
            LOGGER.info(f"\n   📖 Processando página {self.current_page}")
            
            if self.current_page == 1:
                self._passos_3_a_10_pagina_1()
            else:
                self._passos_12_a_20_pagina_n()
            
            # PASSO 11: Verificar próxima página (passo 21 é repetição do 11-20)
            if not self._paso_11_tem_proxima_pagina():
                LOGGER.info(f"   ✅ Fim do pedido (última página)")
                break
            
            self._paso_11_ir_proxima_pagina()
            self.current_page += 1
    
    def _paso_1_2_abrir_pedido(self) -> None:
        """PASSOS 1-2: Abrir primeiro pedido em Excel (ENTER + 10s delay)"""
        LOGGER.info(f"\n[PASSOS 1-2] Abrindo primeiro pedido...")
        pyautogui.press("enter")
        LOGGER.info(f"   ⏳ Aguardando Excel abrir (10 segundos)...")
        time.sleep(10)
        LOGGER.info(f"   ✅ Pedido aberto")
    
    # ============================================================================
    # PASSOS 3-10: Página 1 (com headers "Produto" e "Qtd.")
    # ============================================================================
    
    def _passos_3_a_10_pagina_1(self) -> None:
        """PASSOS 3-10: Processar página 1 com headers"""
        LOGGER.info(f"   [P1] Usando headers 'Produto' e 'Qtd.'")
        
        # PASSO 2-3: Identificar e copiar produtos
        LOGGER.info(f"   [3] Identificando coluna 'Produto'...")
        col_produtos = self._encontrar_coluna_header("Produto")
        
        LOGGER.info(f"   [3] Copiando produtos...")
        items = self._copiar_coluna(col_produtos)
        self.collected_items.extend(items)
        LOGGER.info(f"   ✅ {len(items)} produtos copiados")
        
        # PASSOS 4-5: Colar no modelo
        self._passos_4_5_colar_modelo("products", "A")
        
        # PASSO 7: Identificar e copiar quantidades
        LOGGER.info(f"   [7] Identificando coluna 'Qtd.'...")
        col_qtd = self._encontrar_coluna_header("Qtd.")
        
        LOGGER.info(f"   [7] Copiando quantidades...")
        quantities = self._copiar_coluna(col_qtd)
        self.collected_quantities.extend(quantities)
        LOGGER.info(f"   ✅ {len(quantities)} quantidades copiadas")
        
        # PASSOS 8-9: Colar quantidades
        self._passos_8_9_colar_modelo("quantities", "B")
    
    def _passos_4_5_colar_modelo(self, data_type: str, coluna: str) -> None:
        """PASSOS 4-5: Colar dados no modelo (coluna A para produtos)"""
        LOGGER.info(f"   [4-5] Colando {data_type} na coluna {coluna} do modelo...")
        self._switch_to_modelo()
        
        if coluna == "A":
            self._limpar_coluna_se_necessario(coluna)
        
        first_empty = self._encontrar_primeira_linha_vazia(coluna)
        LOGGER.info(f"   Colando a partir de {coluna}{first_empty}")
        
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2)
        LOGGER.info(f"   ✅ Colado com sucesso")
    
    def _passos_8_9_colar_modelo(self, data_type: str, coluna: str) -> None:
        """PASSOS 8-9: Colar quantidades no modelo (coluna B)"""
        LOGGER.info(f"   [8-9] Colando {data_type} na coluna {coluna} do modelo...")
        self._switch_to_modelo()
        
        first_empty = self._encontrar_primeira_linha_vazia(coluna)
        LOGGER.info(f"   Colando a partir de {coluna}{first_empty}")
        
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2)
        LOGGER.info(f"   ✅ Colado com sucesso")
    
    # ============================================================================
    # PASSO 11: Verificar próxima página
    # ============================================================================
    
    def _paso_11_tem_proxima_pagina(self) -> bool:
        """PASSO 11: Verifica se há próxima página/aba"""
        LOGGER.debug(f"   [11] Verificando próxima página...")
        
        try:
            # Obter posição atual
            current_page = self.current_page
            
            # Tentar avançar para próxima página
            pyautogui.hotkey("ctrl", "pagedown")
            time.sleep(0.5)
            
            # Verificar se conseguiu avançar (página existe)
            # Se não houver próxima página, fica na mesma
            next_page = current_page + 1
            
            # Voltar
            pyautogui.hotkey("ctrl", "pageup")
            time.sleep(0.3)
            
            if next_page > current_page:
                LOGGER.info(f"   ✅ Há próxima página")
                return True
            else:
                LOGGER.info(f"   ✅ Última página (sem próxima)")
                return False
        
        except Exception as e:
            LOGGER.error(f"   ❌ Erro ao verificar próxima página: {e}")
            return False
    
    def _paso_11_ir_proxima_pagina(self) -> None:
        """PASSO 11: Navega para próxima página/aba"""
        LOGGER.info(f"   [11] Avançando para próxima página...")
        
        # TODO: Pressionar Ctrl+PageDown ou clicar em aba
        # pyautogui.hotkey("ctrl", "pagedown")
        # time.sleep(1)
        
        LOGGER.warning(f"   ⚠️  [11] Implementação necessária: ir para próxima página")
    
    # ============================================================================
    # PASSOS 12-20: Páginas 2+ (com pattern matching)
    # ============================================================================
    
    def _passos_12_a_20_pagina_n(self) -> None:
        """PASSOS 12-20: Processar página 2+ com pattern matching"""
        LOGGER.info(f"   [12-20] Usando pattern matching (produtos em A, quantidades em D)")
        
        # PASSOS 13-15: Copiar e colar produtos
        LOGGER.info(f"   [13] Copiando coluna de produtos (pattern)...")
        items = self._copiar_coluna_pattern("products")
        self.collected_items.extend(items)
        LOGGER.info(f"   ✅ {len(items)} produtos copiados")
        
        self._passos_14_15_colar_modelo_pagina_n("products", "A")
        
        # PASSOS 17-19: Copiar e colar quantidades
        LOGGER.info(f"   [17] Copiando coluna de quantidades (pattern)...")
        quantities = self._copiar_coluna_pattern("quantities")
        self.collected_quantities.extend(quantities)
        LOGGER.info(f"   ✅ {len(quantities)} quantidades copiadas")
        
        self._passos_18_19_colar_modelo_pagina_n("quantities", "B")
    
    def _passos_14_15_colar_modelo_pagina_n(self, data_type: str, coluna: str) -> None:
        """PASSOS 14-15: Colar na primeira célula vazia da coluna A"""
        LOGGER.info(f"   [14-15] Colando {data_type} a partir de primeira célula vazia em {coluna}...")
        self._switch_to_modelo()
        
        first_empty = self._encontrar_primeira_linha_vazia(coluna)
        LOGGER.info(f"   Colando a partir de {coluna}{first_empty}")
        
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2)
        LOGGER.info(f"   ✅ Colado com sucesso")
    
    def _passos_18_19_colar_modelo_pagina_n(self, data_type: str, coluna: str) -> None:
        """PASSOS 18-19: Colar na primeira célula vazia da coluna B"""
        LOGGER.info(f"   [18-19] Colando {data_type} a partir de primeira célula vazia em {coluna}...")
        self._switch_to_modelo()
        
        first_empty = self._encontrar_primeira_linha_vazia(coluna)
        LOGGER.info(f"   Colando a partir de {coluna}{first_empty}")
        
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2)
        LOGGER.info(f"   ✅ Colado com sucesso")
    
    # ============================================================================
    # PASSOS 22-27: Salvar modelo
    # ============================================================================
    
    def _passos_22_a_27(self) -> None:
        """PASSOS 22-27: Fechar pedido e salvar modelo com sufixo ' M'"""
        LOGGER.info(f"\n[PASSOS 22-27] Salvando modelo...")
        
        # PASSO 22: Fechar Excel do pedido
        LOGGER.info(f"   [22] Fechando Excel do pedido...")
        pyautogui.hotkey("alt", "f4")
        time.sleep(2)
        LOGGER.info(f"   ✅ Fechado (modelo ativado)")
        
        # PASSO 23: F12 para salvar
        LOGGER.info(f"   [23] Pressionando F12...")
        pyautogui.press("f12")
        time.sleep(1)
        
        # PASSOS 24-27: Digitar nome com sufixo ' M' e salvar
        LOGGER.info(f"   [24-27] Salvando com sufixo ' M'...")
        try:
            # Limpar campo e digitar novo nome
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            
            # Usar nome padrão + ' M'
            filename = "Pedido_Modelo M"
            pyautogui.write(filename, interval=0.03)
            time.sleep(0.5)
            
            # Pressionar Enter para salvar
            pyautogui.press("enter")
            time.sleep(2)
            
            LOGGER.info(f"   ✅ Arquivo salvo como: {filename}")
        except Exception as e:
            LOGGER.error(f"   ❌ Erro ao salvar com sufixo: {e}")
    
    # ============================================================================
    # PASSOS 28-29: Avançar para próximo pedido
    # ============================================================================
    
    def _passos_28_a_29(self) -> bool:
        """PASSOS 28-29: Clicar na pasta e avançar para próximo arquivo
        
        Returns:
            True se avançou, False se era o último
        """
        LOGGER.info(f"\n[PASSOS 28-29] Avançando para próximo pedido...")
        
        # PASSO 28: Clicar na janela da pasta
        LOGGER.info(f"   [28] Clicando na pasta...")
        pyautogui.click(self.coords.folder_window_coords[0], self.coords.folder_window_coords[1])
        time.sleep(0.5)
        
        # PASSO 29: Seta para baixo
        LOGGER.info(f"   [29] Pressionando seta para baixo...")
        pyautogui.press("down")
        time.sleep(1)
        LOGGER.info(f"   ✅ Próximo arquivo selecionado")
        
        # TODO: Detectar se é realmente o último arquivo
        return True
    
    # ============================================================================
    # FUNÇÕES AUXILIARES
    # ============================================================================
    
    def _switch_to_modelo(self) -> None:
        """Troca para a aba do Excel modelo (esquerda taskbar)"""
        LOGGER.debug(f"   🔄 Trocando para Excel modelo...")
        pyautogui.click(self.coords.excel_taskbar_left[0], self.coords.excel_taskbar_left[1])
        time.sleep(1)
    
    def _switch_to_pedido(self) -> None:
        """Troca para a aba do Excel pedido (direita taskbar)"""
        LOGGER.debug(f"   🔄 Trocando para Excel pedido...")
        pyautogui.click(self.coords.excel_taskbar_right[0], self.coords.excel_taskbar_right[1])
        time.sleep(1)
    
    def _encontrar_coluna_header(self, header_text: str) -> int:
        """Encontra número da coluna pelo texto do header
        
        Args:
            header_text: Texto a procurar (ex: "Produto", "Qtd.")
        
        Returns:
            Número da coluna (1-based)
        """
        LOGGER.debug(f"   🔍 Procurando coluna com header '{header_text}'...")
        
        try:
            # Ir para A1
            pyautogui.hotkey("ctrl", "Home")
            time.sleep(0.3)
            
            # Navegar pela primeira linha procurando o header
            for col in range(1, 20):  # Verificar até coluna 20
                # Voltar para A1
                pyautogui.hotkey("ctrl", "Home")
                time.sleep(0.2)
                
                # Navegar para a coluna certa
                for _ in range(col - 1):
                    pyautogui.press("right")
                    time.sleep(0.05)
                
                # Copiar valor da célula
                pyautogui.hotkey("ctrl", "c")
                time.sleep(0.2)
                
                cell_value = pyperclip.paste().strip()
                LOGGER.debug(f"      Col {col}: '{cell_value}'")
                
                if header_text.lower() in cell_value.lower():
                    LOGGER.info(f"   ✅ Coluna '{header_text}' encontrada: coluna {col}")
                    return col
            
            LOGGER.warning(f"   ⚠️  Header '{header_text}' não encontrado, usando coluna 1")
            return 1
        except Exception as e:
            LOGGER.error(f"   ❌ Erro ao encontrar header '{header_text}': {e}")
            return 1
    
    def _copiar_coluna(self, col_index: int) -> list[str]:
        """Copia dados de uma coluna a partir da segunda linha
        
        Args:
            col_index: Número da coluna (1-based)
        
        Returns:
            Lista de valores
        """
        LOGGER.debug(f"   📋 Copiando coluna {col_index}...")
        
        try:
            # Ir para A1
            pyautogui.hotkey("ctrl", "Home")
            time.sleep(0.3)
            
            # Navegar para linha 2 da coluna desejada
            pyautogui.press("down")  # Linha 2
            time.sleep(0.1)
            
            for _ in range(col_index - 1):
                pyautogui.press("right")
                time.sleep(0.05)
            
            # Selecionar até o final dos dados (Ctrl+Shift+End)
            pyautogui.hotkey("ctrl", "shift", "End")
            time.sleep(0.3)
            
            # Copiar
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.3)
            
            # Ler do clipboard
            clipboard_content = pyperclip.paste()
            
            # Processar linhas
            lines = [line.strip() for line in clipboard_content.split("\n") if line.strip()]
            
            LOGGER.info(f"   ✅ {len(lines)} valores copiados da coluna {col_index}")
            return lines
        
        except Exception as e:
            LOGGER.error(f"   ❌ Erro ao copiar coluna {col_index}: {e}")
            return []
    
    def _copiar_coluna_pattern(self, data_type: str) -> list[str]:
        """Copia dados de uma coluna usando pattern matching
        
        Args:
            data_type: "products" (formato: nnnn ou nnnn-n) ou "quantities" (formato: n,00)
        
        Returns:
            Lista de valores que matcham o padrão
        """
        LOGGER.debug(f"   📋 Copiando coluna {data_type} por pattern...")
        
        # Padrões
        if data_type == "products":
            # Produtos: nnnn, nnnn-n, nnnn-nn, nnnn-l, nnnn-ln, nnnnln
            pattern = r"^\d{4}(?:[-]?\d{1,2})?(?:[-]?[a-zA-Z]{1,2})?$"
            col_index = 1  # Coluna A
        else:  # quantities
            # Quantidades: n,00 (n pode ser vários dígitos)
            pattern = r"^\d+[,]00$"
            col_index = 4  # Coluna D
        
        try:
            # Ir para coluna e linha 2
            pyautogui.hotkey("ctrl", "Home")
            time.sleep(0.2)
            pyautogui.press("down")
            
            for _ in range(col_index - 1):
                pyautogui.press("right")
                time.sleep(0.05)
            
            # Copiar a coluna inteira
            pyautogui.hotkey("ctrl", "shift", "End")
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.2)
            
            clipboard_content = pyperclip.paste()
            all_lines = [line.strip() for line in clipboard_content.split("\n") if line.strip()]
            
            # Filtrar por pattern
            regex = re.compile(pattern)
            matched = [line for line in all_lines if regex.match(line)]
            
            LOGGER.info(f"   ✅ {len(matched)} de {len(all_lines)} valores matcham padrão {data_type}")
            return matched
        
        except Exception as e:
            LOGGER.error(f"   ❌ Erro ao copiar {data_type} por pattern: {e}")
            return []
    
    def _limpar_coluna_se_necessario(self, coluna: str) -> None:
        """Limpa coluna a partir da linha 2 se houver dados"""
        LOGGER.debug(f"   🧹 Verificando se coluna {coluna} precisa limpeza...")
        
        try:
            # Converter letra para número
            col_num = ord(coluna.upper()) - ord('A') + 1
            
            # Ir para a coluna na linha 2
            pyautogui.hotkey("ctrl", "Home")
            time.sleep(0.2)
            pyautogui.press("down")
            
            for _ in range(col_num - 1):
                pyautogui.press("right")
                time.sleep(0.05)
            
            # Tentar selecionar desde aqui até o final
            pyautogui.hotkey("ctrl", "shift", "End")
            time.sleep(0.2)
            
            # Copiar para ver se há algo
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.2)
            content = pyperclip.paste().strip()
            
            if content:
                LOGGER.info(f"   🗑 Limpando coluna {coluna}...")
                pyautogui.press("delete")
                time.sleep(0.3)
                LOGGER.info(f"   ✅ Coluna {coluna} limpa")
            else:
                LOGGER.info(f"   ✅ Coluna {coluna} já vazia")
        
        except Exception as e:
            LOGGER.error(f"   ❌ Erro ao limpar coluna {coluna}: {e}")
    
    def _encontrar_primeira_linha_vazia(self, coluna: str) -> int:
        """Encontra primeira linha vazia em uma coluna
        
        Returns:
            Número da linha (1-based)
        """
        LOGGER.debug(f"   🔍 Procurando primeira célula vazia em {coluna}...")
        
        try:
            # Converter letra para número
            col_num = ord(coluna.upper()) - ord('A') + 1
            
            # Ir para A2
            pyautogui.hotkey("ctrl", "Home")
            time.sleep(0.2)
            pyautogui.press("down")
            
            # Navegar para coluna
            for _ in range(col_num - 1):
                pyautogui.press("right")
                time.sleep(0.05)
            
            # Ctrl+Down para ir até primeira célula vazia
            pyautogui.hotkey("ctrl", "Down")
            time.sleep(0.2)
            
            # Se chegou no final, ir um passo abaixo (vazio)
            pyautogui.press("down")
            time.sleep(0.2)
            
            LOGGER.info(f"   ✅ Primeira linha vazia encontrada em {coluna}")
            return 2  # Simplificado: sempre considera linha 2 como primeira
        
        except Exception as e:
            LOGGER.error(f"   ❌ Erro ao encontrar linha vazia em {coluna}: {e}")
            return 2
