from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class GrantSchema(BaseModel):
    id: str = Field(..., description="Stable identifier for this grant")
    title: str = Field(..., description="Grant/RFP title")
    funder: Optional[str] = Field(None, description="Funder organization name")
    url: Optional[HttpUrl] = Field(None, description="Source or program URL")
    summary: Optional[str] = Field(None, description="Short summary")

    eligibility: List[str] = Field(default_factory=list, description="Eligibility bullets")
    deadline: Optional[date] = Field(None, description="Application deadline if available")
    amount: Optional[str] = Field(None, description="Award amount or range textual")
    tags: List[str] = Field(default_factory=list, description="Tag keywords like STEM/EdTech/K-12")

    raw_ref: Optional[str] = Field(None, description="Pointer back to raw file path or hash")

