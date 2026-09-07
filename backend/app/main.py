from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from PIL import Image, UnidentifiedImageError

from .canvas import CANVASES
from .config import settings
from .export import printable_html
from .models import PatternOptions, PlanRequest
from .palettes import public_palette
from .processing import generate_pattern
from .storage import store


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="StitchCraft API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    prolog = "unavailable"
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{settings.prolog_url}/health")
            if response.is_success:
                prolog = "ok"
    except httpx.HTTPError:
        pass
    return {"status": "ok", "service": "backend", "prolog": prolog}


@app.get("/palettes")
async def palettes():
    return [public_palette("dmc"), public_palette("anchor")]


@app.get("/canvas")
async def canvas():
    return CANVASES


@app.post("/patterns", status_code=201)
async def create_pattern(image: UploadFile = File(...), options: str = Form("{}")):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(415, "Нужен файл изображения")
    data = await image.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ")
    try:
        parsed = PatternOptions.model_validate(json.loads(options))
        pattern = await asyncio.to_thread(generate_pattern, data, parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Не удалось прочитать изображение") from exc
    pattern_id = uuid.uuid4().hex[:12]
    pattern.update({"id": pattern_id, "name": image.filename or "pattern"})
    store.put(pattern_id, pattern)
    return pattern


@app.get("/patterns/{pattern_id}")
async def get_pattern(pattern_id: str):
    pattern = store.get(pattern_id)
    if not pattern:
        raise HTTPException(404, "Схема не найдена")
    return pattern


def _region_payload(pattern: dict, region: dict, request: PlanRequest) -> dict:
    ids = set(region["stitches"])
    stitches = [{"id": s["id"], "x": s["x"], "y": s["y"], "stitch_type": s["stitch_type"]}
                for s in pattern["stitches"] if s["id"] in ids]
    options = pattern["options"]
    return {"region": stitches, "thread_length_mm": request.thread_length_mm or options["thread_length_mm"],
            "canvas_count": request.canvas_count or options["canvas_count"],
            "tail_length_mm": options["needle_length_mm"] + 15,
            "fold_parts": request.fold_parts or options["fold_parts"]}


@app.post("/patterns/{pattern_id}/plan")
async def plan_pattern(pattern_id: str, request: PlanRequest = PlanRequest()):
    pattern = store.get(pattern_id)
    if not pattern:
        raise HTTPException(404, "Схема не найдена")
    regions = pattern["regions"]
    if request.region_id:
        regions = [r for r in regions if r["id"] == request.region_id]
        if not regions:
            raise HTTPException(404, "Участок не найден")
    semaphore = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=20) as client:
        async def call(region: dict):
            async with semaphore:
                response = await client.post(f"{settings.prolog_url}/plan", json=_region_payload(pattern, region, request))
                response.raise_for_status()
                return region["id"], response.json()
        try:
            planned = await asyncio.gather(*(call(r) for r in regions))
        except httpx.HTTPError as exc:
            raise HTTPException(503, f"Планировщик Prolog недоступен: {exc}") from exc
    result = store.update_plans(pattern_id, dict(planned))
    return {"pattern_id": pattern_id, "plans": result["plans"]}


@app.get("/patterns/{pattern_id}/regions/{region_id}/facts", response_class=HTMLResponse)
async def region_facts(pattern_id: str, region_id: str):
    pattern = store.get(pattern_id)
    if not pattern:
        raise HTTPException(404, "Схема не найдена")
    region = next((r for r in pattern["regions"] if r["id"] == region_id), None)
    if not region:
        raise HTTPException(404, "Участок не найден")
    ids = set(region["stitches"])
    lines = [f"stitch({s['id']}, {s['x']}, {s['y']}, {s['stitch_type']})." for s in pattern["stitches"] if s["id"] in ids]
    opts = pattern["options"]
    lines += [f"thread_length({opts['thread_length_mm']}).", f"canvas_count({opts['canvas_count']})."]
    return "<pre>" + "\n".join(lines) + "</pre>"


@app.get("/patterns/{pattern_id}/export", response_class=HTMLResponse)
async def export_pattern(pattern_id: str):
    pattern = store.get(pattern_id)
    if not pattern:
        raise HTTPException(404, "Схема не найдена")
    return HTMLResponse(printable_html(pattern), headers={"Content-Disposition": f'inline; filename="pattern-{pattern_id}.html"'})

