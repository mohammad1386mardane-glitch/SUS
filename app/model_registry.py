import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import joblib
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ml_features import FEATURE_NAMES


class ModelMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int = Field(gt=0)
    created_at: datetime
    model_type: str = Field(min_length=1)
    feature_names: tuple[str, ...] = Field(min_length=1)
    normal_rows: int = Field(ge=2)
    suspicious_rows: int = Field(ge=1)
    random_state: int
    contamination: float = Field(gt=0, le=0.5)

    @field_validator("created_at")
    @classmethod
    def require_aware_created_at(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class _RegistryManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int = Field(gt=0)
    artifact: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class RegisteredModel:
    artifact_path: Path
    metadata_path: Path
    metadata: ModelMetadata


class ModelRegistry:
    def __init__(self, base_path: Path) -> None:
        if not base_path.suffix:
            raise ValueError("model registry base path must have a file extension")
        self.base_path = base_path

    @property
    def manifest_path(self) -> Path:
        return self.base_path.with_suffix(".json")

    def register(
        self,
        model: object,
        *,
        model_type: str,
        normal_rows: int,
        suspicious_rows: int,
        random_state: int,
        contamination: float,
        feature_names: tuple[str, ...] = FEATURE_NAMES,
    ) -> RegisteredModel:
        latest = self.latest()
        versions = self._existing_versions()
        if latest is not None:
            versions.append(latest.metadata.version)
        version = max(versions, default=0) + 1
        artifact_path = self._artifact_path(version)
        metadata_path = artifact_path.with_suffix(".json")
        metadata = ModelMetadata(
            version=version,
            created_at=datetime.now(UTC),
            model_type=model_type,
            feature_names=feature_names,
            normal_rows=normal_rows,
            suspicious_rows=suspicious_rows,
            random_state=random_state,
            contamination=contamination,
        )
        manifest = _RegistryManifest(version=version, artifact=artifact_path.name)

        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        _dump_model_atomically(model, artifact_path)
        _write_text_atomically(metadata_path, metadata.model_dump_json(indent=2))
        _write_text_atomically(
            self.manifest_path,
            manifest.model_dump_json(indent=2),
        )
        return RegisteredModel(
            artifact_path=artifact_path,
            metadata_path=metadata_path,
            metadata=metadata,
        )

    def latest(self) -> RegisteredModel | None:
        if not self.manifest_path.exists():
            return None

        manifest = _RegistryManifest.model_validate_json(
            self.manifest_path.read_text(encoding="utf-8")
        )
        artifact_path = self._artifact_path(manifest.version)
        if manifest.artifact != artifact_path.name:
            raise ValueError("registered artifact name does not match its version")
        metadata_path = artifact_path.with_suffix(".json")
        if not artifact_path.is_file():
            raise FileNotFoundError(
                f"registered model artifact is missing: {artifact_path}"
            )
        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"registered model metadata is missing: {metadata_path}"
            )

        metadata = ModelMetadata.model_validate_json(
            metadata_path.read_text(encoding="utf-8")
        )
        if metadata.version != manifest.version:
            raise ValueError(
                "registered model metadata version does not match manifest"
            )
        return RegisteredModel(
            artifact_path=artifact_path,
            metadata_path=metadata_path,
            metadata=metadata,
        )

    def _existing_versions(self) -> list[int]:
        pattern = re.compile(
            rf"^{re.escape(self.base_path.stem)}-v(\d+)"
            rf"{re.escape(self.base_path.suffix)}$"
        )
        versions: list[int] = []
        for artifact_path in self.base_path.parent.glob(
            f"{self.base_path.stem}-v*{self.base_path.suffix}"
        ):
            match = pattern.fullmatch(artifact_path.name)
            if match is not None:
                versions.append(int(match.group(1)))
        return versions

    def _artifact_path(self, version: int) -> Path:
        return self.base_path.with_name(
            f"{self.base_path.stem}-v{version:04d}{self.base_path.suffix}"
        )


def _dump_model_atomically(model: object, artifact_path: Path) -> None:
    temporary_path = _temporary_path(artifact_path)
    try:
        joblib.dump(model, temporary_path)
        temporary_path.replace(artifact_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _write_text_atomically(path: Path, contents: str) -> None:
    temporary_path = _temporary_path(path)
    try:
        temporary_path.write_text(contents, encoding="utf-8")
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.{uuid4().hex}.tmp")
