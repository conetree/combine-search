#!/usr/bin/env python3
"""Call POST /api/v1/combine on a running local server."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE = os.environ.get("COMBINE_SEARCH_BASE", "http://127.0.0.1:8002")


def main() -> int:
    url = f"{BASE.rstrip('/')}/api/v1/combine"
    body = {
        "query": os.environ.get("DEMO_QUERY", "流浪地球2 豆瓣 票房"),
        "scenario": os.environ.get("DEMO_SCENARIO", "film"),
        "search_engine": "bing",
        "links_num": 2,
        "http_tool": "cloudscraper",
        "llm_provider": os.environ.get("DEMO_LLM_PROVIDER", "openai"),
        "include_raw_excerpts": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Cannot reach {url}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
