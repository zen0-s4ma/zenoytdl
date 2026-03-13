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
    serialize_catalog,
)


@pytest.mark.unit
def test_internal_serialization_of_catalog() -> None:
    catalog = DomainCatalog.build(
        general_config=GeneralConfig(id="g1", workspace="/w", library_dir="/l"),
        profiles=(
            Profile(
                id="p1",
                name="Profile 1",
                base_options={"quality": "best"},
                postprocessing_ids=("pp1",),
            ),
        ),
        subscriptions=(
            Subscription(
                id="s1",
                profile_id="p1",
                source_kind=SubscriptionSourceKind.PLAYLIST,
                source_value="https://example.invalid/playlist",
                override_ids=("o1",),
            ),
        ),
        postprocessings=(
            PostProcessing(
                id="pp1",
                kind=PostProcessingKind.EMBED_THUMBNAIL,
                parameters={"format": "jpg"},
            ),
        ),
        overrides=(Override(id="o1", profile_id="p1", options={"quality": "medium"}),),
    )

    payload = serialize_catalog(catalog)
    assert payload["profiles"] == ["p1"]
    assert payload["subscriptions"] == ["s1"]
