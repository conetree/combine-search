from app.services.prompt_loader import load_scenario_prompt, render_prompt


def test_load_film_prompt():
    p = load_scenario_prompt("film")
    assert "影视" in p.system or "摘录" in p.system
    assert "{{" not in render_prompt(
        p.user,
        query="测试",
        retrieved_context="abc",
        current_date="2026-01-01",
    )
