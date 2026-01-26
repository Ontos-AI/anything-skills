"""Skills Forge - FastAPI主入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.routes import router
from src.api.anything2skills import router as a2s_router
from src.api.agent_arena import router as arena_router
from src.core.config import config

# 确保目录存在
config.ensure_dirs()

app = FastAPI(
    title="Skills Forge",
    description="从多源内容提取经验知识，自动生成 Claude Skills",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)
app.include_router(a2s_router)
app.include_router(arena_router)

# 静态与模板
templates = Jinja2Templates(directory=str(config.BASE_DIR / "src" / "templates"))
app.state.templates = templates
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "src" / "static")), name="static")


@app.get("/")
async def root():
    return {
        "name": "Skills Forge",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
