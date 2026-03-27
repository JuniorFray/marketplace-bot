def get_unread_conversations(page) -> list[dict]:
    print("🔍 Procurando conversas no Marketplace...")
    conversations = []
    try:
        page.wait_for_timeout(4000)

        # Pega apenas os itens da área principal de conteúdo (não o menu lateral)
        main = page.query_selector('[role="main"]')
        if not main:
            print("⚠️ Área principal não encontrada.")
            return []

        # Procura links clicáveis que são as conversas reais
        items = main.query_selector_all('a[href*="/marketplace/item/"]')
        
        if not items:
            # Fallback: procura por divs com tabindex na área principal
            items = main.query_selector_all('div[tabindex="0"]')

        print(f"📋 Conversas encontradas: {len(items)}")

        for item in items:
            try:
                full_text = item.inner_text().strip()
                if not full_text or len(full_text) < 5:
                    continue

                # Detecta não lido pelo ponto azul via JavaScript
                is_unread = page.evaluate("""
                    (el) => {
                        const spans = el.querySelectorAll('span');
                        for (const span of spans) {
                            const style = window.getComputedStyle(span);
                            if (style.fontWeight === '700' || style.fontWeight === 'bold') {
                                return true;
                            }
                        }
                        // Verifica ponto azul
                        const circles = el.querySelectorAll('span[style*="background-color"]');
                        for (const c of circles) {
                            if (c.style.backgroundColor.includes('0, 132') ||
                                c.style.backgroundColor.includes('0, 149')) {
                                return true;
                            }
                        }
                        return false;
                    }
                """, item)

                name_el = item.query_selector('span[dir="auto"]')
                name = name_el.inner_text().strip() if name_el else full_text[:30]

                if is_unread:
                    conversations.append({"name": name, "element": item})
                    print(f"📨 Não lida: {name}")

            except:
                continue

    except Exception as e:
        print(f"⚠️ Erro: {e}")

    if not conversations:
        print("✅ Nenhuma mensagem nova no Marketplace.")
    return conversations


def get_last_message(page) -> str:
    try:
        page.wait_for_timeout(2000)
        messages = page.query_selector_all('[dir="auto"]')
        texts = [m.inner_text().strip() for m in messages if m.inner_text().strip()]
        return texts[-1] if texts else ""
    except Exception as e:
        print(f"⚠️ Erro ao ler mensagem: {e}")
        return ""


def get_sender_id(page) -> str:
    try:
        parts = page.url.strip("/").split("/")
        return parts[-1] if parts else "unknown"
    except:
        return "unknown"


def send_message(page, text: str):
    try:
        box = page.query_selector('[contenteditable="true"][role="textbox"]')
        if box:
            box.click()
            page.wait_for_timeout(500)
            box.type(text, delay=60)
            page.wait_for_timeout(800)
            page.keyboard.press("Enter")
            print(f"✅ Mensagem enviada: {text[:60]}...")
        else:
            print("⚠️ Campo de texto não encontrado.")
    except Exception as e:
        print(f"⚠️ Erro ao enviar mensagem: {e}")