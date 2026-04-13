from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import addresses, assets, audit, auth, sweep, system
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.bootstrap_service import bootstrap_initial_data

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_initial_data(db)
    finally:
        db.close()


@app.get('/api/v1/health')
def health():
    return {'ok': True}


api_prefix = '/api/v1'
app.include_router(auth.router, prefix=api_prefix)
app.include_router(addresses.router, prefix=api_prefix)
app.include_router(assets.router, prefix=api_prefix)
app.include_router(sweep.router, prefix=api_prefix)
app.include_router(audit.router, prefix=api_prefix)
app.include_router(system.router, prefix=api_prefix)


static_dir = Path(__file__).resolve().parent / 'static'
app.mount('/static', StaticFiles(directory=static_dir), name='static')


@app.get('/')
def index():
    return FileResponse(static_dir / 'index.html')
