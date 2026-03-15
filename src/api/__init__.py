from src.api.core_api import CoreAPI, CoreAPIError, RetryRequest, SyncRequest


def build_bootstrap_report(*args, **kwargs):
    from src.api.cli import build_bootstrap_report as _build_bootstrap_report

    return _build_bootstrap_report(*args, **kwargs)


def main(*args, **kwargs):
    from src.api.cli import main as _main

    return _main(*args, **kwargs)


__all__ = [
    "build_bootstrap_report",
    "main",
    "CoreAPI",
    "CoreAPIError",
    "RetryRequest",
    "SyncRequest",
]
