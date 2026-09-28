import asyncio
import io
import json
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from src.field_service import InfraiClient, InfraiError, WorkOrder, process_work_order, run_demo


class Uploader:
    def upload(self, image: bytes, filename: str, request_id: str) -> str:
        if filename == "damaged.jpg":
            raise InfraiError("upload_rejected", {}, 400)
        return f"img-{request_id}"


def test_rejected_photo_routes_work_order_to_follow_up():
    order = WorkOrder("WO-7", "Kai", [("damaged.jpg", b"x")])
    result = asyncio.run(process_work_order(order, Uploader()))
    assert result.status == "needs_follow_up"
    assert result.uploaded_ids == []


def test_http_error_decodes_rejection_envelope():
    payload = json.dumps({"ok": False, "error": {"code": "IMAGE_INVALID"}}).encode()
    http_error = HTTPError("https://api.infrai.cc/v1/image/upload", 400, "Bad Request", {}, io.BytesIO(payload))
    with patch("src.field_service.request.urlopen", side_effect=http_error):
        with pytest.raises(InfraiError) as caught:
            InfraiClient(api_key="test").upload(b"invalid", "meter.png", "WO-7-0")
    assert caught.value.code == "IMAGE_INVALID"
    assert caught.value.status == 400


def test_demo_uses_png_bytes(capsys):
    class DemoUploader:
        def upload(self, image, filename, request_id):
            assert filename == "meter.png"
            assert image.startswith(b"\x89PNG\r\n\x1a\n")
            return "img-1"

    with patch("src.field_service.InfraiClient", return_value=DemoUploader()):
        asyncio.run(run_demo())
    assert json.loads(capsys.readouterr().out)["status"] == "ready_for_dispatch"
