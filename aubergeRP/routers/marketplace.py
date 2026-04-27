"""Marketplace router — browse and import community character cards."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..config import get_config

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

# Only allow HTTP(S) schemes for the marketplace index URL to prevent SSRF
# via file:// or other non-network schemes.
_ALLOWED_SCHEMES = {"http", "https"}


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


def _validate_url(url: str) -> None:
    """Raise HTTPException if the URL is not an allowed HTTP(S) URL."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid marketplace index URL in configuration.")
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(
            status_code=400,
            detail=f"Marketplace index URL must use http or https (got '{parsed.scheme}').",
        )


@router.get("/search", response_model=MarketplaceSearchResponse)
async def search_marketplace(
    q: str = Query(default="", description="Search query"),
    index_url: str = Depends(_get_index_url),
) -> MarketplaceSearchResponse:
    """Fetch and filter character cards from the hosted marketplace index.

    The index URL is an administrator-configured value (marketplace.index_url in
    config.yaml).  Only http and https schemes are permitted to prevent SSRF via
    non-network URL schemes such as file://.
    """
    _validate_url(index_url)
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
