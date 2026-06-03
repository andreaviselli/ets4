from datetime import date

from ets4.config import load_config
from ets4.manifest import create_manifest


def test_create_manifest_includes_budget_and_actions() -> None:
    config = load_config("config/feeds.example.toml")

    manifest = create_manifest(config, date(2026, 6, 8), automation_mode="scheduled-draft")

    assert manifest.issue_id == "ets4-2026-06-08"
    assert manifest.automation_mode == "scheduled-draft"
    assert manifest.cost_budget["max_total_cost_usd"] == 10.0
    assert manifest.paper_budget["max_papers_to_full_review"] == 20
    assert "export_draft" in manifest.allowed_actions

