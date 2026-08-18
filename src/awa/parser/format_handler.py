"""Format handler and validation for .yxmd, .xml, and .yxwz files.

Handles format detection, security checks, package extraction, and
structural XML validation. Untrusted input is validated deterministically.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from awa.model.source_info import SourceInfo, PackageMetadata


class FormatValidationError(Exception):
    """Raised when an uploaded file fails format or security validation."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# Security limits for package inspection
MAX_PACKAGE_ENTRIES = 100
MAX_PACKAGE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


def detect_format(filename: str, content: bytes) -> str:
    """Detect file format using extension and magic bytes.

    Returns: 'yxmd', 'yxwz', 'xml', or 'unknown'
    """
    ext = Path(filename).suffix.lower()

    # 1. Check ZIP magic bytes: PK\x03\x04
    if len(content) >= 4 and content[:4] == b"PK\x03\x04":
        if ext in (".yxwz", ".zip"):
            return "yxwz"
        return "yxwz"

    # 2. Check XML start markers
    stripped = content.lstrip()
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<AlteryxDocument") or (stripped.startswith(b"<") and b"yxmdVer" in content[:200]):
        if ext == ".yxwz":
            # XML file incorrectly named .yxwz
            return "xml"
        if ext == ".xml":
            return "xml"
        return "yxmd"

    # Fallback to extension if content begins with standard XML tag
    if stripped.startswith(b"<"):
        if ext == ".xml":
            return "xml"
        if ext == ".yxmd":
            return "yxmd"

    return "unknown"


def validate_alteryx_xml_structure(content: bytes) -> None:
    """Validate that the XML content represents a valid Alteryx workflow.

    Raises:
        FormatValidationError: If XML is malformed or not an Alteryx workflow.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise FormatValidationError(
            "MALFORMED_XML",
            f"The uploaded file is not valid XML: {e}",
        )

    # Check for Alteryx root tag or required child elements
    tag = root.tag
    if "AlteryxDocument" not in tag and "Alteryx" not in tag:
        # Check if it has Nodes and Connections children
        has_nodes = root.find(".//Nodes") is not None
        has_connections = root.find(".//Connections") is not None
        if not (has_nodes and has_connections):
            raise FormatValidationError(
                "UNRECOGNIZED_WORKFLOW_XML",
                "The XML document is not recognized as an Alteryx workflow. "
                "Expected <AlteryxDocument> root or <Nodes>/<Connections> hierarchy.",
            )

    # Must contain at least one of Properties, Nodes, or yxmdVer attribute
    has_nodes_elem = root.find(".//Nodes") is not None
    has_version = bool(root.get("yxmdVer"))
    has_props = root.find(".//Properties") is not None

    if not (has_nodes_elem or has_version or has_props):
        raise FormatValidationError(
            "UNRECOGNIZED_WORKFLOW_XML",
            "The XML document lacks standard Alteryx workflow structure (missing Nodes/Properties).",
        )


def handle_upload(
    filename: str,
    content: bytes,
    temp_dir: Path,
) -> tuple[Path, SourceInfo]:
    """Process an uploaded file, validate it, extract if needed, and return primary workflow path.

    Args:
        filename: Original uploaded filename.
        content: Raw bytes of the uploaded file.
        temp_dir: Directory where temporary files can be written securely.

    Returns:
        tuple of (Path to primary .yxmd file, SourceInfo)

    Raises:
        FormatValidationError: On any validation or security failure.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    fmt = detect_format(filename, content)

    if fmt == "unknown":
        raise FormatValidationError(
            "UNSUPPORTED_FORMAT",
            f"File '{filename}' is not a recognized Alteryx workflow format. Supported: .yxmd, .yxwz, .xml",
        )

    if fmt == "yxwz":
        return _extract_and_validate_yxwz(filename, content, temp_dir)

    # For .yxmd and .xml: validate XML structure
    validate_alteryx_xml_structure(content)

    # Write to temp file for parsing
    target_path = temp_dir / Path(filename).name
    if not target_path.name.endswith((".yxmd", ".xml")):
        target_path = target_path.with_suffix(".yxmd")
    target_path.write_bytes(content)

    source_info = SourceInfo(
        source_format=fmt,
        original_filename=filename,
        package_metadata=None,
    )
    return target_path, source_info


def _extract_and_validate_yxwz(
    filename: str,
    content: bytes,
    temp_dir: Path,
) -> tuple[Path, SourceInfo]:
    """Safely inspect and extract primary .yxmd from a .yxwz package."""
    pkg_path = temp_dir / "package_upload.zip"
    pkg_path.write_bytes(content)

    try:
        with zipfile.ZipFile(pkg_path, "r") as zf:
            infolist = zf.infolist()

            # Security checks
            if len(infolist) > MAX_PACKAGE_ENTRIES:
                raise FormatValidationError(
                    "PACKAGE_TOO_LARGE",
                    f"Package contains {len(infolist)} files (maximum allowed is {MAX_PACKAGE_ENTRIES}).",
                )

            total_size = sum(info.file_size for info in infolist)
            if total_size > MAX_PACKAGE_SIZE_BYTES:
                raise FormatValidationError(
                    "PACKAGE_TOO_LARGE",
                    f"Package uncompressed size ({total_size} bytes) exceeds limit ({MAX_PACKAGE_SIZE_BYTES} bytes).",
                )

            contained_files: list[str] = []
            primary_yxmd_entry: zipfile.ZipInfo | None = None

            for info in infolist:
                entry_name = info.filename
                # Path traversal check
                if ".." in entry_name or entry_name.startswith(("/", "\\")):
                    raise FormatValidationError(
                        "SECURITY_PATH_TRAVERSAL",
                        f"Potentially unsafe path in package entry: '{entry_name}'",
                    )

                contained_files.append(entry_name)

                # Identify candidate primary workflow
                if entry_name.lower().endswith(".yxmd") and primary_yxmd_entry is None:
                    primary_yxmd_entry = info

            if primary_yxmd_entry is None:
                raise FormatValidationError(
                    "NO_WORKFLOW_IN_PACKAGE",
                    "No .yxmd workflow file was found inside the .yxwz package.",
                )

            # Safely extract ONLY the primary .yxmd file
            primary_content = zf.read(primary_yxmd_entry)
            validate_alteryx_xml_structure(primary_content)

            extract_target = temp_dir / Path(primary_yxmd_entry.filename).name
            extract_target.write_bytes(primary_content)

            pkg_meta = PackageMetadata(
                primary_workflow=primary_yxmd_entry.filename,
                contained_files=contained_files,
                total_size_bytes=total_size,
            )

            source_info = SourceInfo(
                source_format="yxwz",
                original_filename=filename,
                package_metadata=pkg_meta,
            )
            return extract_target, source_info

    except zipfile.BadZipFile:
        raise FormatValidationError(
            "INVALID_PACKAGE",
            f"File '{filename}' is not a valid zip/yxwz archive.",
        )
