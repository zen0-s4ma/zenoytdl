import pytest

from src.domain import (
    CompiledArtifact,
    CompiledArtifactFormat,
    DomainCatalog,
    DomainState,
    GeneralConfig,
    Job,
    JobKind,
    JobStatus,
    Override,
    PostProcessing,
    PostProcessingKind,
    Profile,
    Subscription,
    SubscriptionSourceKind,
    serialize_state,
)


@pytest.mark.regression
def test_hito2_canonical_domain_objects_are_consistent() -> None:
    profile = Profile(
        id="canon-profile",
        name="Canon",
        base_options={"quality": "best"},
        postprocessing_ids=("canon-pp",),
    )
    subscription = Subscription(
        id="canon-sub",
        profile_id=profile.id,
        source_kind=SubscriptionSourceKind.CHANNEL,
        source_value="https://example.invalid/canon",
        override_ids=("canon-ov",),
    )
    postprocessing = PostProcessing(
        id="canon-pp",
        kind=PostProcessingKind.EMBED_THUMBNAIL,
        parameters={"format": "jpg"},
    )
    override = Override(id="canon-ov", profile_id=profile.id, options={"quality": "medium"})

    catalog = DomainCatalog.build(
        general_config=GeneralConfig(id="canon-general", workspace="/w", library_dir="/l"),
        profiles=(profile,),
        subscriptions=(subscription,),
        postprocessings=(postprocessing,),
        overrides=(override,),
    )
    effective = catalog.resolve_effective_config(subscription.id)
    artifact = CompiledArtifact(
        id="canon-artifact",
        effective_config_id=effective.id,
        format=CompiledArtifactFormat.ZENO_INTERNAL,
        payload={"profile_id": effective.profile_id},
    )
    job = Job(
        id="canon-job",
        job_kind=JobKind.SYNC,
        status=JobStatus.PENDING,
        effective_config_id=effective.id,
        artifact_id=artifact.id,
    )
    state = DomainState(
        general_config=catalog.general_config,
        profiles=(profile,),
        subscriptions=(subscription,),
        effective_configs=(effective,),
        artifacts=(artifact,),
        jobs=(job,),
    )

    snapshot = serialize_state(state)
    assert snapshot["profiles"] == ["canon-profile"]
    assert snapshot["subscriptions"] == ["canon-sub"]
    assert snapshot["effective_configs"] == [effective.id]
    assert snapshot["jobs"] == ["canon-job"]
