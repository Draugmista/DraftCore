from __future__ import annotations

from sqlmodel import func, select

from draftcore.app.models import Asset, ProjectAsset, ReportProject
from draftcore.app.models.enums import OutputFormat, ProjectStatus
from draftcore.app.services.archive_service import ArchiveService
from draftcore.app.services.draft_service import DraftService
from draftcore.app.services.errors import NotFoundError, ValidationError


class ProjectService:
    def __init__(self) -> None:
        self.archive_service = ArchiveService()
        self.draft_service = DraftService()

    def create_project(
        self,
        session,
        *,
        name: str,
        topic: str,
        target_output: str,
        default_status: str,
    ) -> ReportProject:
        if not name.strip():
            raise ValidationError("Project name cannot be empty.")
        if not topic.strip():
            raise ValidationError("Project topic cannot be empty.")
        if target_output != OutputFormat.MARKDOWN.value:
            raise ValidationError("Only markdown target_output is supported in the current MVP.")

        project = ReportProject(
            name=name.strip(),
            topic=topic.strip(),
            target_output=target_output,
            status=ProjectStatus(default_status),
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        return project

    def list_projects(self, session, *, status: str | None = None, limit: int = 20) -> list[ReportProject]:
        statement = select(ReportProject).order_by(ReportProject.created_at.desc()).limit(limit)
        if status:
            try:
                status_value = ProjectStatus(status)
            except ValueError as exc:
                raise ValidationError(f"Invalid project status filter: {status}") from exc
            statement = statement.where(ReportProject.status == status_value)
        return list(session.exec(statement))

    def get_project(self, session, project_id: int) -> ReportProject:
        project = session.get(ReportProject, project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} does not exist.")
        return project

    def get_project_detail(self, session, project_id: int) -> dict[str, object]:
        project = self.get_project(session, project_id)
        asset_count = session.exec(
            select(func.count(Asset.id))
            .join(ProjectAsset, onclause=ProjectAsset.asset_id == Asset.id)
            .where(ProjectAsset.project_id == project_id)
        ).one()
        return {
            "id": project.id,
            "name": project.name,
            "topic": project.topic,
            "target_output": project.target_output,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "asset_count": asset_count,
            "draft_status": self.draft_service.get_project_draft_status(session, project_id),
            "final_report_status": self.archive_service.get_project_final_report_status(session, project_id),
        }
