from __future__ import annotations

from fastapi import FastAPI, Response

from hancock import __version__
from hancock.api.metrics import metrics_payload
from hancock.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hancock",
        description="CyberViser Hancock — AI cybersecurity co-pilot",
        version=__version__,
    )
    app.include_router(router)

    @app.get("/metrics")
    async def metrics() -> Response:
        body, ctype = metrics_payload()
        return Response(content=body, media_type=ctype)

    return app


app = create_app()
