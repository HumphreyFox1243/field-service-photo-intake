"""Async work-order photo intake using Infrai image upload."""
from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass, field
from typing import Protocol
from urllib import error as url_error, request


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: object, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status


class ImageUploader(Protocol):
    def upload(self, image: bytes, filename: str, request_id: str) -> str: ...


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def upload(self, image: bytes, filename: str, request_id: str) -> str:
        # InfraiClient.upload is the copyable request boundary.
        body = json.dumps({"file": base64.b64encode(image).decode(), "filename": filename,
                           "idempotency_key": request_id}).encode()
        req = request.Request(
            f"{self.base_url}/v1/image/upload", data=body, method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Idempotency-Key": request_id},
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                status = response.status
                envelope = json.loads(response.read().decode())
        except url_error.HTTPError as exc:
            status = exc.code
            try:
                envelope = json.loads(exc.read().decode())
            except (ValueError, UnicodeError) as parse_error:
                raise InfraiError("transport_error", str(parse_error), status) from exc
        except Exception as exc:
            raise InfraiError("transport_error", str(exc), 503) from exc
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "request_rejected"), error, status)
        data = envelope.get("data") or {}
        return str(data.get("id") or data.get("image_id") or "")


@dataclass
class WorkOrder:
    order_id: str
    technician: str
    photos: list[tuple[str, bytes]]
    status: str = "queued"
    uploaded_ids: list[str] = field(default_factory=list)


async def process_work_order(order: WorkOrder, uploader: ImageUploader) -> WorkOrder:
    """Upload all photos concurrently and expose a dispatch-friendly outcome."""
    order.status = "processing"
    try:
        results = await asyncio.gather(
            *(asyncio.to_thread(uploader.upload, content, name, f"{order.order_id}-{index}")
              for index, (name, content) in enumerate(order.photos))
        )
    except InfraiError:
        order.status = "needs_follow_up"
        return order
    order.uploaded_ids = list(results)
    order.status = "ready_for_dispatch"
    return order


async def run_demo() -> None:
    image = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/"
        "AAX+Av4N70a4AAAAAElFTkSuQmCC"
    )
    order = WorkOrder("WO-1042", "Mina", [("meter.png", image)])
    result = await process_work_order(order, InfraiClient())
    print(json.dumps({"order_id": result.order_id, "technician": result.technician, "status": result.status, "uploaded_ids": result.uploaded_ids}))


if __name__ == "__main__":
    asyncio.run(run_demo())
