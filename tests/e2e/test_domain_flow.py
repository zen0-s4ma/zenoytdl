import pytest

from src.domain import (
    DomainCatalog,
    GeneralConfig,
    Override,
    PostProcessing,
    PostProcessingKind,
    Profile,
    Subscription,
    SubscriptionSourceKind,
)


@pytest.mark.e2e
def test_short_domain_flow_profile_subscription_override() -> None:
    catalog = DomainCatalog.build(
        general_config=GeneralConfig(
            id="general-main", workspace="/tmp/work", library_dir="/tmp/lib"
        ),
        profiles=(
            Profile(
                id="music",
                name="Music",
                base_options={"quality": "best"},
                postprocessing_ids=("extract-audio",),
            ),
        ),
        subscriptions=(
            Subscription(
                id="music-sub",
                profile_id="music",
                source_kind=SubscriptionSourceKind.PLAYLIST,
                source_value="https://example.invalid/music",
                override_ids=("ov-music",),
            ),
        ),
        postprocessings=(
            PostProcessing(
                id="extract-audio",
                kind=PostProcessingKind.EXTRACT_AUDIO,
                parameters={"codec": "opus"},
            ),
        ),
        overrides=(Override(id="ov-music", profile_id="music", options={"quality": "medium"}),),
    )

    effective = catalog.resolve_effective_config("music-sub")
    assert effective.subscription_id == "music-sub"
    assert effective.resolved_options["quality"] == "medium"
    assert effective.postprocessings[0].id == "extract-audio"
