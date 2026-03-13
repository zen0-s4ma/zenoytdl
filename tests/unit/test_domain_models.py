import pytest

from src.domain import (
    CompiledArtifact,
    CompiledArtifactFormat,
    DomainState,
    DomainValidationError,
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
    normalize_identifier,
)


@pytest.mark.unit
def test_entity_construction_valid() -> None:
    general = GeneralConfig(id=" Main ", workspace="/tmp/work", library_dir="/tmp/lib")
    post = PostProcessing(
        id="extract",
        kind=PostProcessingKind.EXTRACT_AUDIO,
        parameters={"codec": "mp3"},
    )
    profile = Profile(
        id="music",
        name=" Music Profile ",
        base_options={"quality": "best"},
        postprocessing_ids=(post.id,),
    )
    override = Override(id="ov1", profile_id=profile.id, options={"quality": "medium"})
    subscription = Subscription(
        id="sub1",
        profile_id=profile.id,
        source_kind=SubscriptionSourceKind.CHANNEL,
        source_value="https://example.invalid/channel",
        override_ids=(override.id,),
    )
    artifact = CompiledArtifact(
        id="artifact-1",
        effective_config_id="effective-sub1",
        format=CompiledArtifactFormat.ZENO_INTERNAL,
        payload={"engine": "zenoytdl"},
    )
    job = Job(
        id="job-1",
        job_kind=JobKind.COMPILE,
        status=JobStatus.PENDING,
        effective_config_id="effective-sub1",
        artifact_id=artifact.id,
    )
    state = DomainState(
        general_config=general,
        profiles=(profile,),
        subscriptions=(subscription,),
        effective_configs=(),
        artifacts=(artifact,),
        jobs=(job,),
    )

    assert general.id == "main"
    assert profile.name == "Music Profile"
    assert state.jobs[0].id == "job-1"


@pytest.mark.unit
def test_invariants_raise_errors() -> None:
    with pytest.raises(DomainValidationError):
        normalize_identifier("   ")

    with pytest.raises(DomainValidationError):
        Override(id="ov", profile_id="p1", options={})

    with pytest.raises(DomainValidationError):
        PostProcessing(id="pp", kind=PostProcessingKind.EXTRACT_AUDIO, parameters={})

    with pytest.raises(DomainValidationError):
        Subscription(
            id="sub",
            profile_id="p1",
            source_kind=SubscriptionSourceKind.CHANNEL,
            source_value=" ",
        )


@pytest.mark.unit
def test_equality_and_normalization_are_stable() -> None:
    a = Profile(id="P1", name="One", base_options={"k": "v"})
    b = Profile(id=" p1 ", name="One", base_options={"k": "v"})
    assert a == b


@pytest.mark.unit
def test_domain_state_requires_profiles() -> None:
    with pytest.raises(DomainValidationError):
        DomainState(
            general_config=GeneralConfig(id="g1", workspace="/w", library_dir="/l"),
            profiles=(),
            subscriptions=(),
            effective_configs=(),
            artifacts=(),
            jobs=(),
        )
