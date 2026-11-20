from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import make_verify_token
from .routes import daemon, shell, config_router, vitals, cycle, goals, inbox, audit
from .routes import compliance, rules, github_router, exchange
from .routes import products, fleet, portfolio, metrics

_HERE = Path(__file__).parent


def create_app(config: dict, token: str) -> FastAPI:
    app = FastAPI(title="URACE Web", docs_url=None, redoc_url=None)

    static_dir = _HERE / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    templates = Jinja2Templates(directory=str(_HERE / "templates"))
    verify_token = make_verify_token(token)

    def get_config():
        return config

    app.state.templates = templates
    app.state.token = token
    app.state.get_config = get_config
    app.state.verify_token = verify_token

    app.include_router(
        daemon.build_router(templates, verify_token),
        prefix="/api/daemon",
    )
    app.include_router(
        shell.build_router(verify_token),
        prefix="/api/shell",
    )
    app.include_router(
        config_router.build_router(templates, get_config, verify_token),
        prefix="/api/config",
    )
    app.include_router(
        vitals.build_router(get_config, verify_token),
        prefix="/api/vitals",
    )
    app.include_router(
        cycle.build_router(templates, get_config, verify_token),
        prefix="/api/cycle",
    )
    app.include_router(
        goals.build_router(get_config, verify_token),
        prefix="/api/goals",
    )
    app.include_router(
        inbox.build_router(get_config, verify_token),
        prefix="/api/inbox",
    )
    app.include_router(
        audit.build_router(get_config, verify_token),
        prefix="/api/audit",
    )
    app.include_router(
        compliance.build_router(get_config, verify_token),
        prefix="/api/compliance",
    )
    app.include_router(
        rules.build_router(get_config, verify_token),
        prefix="/api/rules",
    )
    app.include_router(
        github_router.build_router(get_config, verify_token),
        prefix="/api/github",
    )
    app.include_router(
        exchange.build_router(get_config, verify_token),
        prefix="/api/exchange",
    )
    app.include_router(
        products.build_router(get_config, verify_token),
        prefix="/api/products",
    )
    app.include_router(
        fleet.build_router(get_config, verify_token),
        prefix="/api/fleet",
    )
    app.include_router(
        portfolio.build_router(get_config, verify_token),
        prefix="/api/portfolio",
    )
    app.include_router(
        metrics.build_router(verify_token),
        prefix="/api/metrics",
    )

    from .routes.config_router import _get_fields_and_values

    def _ctx(active: str, **extra):
        return {"active": active, "token": token, **extra}

    @app.get("/", include_in_schema=False)
    async def index():
        return RedirectResponse(url="/shell")

    @app.get("/shell", response_class=HTMLResponse, include_in_schema=False)
    async def page_shell(request: Request):
        return templates.TemplateResponse(request, "shell.html", context=_ctx("shell"))

    @app.get("/config", response_class=HTMLResponse, include_in_schema=False)
    async def page_config(request: Request):
        fields, values = _get_fields_and_values(config)
        return templates.TemplateResponse(request, "config.html", context=_ctx("config", fields=fields, values=values))

    @app.get("/vitals", response_class=HTMLResponse, include_in_schema=False)
    async def page_vitals(request: Request):
        return templates.TemplateResponse(request, "vitals.html", context=_ctx("vitals"))

    @app.get("/wallet", response_class=HTMLResponse, include_in_schema=False)
    async def page_wallet(request: Request):
        return templates.TemplateResponse(request, "wallet.html", context=_ctx("wallet"))

    @app.get("/cycle", response_class=HTMLResponse, include_in_schema=False)
    async def page_cycle(request: Request):
        return templates.TemplateResponse(request, "cycle.html", context=_ctx("cycle"))

    @app.get("/goals", response_class=HTMLResponse, include_in_schema=False)
    async def page_goals(request: Request):
        return templates.TemplateResponse(request, "goals.html", context=_ctx("goals"))

    @app.get("/inbox", response_class=HTMLResponse, include_in_schema=False)
    async def page_inbox(request: Request):
        return templates.TemplateResponse(request, "inbox.html", context=_ctx("inbox"))

    @app.get("/audit", response_class=HTMLResponse, include_in_schema=False)
    async def page_audit(request: Request):
        return templates.TemplateResponse(request, "audit.html", context=_ctx("audit"))

    @app.get("/compliance", response_class=HTMLResponse, include_in_schema=False)
    async def page_compliance(request: Request):
        return templates.TemplateResponse(request, "compliance.html", context=_ctx("compliance"))

    @app.get("/rules", response_class=HTMLResponse, include_in_schema=False)
    async def page_rules(request: Request):
        return templates.TemplateResponse(request, "rules.html", context=_ctx("rules"))

    @app.get("/github", response_class=HTMLResponse, include_in_schema=False)
    async def page_github(request: Request):
        return templates.TemplateResponse(request, "github.html", context=_ctx("github"))

    @app.get("/exchange", response_class=HTMLResponse, include_in_schema=False)
    async def page_exchange(request: Request):
        return templates.TemplateResponse(request, "exchange.html", context=_ctx("exchange"))

    @app.get("/products", response_class=HTMLResponse, include_in_schema=False)
    async def page_products(request: Request):
        return templates.TemplateResponse(request, "products.html", context=_ctx("products"))

    @app.get("/fleet", response_class=HTMLResponse, include_in_schema=False)
    async def page_fleet(request: Request):
        return templates.TemplateResponse(request, "fleet.html", context=_ctx("fleet"))

    @app.get("/portfolio", response_class=HTMLResponse, include_in_schema=False)
    async def page_portfolio(request: Request):
        return templates.TemplateResponse(request, "portfolio.html", context=_ctx("portfolio"))

    return app
