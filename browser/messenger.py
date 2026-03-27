"""
browser/messenger.py
====================
Automação do Facebook Marketplace Inbox via Playwright.

Estratégia de seletores
------------------------
O Facebook usa class names ofuscados que mudam a cada deploy.
Por isso priorizamos seletores baseados em:
  1. ARIA roles/labels   → mais estáveis entre deploys
  2. Atributos href      → baseados em URLs, mudam só com mudança de rota
  3. Atributos dir/tabindex → convenções do React/WAI-ARIA
  4. Posição na página   → fallback via JavaScript

URL alvo: https://www.facebook.com/marketplace/inbox/
"""

from __future__ import annotations

import re
from typing import Optional

from config.settings import MARKETPLACE_INBOX_URL, CLICK_WAIT, PAGE_LOAD_WAIT, TYPE_DELAY
from utils.logger import log

# ── Seletores de conversas (ordem de prioridade) ──────────────────────────

# Links de conversas dentro do inbox do Marketplace
_CONV_LINK_SELECTORS = [
    'a[href*="/marketplace/inbox/"]',   # Link direto para conversa no marketplace inbox
    'a[href*="/messages/t/"]',           # Thread do Messenger associado ao marketplace
]

# Container da lista de conversas
_LIST_CONTAINER_SELECTORS = [
    '[aria-label*="Conversas"]',
    '[aria-label*="Chats"]',
    '[aria-label*="Messages"]',
    '[role="navigation"]',
    '[role="complementary"]',
]

# ── Seletores de mensagens ─────────────────────────────────────────────────

# Container principal de mensagens
_MSG_AREA_SELECTORS = [
    '[role="main"]',
]

# Campo de texto para envio
_TEXTBOX_SELECTORS = [
    '[contenteditable="true"][role="textbox"]',
    '[contenteditable="true"][aria-label]',
    '[contenteditable="true"]',
]


# ══════════════════════════════════════════════════════════════════════════
# Funções públicas
# ══════════════════════════════════════════════════════════════════════════

