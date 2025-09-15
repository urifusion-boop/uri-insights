# app/routers/service_health.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict
import time

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
