from enum import Enum
from pydantic import BaseModel, Field


class StitchType(str, Enum):
    full = "full"
    half_forward = "half_forward"
    half_backward = "half_backward"


class PatternOptions(BaseModel):
    width: int | None = Field(80, ge=8, le=220)
    height: int | None = Field(None, ge=8, le=220)
    size_unit: str = "stitches"
    physical_size: float | None = Field(None, gt=0, le=100)
    size_axis: str = "width"
    canvas_count: int = Field(14, ge=6, le=32)
    palette: str = "dmc"
    max_colors: int = Field(16, ge=2, le=40)
    blends: bool = True
    half_cross: bool = True
    backstitch: bool = True
    min_component_size: int = Field(3, ge=1, le=20)
    thread_length_mm: float = Field(1000, ge=200, le=3000)
    strands: int = Field(2, ge=1, le=6)
    fold_parts: int = Field(2, ge=2, le=3)
    needle_length_mm: float = Field(40, ge=25, le=70)
    canvas_color: str | None = None
    remove_background: bool = False
    background_tolerance: float = Field(1, ge=1, le=50)


class PlanRequest(BaseModel):
    region_id: str | None = None
    thread_length_mm: float | None = None
    canvas_count: int | None = None
    fold_parts: int | None = None
