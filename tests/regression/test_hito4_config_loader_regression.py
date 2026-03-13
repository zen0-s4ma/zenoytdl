from pathlib import Path

import pytest

from src.config.config_loader import load_parsed_config_bundle


@pytest.mark.regression
def test_hito4_regression_signatures_are_stable() -> None:
    expected = {
        "minimal": "d61926b5417a8212bd077be3a02403917ab91c2897ac05b254a2fe3f74d57708",
        "medium": "2881b89d73c7888f0342a3e67384a48899aa324e58bfeb6bb38dec697cc32a30",
        "complex": "bce02699ea521a57b987296498a5285bf3256cf1f1e129272ea77b3acf2a4ed2",
    }

    for fixture_dir, expected_signature in expected.items():
        bundle = load_parsed_config_bundle(Path("tests/fixtures/hito4/valid") / fixture_dir)
        assert bundle.signature == expected_signature


@pytest.mark.regression
def test_hito4_regression_structural_output_stays_consistent() -> None:
    bundle = load_parsed_config_bundle(Path("tests/fixtures/hito4/valid/complex"))

    snapshot = {
        "profiles": [profile.name for profile in bundle.profiles],
        "subscriptions": [subscription.name for subscription in bundle.subscriptions],
        "source_kinds": [
            bundle.to_domain_catalog().subscriptions[item.name].source_kind.value
            for item in bundle.subscriptions
        ],
    }

    assert snapshot == {
        "profiles": ["archive-video", "audio-daily", "shorts-fast"],
        "subscriptions": ["documentaries", "tech-audio", "quick-shorts"],
        "source_kinds": ["channel", "channel", "playlist"],
    }
