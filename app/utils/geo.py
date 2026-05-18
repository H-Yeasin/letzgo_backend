import math
from typing import Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    Returns distance in meters.
    """
    R = 6371000  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def create_point_wkt(lat: float, lng: float) -> str:
    """Create WKT point string for PostGIS."""
    return f"SRID=4326;POINT({lng} {lat})"


def extract_coordinates(geom) -> Tuple[float, float]:
    """Extract (lat, lng) from a PostGIS geometry object."""
    if geom is None:
        return None, None

    # Try shapely conversion first
    try:
        from geoalchemy2.shape import to_shape
        shape = to_shape(geom)
        return float(shape.y), float(shape.x)
    except Exception:
        pass

    # Fallback to direct WKB/hex parsing
    import struct
    import binascii

    # Get hex string representation
    if isinstance(geom, str):
        hex_str = geom
    elif hasattr(geom, "data"):
        data = geom.data
        if isinstance(data, (bytes, bytearray)):
            hex_str = binascii.hexlify(data).decode("ascii")
        elif isinstance(data, memoryview):
            hex_str = binascii.hexlify(data.tobytes()).decode("ascii")
        else:
            hex_str = str(data)
    else:
        hex_str = str(geom)

    # Clean the hex string
    hex_str = hex_str.strip()

    # Parse standard EWKB or WKB
    try:
        wkb_bytes = binascii.unhexlify(hex_str)
        if len(wkb_bytes) >= 21:
            byte_order = wkb_bytes[0]
            is_little = (byte_order == 1)
            fmt_prefix = '<' if is_little else '>'
            
            # Read geometry type (4 bytes)
            geom_type = struct.unpack(fmt_prefix + 'I', wkb_bytes[1:5])[0]
            
            # Check if SRID flag (0x20000000) is set
            has_srid = bool(geom_type & 0x20000000)
            
            if has_srid:
                # EWKB format with SRID: type (4 bytes), SRID (4 bytes), X (8 bytes), Y (8 bytes)
                if len(wkb_bytes) >= 25:
                    _, _, x, y = struct.unpack(fmt_prefix + 'IIdd', wkb_bytes[1:25])
                    return float(y), float(x)
            else:
                # Standard WKB: type (4 bytes), X (8 bytes), Y (8 bytes)
                _, x, y = struct.unpack(fmt_prefix + 'Idd', wkb_bytes[1:21])
                return float(y), float(x)
    except Exception:
        pass

    # If it is a WKT string (e.g., 'POINT(lng lat)')
    wkt = str(geom)
    if "POINT" in wkt:
        try:
            coords = wkt.replace("POINT(", "").replace(")", "").strip()
            parts = coords.split()
            if len(parts) == 2:
                return float(parts[1]), float(parts[0])  # lat, lng
        except Exception:
            pass

    return None, None


def meters_to_degrees(meters: float, latitude: float) -> float:
    """
    Roughly convert meters to degrees at a given latitude.
    1 degree latitude ~ 111,320 meters
    1 degree longitude ~ 111,320 * cos(latitude) meters
    Returns a conservative degree estimate.
    """
    lat_degree = meters / 111320.0
    lon_degree = meters / (111320.0 * math.cos(math.radians(latitude)))
    return max(lat_degree, lon_degree)


def is_within_radius(
    lat1: float, lon1: float, lat2: float, lon2: float, radius_meters: float
) -> bool:
    """Check if two coordinates are within a given radius."""
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    return distance <= radius_meters
