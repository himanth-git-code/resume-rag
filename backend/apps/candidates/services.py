from dataclasses import asdict, dataclass

from apps.resume_parser.services import ResumeProcessingService


@dataclass(frozen=True)
class DashboardState:
    has_resume: bool
    latest_parse_status: str | None
    latest_job_id: int | None
    has_profile: bool


class CandidateDashboardService:
    """Summarises where the candidate is in onboarding, for the dashboard."""

    @staticmethod
    def get_state(user) -> dict:
        job = ResumeProcessingService.latest_job_for(user)
        return asdict(
            DashboardState(
                has_resume=job is not None,
                latest_parse_status=job.status if job else None,
                latest_job_id=job.pk if job else None,
                # Structured profile arrives in the next sub-slice.
                has_profile=False,
            )
        )
