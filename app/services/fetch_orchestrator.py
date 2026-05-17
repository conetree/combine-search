"""Try multiple HTTP clients (chain) for a single URL until one returns usable text."""
from __future__ import annotations

from typing import Dict, List, Optional

from app.core.logging import logger
from app.services.base_search import BaseSearch


class FetchOrchestrator:
    def __init__(self, base: BaseSearch, chain: Optional[List[str]] = None):
        self.base = base
        self.chain = [t.strip() for t in (chain or []) if t and t.strip()]

    def fetch_url_as_text(self, url: str, headers: Optional[Dict] = None, min_chars: int = 80) -> str:
        last_err: Exception | None = None
        for tool in self.chain:
            try:
                client = self.base.get_client(tool)
                html = client.fetch(url, headers=headers or {})
                text = self.base.extract_content_text(html).strip()
                if len(text) >= min_chars:
                    return text
                logger.debug("fetch tool=%s url=%s text too short (%s)", tool, url, len(text))
            except Exception as e:
                last_err = e
                logger.warning("fetch tool=%s url=%s err=%s", tool, url, e)
                continue
        if last_err:
            raise RuntimeError(f"All fetch tools failed for {url}: {last_err}") from last_err
        raise RuntimeError(f"No usable text for {url}")
