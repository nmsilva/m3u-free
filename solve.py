# solve.py
import asyncio, os, re
from playwright.async_api import async_playwright

SITE = "https://freeiptv2023-d.ottc.xyz/index.php"
VALTOWN = "https://nmsilva--09b5306a43a711f1a98b42b51c65c3df.web.val.run"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx  = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        print("A carregar a página...")
        await page.goto(SITE, wait_until="networkidle")

        # espera até o input do turnstile ter valor (máx 30s)
        print("À espera do Turnstile resolver...")
        try:
            await page.wait_for_function(
                """() => {
                    const el = document.querySelector('[name="cf-turnstile-response"]');
                    return el && el.value && el.value.length > 10;
                }""",
                timeout=30000,
            )
        except Exception:
            # tenta clicar se for o modo managed (checkbox)
            print("A tentar clicar no Turnstile...")
            try:
                frame = next(
                    f for f in page.frames
                    if "challenges.cloudflare.com" in f.url
                )
                await frame.locator("input[type=checkbox]").click(timeout=5000)
                await page.wait_for_function(
                    """() => {
                        const el = document.querySelector('[name="cf-turnstile-response"]');
                        return el && el.value && el.value.length > 10;
                    }""",
                    timeout=20000,
                )
            except Exception as e:
                print(f"Turnstile não resolveu: {e}")
                # screenshot para debug
                await page.screenshot(path="debug.png")
                raise

        # lê token do DOM
        token = await page.eval_on_selector(
            '[name="cf-turnstile-response"]',
            "el => el.value"
        )
        print(f"Token obtido: {token[:30]}...")

        # lê cookie de sessão
        cookies = await ctx.cookies()
        session = next(
            (c["value"] for c in cookies if c["name"] == "ottc_sess"),
            None
        )

        if not session:
            # tenta extrair do header da página
            session = await page.evaluate(
                "() => document.cookie"
            )
            print(f"Cookies raw: {session}")
            raise Exception("Cookie ottc_sess não encontrado")

        print(f"Session: {session[:12]}...")

        # chama o Val Town
        url = (
            f"{VALTOWN}/activate"
            f"?token={urllib.parse.quote(token)}"
            f"&session={urllib.parse.quote(session)}"
        )
        print(f"A chamar Val Town...")
        resp = urllib.request.urlopen(url, timeout=30)
        body = resp.read().decode()
        print(f"Resposta Val Town: {body}")

        await browser.close()

asyncio.run(main())