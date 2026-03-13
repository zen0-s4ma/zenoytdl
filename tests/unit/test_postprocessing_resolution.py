from pathlib import Path

import pytest

from src.config import load_parsed_config_bundle
from src.config.effective_resolution import EffectiveResolutionError, resolve_effective_configs


@pytest.mark.unit
def test_postprocessing_types_and_subscription_adjustments_are_resolved() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito8/valid/full-flow"))

    effective = resolve_effective_configs(bundle)
    first = next(item for item in effective if item.subscription_id == "sub-video")

    kinds = [item.kind.value for item in first.postprocessings]
    assert kinds == ["embed_metadata", "export_info_json", "metadata_text"]

    text_pp = next(item for item in first.postprocessings if item.kind.value == "metadata_text")
    assert text_pp.parameters["filename"] == "custom-metadata.txt"
    assert text_pp.parameter_origins["filename"].endswith("postprocessings[0]")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fixture_dir", "message"),
    [
        ("tests/fixtures/hito8/invalid/embed-without-metadata", "embed_metadata requiere"),
        ("tests/fixtures/hito8/invalid/max-duration-audio", "max_duration no es compatible"),
        (
            "tests/fixtures/hito8/invalid/metadata-json-conflict",
            "incompatible con export_info_json",
        ),
    ],
)
def test_postprocessing_compatibility_rules_are_enforced(fixture_dir: str, message: str) -> None:
    bundle = load_parsed_config_bundle(Path(fixture_dir))

    with pytest.raises(EffectiveResolutionError, match=message):
        resolve_effective_configs(bundle)


@pytest.mark.unit
def test_max_duration_requires_seconds_parameter(tmp_path: Path) -> None:
    source = Path("tests/fixtures/hito8/valid/pattern-max-duration")
    for name in ("general.yaml", "profiles.yaml", "subscriptions.yaml", "ytdl-sub-conf.yaml"):
        (tmp_path / name).write_text((source / name).read_text(encoding="utf-8"), encoding="utf-8")

    (tmp_path / "subscriptions.yaml").write_text(
        "subscriptions:\n"
        "  - name: pp-sub\n"
        "    profile: pp-profile\n"
        "    sources:\n"
        "      - playlist_shorts\n"
        "    postprocessings:\n"
        "      - type: max_duration\n",
        encoding="utf-8",
    )

    bundle = load_parsed_config_bundle(tmp_path)
    with pytest.raises(EffectiveResolutionError, match="parameters.seconds"):
        resolve_effective_configs(bundle)
