from datetime import date
from dataclasses import replace
import json

from ets4.config import load_config
from ets4.manifest import create_manifest
from ets4.selection import select_full_review_candidates, select_publication_candidates
from ets4.store.db import (
    connect,
    init_db,
    insert_document,
    insert_manifest,
    upsert_paper,
    upsert_source,
)


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


def test_full_review_selection_can_require_successful_document(tmp_path) -> None:
    base_config = load_config("config/feeds.example.toml")
    config = replace(
        base_config,
        issue=replace(base_config.issue, max_papers_to_full_review=5),
    )
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        upsert_source(conn, config.sources[0])
        titles = (
            "Inflation forecasting with a useful empirical angle",
            "Energy demand nowcasting with a useful empirical angle",
            "GDP forecast evaluation with a useful empirical angle",
        )
        for idx, (title, status) in enumerate(zip(titles, ("ok", "error", None)), start=1):
            paper_id = f"paper-{idx}"
            upsert_paper(
                conn,
                paper_id=paper_id,
                title=title,
                canonical_url=f"https://example.test/{paper_id}",
                abstract="Applied forecasting with a useful empirical angle.",
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
                    "openai",
                    "assign_reviewers",
                    "directly_relevant",
                    "explicit",
                    "explicit",
                    8.0 - idx * 0.1,
                    0.75,
                    "fixture",
                ),
            )
            if status is not None:
                insert_document(
                    conn,
                    document_id=f"doc-{paper_id}",
                    paper_id=paper_id,
                    run_id=manifest.run_id,
                    source_uri=f"https://example.test/{paper_id}.pdf",
                    content_type="application/pdf",
                    content_sha256=f"sha-{paper_id}",
                    page_count=2,
                    status=status,
                )

        selection = select_full_review_candidates(
            conn,
            run_id=manifest.run_id,
            config=config,
            require_successful_document=True,
        )

        assert selection.candidate_count == 1
        assert selection.selected_count == 1
        rows = conn.execute(
            """
            SELECT paper_id FROM candidate_selections
            WHERE run_id = ? AND selection_stage = 'full_review'
            """,
            (manifest.run_id,),
        ).fetchall()
        assert [row["paper_id"] for row in rows] == ["paper-1"]


def test_publication_selection_does_not_publish_watchlist_as_short_mention(tmp_path) -> None:
    base_config = load_config("config/feeds.example.toml")
    config = replace(
        base_config,
        issue=replace(base_config.issue, max_deep_dive_drafts=0, max_short_mentions=5),
    )
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        for paper_id, title, decision in (
            ("paper-1", "Applied forecast note", "short_mention"),
            ("paper-2", "Method watchlist item", "watchlist"),
        ):
            upsert_paper(
                conn,
                paper_id=paper_id,
                title=title,
                canonical_url=f"https://example.test/{paper_id}",
                abstract="Forecasting GDP.",
            )
            conn.execute(
                """
                INSERT INTO review_dossiers (
                    id, paper_id, run_id, document_id, evidence_count, dossier_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"dossier-{paper_id}",
                    paper_id,
                    manifest.run_id,
                    None,
                    6,
                    "{}",
                    "ok",
                ),
            )
            conn.execute(
                """
                INSERT INTO editorial_decisions (
                    id, paper_id, run_id, dossier_id, provider, decision,
                    deep_dive_score, confidence, memo_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"decision-{paper_id}",
                    paper_id,
                    manifest.run_id,
                    f"dossier-{paper_id}",
                    "fake",
                    decision,
                    6.0,
                    0.7,
                    "{}",
                    "ok",
                ),
            )

        selection = select_publication_candidates(conn, run_id=manifest.run_id, config=config)

        assert selection.deep_dive_selected_count == 0
        assert selection.short_mention_selected_count == 1
        short_rows = conn.execute(
            """
            SELECT paper_id FROM candidate_selections
            WHERE run_id = ? AND selection_stage = 'short_mention'
            """,
            (manifest.run_id,),
        ).fetchall()
        assert [row["paper_id"] for row in short_rows] == ["paper-1"]


