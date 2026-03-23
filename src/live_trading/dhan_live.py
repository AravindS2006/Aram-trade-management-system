"""Live trading client wrapper with explicit confirmation guard."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from loguru import logger

from src.forward_testing.dhan_sandbox import DhanSandboxClient

load_dotenv()


class DhanLiveClient(DhanSandboxClient):
    """Live trading client using production Dhan credentials."""

    def __init__(
        self,
        client_id: str | None = None,
        access_token: str | None = None,
        confirm_live: bool = False,
    ) -> None:
        if not confirm_live:
            raise RuntimeError("Live mode requires explicit confirm_live=True")
        live_client = client_id or os.getenv("DHAN_CLIENT_ID", "")
        live_token = access_token or os.getenv("DHAN_ACCESS_TOKEN", "")
        if not live_client or not live_token:
            raise ValueError("Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env")
        logger.critical("LIVE TRADING MODE ENABLED")
        super().__init__(client_id=live_client, access_token=live_token)
