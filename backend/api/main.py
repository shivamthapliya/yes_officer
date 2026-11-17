import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis

from api.common.security import JwtService
from api.config.settings import settings
from api.dependencies import limiter
from api.exceptions import register_exception_handlers
from api.realtime.connection_manager import ConnectionManager
from api.realtime.live_state import LiveStateStore
from api.routers import auth, history, internal, polls, rooms, ws

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(redis_client: Redis | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        redis = redis_client or Redis.from_url(settings.REDIS_URL)
        app.state.redis = redis
        app.state.live_state = LiveStateStore(redis)
        app.state.jwt_service = JwtService(settings.SECRET_KEY, settings.JWT_ALGORITHM)
        app.state.connection_manager = ConnectionManager()
        try:
            yield
        finally:
            if redis_client is None:
                redis.close()

    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan, docs_url=f"{settings.API_PREFIX}/docs",
                  openapi_url=f"{settings.API_PREFIX}/openapi.json")
    app.state.limiter = limiter
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    for router in (auth.router, rooms.router, polls.router, history.router, internal.router):
        app.include_router(router, prefix=settings.API_PREFIX)
    app.include_router(ws.router)

    @app.get(f"{settings.API_PREFIX}/health", tags=["Health"])
    def health():
        app.state.redis.ping()
        return {"status": "ok"}

    return app


app = create_app()
