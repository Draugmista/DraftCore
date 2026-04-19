from __future__ import annotations

from sqlalchemy import delete
from sqlmodel import select

from draftcore.app.models import Asset, AssetCollection, AssetCollectionItem, ProjectAsset
from draftcore.app.models.enums import SourceCategory
from draftcore.app.services.errors import NotFoundError, ValidationError
from draftcore.app.services.project_service import ProjectService


DEFAULT_COLLECTION_USAGE_NOTES = {
    SourceCategory.RAW: "background reference",
    SourceCategory.TEMPLATE: "structure template",
    SourceCategory.REFERENCE: "history reference",
}


def derive_collection_usage_note(project_asset: ProjectAsset, asset: Asset) -> str:
    if project_asset.relation_note and project_asset.relation_note.strip():
        return project_asset.relation_note.strip()
    if asset.usage_note and asset.usage_note.strip():
        return asset.usage_note.strip()
    return DEFAULT_COLLECTION_USAGE_NOTES[asset.source_category]


def derive_collection_candidate_flag(project_asset: ProjectAsset, asset: Asset) -> bool:
    if asset.source_category in {SourceCategory.TEMPLATE, SourceCategory.REFERENCE}:
        return True
    if asset.source_category == SourceCategory.RAW:
        return bool(
            (project_asset.relation_note and project_asset.relation_note.strip())
            or (asset.usage_note and asset.usage_note.strip())
        )
    return False


class CollectionService:
    def __init__(self) -> None:
        self.project_service = ProjectService()

    def build_collection(
        self,
        session,
        *,
        project_id: int,
        name: str,
        purpose: str,
    ) -> dict[str, object]:
        project = self.project_service.get_project(session, project_id)
        collection_name = self._validate_text(name, field_name="Collection name")
        collection_purpose = self._validate_text(purpose, field_name="Collection purpose")

        project_assets = self._load_project_assets(session, project_id)
        if not project_assets:
            raise ValidationError(
                f"Project {project_id} has no registered assets and cannot build a collection yet."
            )

        collection = session.exec(
            select(AssetCollection).where(
                AssetCollection.project_id == project_id,
                AssetCollection.name == collection_name,
            )
        ).first()
        created = False
        if collection is None:
            collection = AssetCollection(
                project_id=project.id,
                name=collection_name,
                purpose=collection_purpose,
            )
            session.add(collection)
            session.flush()
            created = True
        else:
            collection.purpose = collection_purpose
            session.add(collection)
            session.flush()
            session.exec(
                delete(AssetCollectionItem).where(AssetCollectionItem.collection_id == collection.id)
            )

        for link, asset in project_assets:
            session.add(
                AssetCollectionItem(
                    collection_id=collection.id,
                    asset_id=asset.id,
                    usage_note=derive_collection_usage_note(link, asset),
                    is_candidate=derive_collection_candidate_flag(link, asset),
                )
            )

        session.commit()
        detail = self.get_collection_detail(session, collection.id)
        detail["created"] = created
        return detail

    def get_collection_detail(self, session, collection_id: int) -> dict[str, object]:
        collection = session.get(AssetCollection, collection_id)
        if collection is None:
            raise NotFoundError(f"Collection {collection_id} does not exist.")

        items = self._load_collection_items(session, collection_id)
        asset_items = [self._serialize_collection_item(asset, item) for item, asset in items]
        candidate_count = sum(1 for item in asset_items if item["is_candidate"])
        asset_count = len(asset_items)
        covered_count = sum(1 for item in asset_items if item["usage_note"])

        return {
            "id": collection.id,
            "project_id": collection.project_id,
            "name": collection.name,
            "purpose": collection.purpose,
            "created_at": collection.created_at,
            "asset_count": asset_count,
            "candidate_count": candidate_count,
            "collected_only_count": asset_count - candidate_count,
            "usage_note_coverage": {
                "covered": covered_count,
                "total": asset_count,
                "ratio": round(covered_count / asset_count, 4) if asset_count else 0.0,
            },
            "items": asset_items,
        }

    def _load_project_assets(self, session, project_id: int) -> list[tuple[ProjectAsset, Asset]]:
        statement = (
            select(ProjectAsset, Asset)
            .join(Asset, onclause=ProjectAsset.asset_id == Asset.id)
            .where(ProjectAsset.project_id == project_id)
            .order_by(Asset.created_at.asc(), Asset.id.asc())
        )
        return list(session.exec(statement).all())

    def _load_collection_items(
        self,
        session,
        collection_id: int,
    ) -> list[tuple[AssetCollectionItem, Asset]]:
        statement = (
            select(AssetCollectionItem, Asset)
            .join(Asset, onclause=AssetCollectionItem.asset_id == Asset.id)
            .where(AssetCollectionItem.collection_id == collection_id)
            .order_by(Asset.created_at.asc(), Asset.id.asc())
        )
        return list(session.exec(statement).all())

    def _serialize_collection_item(
        self,
        asset: Asset,
        item: AssetCollectionItem,
    ) -> dict[str, object]:
        return {
            "asset_id": asset.id,
            "asset_name": asset.name,
            "source_category": asset.source_category,
            "usage_note": item.usage_note,
            "is_candidate": item.is_candidate,
            "ingestion_status": asset.ingestion_status,
        }

    def _validate_text(self, raw_value: str, *, field_name: str) -> str:
        value = raw_value.strip()
        if not value:
            raise ValidationError(f"{field_name} cannot be empty.")
        return value
