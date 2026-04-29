
import asyncio, os, urllib.request, urllib.parse
from playwright.async_api import async_playwright

LANDING = "https://freeiptv2023-d.ottc.xyz"
SITE    = "https://freeiptv2023-d.ottc.xyz/index.php"
VALTOWN = "https://nmsilva--09b5306a43a711f1a98b42b51c65c3df.web.val.run"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-blink-features=AutomationControlled"],
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
        page.set_default_timeout(60000)

        print("A carregar landing page...")
        await page.goto(LANDING, wait_until="domcontentloaded", timeout=60000)

        # espera o botão ficar enabled (o countdown acaba)
        print("À espera do botão ficar activo...")
        btn = page.locator("#create-btn")
        await btn.wait_for(state="enabled", timeout=20000)
        print("Botão activo, a clicar...")
        await btn.click()

        # espera a navegação para index.php
        print("À espera de index.php...")
        await page.wait_for_url("**/index.php", timeout=15000)
        await page.wait_for_timeout(3000)

        print("À espera do Turnstile resolver (máx 45s)...")
        try:
            await page.wait_for_function(
                """() => {
                    const el = document.querySelector('[name="cf-turnstile-response"]');
                    return el && el.value && el.value.length > 10;
                }""",
                timeout=45000,
                polling=1000,
            )
        except Exception:
            await page.screenshot(path="debug.png")
            inputs = await page.eval_on_selector_all(
                "input",
                "els => els.map(e => ({name: e.name, value: e.value.slice(0,30)}))"
            )
            print("Inputs:", inputs)
            print("Frames:", [f.url for f in page.frames])
            raise Exception("Turnstile não resolveu — ver debug.png")

        token = await page.evaluate(
            "() => document.querySelector('[name=\"cf-turnstile-response\"]').value"
        )
        print(f"Token: {token[:30]}...")

        cookies = await ctx.cookies()
        session = next(
            (c["value"] for c in cookies if c["name"] == "ottc_sess"), None
        )
        if not session:
            raise Exception(f"Cookie não encontrado. Cookies: {[c['name'] for c in cookies]}")
        print(f"Session: {session[:12]}...")

        url = (
            f"{VALTOWN}/activate"
            f"?token={urllib.parse.quote(token)}"
            f"&session={urllib.parse.quote(session)}"
        )
        print("A chamar Val Town...")
        resp = urllib.request.urlopen(url, timeout=30)
        print(f"Resposta: {resp.read().decode()}")

        await browser.close()

asyncio.run(main())