from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from typing import Optional
import requests
import piexif
from pathlib import Path


# Directory for weather icons (should be in web/static or similar)
WEATHER_ICON_DIR = Path(__file__).parent.parent / "web" / "weather_icons"
WEATHER_ICON_MAP = {
    0: "clear.png", 1: "partly_cloudy.png", 2: "cloudy.png", 3: "overcast.png", 45: "fog.png", 48: "fog.png", 51: "drizzle.png", 61: "rain.png", 80: "rain.png", 95: "storm.png"
}


def get_address(latitude: float, longitude: float) -> str:
    """Reverse geocode lat/lon to a detailed address using Nominatim."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={latitude}&lon={longitude}&zoom=16&addressdetails=1"
        headers = {"User-Agent": "FakeGeoTag/1.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.ok:
            data = resp.json()
            addr = data.get('address', {})
            # Prefer street/road, then neighbourhood, suburb, city, state, country
            fields = [
                'road', 'pedestrian', 'footway', 'cycleway', 'neighbourhood', 'suburb', 'village', 'town', 'city', 'state', 'country'
            ]
            parts = [addr.get(f) for f in fields if addr.get(f)]
            if parts:
                return ', '.join(parts)
            # Fallback to display_name
            if 'display_name' in data and data['display_name']:
                return data['display_name']
            if 'name' in data and data['name']:
                return data['name']
    except Exception:
        pass
    return "Unknown Location"


def get_weather(latitude: float, longitude: float):
    """Fetch current weather for the location using Open-Meteo (no API key required). Returns (icon_path, temp_str)."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        resp = requests.get(url, timeout=5)
        if resp.ok:
            data = resp.json()
            weather = data.get('current_weather', {})
            temp = weather.get('temperature')
            code = weather.get('weathercode')
            icon_file = WEATHER_ICON_MAP.get(code)
            icon_path = str(WEATHER_ICON_DIR / icon_file) if icon_file and (WEATHER_ICON_DIR / icon_file).exists() else None
            temp_str = f"{temp:.1f}°C" if temp is not None else "N/A"
            return icon_path, temp_str
    except Exception:
        pass
    return None, "N/A"


