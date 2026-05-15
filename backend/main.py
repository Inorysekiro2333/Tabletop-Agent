from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from config import get_settings
from routers import auth, ai_configs, characters, campaigns, saves, chat

# Import models to register them with Base.metadata
import models.user
import models.ai_config
import models.character
import models.campaign
import models.save
import models.chat_branch

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tabletop Agent API",
    description="跑团游戏 KP Agent 后端 API",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(ai_configs.router, prefix=settings.api_prefix)
app.include_router(characters.router, prefix=settings.api_prefix)
app.include_router(campaigns.router, prefix=settings.api_prefix)
app.include_router(saves.router, prefix=settings.api_prefix)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"message": "Tabletop Agent API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
