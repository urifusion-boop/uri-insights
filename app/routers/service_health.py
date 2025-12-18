# app/routers/service_health.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict
import time
import psutil
import pymongo
from app.database import get_db
from datetime import datetime

router = APIRouter()


class Message(BaseModel):
    cmd: str


@router.post("/message")
def handle_message(message: Message):
    if message.cmd == "ping":
        return {"message": "pong right here"}
    return {"message": "Unknown command"}


@router.get("/test")
def test():
    return "Microservice is working"


@router.get("/health")
def health_check():
    """
    Health check endpoint that returns service status, uptime, and system metrics
    """
    # Check MongoDB connection
    try:
        # Ping MongoDB to check if it's connected
        database = get_db()
        database.command('ping')
        is_mongo_connected = True
        mongo_state = "connected"
    except Exception as e:
        is_mongo_connected = False
        mongo_state = "disconnected"

    # Get system metrics using psutil
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
    except Exception:
        cpu_percent = 0
        memory_percent = 0

    # Get process uptime
    try:
        process = psutil.Process()
        uptime_seconds = time.time() - process.create_time()
    except Exception:
        uptime_seconds = 0

    return {
        "status": "healthy",
        "service": "uri-insights",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime": uptime_seconds,
        "database": {
            "mongodb": {
                "connected": is_mongo_connected,
                "state": mongo_state,
            }
        },
        "system": {
            "cpu": round(cpu_percent),
            "memory": round(memory_percent),
        },
    }
