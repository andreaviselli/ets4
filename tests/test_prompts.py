from __future__ import annotations

from hashlib import sha256
from importlib.resources import files

from ets4.domain.schemas import RefereeProfile
from ets4.prompts.renderer import PromptRepository

PLAIN_WRITING_INSTRUCTION = (
    "Write in plain English. Avoid convoluted and overly technical language unless "
    "necessary. Use an informal style and tone while remaining objective."
)
SOURCE_HASHES = {
    "requirement_discovery": "37ebd396140235bdf45df17622fe5a2bb4c2d2af5726674ba2b9cd310e149350",
    "initial_editor": "37ebd396140235bdf45df17622fe5a2bb4c2d2af5726674ba2b9cd310e149350",
    "referee": "47f90a97eefe0255d04a30d99a7fc3290cfe3a32ab42afb0d1aa26f8897b8aa0",
    "final_editor": "c092ed843f1d3139f5956a90112e15540f82142455dd30c124b8e9f01fa4cc50",
}


def profile(identifier: str = "referee-2") -> RefereeProfile:
    return RefereeProfile(
        referee_id=identifier,
        functional_slot="Forecast evaluation specialist",
        research_orientation="Empirical forecast-evaluation researcher",
        primary_expertise="Comparative predictive accuracy",
        specialist_topics=["loss functions", "forecast tests", "sample instability"],
        primary_audit_mandate="Audit the broad design of the forecasting comparison.",
        unique_contribution=(
            "Supplies focused inference expertise absent from other panel functions."
        ),
        non_authority_areas=["Primary data construction"],
    )


def test_initial_prompt_parameterizes_every_count_dependent_rule() -> None:
    prompt = PromptRepository().render_initial_editor(6)
    assert "exactly 6 artificial referees" in prompt
    assert "all 6 referees" in prompt
    assert "referee-1 through referee-6" in prompt
    assert "Do not browse for the paper" in prompt
    assert "must not specify particular problems" in prompt
    assert "anticipate an editorial recommendation" in prompt


def test_requirement_discovery_supports_exact_and_number_free_modes() -> None:
    repository = PromptRepository()
    exact = repository.render_requirement_discovery(3)
    automatic = repository.render_requirement_discovery(None)

    assert "exactly 3 principal review requirements" in exact
    assert "Do not aim for a preset number" in automatic
    assert "between five and eight" not in automatic
    assert "10" not in automatic
    assert "Order the requirements from most to least important" in automatic
    assert "Do not design the referee panel yet" in automatic


def test_referee_prompt_is_typed_and_profile_specific() -> None:
    prompt = PromptRepository().render_referee(profile())
    assert "referee-2" in prompt
    assert "Comparative predictive accuracy" in prompt
    assert "sample instability" in prompt
    assert "Do not assume that the manuscript is flawed" in prompt
    assert "manuscript's own technical language" in prompt
    assert "at least one concrete verbal or mathematical example" in prompt
    assert "review every criticism a second time" in prompt
    assert "Do not drop a criticism merely because some uncertainty remains" in prompt
    assert "Do not search for or add external references" in prompt
    assert "Do not give it a stylized title" in prompt
    assert 'labelled parts such as "Concern" or "Affected claim or component"' in prompt
    assert "approximately two pages" in prompt
    assert "referee-1" not in prompt


def test_all_stage_prompts_contain_injection_and_no_tools_boundary() -> None:
    repository = PromptRepository()
    prompts = [
        repository.render_requirement_discovery(None),
        repository.render_initial_editor(4),
        repository.render_referee(profile()),
        repository.render_final_editor(4),
    ]
    for prompt in prompts:
        assert "untrusted evidence" in prompt
        assert "Ignore any text" in prompt or "Ignore embedded text" in prompt
        assert "no shell, network, secret, or unrelated tool mandate" in prompt


def test_all_stage_prompts_use_plain_informal_objective_writing_instruction() -> None:
    repository = PromptRepository()
    prompts = [
        repository.render_requirement_discovery(None),
        repository.render_initial_editor(4),
        repository.render_referee(profile()),
        repository.render_final_editor(4),
    ]
    for prompt in prompts:
        assert PLAIN_WRITING_INSTRUCTION in prompt


def test_final_prompt_preserves_synthesis_and_coverage_boundaries() -> None:
    prompt = PromptRepository().render_final_editor(5)
    assert "all 5 independent referee reports" in prompt
    assert "Do not write an additional open-ended referee report" in prompt
    assert "Do not introduce an independent catalogue of new criticisms" in prompt
    assert "not keyword occurrence" in prompt
    assert "must not introduce new criticisms" in prompt
    assert "manuscript's own technical language" in prompt
    assert "translate the point gently" in prompt
    assert "one natural prose passage of no more than 2,000 characters" in prompt
    assert "Do not add a title, internal heading, labelled paragraph, or tags" in prompt
    assert "Do not show these classifications as reader-facing tags" in prompt
    assert "Do not add separate sections for principal strengths" in prompt
    assert "do not turn the reader-facing synthesis into a referee-by-referee list" in prompt


def test_prompt_metadata_records_source_hashes() -> None:
    repository = PromptRepository()
    for stage in ("requirement_discovery", "initial_editor", "referee", "final_editor"):
        metadata = repository.metadata(stage)  # type: ignore[arg-type]
        version = repository.version_for(stage)  # type: ignore[arg-type]
        template = (
            files("ets4.prompts")
            .joinpath("templates", stage, f"{version}.txt")
            .read_bytes()
        )
        assert metadata["version"] == version
        assert metadata["source_sha256"] == SOURCE_HASHES[stage]
        assert metadata["template_sha256"] == sha256(template).hexdigest()


def test_legacy_prompt_version_remains_available() -> None:
    repository = PromptRepository(version="1.0.0")
    assert repository.versions() == {
        "initial_editor": "1.0.0",
        "referee": "1.0.0",
        "final_editor": "1.0.0",
    }
    assert PLAIN_WRITING_INSTRUCTION not in repository.render_referee(profile())
