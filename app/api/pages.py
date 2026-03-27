from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "landing.html")


@router.get("/scan", response_class=HTMLResponse)
async def scan(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "scan.html")


@router.get("/dictionary", response_class=HTMLResponse)
async def dictionary(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "dictionary.html")


@router.get("/write", response_class=HTMLResponse)
async def write(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "write.html")


@router.get("/explore", response_class=HTMLResponse)
async def explore(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "explore.html")


@router.get("/hieroglyphs", response_class=HTMLResponse)
async def hieroglyphs(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "hieroglyphs.html")


@router.get("/landmarks", response_class=HTMLResponse)
async def landmarks(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "landmarks.html")


@router.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "chat.html")


@router.get("/quiz", response_class=HTMLResponse)
async def quiz(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "quiz.html")