def overlay_with_map_and_info(
    img: Image.Image,
    latitude: float,
    longitude: float,
    date: str,
    time: str,
    map_image_path: Optional[str] = None
) -> Image.Image:
    """
    Overlay a single-row geotag card at the bottom of the image.
    Layout: 3 columns (map | address/date/time/coords | weather)
    Center column: address (word-wrapped), date+time below, lat+lon below.
    Weather column: icon (smaller), temp text below icon, both centered.
    Dynamically adapts to image aspect ratio for best fit.
    """
    print("[DEBUG] Starting overlay_with_map_and_info")
    # --- Load map image (screenshot from frontend) ---
    try:
        if map_image_path:
            print(f"[DEBUG] Loading map image from {map_image_path}")
            map_img = Image.open(map_image_path).convert("RGBA")
        else:
            print("[DEBUG] No map image path provided, using blank map")
            map_img = Image.new("RGBA", (320, 180), (220, 220, 220, 255))
    except Exception as e:
        print(f"[ERROR] Loading map image failed: {e}")
        map_img = Image.new("RGBA", (320, 180), (220, 220, 220, 255))
    print("[DEBUG] Map image loaded")
    print("[DEBUG] Fetching address...")
    address = get_address(latitude, longitude)
    print(f"[DEBUG] Address: {address}")
    print("[DEBUG] Fetching weather...")
    weather_icon_path, temp_str = get_weather(latitude, longitude)
    print(f"[DEBUG] Weather icon: {weather_icon_path}, Temp: {temp_str}")
    width, height = img.size
    print(f"[DEBUG] Image size: {width}x{height}")

    # Overlay dimensions
    overlay_height = int(height * 0.22)
    overlay = Image.new("RGBA", (width, overlay_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([(0, 0), (width, overlay_height)], fill=(28, 28, 28, 210))
    print("[DEBUG] Overlay created (rectangle)")

    # --- Dynamic column widths based on aspect ratio ---
    aspect = width / height
    col_pad = max(12, int(width * 0.01))
    min_center_col_w = 120
    min_map_col_w = int(overlay_height * 0.7)
    min_weather_col_w = int(overlay_height * 0.5)
    # For tall images, reduce map/weather columns, give more to center
    if aspect < 0.7:  # very tall (9:16 or taller)
        map_col_w = min_map_col_w
        weather_col_w = min_weather_col_w
        center_col_w = width - map_col_w - weather_col_w - 2 * col_pad * 2
        if center_col_w < min_center_col_w:
            # If still too small, shrink map/weather more
            shrink = min_center_col_w - center_col_w
            map_col_w = max(40, map_col_w - shrink // 2)
            weather_col_w = max(40, weather_col_w - shrink // 2)
            center_col_w = width - map_col_w - weather_col_w - 2 * col_pad * 2
    else:
        map_col_w = int(overlay_height * 1.1)
        weather_col_w = int(overlay_height * 0.7)
        center_col_w = width - map_col_w - weather_col_w - 2 * col_pad * 2
    print(f"[DEBUG] Column widths: map={map_col_w}, center={center_col_w}, weather={weather_col_w}")

    # --- Map (left column, flush left) ---
    try:
        map_target_height = overlay_height - 10
        map_target_width = int(map_img.width * (map_target_height / map_img.height))
        if map_target_width > map_col_w - 8:
            map_target_width = map_col_w - 8
            map_target_height = int(map_img.height * (map_target_width / map_img.width))
        map_resized = map_img.resize((max(1,map_target_width), max(1,map_target_height)), resample=Image.Resampling.LANCZOS)
        border = 2
        map_box = Image.new("RGBA", (map_target_width + 2*border, map_target_height + 2*border), (0,0,0,0))
        map_box.paste(map_resized, (border, border), map_resized)
        map_y = (overlay_height - map_box.height) // 2
        overlay.paste(map_box, (col_pad, map_y), map_box)
        print("[DEBUG] Map column drawn (left)")
    except Exception as e:
        print(f"[ERROR] Drawing map column failed: {e}")

    # --- Center column: address (word-wrapped), date+time, lat+lon ---
    try:
        print("[DEBUG] Center column: loading fonts...")
        # Reduce font size for very tall images
        if aspect < 0.7:
            font_size_addr = max(12, overlay_height // 8)
            font_size_meta = max(9, overlay_height // 14)
            addr_line_spacing = 10  # increased spacing
            meta_spacing = 18       # increased spacing
        else:
            font_size_addr = max(16, overlay_height // 6)
            font_size_meta = max(13, overlay_height // 9)
            addr_line_spacing = 14  # increased spacing
            meta_spacing = 24       # increased spacing
        try:
            font_addr = ImageFont.truetype("arialbd.ttf", font_size_addr)
        except Exception:
            font_addr = ImageFont.load_default()
        try:
            font_meta = ImageFont.truetype("arial.ttf", font_size_meta)
        except Exception:
            font_meta = ImageFont.load_default()
        print("[DEBUG] Center column: fonts loaded")

        # Address (word-wrapped, with safety)
        center_x = col_pad + map_col_w + col_pad
        max_addr_width = center_col_w
        addr_lines = []
        words = address.split()
        word_wrap_safety = 0
        print(f"[DEBUG] Center column: address split into {len(words)} words")
        while words and word_wrap_safety < 10:
            line = ''
            inner_wrap_safety = 0
            while words and inner_wrap_safety < 50:
                test_line = line + ('' if not line else ' ') + words[0]
                bbox = draw.textbbox((0, 0), test_line, font=font_addr)
                w = bbox[2] - bbox[0]
                if w <= max_addr_width:
                    line = test_line
                    words.pop(0)
                else:
                    break
                inner_wrap_safety += 1
            if line:
                addr_lines.append(line)
            word_wrap_safety += 1
        if not addr_lines:
            addr_lines = [address]
        print(f"[DEBUG] Center column: address wrapped into {len(addr_lines)} lines")
        addr_line_height = font_addr.getbbox("A")[3] - font_addr.getbbox("A")[1]
        addr_block_height = len(addr_lines) * (addr_line_height + addr_line_spacing)

        # Date/time and lat/lon
        meta_height = font_meta.getbbox("A")[3] - font_meta.getbbox("A")[1]
        date_time_str = f"{date} {time}"
        latlon_str = f"{latitude:.5f}, {longitude:.5f}"
        meta_block_height = meta_height * 2 + meta_spacing

        # Vertical stacking for center column (address, date/time, lat/lon)
        total_center_height = addr_block_height + meta_block_height + meta_spacing * 2  # extra space between blocks
        center_y = (overlay_height - total_center_height) // 2
        y_cursor = center_y
        # Draw address lines
        for line in addr_lines:
            draw.text((center_x, y_cursor), line, font=font_addr, fill=(255,255,255,255))
            y_cursor += addr_line_height + addr_line_spacing
        y_cursor += meta_spacing  # extra space before date/time
        # Draw date/time
        draw.text((center_x, y_cursor), date_time_str, font=font_meta, fill=(220,220,220,230))
        y_cursor += meta_height + meta_spacing
        # Draw lat/lon
        draw.text((center_x, y_cursor), latlon_str, font=font_meta, fill=(180,180,180,210))
        print("[DEBUG] Center column drawn")
    except Exception as e:
        print(f"[ERROR] Drawing center column failed: {e}")

    # --- Weather (right column) ---
    print("[DEBUG] Entering weather column block...")
    try:
        wx_icon_size = int(weather_col_w * 0.35)
        wx_x = width - weather_col_w + (weather_col_w - wx_icon_size) // 2 - col_pad
        wx_y = (overlay_height - wx_icon_size - 12) // 2
        if weather_icon_path and Path(weather_icon_path).exists():
            wx_icon = Image.open(weather_icon_path).convert("RGBA").resize((wx_icon_size, wx_icon_size))
            overlay.paste(wx_icon, (wx_x, wx_y), wx_icon)
        font_size_temp = max(10, wx_icon_size // 3)
        try:
            font_temp = ImageFont.truetype("arial.ttf", font_size_temp)
        except Exception:
            font_temp = ImageFont.load_default()
        temp_color = (255, 255, 255, 230)
        temp_bbox = font_temp.getbbox(temp_str)
        temp_width = temp_bbox[2] - temp_bbox[0]
        temp_x = wx_x + (wx_icon_size - temp_width) // 2
        temp_y = wx_y + wx_icon_size + 2
        draw.text((temp_x, temp_y), temp_str, font=font_temp, fill=temp_color)
        print("[DEBUG] Weather column drawn")
    except Exception as e:
        print(f"[ERROR] Drawing weather column failed: {e}")

    # --- Composite overlay onto image ---
    try:
        out_img = img.convert("RGBA")
        out_img.alpha_composite(overlay, (0, height - overlay_height))
        print("[DEBUG] Overlay composited onto image")
        return out_img.convert("RGB")
    except Exception as e:
        print(f"[ERROR] Compositing overlay failed: {e}")
        return img


# Removed duplicate embed_metadata function to resolve name conflict.

def embed_metadata(input_path: str, output_path: str, latitude: float, longitude: float, date: str, time: str, map_image_path: Optional[str] = None) -> None:
    """
    Embed EXIF metadata (GPS, date/time) into an image and save to output_path.
    Also overlays map and info at the bottom. If map_image_path is provided, use it as the map overlay.
    """
    img = Image.open(input_path)
    # Overlay map and info
    img = overlay_with_map_and_info(img, latitude, longitude, date, time, map_image_path)
    # Try to load EXIF, or create a new one if not present
    try:
        exif_bytes = img.info.get('exif')
        exif_dict = piexif.load(exif_bytes) if exif_bytes else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    # GPS
    def to_deg(value):
        deg = int(abs(value))
        min_ = int((abs(value) - deg) * 60)
        sec = float((abs(value) - deg - min_ / 60) * 3600)
        return ((deg, 1), (min_, 1), (int(sec * 100), 100))
    exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = b'N' if latitude >= 0 else b'S'
    exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = to_deg(latitude)
    exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = b'E' if longitude >= 0 else b'W'
    exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = to_deg(longitude)
    dt_fmt = "%Y-%m-%d %H:%M"
    try:
        dt_str = f"{date} {time}"
        dt = datetime.strptime(dt_str, dt_fmt)
        dt_bytes = dt.strftime("%Y:%m:%d %H:%M:%S").encode()
        exif_dict['0th'][piexif.ImageIFD.DateTime] = dt_bytes
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = dt_bytes
        exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = dt_bytes
    except Exception:
        pass  # If date/time invalid, skip
    exif_bytes = piexif.dump(exif_dict)
    img.save(output_path, exif=exif_bytes)


def draw_wrapped_text(draw, text, font, x, y, max_width, fill, line_spacing=4):
    """Draw text with word wrap to fit max_width using draw.textbbox for width measurement."""
    lines = []
    words = text.split()
    while words:
        line = ''
        while words:
            test_line = line + ('' if not line else ' ') + words[0]
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                line = test_line
                words.pop(0)
            else:
                break
        lines.append(line)
    for i, line in enumerate(lines):
        draw.text((x, y + i * (font.size + line_spacing)), line, font=font, fill=fill)
    return y + len(lines) * (font.size + line_spacing)
