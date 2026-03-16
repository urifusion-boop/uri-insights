"""
One-time setup script: registers your platform OAuth credentials with Outstand (BYOK).
Run this once — credentials are stored in Outstand and not needed again.

Usage:
    python setup_outstand_networks.py
"""

import asyncio
import httpx
import os
import re

# Manual .env loader — skips lines that aren't valid KEY=VALUE pairs
def load_env(path=".env"):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if re.match(r"^[A-Z0-9_]+$", key):
                    os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass

load_env()

OUTSTAND_API_KEY = os.getenv("OUTSTAND_API_KEY")
OUTSTAND_BASE_URL = "https://api.outstand.so"

HEADERS = {
    "Authorization": f"Bearer {OUTSTAND_API_KEY}",
    "Content-Type": "application/json",
}


async def configure_network(client: httpx.AsyncClient, network: str, client_key: str, client_secret: str):
    print(f"\n[{network.upper()}] Configuring...")
    resp = await client.post(
        f"{OUTSTAND_BASE_URL}/v1/social-networks",
        headers=HEADERS,
        json={"network": network, "client_key": client_key, "client_secret": client_secret},
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"  OK — id: {data.get('data', {}).get('id')}")
    elif resp.status_code == 409:
        print(f"  Already configured (skipping)")
    else:
        print(f"  FAILED ({resp.status_code}): {resp.text}")


async def main():
    if not OUTSTAND_API_KEY:
        print("ERROR: OUTSTAND_API_KEY not found in .env")
        return

    print(f"Using Outstand key: {OUTSTAND_API_KEY[:20]}...")

    # ── Credentials from .env ─────────────────────────────────────────────────
    meta_app_id     = os.getenv("META_APP_ID", "").strip("'")
    meta_app_secret = os.getenv("META_APP_SECRET", "").strip("'")
    linkedin_client_id     = os.getenv("LINKEDIN_CLIENT_ID", "").strip("'")
    linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip("'")
    x_client_id            = os.getenv("X_CLIENT_ID", "").strip("'")
    x_client_secret        = os.getenv("X_CLIENT_SECRET", "").strip("'")
    # tiktok_client_key    = os.getenv("TIKTOK_CLIENT_KEY", "").strip("'")
    # tiktok_client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "").strip("'")

    async with httpx.AsyncClient(timeout=30) as client:

        # Facebook — uses Meta App ID + Secret
        if meta_app_id and meta_app_secret:
            await configure_network(client, "facebook", meta_app_id, meta_app_secret)
        else:
            print("\n[FACEBOOK] Skipped — META_APP_ID or META_APP_SECRET missing")

        # Instagram — same Meta app as Facebook
        if meta_app_id and meta_app_secret:
            await configure_network(client, "instagram", meta_app_id, meta_app_secret)
        else:
            print("\n[INSTAGRAM] Skipped — META_APP_ID or META_APP_SECRET missing")

        # LinkedIn
        if linkedin_client_id and linkedin_client_secret:
            await configure_network(client, "linkedin", linkedin_client_id, linkedin_client_secret)
        else:
            print("\n[LINKEDIN] Skipped — LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET missing in .env")

        # X (Twitter) — OAuth 2.0 credentials from developer.twitter.com
        if x_client_id and x_client_secret:
            await configure_network(client, "x", x_client_id, x_client_secret)
        else:
            print("\n[X] Skipped — X_CLIENT_ID or X_CLIENT_SECRET missing in .env")

        # TikTok (uncomment when credentials are available):
        # if tiktok_client_key and tiktok_client_secret:
        #     await configure_network(client, "tiktok", tiktok_client_key, tiktok_client_secret)

    print("\nDone. You can now call POST /social-media/connect/initiate for configured platforms.")


if __name__ == "__main__":
    asyncio.run(main())
