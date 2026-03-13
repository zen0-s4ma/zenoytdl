import pytest

from src.domain import (
    DomainCatalog,
    DomainValidationError,
    GeneralConfig,
    Override,
    PostProcessing,
    PostProcessingKind,
    Profile,
    Subscription,
    SubscriptionSourceKind,
)


@pytest.mark.integration
def test_profile_subscription_effective_config_relationship() -> None:
    catalog = DomainCatalog.build(
        general_config=GeneralConfig(id="g1", workspace="/w", library_dir="/l"),
        profiles=(
            Profile(
                id="profile-a",
                name="A",
                base_options={"quality": "best"},
                postprocessing_ids=("pp-a",),
            ),
        ),
        subscriptions=(
            Subscription(
                id="sub-a",
                profile_id="profile-a",
                source_kind=SubscriptionSourceKind.CHANNEL,
                source_value="https://example.invalid/channel",
                override_ids=("ov-a",),
            ),
        ),
        postprocessings=(
            PostProcessing(
                id="pp-a",
                kind=PostProcessingKind.CLEANUP_METADATA,
                parameters={"cleanup": True},
            ),
        ),
        overrides=(Override(id="ov-a", profile_id="profile-a", options={"quality": "medium"}),),
    )

    effective = catalog.resolve_effective_config("sub-a")
    assert effective.profile_id == "profile-a"
    assert effective.resolved_options["quality"] == "medium"
    assert effective.resolved_options["source_kind"] == "channel"


@pytest.mark.integration
def test_domain_detects_invalid_cross_reference() -> None:
    with pytest.raises(DomainValidationError):
        DomainCatalog.build(
            general_config=GeneralConfig(id="g1", workspace="/w", library_dir="/l"),
            profiles=(Profile(id="p1", name="P1"),),
            subscriptions=(
                Subscription(
                    id="s1",
                    profile_id="p1",
                    source_kind=SubscriptionSourceKind.CHANNEL,
                    source_value="x",
                    override_ids=("ov1",),
                ),
            ),
            postprocessings=(),
            overrides=(),
        )
