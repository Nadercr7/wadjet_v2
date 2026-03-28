from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.config import settings
from app.i18n import get_lang

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "landing.html", {"lang": lang})


@router.get("/scan", response_class=HTMLResponse)
async def scan(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "scan.html", {"lang": lang})


@router.get("/dictionary", response_class=HTMLResponse)
async def dictionary(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "dictionary.html", {"lang": lang})


@router.get("/write", response_class=HTMLResponse)
async def write(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "write.html", {"lang": lang})


@router.get("/explore", response_class=HTMLResponse)
async def explore(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "explore.html", {"lang": lang})


@router.get("/hieroglyphs", response_class=HTMLResponse)
async def hieroglyphs(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "hieroglyphs.html", {"lang": lang})


@router.get("/landmarks", response_class=HTMLResponse)
async def landmarks(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "landmarks.html", {"lang": lang})


@router.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "chat.html", {"lang": lang})


@router.get("/quiz", response_class=HTMLResponse)
async def quiz(request: Request):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "quiz.html", {"lang": lang})


@router.get("/dictionary/lesson/{level}", response_class=HTMLResponse)
async def dictionary_lesson_page(request: Request, level: int):
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "lesson_page.html", {"level": level, "lang": lang})


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    base = settings.base_url.rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: GPTBot\n"
        "Disallow: /\n"
        "\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


@router.get("/sitemap.xml")
async def sitemap_xml():
    base = settings.base_url.rstrip("/")
    pages = [
        "/",
        "/hieroglyphs",
        "/landmarks",
        "/scan",
        "/dictionary",
        "/write",
        "/explore",
        "/chat",
        "/quiz",
    ]
    urls = ""
    for page in pages:
        urls += (
            "  <url>\n"
            f"    <loc>{base}{page}</loc>\n"
            "    <changefreq>weekly</changefreq>\n"
            "  </url>\n"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}"
        "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml")
