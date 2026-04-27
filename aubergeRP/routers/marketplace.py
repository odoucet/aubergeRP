"""Marketplace router — browse and import community character cards."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..config import get_config

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class MarketplaceCard(BaseModel):
    """A single card entry from the marketplace index."""

    id: str
    name: str
    description: str = ""
    tags: list[str] = []
    creator: str = ""
    download_url: str
    preview_url: str = ""


class MarketplaceSearchResponse(BaseModel):
    cards: list[MarketplaceCard]
    total: int


def _get_index_url() -> str:
    return get_config().marketplace.index_url


@router.get("/search", response_model=MarketplaceSearchResponse)
async def search_marketplace(
    q: str = Query(default="", description="Search query"),
    index_url: str = Depends(_get_index_url),
) -> MarketplaceSearchResponse:
    """Fetch and filter character cards from the hosted marketplace index."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(index_url)
            resp.raise_for_status()
            raw: list[dict] = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch marketplace index: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Marketplace unavailable: {exc}") from exc

    cards: list[MarketplaceCard] = []
    for item in raw:
        try:
            cards.append(MarketplaceCard(**item))
        except Exception:
            continue  # skip malformed entries

    if q:
        q_lower = q.lower()
        cards = [
            c for c in cards
            if q_lower in c.name.lower()
            or q_lower in c.description.lower()
            or any(q_lower in t.lower() for t in c.tags)
        ]

    return MarketplaceSearchResponse(cards=cards, total=len(cards))
