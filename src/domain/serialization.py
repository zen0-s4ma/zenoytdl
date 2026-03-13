from __future__ import annotations

from src.domain.catalog import DomainCatalog
from src.domain.models import DomainState


def serialize_catalog(catalog: DomainCatalog) -> dict[str, object]:
    return {
        "general_config_id": catalog.general_config.id,
        "profiles": list(catalog.profiles.keys()),
        "subscriptions": list(catalog.subscriptions.keys()),
        "postprocessings": list(catalog.postprocessings.keys()),
        "overrides": list(catalog.overrides.keys()),
    }


def serialize_state(state: DomainState) -> dict[str, object]:
    return {
        "general_config_id": state.general_config.id,
        "profiles": [profile.id for profile in state.profiles],
        "subscriptions": [subscription.id for subscription in state.subscriptions],
        "effective_configs": [effective_config.id for effective_config in state.effective_configs],
        "artifacts": [artifact.id for artifact in state.artifacts],
        "jobs": [job.id for job in state.jobs],
    }
