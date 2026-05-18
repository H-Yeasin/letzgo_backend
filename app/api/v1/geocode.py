from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pydantic import BaseModel
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

router = APIRouter(prefix="/geocode", tags=["Geocoding"])

# Initialize Nominatim geocoder with a user agent
geolocator = Nominatim(user_agent="letzgo_app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)


class GeocodeResult(BaseModel):
    display_name: str
    lat: float
    lng: float


class GeocodeResponse(BaseModel):
    results: list[GeocodeResult]


class DirectGeocodeResponse(BaseModel):
    lat: float
    lng: float


@router.get("", response_model=DirectGeocodeResponse)
def geocode_location(
    q: str = Query(..., description="Place name to search (e.g. 'Mirpur')"),
):
    """Convert a place name directly into coordinates (lat, lng).
    
    Returns the top match's latitude and longitude.
    """
    try:
        search_query = q
        if "dhaka" not in q.lower() and "bangladesh" not in q.lower():
            search_query = f"{q}, Dhaka, Bangladesh"

        locations = geocode(search_query, exactly_one=True)

        if not locations:
            raise HTTPException(status_code=404, detail="Location not found")

        return DirectGeocodeResponse(
            lat=locations.latitude,
            lng=locations.longitude,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding failed: {str(e)}")


@router.get("/search", response_model=GeocodeResponse)
def search_location(
    q: str = Query(..., description="Place name to search (e.g. 'Mirpur, Dhaka')"),
    limit: int = Query(5, ge=1, le=10),
):
    """Search for a location by name using OpenStreetMap Nominatim.

    Returns matching places with display name, lat, lng.
    """
    try:
        # Add "Dhaka" context if not specified to get relevant results
        search_query = q
        if "dhaka" not in q.lower() and "bangladesh" not in q.lower():
            search_query = f"{q}, Dhaka, Bangladesh"

        locations = geocode(search_query, exactly_one=False, limit=limit)

        if not locations:
            return {"results": []}

        results = []
        for loc in locations:
            results.append(
                GeocodeResult(
                    display_name=loc.address,
                    lat=loc.latitude,
                    lng=loc.longitude,
                )
            )

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding failed: {str(e)}")


@router.get("/reverse", response_model=GeocodeResult)
def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
):
    """Convert coordinates (lat, lng) back into a display name / address."""
    try:
        # Use RateLimiter or direct geolocator for reverse geocoding
        location = geolocator.reverse((lat, lng), exactly_one=True)
        if not location:
            raise HTTPException(status_code=404, detail="Address not found")
        return GeocodeResult(
            display_name=location.address,
            lat=lat,
            lng=lng,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reverse geocoding failed: {str(e)}")