def navigate_to_inbox(page) -> bool:
    """
    Navega para o inbox do Marketplace.
    Retorna True se a navegação foi bem-sucedida.
    """
    try:
        log.info(f"📍 Navegando para: {MARKETPLACE_INBOX_URL}")
        page.goto(MARKETPLACE_INBOX_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(PAGE_LOAD_WAIT)

        # Verifica se chegou na página certa
        if "marketplace/inbox" not in page.url and "facebook.com" not in page.url:
            log.warning(f"⚠️  URL inesperada após navegação: {page.url}")
            return False

        log.info(f"✅ Inbox carregado. URL: {page.url}")
        return True

    except Exception as e:
        log.error(f"❌ Falha ao navegar para inbox: {e}")
        return False


def get_unread_conversations(page) -> list[dict]:
    """
    Retorna lista de conversas com mensagens não lidas.

    Cada item é:  {"name": str, "element": ElementHandle, "href": str}
    """
    log.info("🔍 Buscando conversas não lidas...")
    conversations: list[dict] = []

    try:
        page.wait_for_timeout(3000)

        # 1. Tenta encontrar links de conversas diretamente
        conv_elements = _find_conversation_elements(page)
        log.info(f"📋 Total de conversas encontradas: {len(conv_elements)}")

        for el in conv_elements:
            try:
                info = _extract_conversation_info(page, el)
                if info is None:
                    continue

                if _is_unread(page, el):
                    conversations.append(info)
                    log.info(f"📨 Não lida: {info['name']}")

            except Exception as e:
                log.debug(f"Elemento ignorado: {e}")
                continue

    except Exception as e:
        log.error(f"❌ Erro ao buscar conversas: {e}")

    if not conversations:
        log.info("✅ Nenhuma mensagem nova no Marketplace.")

    return conversations


def get_last_buyer_message(page) -> Optional[str]:
    """
    Retorna o ÚLTIMO texto enviado pelo comprador (não pelo vendedor/bot).

    Estratégia:
    - Busca todas as linhas de mensagem visíveis
    - Filtra as mensagens que NÃO são nossas (lado esquerdo do chat = comprador)
    - Retorna o texto da última mensagem do comprador
    """
    try:
        page.wait_for_timeout(2500)

        # Aguarda o container de mensagens carregar
        msg_area = _wait_for_message_area(page)
        if not msg_area:
            log.warning("⚠️  Área de mensagens não encontrada.")
            return None

        # Busca mensagens do comprador via JavaScript (mais confiável que seletores)
        buyer_messages: list[str] = page.evaluate("""
            () => {
                // Pega todos os elementos com role="row" (linhas de mensagem)
                const rows = Array.from(document.querySelectorAll('[role="row"]'));
                const messages = [];

                for (const row of rows) {
                    // Cada row contém o texto da mensagem
                    const textEl = row.querySelector('[dir="auto"]');
                    if (!textEl) continue;

                    const text = textEl.innerText.trim();
                    if (!text || text.length < 1) continue;

                    // Detecta se é mensagem ENVIADA por nós:
                    // Mensagens enviadas ficam alinhadas à DIREITA do container
                    const rowRect  = row.getBoundingClientRect();
                    const parentEl = row.closest('[role="grid"], [role="log"], [role="main"]');
                    if (!parentEl) continue;

                    const parentRect = parentEl.getBoundingClientRect();
                    const centerX = rowRect.left + rowRect.width / 2;
                    const parentCenterX = parentRect.left + parentRect.width / 2;

                    // Se o centro do bloco está à DIREITA do centro do container → é nossa msg
                    const isOutgoing = centerX > parentCenterX + 20;

                    if (!isOutgoing) {
                        messages.push(text);
                    }
                }

                return messages;
            }
        """)

        if buyer_messages:
            last = buyer_messages[-1].strip()
            log.debug(f"Última mensagem do comprador: {last[:80]}")
            return last

        # Fallback: tenta via seletor ARIA "incoming"
        return _fallback_get_message(page)

    except Exception as e:
        log.error(f"❌ Erro ao ler mensagem: {e}")
        return None


def get_thread_id(page) -> str:
    """
    Extrai o ID único da conversa a partir da URL atual.
    Suporta padrões:
      - /marketplace/inbox/XXXXXXXXX/
      - /messages/t/XXXXXXXXX/
    """
    try:
        url = page.url.rstrip("/")
        # Tenta pegar o último segmento numérico da URL
        match = re.search(r"/(\d{5,})", url)
        if match:
            return match.group(1)
        # Fallback: último segmento da URL
        parts = url.split("/")
        return parts[-1] if parts[-1] else parts[-2]
    except Exception:
        return "unknown"


def send_message(page, text: str) -> bool:
    """
    Digita e envia uma mensagem na conversa aberta.
    Retorna True se enviou com sucesso.
    """
    try:
        box = _find_textbox(page)
        if not box:
            log.error("❌ Campo de texto não encontrado para envio.")
            return False

        box.click()
        page.wait_for_timeout(400)
        box.type(text, delay=TYPE_DELAY)
        page.wait_for_timeout(600)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)

        log.info(f"✅ Mensagem enviada: {text[:60]}{'...' if len(text) > 60 else ''}")
        return True

    except Exception as e:
        log.error(f"❌ Erro ao enviar mensagem: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════
# Funções internas
# ══════════════════════════════════════════════════════════════════════════

def _find_conversation_elements(page) -> list:
    """Tenta diferentes seletores para encontrar as conversas."""

    # Estratégia 1: links diretos de conversa
    for selector in _CONV_LINK_SELECTORS:
        elements = page.query_selector_all(selector)
        if elements:
            log.debug(f"Conversas via seletor '{selector}': {len(elements)}")
            return elements

    # Estratégia 2: busca via JavaScript pelo padrão de URL nas conversas
    log.debug("Tentando busca de conversas via JavaScript...")
    elements = page.evaluate_handle("""
        () => {
            // Pega todos os links que contenham padrões de conversa
            const patterns = ['/marketplace/inbox/', '/messages/t/'];
            const links = Array.from(document.querySelectorAll('a[href]'));
            return links.filter(a => patterns.some(p => a.href.includes(p)));
        }
    """)

    # Converte JSHandle para lista de ElementHandle
    try:
        count = page.evaluate("(arr) => arr.length", elements)
        result = []
        for i in range(count):
            el = page.evaluate_handle(f"(arr) => arr[{i}]", elements)
            result.append(el.as_element())
        if result:
            log.debug(f"Conversas via JS: {len(result)}")
            return result
    except Exception as e:
        log.debug(f"JS handle falhou: {e}")

    # Estratégia 3: fallback por role=listitem na área principal
    log.debug("Fallback: role=listitem na área principal")
    main = page.query_selector('[role="main"]')
    if main:
        items = main.query_selector_all('[role="listitem"]')
        if items:
            return list(items)

    log.warning("⚠️  Nenhum seletor de conversas funcionou. Verifique a URL e o login.")
    return []


def _extract_conversation_info(page, el) -> Optional[dict]:
    """Extrai nome e href de um elemento de conversa."""
    try:
        # Nome do remetente
        name_el = (
            el.query_selector('[aria-label]') or
            el.query_selector('span[dir="auto"]') or
            el.query_selector('span')
        )
        name = name_el.inner_text().strip() if name_el else el.inner_text()[:40].strip()

        if not name or len(name) < 2:
            return None

        # URL da conversa
        href = el.get_attribute("href") or ""

        return {"name": name, "element": el, "href": href}

    except Exception:
        return None


def _is_unread(page, el) -> bool:
    """
    Detecta se uma conversa possui mensagens não lidas.

    Usa múltiplas estratégias em ordem de confiabilidade:
    1. aria-label indicando "não lido" / "unread"
    2. Ponto azul (badge de notificação)
    3. Texto em negrito (font-weight >= 700)
    """
    try:
        return page.evaluate("""
            (el) => {
                // 1. ARIA label com "não lido" / "unread"
                const allLabels = el.querySelectorAll('[aria-label]');
                for (const labeled of allLabels) {
                    const label = labeled.getAttribute('aria-label') || '';
                    if (/n[ãa]o.?l(i|e)do|unread/i.test(label)) return true;
                }

                // 2. Badge de notificação (círculo colorido)
                // Facebook usa SVG circles ou spans com background azul
                const svgCircles = el.querySelectorAll('circle[fill]');
                for (const c of svgCircles) {
                    const fill = c.getAttribute('fill') || '';
                    // Azul do Facebook: #0084ff, #1877f2, ou similares
                    if (/^#?0{0,2}[89a-f]{1}[0-9a-f]/i.test(fill)) return true;
                }

                const badges = el.querySelectorAll('span[class]');
                for (const b of badges) {
                    const bg = window.getComputedStyle(b).backgroundColor;
                    // rgb(0, 132, 255) ou rgb(24, 119, 242) = azul do Facebook
                    if (bg.includes('0, 132') || bg.includes('0, 149') ||
                        bg.includes('24, 119') || bg.includes('0, 100')) return true;
                }

                // 3. Nome em negrito = conversa não lida
                const nameSpans = el.querySelectorAll('span[dir="auto"], span[class]');
                for (const span of nameSpans) {
                    const fw = window.getComputedStyle(span).fontWeight;
                    const numFw = parseInt(fw, 10);
                    if (numFw >= 700) return true;
                }

                return false;
            }
        """, el)

    except Exception as e:
        log.debug(f"Erro ao verificar 'não lido': {e}")
        return False


def _wait_for_message_area(page):
    """Aguarda e retorna o container de mensagens."""
    for selector in _MSG_AREA_SELECTORS:
        try:
            page.wait_for_selector(selector, timeout=8000)
            el = page.query_selector(selector)
            if el:
                return el
        except Exception:
            continue
    return None


def _fallback_get_message(page) -> Optional[str]:
    """
    Fallback para leitura de mensagens quando o método principal falha.
    Pega o último elemento [dir="auto"] que pareça uma mensagem real
    (filtra textos muito curtos, timestamps, nomes).
    """
    try:
        elements = page.query_selector_all('[dir="auto"]')
        candidates = []
        for el in elements:
            text = el.inner_text().strip()
            # Filtra textos triviais: timestamps, nomes curtos, labels
            if len(text) >= 3 and not re.match(r'^[\d:hm\s,]+$', text):
                candidates.append(text)

        if candidates:
            log.debug(f"[Fallback] Mensagem encontrada: {candidates[-1][:80]}")
            return candidates[-1]

    except Exception as e:
        log.debug(f"[Fallback] Erro: {e}")

    return None


def _find_textbox(page):
    """Encontra o campo de texto para envio de mensagem."""
    for selector in _TEXTBOX_SELECTORS:
        el = page.query_selector(selector)
        if el and el.is_visible():
            return el
    return None