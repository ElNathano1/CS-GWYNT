"""Main API Routes"""

from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter()


@router.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@router.get("/api/v1/info")
async def get_info():
    """Get game information"""
    return {
        "name": "CS-GWYNT",
        "version": "0.1.0",
        "description": "Online Trading Card Game inspired by Gwent",
    }
