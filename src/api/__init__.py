from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
# Import the app instance from main.py
from src.api.main import app

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )
    
    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

app = create_application() 