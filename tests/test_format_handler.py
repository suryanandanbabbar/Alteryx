"""Tests for format detection, XML structural validation, and .yxwz package handling."""

import io
import zipfile
from pathlib import Path
import pytest

from awa.parser.format_handler import (
    detect_format,
    validate_alteryx_xml_structure,
    handle_upload,
    FormatValidationError,
)


def test_detect_format_yxmd():
    content = b'<?xml version="1.0"?>\n<AlteryxDocument yxmdVer="2025.1"/>'
    assert detect_format("workflow.yxmd", content) == "yxmd"


def test_detect_format_xml():
    content = b'<?xml version="1.0"?>\n<AlteryxDocument yxmdVer="2025.1"/>'
    assert detect_format("workflow.xml", content) == "xml"


def test_detect_format_yxwz():
    # ZIP magic bytes PK\x03\x04
    content = b"PK\x03\x04\x14\x00\x00\x00..."
    assert detect_format("package.yxwz", content) == "yxwz"


def test_validate_alteryx_xml_valid():
    valid_xml = b"""<?xml version="1.0"?>
    <AlteryxDocument yxmdVer="2025.2">
      <Nodes>
        <Node ToolID="1">
          <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"/>
        </Node>
      </Nodes>
      <Connections/>
    </AlteryxDocument>"""
    # Should not raise
    validate_alteryx_xml_structure(valid_xml)


def test_validate_alteryx_xml_invalid_structure():
    non_alteryx_xml = b"""<?xml version="1.0"?>
    <catalog>
      <book id="bk101">
        <author>Gambardella, Matthew</author>
        <title>XML Developer's Guide</title>
      </book>
    </catalog>"""
    with pytest.raises(FormatValidationError) as exc:
        validate_alteryx_xml_structure(non_alteryx_xml)
    assert exc.value.code == "UNRECOGNIZED_WORKFLOW_XML"


def test_validate_alteryx_xml_malformed():
    malformed = b"<AlteryxDocument><unclosed>"
    with pytest.raises(FormatValidationError) as exc:
        validate_alteryx_xml_structure(malformed)
    assert exc.value.code == "MALFORMED_XML"


def test_handle_upload_yxmd(tmp_path: Path):
    with open("fixtures/basic/simple_filter.yxmd", "rb") as f:
        content = f.read()

    path, sinfo = handle_upload("simple_filter.yxmd", content, tmp_path)
    assert path.exists()
    assert sinfo.source_format == "yxmd"
    assert sinfo.original_filename == "simple_filter.yxmd"
    assert sinfo.package_metadata is None


def test_handle_upload_yxwz_valid(tmp_path: Path):
    # Create an in-memory .yxwz package containing simple_filter.yxmd
    with open("fixtures/basic/simple_filter.yxmd", "rb") as f:
        wf_content = f.read()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("MyWorkflow.yxmd", wf_content)
        zf.writestr("data/sample.csv", "id,val\n1,a\n2,b")
    pkg_bytes = zip_buffer.getvalue()

    path, sinfo = handle_upload("packaged_workflow.yxwz", pkg_bytes, tmp_path)
    assert path.exists()
    assert sinfo.source_format == "yxwz"
    assert sinfo.original_filename == "packaged_workflow.yxwz"
    assert sinfo.package_metadata is not None
    assert sinfo.package_metadata.primary_workflow == "MyWorkflow.yxmd"
    assert "data/sample.csv" in sinfo.package_metadata.contained_files


def test_handle_upload_yxwz_path_traversal(tmp_path: Path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("../../../etc/evil.yxmd", b"<AlteryxDocument/>")
    pkg_bytes = zip_buffer.getvalue()

    with pytest.raises(FormatValidationError) as exc:
        handle_upload("attack.yxwz", pkg_bytes, tmp_path)
    assert exc.value.code == "SECURITY_PATH_TRAVERSAL"


def test_handle_upload_unknown_format(tmp_path: Path):
    with pytest.raises(FormatValidationError) as exc:
        handle_upload("document.pdf", b"%PDF-1.4 ...", tmp_path)
    assert exc.value.code == "UNSUPPORTED_FORMAT"
