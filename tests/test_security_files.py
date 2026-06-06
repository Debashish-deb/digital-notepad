import pytest
from fastapi import HTTPException
from app_skeleton.security.secure_files import _resolve_secure_path
import tempfile
from pathlib import Path
import app_skeleton.security.secure_files as secure_files

def test_resolve_secure_path_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        secure_files.ALLOWED_ROOTS = {"test_root": tmp_path}
        
        # Create a dummy file
        dummy = tmp_path / "test.txt"
        dummy.write_text("hello")
        
        resolved = _resolve_secure_path("test_root", "test.txt")
        assert resolved == dummy.resolve()

def test_resolve_secure_path_invalid_provider():
    with pytest.raises(HTTPException) as exc:
        _resolve_secure_path("invalid", "test.txt")
    assert exc.value.status_code == 400

def test_resolve_secure_path_traversal():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        secure_files.ALLOWED_ROOTS = {"test_root": tmp_path}
        
        with pytest.raises(HTTPException) as exc:
            _resolve_secure_path("test_root", "../outside.txt")
        assert exc.value.status_code == 400

def test_resolve_secure_path_absolute():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        secure_files.ALLOWED_ROOTS = {"test_root": tmp_path}
        
        with pytest.raises(HTTPException) as exc:
            _resolve_secure_path("test_root", "/etc/passwd")
        assert exc.value.status_code == 400
