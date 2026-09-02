"""
Unit tests for app.routers.reports (report store and download validation).
"""

import pytest
from fastapi import HTTPException

from app.routers.reports import _report_store, download_report


@pytest.mark.asyncio
class TestReportRouterValidation:
    async def test_invalid_report_id_traversal_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await download_report("../etc/passwd")
        assert exc_info.value.status_code == 400

    async def test_invalid_report_id_slash_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await download_report("sub/folder/id")
        assert exc_info.value.status_code == 400

    async def test_nonexistent_report_404(self):
        with pytest.raises(HTTPException) as exc_info:
            await download_report("nonexistent-uuid-12345")
        assert exc_info.value.status_code == 404

    async def test_invalid_report_id_special_chars_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await download_report("report;rm -rf /")
        assert exc_info.value.status_code == 400

    async def test_empty_report_id_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await download_report("")
        assert exc_info.value.status_code == 400

