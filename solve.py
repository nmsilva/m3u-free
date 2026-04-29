# solve.py
import asyncio, os, re
from playwright.async_api import async_playwright

SITE = "https://freeiptv2023-d.ottc.xyz/index.php"
VALTOWN = "https://nmsilva--09b5306a43a711f1a98b42b51c65c3df.web.val.run"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        token = None
        session = None

        # captura o cookie de sessão
        async def handle_response(response):
            nonlocal session
            if "ottc.xyz" in response.url:
                cookies = await ctx.cookies()
                for c in cookies:
                    if c["name"] == "ottc_sess":
                        session = c["value"]

        # interceta o token do turnstile no POST
        async def handle_request(request):
            nonlocal token
            if "index.php" in request.url and request.method == "POST":
                body = request.post_data or ""
                m = re.search(r"cf-turnstile-response=([^&]+)", body)
                if m:
                    token = m.group(1)

        page.on("response", handle_response)
        page.on("request", handle_request)

        await page.goto(SITE)
        # espera até o turnstile ser resolvido automaticamente
        await page.wait_for_timeout(8000)

        if token and session:
            import urllib.request, urllib.parse
            url = f"{VALTOWN}/activate?token={urllib.parse.quote(token)}&session={session}"
            req = urllib.request.urlopen(url)
            print("Resposta:", req.read().decode())
        else:
            print("ERRO: token ou session não encontrados")
            raise Exception("Falhou")

asyncio.run(main())