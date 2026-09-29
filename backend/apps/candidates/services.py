from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DashboardState:
    has_resume: bool
    latest_parse_status: str | None
    has_profile: bool


class CandidateDashboardService:
    """Summarises where the candidate is in onboarding, for the dashboard."""

    @staticmethod
    def get_state(user) -> dict:
        # Resume and profile data arrive in later sub-slices; until then a new
        # candidate has neither.
        return asdict(DashboardState(has_resume=False, latest_parse_status=None, has_profile=False))
