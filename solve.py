# solve.py
import asyncio, os, urllib.request, urllib.parse
from playwright.async_api import async_playwright

SITE = "https://freeiptv2023-d.ottc.xyz/index.php"
VALTOWN = "https://nmsilva--09b5306a43a711f1a98b42b51c65c3df.web.val.run"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()

        # aumenta timeout global
        page.set_default_timeout(60000)

        print("A carregar a página...")
        # usa domcontentloaded em vez de networkidle
        await page.goto(SITE, wait_until="domcontentloaded", timeout=60000)

        print("Página carregada, à espera do Turnstile (máx 45s)...")
        # aguarda o input ter valor
        try:
            await page.wait_for_function(
                """() => {
                    const inputs = document.querySelectorAll('input');
                    for (const el of inputs) {
                        if (el.name === 'cf-turnstile-response' && el.value.length > 10)
                            return true;
                    }
                    // também tenta pelo iframe
                    return false;
                }""",
                timeout=45000,
                polling=1000,
            )
            print("Turnstile resolvido via DOM!")
        except Exception:
            print("Input não encontrado, a verificar frames...")

            # dump de debug
            for f in page.frames:
                print("  frame:", f.url[:80])

            inputs = await page.eval_on_selector_all(
                "input",
                "els => els.map(e => ({name: e.name, value: e.value.slice(0,30)}))"
            )
            print("  inputs na página:", inputs)

            await page.screenshot(path="debug.png")
            raise Exception("Turnstile não resolveu — ver debug.png")

        # lê o token
        token = await page.evaluate("""() => {
            const el = document.querySelector('[name="cf-turnstile-response"]');
            return el ? el.value : null;
        }""")

        if not token:
            await page.screenshot(path="debug.png")
            raise Exception("Token vazio após wait")

        print(f"Token: {token[:30]}...")

        # lê o cookie
        cookies = await ctx.cookies()
        session = next(
            (c["value"] for c in cookies if c["name"] == "ottc_sess"),
            None,
        )

        if not session:
            print("Cookies disponíveis:", [c["name"] for c in cookies])
            raise Exception("Cookie ottc_sess não encontrado")

        print(f"Session: {session[:12]}...")

        # chama o Val Town
        url = (
            f"{VALTOWN}/activate"
            f"?token={urllib.parse.quote(token)}"
            f"&session={urllib.parse.quote(session)}"
        )
        print("A chamar Val Town...")
        resp = urllib.request.urlopen(url, timeout=30)
        body = resp.read().decode()
        print(f"Val Town response: {body}")

        await browser.close()

asyncio.run(main())