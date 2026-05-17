"""
Gradio UI for POST /api/v1/combine.

Requires the optional UI stack (install after core):

    pip install -r requirements-core.txt -r requirements-extra.txt

Run API first:

    uvicorn app.main:app --host 0.0.0.0 --port 8002

Then:

    python examples/gradio_combine_demo.py

Environment:

    COMBINE_API_BASE   Base URL of the API (default http://127.0.0.1:8002)
"""
from __future__ import annotations

import os

import gradio as gr
import httpx

DEFAULT_BASE = os.environ.get("COMBINE_API_BASE", "http://127.0.0.1:8002").rstrip("/")


def run_combine(
    query: str,
    scenario: str,
    search_engine: str,
    links_num: int,
    llm_provider: str,
    locale: str,
) -> str:
    payload: dict = {
        "query": query.strip(),
        "scenario": scenario,
        "search_engine": search_engine.lower().strip(),
        "links_num": int(links_num),
        "http_tool": "request",
        "llm_provider": llm_provider.strip() or "openai",
        "temperature": 0.3,
    }
    loc = (locale or "").strip()
    if loc:
        payload["locale"] = loc
    try:
        r = httpx.post(
            f"{DEFAULT_BASE}/api/v1/combine",
            json=payload,
            timeout=120.0,
        )
    except httpx.RequestError as e:
        return f"请求失败: {e}"
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {r.text[:2000]}"
    data = r.json()
    parts = [data.get("llm_output") or ""]
    errs = data.get("errors") or []
    if errs:
        parts.append("\n\n--- errors ---\n" + "\n".join(str(x) for x in errs))
    parts.append("\n\n--- timings ---\n" + str(data.get("timings")))
    return "".join(parts)


def main() -> None:
    with gr.Blocks(title="Combine Search") as demo:
        gr.Markdown(
            f"调用 `{DEFAULT_BASE}/api/v1/combine`。"
            " 请先启动 FastAPI 并配置 LLM API Key。"
        )
        q = gr.Textbox(label="Query", lines=2)
        scenario = gr.Dropdown(
            ["film", "stock", "news", "product"], value="news", label="Scenario"
        )
        engine = gr.Dropdown(
            ["bing", "duckduckgo", "baidu", "google"],
            value="bing",
            label="Search engine",
        )
        links = gr.Slider(1, 10, value=2, step=1, label="links_num")
        provider = gr.Textbox(value="openai", label="llm_provider")
        locale = gr.Textbox(value="", label="locale (optional, e.g. zh)")
        out = gr.Textbox(label="Result", lines=24)
        btn = gr.Button("Run")
        btn.click(
            run_combine,
            inputs=[q, scenario, engine, links, provider, locale],
            outputs=out,
        )
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("GRADIO_PORT", "7860")))


if __name__ == "__main__":
    main()
