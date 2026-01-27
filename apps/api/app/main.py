from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env file FIRST, before any other imports
# that might use environment variables
# Look for .env file in the api directory (parent of app directory)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import financial
import app.services.edgar_init  # Initialize EdgarTools with identity
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Storcky API", version="0.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(financial.router, prefix="/api", tags=["financial"])


@app.get("/")
async def root():
    return {"message": "Storcky API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
