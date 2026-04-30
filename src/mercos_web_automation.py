"""
Automação da Etapa 3: Criar pedidos no sistema web Mercos
Lê os arquivos M.xlsx + M.json gerados pela Etapa 2 e cria os pedidos no Mercos.

Fluxo por pedido:
  1. Criar novo orçamento
  2. Preencher cliente
  3. Selecionar representada
  4. Importar M.xlsx por planilha
  5. Finalizar adição de produtos
  6. Preencher condição de pagamento e salvar detalhes
  7. Gerar pedido (orçamento → pedido)
  8. Alterar data de emissão para a data original do pedido
  9. Avançar para o próximo
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page, Browser, Playwright

LOGGER = logging.getLogger(__name__)

# Sufixos jurídicos removidos antes da busca no autocomplete do Mercos
_RE_SUFIXOS = re.compile(
    r'\s*[-–]?\s*\b(LTDA\.?|EIRELI\.?|EIRELLI|EPP|S\.?A\.?|CIA\.?|INC\.?|EIRL\.?|ME)\b.*$',
    flags=re.IGNORECASE,
)


def _preparar_busca_cliente(nome: str) -> str:
    """Remove sufixos jurídicos e limita a 4 palavras para busca no autocomplete.

    Exemplos:
      "WIEBBELLING DISTRIBUIDORA DE PECAS AUTOMOTIVAS LTDA - EPP"
        → "WIEBBELLING DISTRIBUIDORA DE PECAS"
      "BRUNO AUGUSTO WEHRLE LUDWIG EIRELLI-ME"
        → "BRUNO AUGUSTO WEHRLE LUDWIG"
    """
    limpo = _RE_SUFIXOS.sub("", nome).strip() or nome
    return " ".join(limpo.split()[:4])


@dataclass
class Etapa3Config:
    mercos_url: str
    email: str
    senha: str
    representada: str
    condicao_pagamento: str
    output_dir: Path
    playwright_headless: bool = False
    playwright_slow_mo: int = 500
    timeout_elemento_ms: int = 10000


@dataclass
class MetadadosPedido:
    cliente: str
    data_pedido: str        # formato DD/MM/AAAA
    arquivo_xlsx: Path      # caminho absoluto do M.xlsx
    nome_arquivo: str = ""  # nome do arquivo para log


class _Sel:
    """Seletores centralizados — alterar aqui se o Mercos mudar a UI."""
    CAMPO_CLIENTE        = 'input[placeholder="Digite o nome ou CNPJ/CPF do cliente e selecione"]'
    DROPDOWN_OPCAO_1     = '[role="option"]:first-child, .select2-result:first-child, .autocomplete-result:first-child'
    BTN_LISTAR_REPRES    = 'text=Listar todas as representadas'
    CAMPO_REPRESENTADA   = 'input[placeholder="Digite o nome da representada e selecione"]'
    BTN_ADICIONAR_PLAN   = 'text=Adicionar por planilha'
    INPUT_FILE_UPLOAD    = 'input[type="file"]'
    SELECT_TABELA_PRECOS = 'select'
    BTN_ADICIONAR_PROD   = 'text=Adicionar os produtos da planilha'
    NOTIF_IMPORTADOS     = 'text=produtos importados'
    BTN_TERMINEI         = 'text=Terminei de adicionar os produtos'
    CAMPO_COND_PGTO      = 'input[placeholder="obrigatório"]'
    BTN_SALVAR_DETALHES  = 'text=Salvar detalhes'
    BTN_GERAR_PEDIDO     = 'text=Gerar pedido'
    BTN_ALTERAR_DETALHES = 'text=Alterar detalhes do pedido'
    CAMPO_DATA_EMISSAO   = 'input[name="data_emissao"]'
    BTN_CRIAR_PEDIDO     = 'text=Criar pedido / orçamento'
    LINK_PEDIDOS_SIDEBAR = 'a:has-text("PEDIDOS")'
    POPUP_FECHAR         = 'button:has-text("×"), button.close, [aria-label="Close"], button:has-text("Fechar")'


class MercosWebAutomation:
    """Automação web do Mercos usando Playwright."""

    def __init__(self, config: Etapa3Config) -> None:
        self.config = config
        self.output_dir = Path(config.output_dir)
        self._page: Optional[Page] = None
        self._browser: Optional[Browser] = None
        self._pw: Optional[Playwright] = None
        self.pedido_count = 0
        self.falhas = 0

    def run(self) -> None:
        LOGGER.info("=" * 70)
        LOGGER.info("🚀 INICIANDO AUTOMAÇÃO ETAPA 3 - CRIAÇÃO DE PEDIDOS NO MERCOS")
        LOGGER.info("=" * 70)

        pedidos = self._carregar_pedidos_pendentes()
        if not pedidos:
            LOGGER.warning("⚠️  Nenhum pedido pendente encontrado (sem pares .xlsx + .json)")
            return

        LOGGER.info(f"📂 {len(pedidos)} pedido(s) encontrado(s)")

        self._pw = sync_playwright().start()
        try:
            self._iniciar_browser()
            self._fazer_login()

            for pedido in pedidos:
                self.pedido_count += 1
                LOGGER.info(f"\n{'='*70}")
                LOGGER.info(f"📋 PEDIDO {self.pedido_count}/{len(pedidos)}: {pedido.nome_arquivo}")
                LOGGER.info(f"   Cliente: {pedido.cliente} | Data: {pedido.data_pedido}")
                LOGGER.info(f"{'='*70}")
                try:
                    self._processar_pedido(pedido)
                except Exception as e:
                    self.falhas += 1
                    LOGGER.error(f"❌ Erro ao processar {pedido.nome_arquivo}: {e}")
                    self._screenshot_debug(f"erro_{pedido.nome_arquivo}")
                    self._ir_para_lista_pedidos()
                    continue
        finally:
            if self._browser:
                self._browser.close()
            self._pw.stop()

        LOGGER.info(f"\n{'='*70}")
        LOGGER.info(f"✅ ETAPA 3 CONCLUÍDA — {self.pedido_count} pedido(s), {self.falhas} falha(s)")
        LOGGER.info(f"{'='*70}\n")

    # -------------------------------------------------------------------------
    # Carregamento de dados
    # -------------------------------------------------------------------------

    def _carregar_pedidos_pendentes(self) -> list[MetadadosPedido]:
        pedidos = []
        for json_path in sorted(self.output_dir.glob("* M.json")):
            xlsx_path = json_path.with_suffix(".xlsx")
            if not xlsx_path.exists():
                LOGGER.warning(f"⚠️  JSON sem xlsx correspondente: {json_path.name}")
                continue
            try:
                dados = json.loads(json_path.read_text(encoding="utf-8"))
                pedidos.append(MetadadosPedido(
                    cliente=dados.get("cliente") or "",
                    data_pedido=dados.get("data_pedido") or "",
                    arquivo_xlsx=xlsx_path.resolve(),
                    nome_arquivo=xlsx_path.name,
                ))
            except Exception as e:
                LOGGER.warning(f"⚠️  Falha ao ler {json_path.name}: {e}")
        return pedidos

    # -------------------------------------------------------------------------
    # Browser e login
    # -------------------------------------------------------------------------

    def _iniciar_browser(self) -> None:
        # Perfil dedicado ao Playwright dentro da pasta do projeto.
        # Evita conflito com o Chrome já aberto (dois processos não podem usar
        # o mesmo user-data-dir ao mesmo tempo).
        # Na primeira execução o usuário faz login; a sessão fica salva aqui.
        profile_dir = Path(__file__).parent.parent / "playwright_profile"
        profile_dir.mkdir(exist_ok=True)

        self._browser = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=self.config.playwright_headless,
            slow_mo=self.config.playwright_slow_mo,
            args=["--start-maximized"],
            no_viewport=True,
        )
        self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
        self._page.set_default_timeout(self.config.timeout_elemento_ms)

    def _fazer_login(self) -> None:
        self._page.goto(self.config.mercos_url, wait_until="domcontentloaded")

        # Se já estiver logado (sessão salva no perfil), pula login
        if "/pedidos" in self._page.url or "/indicadores" in self._page.url:
            LOGGER.info("✅ Sessão já autenticada, pulando login")
            self._ir_para_lista_pedidos()
            return

        # Login automático com credenciais do config
        if self.config.email and self.config.senha:
            LOGGER.info("🔐 Realizando login automático...")
            self._page.locator('input[type="email"], input[name="email"]').first.fill(self.config.email)
            self._page.locator('input[type="password"], input[name="password"]').first.fill(self.config.senha)
            self._page.locator('button:has-text("ENTRAR"), button[type="submit"]').first.click()
            self._page.wait_for_load_state("networkidle", timeout=20000)
            LOGGER.info("✅ Login realizado com sucesso")
            self._ir_para_lista_pedidos()
            return

        # Fallback: aguarda login manual (sem credenciais no config)
        LOGGER.info("🔐 Faça login no Mercos no browser que abriu e pressione Enter aqui para continuar...")
        input("   >>> Pressione Enter após concluir o login: ")
        self._page.wait_for_load_state("domcontentloaded")
        self._ir_para_lista_pedidos()

    # -------------------------------------------------------------------------
    # Fluxo principal por pedido
    # -------------------------------------------------------------------------

    def _processar_pedido(self, pedido: MetadadosPedido) -> None:
        self._navegar_para_novo_pedido()
        self._preencher_cliente(pedido.cliente)
        self._selecionar_representada()
        self._abrir_modal_planilha()
        self._fazer_upload_xlsx(pedido.arquivo_xlsx)
        self._selecionar_tabela_precos()
        self._confirmar_importacao()
        self._aguardar_importacao()
        self._terminar_adicao_produtos()
        self._preencher_detalhes_iniciais()
        self._gerar_pedido()
        if pedido.data_pedido:
            self._alterar_data(pedido.data_pedido)
        LOGGER.info(f"   ✅ Pedido criado com sucesso")

    def _fechar_popups(self) -> None:
        """Fecha qualquer popup/tooltip flutuante antes de interagir com a página."""
        for sel in [_Sel.POPUP_FECHAR, 'button:has-text("×")', '.modal .close']:
            try:
                btn = self._page.locator(sel).first
                if btn.is_visible(timeout=800):
                    btn.click()
            except Exception:
                pass

    def _navegar_para_novo_pedido(self) -> None:
        LOGGER.info("   [1] Navegando para novo pedido...")
        self._ir_para_lista_pedidos()
        self._page.locator(_Sel.BTN_CRIAR_PEDIDO).first.click()
        # Aguarda o campo de cliente aparecer — confirma que a página carregou
        self._page.wait_for_selector(_Sel.CAMPO_CLIENTE, timeout=15000)
        self._fechar_popups()

    def _preencher_cliente(self, nome: str) -> None:
        LOGGER.info(f"   [2] Preenchendo cliente: {nome}...")
        busca = _preparar_busca_cliente(nome)
        if busca != nome:
            LOGGER.info(f"      → buscando por: '{busca}'")
        campo = self._page.locator(_Sel.CAMPO_CLIENTE).first
        campo.click()
        campo.press_sequentially(busca, delay=50)
        self._page.wait_for_timeout(2000)
        campo.press("Enter")

    def _selecionar_representada(self) -> None:
        LOGGER.info(f"   [3] Selecionando representada: {self.config.representada}...")
        campo = self._page.locator(_Sel.CAMPO_REPRESENTADA).first
        campo.click()
        campo.press_sequentially(self.config.representada, delay=50)
        self._page.wait_for_timeout(3000)
        campo.press("Enter")
        # Aguarda a página atualizar após seleção da representada
        self._page.wait_for_timeout(2000)

    def _abrir_modal_planilha(self) -> None:
        LOGGER.info("   [4] Abrindo modal de upload de planilha...")
        self._page.locator(_Sel.BTN_ADICIONAR_PLAN).click()
        self._page.wait_for_selector('text=Adicionar produtos utilizando planilha', timeout=10000)

    def _fazer_upload_xlsx(self, caminho: Path) -> None:
        LOGGER.info(f"   [5] Fazendo upload: {caminho.name}...")
        # set_input_files funciona mesmo com input oculto
        self._page.locator(_Sel.INPUT_FILE_UPLOAD).set_input_files(str(caminho))

    def _selecionar_tabela_precos(self) -> None:
        LOGGER.info("   [6] Selecionando tabela de preços...")
        # React Select expõe um input[role="combobox"] dentro do dropdown visível
        self._page.get_by_role("combobox").first.click()
        self._page.wait_for_timeout(500)
        self._page.keyboard.press("ArrowDown")
        self._page.wait_for_timeout(300)
        self._page.keyboard.press("Enter")

    def _confirmar_importacao(self) -> None:
        LOGGER.info("   [7] Confirmando importação...")
        self._page.locator(_Sel.BTN_ADICIONAR_PROD).click()

    def _aguardar_importacao(self) -> None:
        LOGGER.info("   [8] Aguardando importação dos produtos...")
        self._page.wait_for_selector(_Sel.NOTIF_IMPORTADOS, timeout=30000)
        LOGGER.info("      ✅ Produtos importados!")

    def _terminar_adicao_produtos(self) -> None:
        LOGGER.info("   [9] Finalizando adição de produtos...")
        self._page.locator(_Sel.BTN_TERMINEI).click()
        # Aguarda modal de detalhes abrir
        self._page.wait_for_selector('text=Detalhes do pedido', timeout=8000)

    def _preencher_detalhes_iniciais(self) -> None:
        LOGGER.info(f"   [10] Preenchendo condição de pagamento: {self.config.condicao_pagamento}...")
        campo = self._page.locator(_Sel.CAMPO_COND_PGTO).first
        campo.click()
        campo.press_sequentially(self.config.condicao_pagamento, delay=50)
        self._page.wait_for_timeout(1500)
        # Enter fecha o modal automaticamente — não precisa clicar em "Salvar detalhes"
        campo.press("Enter")
        self._page.wait_for_timeout(1000)

    def _gerar_pedido(self) -> None:
        LOGGER.info("   [11] Gerando pedido...")
        btn = self._page.locator(_Sel.BTN_GERAR_PEDIDO).first
        btn.scroll_into_view_if_needed()
        btn.click()
        self._page.wait_for_load_state("domcontentloaded")

    def _alterar_data(self, data: str) -> None:
        LOGGER.info(f"   [12] Alterando data para: {data}...")
        btn_alterar = self._page.locator(_Sel.BTN_ALTERAR_DETALHES).first
        btn_alterar.scroll_into_view_if_needed()
        btn_alterar.click()
        self._page.wait_for_timeout(1000)
        campo_data = self._page.locator(_Sel.CAMPO_DATA_EMISSAO).first
        campo_data.fill("")
        campo_data.type(data)
        # Enter salva o modal — mesmo comportamento do campo de pagamento
        campo_data.press("Enter")
        self._page.wait_for_timeout(1000)

    def _ir_para_lista_pedidos(self) -> None:
        # Fecha qualquer modal aberto que bloqueie cliques na sidebar
        try:
            self._page.keyboard.press("Escape")
            self._page.wait_for_timeout(300)
        except Exception:
            pass
        # force=True ignora modal ou overlay que esteja bloqueando o clique
        self._page.locator(_Sel.LINK_PEDIDOS_SIDEBAR).first.click(force=True)
        self._page.wait_for_load_state("domcontentloaded")

    # -------------------------------------------------------------------------
    # Utilitários
    # -------------------------------------------------------------------------

    def _screenshot_debug(self, nome: str) -> None:
        try:
            out = Path("out")
            out.mkdir(exist_ok=True)
            caminho = out / f"etapa3_debug_{nome[:40]}.png"
            self._page.screenshot(path=str(caminho))
            LOGGER.info(f"      📸 Screenshot salvo: {caminho}")
        except Exception:
            pass
