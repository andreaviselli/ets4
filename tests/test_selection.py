from datetime import date
from dataclasses import replace

from ets4.config import load_config
from ets4.manifest import create_manifest
from ets4.selection import select_full_review_candidates
from ets4.store.db import connect, init_db, insert_manifest, upsert_paper, upsert_source


def test_selection_respects_full_review_budget(tmp_path) -> None:
    base_config = load_config("config/feeds.example.toml")
    config = replace(
        base_config,
        issue=replace(base_config.issue, max_papers_to_full_review=2),
    )
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_source(conn, config.sources[0])
        titles = (
            "Oil price forecasting with probabilistic models",
            "Inflation nowcasting from real-time indicators",
            "GDP growth prediction with mixed-frequency data",
            "Electricity demand forecasting with weather features",
        )
        for idx, (title, score) in enumerate(zip(titles, (9.0, 8.5, 8.0, 7.5)), start=1):
            paper_id = f"paper-{idx}"
            upsert_paper(
                conn,
                paper_id=paper_id,
                title=title,
                canonical_url=f"https://example.test/{paper_id}",
                abstract="Forecasting GDP.",
                source_id=config.sources[0].id,
            )
            conn.execute(
                """
                INSERT INTO triage_reviews (
                    paper_id, run_id, provider, decision, category_hint,
                    forecasting_signal, economic_signal, score, confidence, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    manifest.run_id,
                    "fake",
                    "assign_reviewers",
                    "directly_relevant",
                    "explicit",
                    "explicit",
                    score,
                    0.75,
                    "fixture",
                ),
            )

        selection = select_full_review_candidates(conn, run_id=manifest.run_id, config=config)

        assert selection.candidate_count == 4
        assert selection.selected_count == config.issue.max_papers_to_full_review
        ranks = conn.execute(
            """
            SELECT paper_id FROM candidate_selections
            WHERE run_id = ? AND selection_stage = 'full_review'
            ORDER BY rank ASC
            """,
            (manifest.run_id,),
        ).fetchall()
        assert [row["paper_id"] for row in ranks[:2]] == ["paper-1", "paper-2"]
