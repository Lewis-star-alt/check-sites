from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import httpx
import asyncio
from tabulate import tabulate
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")


async def check_site(url: str):
    """Проверка одного сайта с детальной обработкой ошибок"""
    async with httpx.AsyncClient(
            http2=True,
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
    ) as client:
        try:

            try:
                response = await client.head(url)
            except (httpx.RemoteProtocolError, httpx.ProtocolError):
                response = await client.get(url)

            is_success = 200 <= response.status_code < 400
            return {
                'url': url,
                'status': response.status_code,
                'http_version': response.http_version,
                'success': is_success,
                'error': None
            }

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            if isinstance(e, httpx.ConnectError):
                error_type = "Connection Error"
            elif isinstance(e, httpx.TimeoutException):
                error_type = "Timeout"
            elif isinstance(e, httpx.HTTPStatusError):
                error_type = f"HTTP Error {e.response.status_code}"

            return {
                'url': url,
                'status': 0,
                'http_version': "",
                'success': False,
                'error': f"{error_type}: {error_msg}"
            }


@app.post("/check", response_class=HTMLResponse)
async def check_urls(request: Request, urls: str = Form(...)):

    url_list = [url.strip() for url in urls.split('\n') if url.strip()]

    tasks = [check_site(url) for url in url_list]
    results = await asyncio.gather(*tasks)


    table_data = []
    for r in results:
        if r['success']:
            status_icon = "✓"
            details = f"HTTP/{r['http_version']}"
        else:
            status_icon = "🔴"
            details = r['error'] or f"Status: {r['status']}"

        table_data.append([
            r['url'],
            f"{status_icon} {r['status']}" if r['status'] > 0 else status_icon,
            details
        ])

    headers = ["URL", "Статус", "Детали"]
    html_table = tabulate(table_data, headers=headers, tablefmt="html")


    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "table": html_table,
            "total": len(results),
            "success": sum(1 for r in results if r['success'])
        }
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
    )