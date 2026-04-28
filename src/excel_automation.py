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
        
        # TODO: Implementar lógica de detecção (contar abas, usar Ctrl+Page Down, etc)
        LOGGER.warning(f"   ⚠️  [11] Implementação necessária: detectar próxima página")
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
        
        # PASSOS 24-27: TODO - Digitar nome com sufixo ' M' e salvar
        LOGGER.warning(f"   ⚠️  [24-27] Implementação necessária: digitar nome + sufixo ' M' e clicar OK")
    
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
        
        # TODO: Implementar busca por header
        # - Ler primeira linha
        # - Comparar célula por célula até encontrar
        # - Retornar índice da coluna
        
        LOGGER.warning(f"   ⚠️  Implementação necessária: localizar header '{header_text}'")
        return 1
    
    def _copiar_coluna(self, col_index: int) -> list[str]:
        """Copia dados de uma coluna a partir da segunda linha
        
        Args:
            col_index: Número da coluna (1-based)
        
        Returns:
            Lista de valores
        """
        LOGGER.debug(f"   📋 Copiando coluna {col_index}...")
        
        # TODO: Implementar cópia
        # - Clicar em célula (col, linha 2)
        # - Ctrl+Shift+End para selecionar até o final
        # - Ctrl+C para copiar
        # - Ler do clipboard
        
        LOGGER.warning(f"   ⚠️  Implementação necessária: copiar dados da coluna {col_index}")
        return []
    
    def _copiar_coluna_pattern(self, data_type: str) -> list[str]:
        """Copia dados de uma coluna usando pattern matching
        
        Args:
            data_type: "products" (formato: nnnn ou nnnn-n) ou "quantities" (formato: n,00)
        
        Returns:
            Lista de valores que matcham o padrão
        """
        LOGGER.debug(f"   📋 Copiando coluna {data_type} por pattern...")
        
        patterns = {
            "products": r"^\d{4}(?:[-]\d{1,2})?(?:[-]\w{1,2})?$",
            "quantities": r"^\d+(?:\.\d+)?[,]\d{2}$"
        }
        
        # TODO: Implementar lógica de pattern matching
        # - Iterar linhas
        # - Validar cada célula contra padrão
        # - Acumular valores válidos
        
        LOGGER.warning(f"   ⚠️  Implementação necessária: extrair {data_type} por pattern matching")
        return []
    
    def _limpar_coluna_se_necessario(self, coluna: str) -> None:
        """Limpa coluna a partir da linha 2 se houver dados"""
        LOGGER.debug(f"   🧹 Verificando se coluna {coluna} precisa limpeza...")
        
        # TODO: Implementar limpeza
        # - Selecionar de coluna[2:end]
        # - Deletar se houver dados
        
        LOGGER.warning(f"   ⚠️  Implementação necessária: limpar coluna {coluna} se necessário")
    
    def _encontrar_primeira_linha_vazia(self, coluna: str) -> int:
        """Encontra primeira linha vazia em uma coluna
        
        Returns:
            Número da linha (1-based)
        """
        LOGGER.debug(f"   🔍 Procurando primeira célula vazia em {coluna}...")
        
        # TODO: Implementar busca
        # - Clicar em coluna[2]
        # - Ctrl+Down para pular células vazias
        # - Retornar linha atual
        
        LOGGER.warning(f"   ⚠️  Implementação necessária: encontrar primeira linha vazia em {coluna}")
        return 2
