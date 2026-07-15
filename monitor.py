import json
import os
import sys
import unicodedata

from playwright.sync_api import sync_playwright


def normalize(text: str) -> str:
    """Quita acentos y pasa a minúsculas para comparación robusta."""
    nfkd = unicodedata.normalize("NFD", text)
    return nfkd.encode("ascii", "ignore").decode("ascii").lower()


def send_telegram(token: str, chat_id: str, message: str) -> bool:
    import urllib.request, urllib.parse
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false",
    }).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def scrape_page(url: str) -> str:
    """Abre la URL con Playwright y devuelve el texto visible de la página."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page.goto(url, wait_until="networkidle", timeout=30_000)
        text = page.inner_text("body")
        browser.close()
        return text


def main():
    with open("config.json", encoding="utf-8") as f:
        config = json.load(f)

    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")

    if not token or not chat_id:
        print("ERROR: TELEGRAM_TOKEN y CHAT_ID deben estar en los secrets.")
        sys.exit(1)

    url = config["url"]
    event_name = config.get("event_name", "Evento")
    keywords = config["keywords_available"]

    print(f"Verificando: {event_name}")
    print(f"URL: {url}")

    try:
        page_text = scrape_page(url)
    except Exception as e:
        print(f"Error al cargar la página: {e}")
        sys.exit(1)

    page_normalized = normalize(page_text)

    matched = []
    for kw in keywords:
        if normalize(kw) in page_normalized:
            matched.append(kw)

    if matched:
        matched_str = "\n".join(f"  • {kw}" for kw in matched)
        msg = (
            f"🎟 <b>BOLETOS DISPONIBLES!</b>\n\n"
            f"Evento: <b>{event_name}</b>\n\n"
            f"Detectado:\n{matched_str}\n\n"
            f'<a href="{url}">Comprar ahora →</a>'
        )
        ok = send_telegram(token, chat_id, msg)
        print(f"ENCONTRADO — keywords: {matched}")
        print("Telegram enviado." if ok else "FALLO al enviar Telegram.")
    else:
        print("No disponible aún — ninguna keyword encontrada.")
        # Solo manda mensaje negativo en ejecuciones manuales (no spam cada 5 min)
        if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
            msg = (
                f"❌ <b>Sin novedad</b>\n\n"
                f"Evento: <b>{event_name}</b>\n"
                f"Boletos aún no disponibles.\n\n"
                f'<a href="{url}">Ver página →</a>'
            )
            send_telegram(token, chat_id, msg)


if __name__ == "__main__":
    main()
