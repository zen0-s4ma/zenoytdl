from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle
from src.domain import SubscriptionSourceKind


@pytest.mark.integration
def test_loader_builds_domain_catalog_from_parsed_bundle() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito4/valid/medium"))

    catalog = bundle.to_domain_catalog()

    assert catalog.general_config.workspace == "/srv/zeno"
    assert "news" in catalog.profiles
    assert "world-news" in catalog.subscriptions
    assert catalog.subscriptions["world-news"].source_kind == SubscriptionSourceKind.PLAYLIST


@pytest.mark.integration
def test_loader_resolves_relative_and_absolute_paths() -> None:
    relative_bundle = load_parsed_config_bundle(Path("tests/fixtures/hito4/valid/medium"))
    absolute_bundle = load_parsed_config_bundle(Path("tests/fixtures/hito4/valid/medium").resolve())

    assert relative_bundle.general.library_dir == absolute_bundle.general.library_dir
    assert relative_bundle.ytdl_sub_conf.integration_binary.endswith("bin/ytdl-sub")
