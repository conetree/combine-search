"""Load scenario prompts from app/prompts, with optional PROMPTS_DIR override."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from app.core.config import settings
from app.core.logging import logger

BUILTIN_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

STANDARD_SCENARIOS: tuple[str, ...] = ("film", "stock", "news", "product")

_prompt_body_cache: Dict[str, Tuple[int, "ScenarioPrompt"]] = {}


@dataclass
class ScenarioPrompt:
    system: str
    user: str


def _norm_locale(locale: Optional[str]) -> Optional[str]:
    s = (locale or "").strip().lower()
    return s or None


def _norm_scenario(scenario: str) -> str:
    return scenario.lower().strip()


def _cache_key(scenario: str, locale: Optional[str]) -> str:
    return f"{_norm_scenario(scenario)}:{_norm_locale(locale) or ''}"


def _iter_candidate_paths(scenario: str, locale: Optional[str]) -> list[Path]:
    scen = _norm_scenario(scenario)
    loc = _norm_locale(locale)
    odir = (settings.PROMPTS_DIR or "").strip()
    out: list[Path] = []
    if odir:
        base = Path(odir)
        if loc:
            out.append(base / f"{scen}.{loc}.yaml")
        out.append(base / f"{scen}.yaml")
    if loc:
        out.append(BUILTIN_PROMPTS / f"{scen}.{loc}.yaml")
    out.append(BUILTIN_PROMPTS / f"{scen}.yaml")
    return out


def resolve_prompt_path(scenario: str, locale: Optional[str] = None) -> Path:
    for p in _iter_candidate_paths(scenario, locale):
        if p.is_file():
            logger.debug("Resolved prompt path: %s", p)
            return p
    loc = _norm_locale(locale)
    hint = f" (locale={loc})" if loc else ""
    raise FileNotFoundError(f"No prompt template for scenario: {_norm_scenario(scenario)}{hint}")


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _path_to_prompt(path: Path) -> ScenarioPrompt:
    raw = _load_yaml_file(path)
    system = (raw.get("system") or "").strip()
    user = (raw.get("user") or "").strip()
    if not system or not user:
        raise ValueError(f"Invalid prompt file {path}: need system and user")
    return ScenarioPrompt(system=system, user=user)


def load_scenario_prompt(scenario: str, locale: Optional[str] = None) -> ScenarioPrompt:
    path = resolve_prompt_path(scenario, locale)
    ck = _cache_key(scenario, locale)
    if settings.PROMPTS_CACHE_ENABLED:
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            mtime_ns = 0
        hit = _prompt_body_cache.get(ck)
        if hit is not None and hit[0] == mtime_ns:
            return hit[1]
        sp = _path_to_prompt(path)
        _prompt_body_cache[ck] = (mtime_ns, sp)
        return sp
    return _path_to_prompt(path)


def invalidate_prompt_cache() -> None:
    _prompt_body_cache.clear()


def render_prompt(
    template: str,
    *,
    query: str,
    retrieved_context: str,
    current_date: str,
) -> str:
    return (
        template.replace("{{ query }}", query)
        .replace("{{query}}", query)
        .replace("{{ retrieved_context }}", retrieved_context)
        .replace("{{retrieved_context}}", retrieved_context)
        .replace("{{ current_date }}", current_date)
        .replace("{{current_date}}", current_date)
    )


def get_prompt_resolution(
    scenario: str, locale: Optional[str] = None
) -> Dict[str, Any]:
    scen = _norm_scenario(scenario)
    loc = _norm_locale(locale)
    for p in _iter_candidate_paths(scenario, locale):
        if not p.is_file():
            continue
        src = "builtin"
        odir = (settings.PROMPTS_DIR or "").strip()
        if odir:
            try:
                p.resolve().relative_to(Path(odir).resolve())
                src = "external"
            except ValueError:
                pass
        row: Dict[str, Any] = {
            "scenario": scen,
            "source": src,
            "path": str(p.resolve()),
        }
        if loc:
            row["locale"] = loc
        return row
    row = {"scenario": scen, "source": "missing", "path": None}
    if loc:
        row["locale"] = loc
    return row


def _scenario_slug_from_filename(stem: str) -> str:
    """film.zh -> film; news -> news"""
    parts = stem.lower().split(".")
    return parts[0] if parts else stem.lower()


def list_prompt_catalog(locale: Optional[str] = None) -> Dict[str, Any]:
    discovered: set[str] = set(STANDARD_SCENARIOS)
    if BUILTIN_PROMPTS.is_dir():
        for p in BUILTIN_PROMPTS.glob("*.yaml"):
            discovered.add(_scenario_slug_from_filename(p.stem))
    override_dir = (settings.PROMPTS_DIR or "").strip()
    if override_dir:
        d = Path(override_dir)
        if d.is_dir():
            for p in d.glob("*.yaml"):
                discovered.add(_scenario_slug_from_filename(p.stem))
    rows = [get_prompt_resolution(s, locale) for s in sorted(discovered)]
    return {
        "prompts_dir": override_dir or None,
        "locale": _norm_locale(locale),
        "scenarios": rows,
    }


def validate_prompt_yaml_bytes(raw: bytes) -> ScenarioPrompt:
    data = yaml.safe_load(raw.decode("utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    system = (data.get("system") or "").strip()
    user = (data.get("user") or "").strip()
    if not system or not user:
        raise ValueError("YAML must contain non-empty system and user")
    return ScenarioPrompt(system=system, user=user)
