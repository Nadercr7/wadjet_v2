import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from app.config import settings
from app.core.stories_engine import load_story
from app.i18n import get_lang

_STORY_ID_RE = re.compile(r"^[a-z0-9\-]{1,50}$")

router = APIRouter()


def _require_session(request: Request):
    """Redirect unauthenticated users to /welcome with ?next= for return path."""
    if not request.cookies.get("wadjet_session"):
        next_path = quote(request.url.path, safe="/")
        return RedirectResponse(f"/welcome?next={next_path}", status_code=302)
    return None


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    if not request.cookies.get("wadjet_session"):
        return RedirectResponse("/welcome", status_code=302)
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "landing.html", {"lang": lang, "page_name": "home"})


@router.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    if request.cookies.get("wadjet_session"):
        return RedirectResponse("/", status_code=302)
    templates = request.app.state.templates
    lang = get_lang(request)
    next_url = request.query_params.get("next", "")
    return templates.TemplateResponse(request, "welcome.html", {"lang": lang, "page_name": "welcome", "next_url": next_url})


@router.get("/scan", response_class=HTMLResponse)
async def scan(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "scan.html", {"lang": lang, "page_name": "scan"})


@router.get("/dictionary", response_class=HTMLResponse)
async def dictionary(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    extra_jsonld = {
        "@context": "https://schema.org",
        "@type": "DefinedTermSet",
        "name": "Gardiner Sign List",
        "description": "Comprehensive dictionary of 1,000+ ancient Egyptian hieroglyphic signs",
        "inLanguage": ["en", "ar"],
        "educationalLevel": "Beginner to Advanced",
    }
    return templates.TemplateResponse(request, "dictionary.html", {"lang": lang, "page_name": "dictionary", "extra_jsonld": extra_jsonld})


@router.get("/write", response_class=HTMLResponse)
async def write(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "write.html", {"lang": lang, "page_name": "write"})


@router.get("/explore", response_class=HTMLResponse)
async def explore(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    extra_jsonld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Egyptian Heritage Sites",
        "description": "Explore 260+ ancient Egyptian landmarks and heritage sites",
        "numberOfItems": 260,
        "itemListOrder": "Unordered",
    }
    return templates.TemplateResponse(request, "explore.html", {"lang": lang, "page_name": "explore", "extra_jsonld": extra_jsonld})


@router.get("/hieroglyphs", response_class=HTMLResponse)
async def hieroglyphs(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "hieroglyphs.html", {"lang": lang, "page_name": "hieroglyphs"})


@router.get("/landmarks", response_class=HTMLResponse)
async def landmarks(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "landmarks.html", {"lang": lang, "page_name": "landmarks"})


@router.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "chat.html", {"lang": lang, "page_name": "chat"})


@router.get("/quiz")
async def quiz(request: Request):
    return RedirectResponse("/stories", status_code=301)


@router.get("/stories", response_class=HTMLResponse)
async def stories(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "stories.html", {"lang": lang, "page_name": "stories"})


@router.get("/stories/{story_id}", response_class=HTMLResponse)
async def story_reader(request: Request, story_id: str):
    gate = _require_session(request)
    if gate:
        return gate
    if not _STORY_ID_RE.match(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    story = load_story(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    templates = request.app.state.templates
    lang = get_lang(request)
    # Story title/subtitle may be dicts (bilingual) — extract current language
    raw_title = story.get("title", story_id)
    raw_subtitle = story.get("subtitle", "")
    story_title = raw_title.get(lang, raw_title.get("en", story_id)) if isinstance(raw_title, dict) else raw_title
    story_subtitle = raw_subtitle.get(lang, raw_subtitle.get("en", "")) if isinstance(raw_subtitle, dict) else raw_subtitle
    # Per-page JSON-LD for story (CreativeWork)
    extra_jsonld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": story_title,
        "description": story_subtitle,
        "inLanguage": ["en", "ar"],
        "genre": "Mythology",
        "author": {"@type": "Person", "name": "Mr Robot"},
    }
    return templates.TemplateResponse(request, "story_reader.html", {
        "story_id": story_id, "lang": lang, "page_name": "stories",
        "story_title": story_title,
        "story_subtitle": story_subtitle,
        "extra_jsonld": extra_jsonld,
    })


@router.get("/dictionary/lesson/{level}", response_class=HTMLResponse)
async def dictionary_lesson_page(request: Request, level: int):
    gate = _require_session(request)
    if gate:
        return gate
    if level < 1 or level > 5:
        raise HTTPException(status_code=404, detail="Lesson not found")
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "lesson_page.html", {"level": level, "lang": lang, "page_name": "dictionary"})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "dashboard.html", {"lang": lang, "page_name": "dashboard"})


@router.get("/settings", response_class=HTMLResponse)
async def user_settings(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "settings.html", {"lang": lang, "page_name": "settings"})


@router.get("/feedback", response_class=HTMLResponse)
async def feedback_admin(request: Request):
    gate = _require_session(request)
    if gate:
        return gate
    templates = request.app.state.templates
    lang = get_lang(request)
    return templates.TemplateResponse(request, "feedback_admin.html", {"lang": lang, "page_name": "feedback", "admin_email": settings.admin_email})


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    base = settings.base_url.rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        f"Sitemap: {base}/sitemap.xml\n"
        "\n"
        "User-agent: GPTBot\n"
        "Disallow: /api/\n"
    )


@router.get("/sitemap.xml")
async def sitemap_xml():
    from datetime import date

    from app.core.stories_engine import get_story_ids

    base = settings.base_url.rstrip("/")
    today = date.today().isoformat()

    # Page priorities for SEO weighting
    priorities = {
        "/": "0.8", "/welcome": "0.9", "/stories": "0.7",
        "/scan": "0.7", "/dictionary": "0.7", "/explore": "0.7",
    }

    pages = [
        "/", "/welcome", "/hieroglyphs", "/landmarks",
        "/scan", "/dictionary", "/write", "/explore", "/chat", "/stories",
    ]
    # Add lesson pages (5 levels)
    for level in range(1, 6):
        pages.append(f"/dictionary/lesson/{level}")
    # Add all story detail pages
    for sid in get_story_ids():
        pages.append(f"/stories/{sid}")

    urls = ""
    for page in pages:
        prio = priorities.get(page, "")
        urls += "  <url>\n"
        urls += f"    <loc>{base}{page}</loc>\n"
        urls += f"    <lastmod>{today}</lastmod>\n"
        urls += "    <changefreq>weekly</changefreq>\n"
        if prio:
            urls += f"    <priority>{prio}</priority>\n"
        urls += "  </url>\n"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}"
        "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml")
