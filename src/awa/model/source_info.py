"""Source information model — tracks the origin format and metadata."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field


@dataclass
class PackageMetadata:
    """Metadata from a .yxwz package.

    Attributes:
        primary_workflow: Name of the primary .yxmd inside the package.
        contained_files: List of file paths within the package.
        total_size_bytes: Total uncompressed size of the package.
    """
    primary_workflow: str = ""
    contained_files: list[str] = dc_field(default_factory=list)
    total_size_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "primary_workflow": self.primary_workflow,
            "contained_files": self.contained_files,
            "total_size_bytes": self.total_size_bytes,
        }


@dataclass
class SourceInfo:
    """Information about the source file that was analyzed.

    Attributes:
        source_format: Detected format ('yxmd', 'yxwz', 'xml').
        original_filename: The filename as uploaded.
        package_metadata: Metadata if source was a .yxwz package.
    """
    source_format: str
    original_filename: str
    package_metadata: PackageMetadata | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "source_format": self.source_format,
            "original_filename": self.original_filename,
        }
        if self.package_metadata is not None:
            d["package_metadata"] = self.package_metadata.to_dict()
        return d