def test_publication_selection_keeps_short_mentions_out_of_deep_dive_slots(tmp_path) -> None:
    base_config = load_config("config/feeds.example.toml")
    config = replace(
        base_config,
        issue=replace(base_config.issue, max_deep_dive_drafts=2, max_short_mentions=2),
    )
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        for paper_id, title, decision in (
            ("paper-1", "Main applied forecast", "full_deep_dive"),
            ("paper-2", "Applied note", "short_mention"),
        ):
            upsert_paper(
                conn,
                paper_id=paper_id,
                title=title,
                canonical_url=f"https://example.test/{paper_id}",
                abstract="Forecasting GDP.",
            )
            conn.execute(
                """
                INSERT INTO review_dossiers (
                    id, paper_id, run_id, document_id, evidence_count, dossier_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"dossier-{paper_id}",
                    paper_id,
                    manifest.run_id,
                    None,
                    6,
                    "{}",
                    "ok",
                ),
            )
            conn.execute(
                """
                INSERT INTO editorial_decisions (
                    id, paper_id, run_id, dossier_id, provider, decision,
                    deep_dive_score, confidence, memo_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"decision-{paper_id}",
                    paper_id,
                    manifest.run_id,
                    f"dossier-{paper_id}",
                    "fake",
                    decision,
                    8.0,
                    0.8,
                    "{}",
                    "ok",
                ),
            )

        selection = select_publication_candidates(conn, run_id=manifest.run_id, config=config)

        assert selection.deep_dive_selected_count == 1
        assert selection.short_mention_selected_count == 1
        deep_rows = conn.execute(
            """
            SELECT paper_id FROM candidate_selections
            WHERE run_id = ? AND selection_stage = 'deep_dive_draft'
            """,
            (manifest.run_id,),
        ).fetchall()
        short_rows = conn.execute(
            """
            SELECT paper_id FROM candidate_selections
            WHERE run_id = ? AND selection_stage = 'short_mention'
            """,
            (manifest.run_id,),
        ).fetchall()
        assert [row["paper_id"] for row in deep_rows] == ["paper-1"]
        assert [row["paper_id"] for row in short_rows] == ["paper-2"]


def test_publication_selection_uses_explicit_publication_track(tmp_path) -> None:
    base_config = load_config("config/feeds.example.toml")
    config = replace(
        base_config,
        issue=replace(base_config.issue, max_deep_dive_drafts=2, max_short_mentions=2),
    )
    manifest = create_manifest(config, date(2026, 6, 8))

    with connect(tmp_path / "ets4.sqlite") as conn:
        init_db(conn)
        insert_manifest(conn, manifest)
        for paper_id, title, track in (
            ("paper-1", "Main applied forecast", "deep_dive"),
            ("paper-2", "Applied method note", "applied_note"),
        ):
            upsert_paper(
                conn,
                paper_id=paper_id,
                title=title,
                canonical_url=f"https://example.test/{paper_id}",
                abstract="Forecasting GDP.",
            )
            conn.execute(
                """
                INSERT INTO review_dossiers (
                    id, paper_id, run_id, document_id, evidence_count, dossier_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"dossier-{paper_id}",
                    paper_id,
                    manifest.run_id,
                    None,
                    6,
                    "{}",
                    "ok",
                ),
            )
            conn.execute(
                """
                INSERT INTO editorial_decisions (
                    id, paper_id, run_id, dossier_id, provider, decision,
                    deep_dive_score, confidence, memo_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"decision-{paper_id}",
                    paper_id,
                    manifest.run_id,
                    f"dossier-{paper_id}",
                    "fake",
                    "full_deep_dive",
                    8.0,
                    0.8,
                    json.dumps({"publication_track": track}),
                    "ok",
                ),
            )

        selection = select_publication_candidates(conn, run_id=manifest.run_id, config=config)

        assert selection.deep_dive_selected_count == 1
        assert selection.short_mention_selected_count == 1
        deep_rows = conn.execute(
            """
            SELECT paper_id FROM candidate_selections
            WHERE run_id = ? AND selection_stage = 'deep_dive_draft'
            """,
            (manifest.run_id,),
        ).fetchall()
        short_rows = conn.execute(
            """
            SELECT paper_id FROM candidate_selections
            WHERE run_id = ? AND selection_stage = 'short_mention'
            """,
            (manifest.run_id,),
        ).fetchall()
        assert [row["paper_id"] for row in deep_rows] == ["paper-1"]
        assert [row["paper_id"] for row in short_rows] == ["paper-2"]
