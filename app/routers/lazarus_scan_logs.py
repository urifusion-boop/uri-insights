"""
Lazarus Scan Logs Endpoint - Returns real-time scan logs and fetched posts
"""
from fastapi import APIRouter, Query
from typing import Dict, List, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory storage for scan logs (simple approach for now)
# In production, use Redis or similar
scan_logs_storage: Dict[str, List[Dict[str, Any]]] = {}

@router.get("/scan-logs/{scan_id}")
async def get_scan_logs(scan_id: str) -> Dict[str, Any]:
    """
    Get real-time scan logs for a specific scan ID

    Returns:
        {
            "logs": [
                {
                    "timestamp": "08:26:32",
                    "level": "info",
                    "message": "Fetching LinkedIn posts...",
                    "icon": "linkedin"
                }
            ],
            "posts": [
                {
                    "text": "Post content...",
                    "author": "John Doe",
                    "platform": "linkedin",
                    "engagement": {"likes": 10, "comments": 5}
                }
            ]
        }
    """
    logs = scan_logs_storage.get(scan_id, [])

    return {
        "success": True,
        "logs": logs,
        "scan_id": scan_id
    }

def add_scan_log(scan_id: str, level: str, message: str, icon: str = None, metadata: Dict = None):
    """
    Add a log entry for a scan

    Args:
        scan_id: Unique scan identifier
        level: Log level (info, success, warning, error)
        message: Log message
        icon: Icon type (linkedin, twitter, search, check, etc.)
        metadata: Additional data (posts, signals, etc.)
    """
    from datetime import datetime

    if scan_id not in scan_logs_storage:
        scan_logs_storage[scan_id] = []

    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
        "icon": icon,
        "metadata": metadata or {}
    }

    scan_logs_storage[scan_id].append(log_entry)

    # Keep only last 100 logs per scan
    if len(scan_logs_storage[scan_id]) > 100:
        scan_logs_storage[scan_id] = scan_logs_storage[scan_id][-100:]

def clear_scan_logs(scan_id: str):
    """Clear logs for a specific scan"""
    if scan_id in scan_logs_storage:
        del scan_logs_storage[scan_id]
