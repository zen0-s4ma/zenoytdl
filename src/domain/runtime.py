from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    available: bool
    detail: str


@dataclass(frozen=True)
class BootstrapReport:
    runtime_workspace: str
    runtime_log_level: str
    config_loaded: bool
    sqlite_ready: bool
    ytdl_sub: DependencyStatus
    ffmpeg: DependencyStatus

    @property
    def ok(self) -> bool:
        return (
            self.config_loaded
            and self.sqlite_ready
            and self.ytdl_sub.available
            and self.ffmpeg.available
        )
