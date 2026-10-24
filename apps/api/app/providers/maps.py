"""
Maps Provider interface + Mock implementation.
AGENTS.md: Every external service sits behind an interface with a mock
implementation that is the DEFAULT in dev.
"""
from abc import ABC, abstractmethod
import math
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class MapsProvider(ABC):
    """Abstract Maps / Geocoding provider interface."""

    @abstractmethod
    async def reverse_geocode(self, lat: float, lng: float) -> str:
        """Convert lat, lng into human-readable address."""
        ...

    @abstractmethod
    async def get_distance_and_eta(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> dict[str, Any]:
        """
        Calculate driving distance (km) and estimated travel time (minutes).
        Returns {"distance_km": float, "duration_minutes": int}
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Health check."""
        ...


class MockMapsProvider(MapsProvider):
    """
    Mock Maps provider for local development without Goong / Google Maps API keys.
    Computes haversine distance and estimates 25 km/h urban travel speed in Hue.
    """

    async def reverse_geocode(self, lat: float, lng: float) -> str:
        # Default mock addresses in Hue city
        if 16.45 <= lat <= 16.48 and 107.56 <= lng <= 107.60:
            return "Số 12 Lê Lợi, Phường Vĩnh Ninh, TP. Huế"
        return f"Vị trí ({lat:.4f}, {lng:.4f}), TP. Huế, Thừa Thiên Huế"

    async def get_distance_and_eta(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> dict[str, Any]:
        # Haversine distance formula
        r = 6371.0  # Earth radius in km
        dlat = math.radians(dest_lat - origin_lat)
        dlng = math.radians(dest_lng - origin_lng)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(origin_lat))
            * math.cos(math.radians(dest_lat))
            * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = round(r * c, 2)

        # Average urban speed 25 km/h in Hue + 2 min buffer
        duration_minutes = max(3, round((distance_km / 25.0) * 60) + 2)

        logger.info(
            "mock_maps_distance_calculated",
            distance_km=distance_km,
            duration_minutes=duration_minutes,
        )
        return {
            "distance_km": distance_km,
            "duration_minutes": duration_minutes,
        }

    async def is_available(self) -> bool:
        return True


def get_maps_provider() -> MapsProvider:
    """Factory: returns correct provider based on settings."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.provider_maps == "mock":
        return MockMapsProvider()
    raise NotImplementedError(f"Maps provider '{settings.provider_maps}' not yet implemented")
