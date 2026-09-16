
import io
import math
import os
import uuid
import httpx
from PIL import Image, ImageDraw
from app.http_client import SSL_CONTEXT
from app.logger import get_logger

logger = get_logger(__name__)

_USER_AGENT = "TeachAIweb/1.0 (educational konspekt map generation)"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_TILE_SIZE = 256

_MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "maps")
_TILE_CACHE_DIR = os.path.join(_MAPS_DIR, "tile_cache")
os.makedirs(_TILE_CACHE_DIR, exist_ok=True)

_MAP_WIDTH = 640
_MAP_HEIGHT = 420
_MAX_ZOOM = 15
_MIN_ZOOM = 2


async def _geocode(client: httpx.AsyncClient, place: str) -> dict | None:
    try:
        resp = await client.get(
            _NOMINATIM_URL,
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": _USER_AGENT},
            timeout=8.0,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        r = results[0]
        south, north, west, east = (float(x) for x in r["boundingbox"])
        return {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "bbox": (west, south, east, north),
            "name": r.get("display_name", place),
        }
    except Exception as e:
        logger.warning(f"Map geocoding failed for '{place}': {e}")
        return None


def _lonlat_to_pixel(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n * _TILE_SIZE
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n * _TILE_SIZE
    return x, y


def _zoom_for_bboxes(points: list[tuple[float, float]], width_px: int, height_px: int) -> int:
    pad = 0.85
    for zoom in range(_MAX_ZOOM, _MIN_ZOOM - 1, -1):
        xs, ys = [], []
        for lon, lat in points:
            x, y = _lonlat_to_pixel(lon, lat, zoom)
            xs.append(x)
            ys.append(y)
        if (max(xs) - min(xs)) <= width_px * pad and (max(ys) - min(ys)) <= height_px * pad:
            return zoom
    return _MIN_ZOOM


async def _fetch_tile(client: httpx.AsyncClient, z: int, x: int, y: int) -> Image.Image | None:
    n = 2 ** z
    x, y = x % n, y % n
    cache_path = os.path.join(_TILE_CACHE_DIR, f"{z}_{x}_{y}.png")
    if os.path.exists(cache_path):
        try:
            return Image.open(cache_path).convert("RGBA")
        except Exception:
            pass
    try:
        resp = await client.get(
            _TILE_URL.format(z=z, x=x, y=y),
            headers={"User-Agent": _USER_AGENT},
            timeout=8.0,
        )
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        try:
            img.save(cache_path)
        except Exception:
            pass
        return img
    except Exception as e:
        logger.warning(f"Tile fetch failed for z={z} x={x} y={y}: {e}")
        return None


async def build_geography_map(place_names: list[str]) -> str | None:
    if not place_names:
        return None
    place_names = place_names[:3]

    async with httpx.AsyncClient(verify=SSL_CONTEXT) as client:
        geocoded = []
        for place in place_names:
            hit = await _geocode(client, place)
            if hit:
                geocoded.append(hit)

        if not geocoded:
            return None

        fit_points = []
        for g in geocoded:
            west, south, east, north = g["bbox"]
            fit_points.append((west, south))
            fit_points.append((east, north))
        zoom = _zoom_for_bboxes(fit_points, _MAP_WIDTH, _MAP_HEIGHT)

        centers = [(g["lon"], g["lat"]) for g in geocoded]
        cx = sum(x for x, _ in [_lonlat_to_pixel(lon, lat, zoom) for lon, lat in centers]) / len(centers)
        cy = sum(y for _, y in [_lonlat_to_pixel(lon, lat, zoom) for lon, lat in centers]) / len(centers)
        top_left_x = cx - _MAP_WIDTH / 2
        top_left_y = cy - _MAP_HEIGHT / 2

        first_tile_x = math.floor(top_left_x / _TILE_SIZE)
        first_tile_y = math.floor(top_left_y / _TILE_SIZE)
        last_tile_x = math.floor((top_left_x + _MAP_WIDTH) / _TILE_SIZE)
        last_tile_y = math.floor((top_left_y + _MAP_HEIGHT) / _TILE_SIZE)

        canvas = Image.new("RGBA", (_MAP_WIDTH, _MAP_HEIGHT), (240, 240, 240, 255))
        for tx in range(first_tile_x, last_tile_x + 1):
            for ty in range(first_tile_y, last_tile_y + 1):
                tile = await _fetch_tile(client, zoom, tx, ty)
                if tile is None:
                    continue
                paste_x = int(tx * _TILE_SIZE - top_left_x)
                paste_y = int(ty * _TILE_SIZE - top_left_y)
                canvas.paste(tile, (paste_x, paste_y), tile)

        draw = ImageDraw.Draw(canvas)
        for g in geocoded:
            px, py = _lonlat_to_pixel(g["lon"], g["lat"], zoom)
            mx, my = px - top_left_x, py - top_left_y
            r = 9
            draw.ellipse([mx - r, my - r - 4, mx + r, my + r - 4], fill=(220, 38, 38, 255), outline=(255, 255, 255, 255), width=2)
            draw.polygon([(mx - 6, my + r - 6), (mx + 6, my + r - 6), (mx, my + r + 8)], fill=(220, 38, 38, 255))
            draw.ellipse([mx - 3, my - r - 7, mx + 3, my - r - 1], fill=(255, 255, 255, 255))

        filename = f"{uuid.uuid4().hex}.png"
        out_path = os.path.join(_MAPS_DIR, filename)
        canvas.convert("RGB").save(out_path, "PNG")
        return f"/uploads/maps/{filename}"
