from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO
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
    Overlay a modern, camera-style geotag card at the bottom (landscape) or side (portrait) of the image.
    Map screenshot on left/top, weather on right/bottom, address and metadata in center.
    Responsive for 16x9 and 9x16 images.
    """
    # --- Load map image (screenshot from frontend) ---
    if map_image_path:
        map_img = Image.open(map_image_path).convert("RGBA")
    else:
        map_img = Image.new("RGBA", (320, 180), (220, 220, 220, 255))
    # --- Get address and weather ---
    address = get_address(latitude, longitude)
    weather_icon_path, temp_str = get_weather(latitude, longitude)
    width, height = img.size
    aspect = width / height
    # Responsive: landscape (overlay bottom), portrait (overlay right)
    if aspect >= 1:  # Landscape (16x9, etc)
        overlay_height = int(height * 0.28)
        overlay = Image.new("RGBA", (width, overlay_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        radius = overlay_height // 2
        draw.rounded_rectangle([(0, 0), (width, overlay_height)], radius=radius, fill=(28, 28, 28, 210))
        # --- Map on left with border/shadow ---
        map_target_height = overlay_height - 32
        map_target_width = int(map_img.width * (map_target_height / map_img.height))
        map_resized = map_img.resize((map_target_width, map_target_height), resample=Image.Resampling.LANCZOS)
        # Add border and shadow
        border = 5
        map_box = Image.new("RGBA", (map_target_width + 2*border, map_target_height + 2*border), (0,0,0,0))
        shadow = Image.new("RGBA", (map_box.width+8, map_box.height+8), (0,0,0,0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [(4, 4), (shadow.width-4, shadow.height-4)],
            radius=18,
            fill=(0,0,0,80)
        )
        map_box.paste(map_resized, (border, border), map_resized)
        shadow.paste(map_box, (4,4), map_box)
        map_y = (overlay_height - shadow.height) // 2
        overlay.paste(shadow, (18, map_y), shadow)
        # --- Weather icon and temp on top right (move left for visibility) ---
        wx_icon = None
        wx_icon_size = overlay_height // 3
        wx_x = width - wx_icon_size - 250  # moved left from -32 to -180
        wx_y = 18
        if weather_icon_path and Path(weather_icon_path).exists():
            wx_icon = Image.open(weather_icon_path).convert("RGBA").resize((wx_icon_size, wx_icon_size))
            overlay.paste(wx_icon, (wx_x, wx_y), wx_icon)
        # Temp text
        font_size_temp = wx_icon_size // 2 + 4
        try:
            font_temp = ImageFont.truetype("arial.ttf", font_size_temp)
        except Exception:
            font_temp = ImageFont.load_default()
        temp_color = (255, 255, 255, 240)
        draw.text((wx_x + wx_icon_size + 12, wx_y + wx_icon_size//4), temp_str, font=font_temp, fill=temp_color)
        # --- Address, date, time, coords in center ---
        font_size_addr = max(20, overlay_height // 7)
        font_size_meta = max(16, overlay_height // 10)
        try:
            font_addr = ImageFont.truetype("arialbd.ttf", font_size_addr)
        except Exception:
            font_addr = ImageFont.load_default()
        try:
            font_meta = ImageFont.truetype("arial.ttf", font_size_meta)
        except Exception:
            font_meta = ImageFont.load_default()
        text_x = shadow.width + 36
        text_y = 28
        # Address (bold, wrapped)
        max_addr_width = width - text_x - 60 - wx_icon_size
        addr_font_size = font_size_addr
        addr_font = font_addr
        # Shrink font if address is too wide
        while True:
            bbox = addr_font.getbbox(address)
            w = bbox[2] - bbox[0]
            if w <= max_addr_width or addr_font_size <= 14:
                break
            addr_font_size -= 2
            try:
                addr_font = ImageFont.truetype("arialbd.ttf", addr_font_size)
            except Exception:
                addr_font = ImageFont.load_default()
        y_addr_end = draw_wrapped_text(draw, address, addr_font, text_x, text_y, max_addr_width, (255,255,255,255))
        # Date/time
        draw.text((text_x, y_addr_end + 2), f"{date} {time}", font=font_meta, fill=(220,220,220,230))
        # Lat/lon
        draw.text((text_x, y_addr_end + 2 + font_size_meta + 6), f"{latitude:.5f}, {longitude:.5f}", font=font_meta, fill=(180,180,180,210))
        # --- Composite overlay onto image ---
        out_img = img.convert("RGBA")
        out_img.alpha_composite(overlay, (0, height - overlay_height))
        return out_img.convert("RGB")
    else:  # Portrait (9x16, etc)
        overlay_width = int(width * 0.92)
        overlay_height = int(height * 0.38)
        overlay = Image.new("RGBA", (overlay_width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        radius = overlay_width // 8
        draw.rounded_rectangle([(0, height - overlay_height), (overlay_width, height)], radius=radius, fill=(28, 28, 28, 210))
        # --- Map on top ---
        map_target_width = overlay_width - 32
        map_target_height = int(map_img.height * (map_target_width / map_img.width))
        if map_target_height > overlay_height // 2:
            map_target_height = overlay_height // 2
            map_target_width = int(map_img.width * (map_target_height / map_img.height))
        map_resized = map_img.resize((map_target_width, map_target_height), resample=Image.Resampling.LANCZOS)
        # Add border and shadow
        border = 5
        map_box = Image.new("RGBA", (map_target_width + 2*border, map_target_height + 2*border), (0,0,0,0))
        shadow = Image.new("RGBA", (map_box.width+8, map_box.height+8), (0,0,0,0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            [(4, 4), (shadow.width-4, shadow.height-4)],
            radius=18,
            fill=(0,0,0,80)
        )
        map_box.paste(map_resized, (border, border), map_resized)
        shadow.paste(map_box, (4,4), map_box)
        map_x = (overlay_width - shadow.width) // 2
        overlay.paste(shadow, (map_x, height - overlay_height + 18), shadow)
        # --- Weather icon and temp below map, centered ---
        wx_icon = None
        wx_icon_size = overlay_height // 6
        wx_x = (overlay_width - wx_icon_size) // 2
        wx_y = height - overlay_height + 18 + shadow.height + 8
        if weather_icon_path and Path(weather_icon_path).exists():
            wx_icon = Image.open(weather_icon_path).convert("RGBA").resize((wx_icon_size, wx_icon_size))
            overlay.paste(wx_icon, (wx_x, wx_y), wx_icon)
        # Temp text
        font_size_temp = wx_icon_size // 2 + 4
        try:
            font_temp = ImageFont.truetype("arial.ttf", font_size_temp)
        except Exception:
            font_temp = ImageFont.load_default()
        temp_color = (255, 255, 255, 240)
        draw.text((wx_x + wx_icon_size + 8, wx_y + wx_icon_size//4), temp_str, font=font_temp, fill=temp_color)
        # --- Address, date, time, coords below weather ---
        font_size_addr = max(18, overlay_height // 10)
        font_size_meta = max(14, overlay_height // 16)
        try:
            font_addr = ImageFont.truetype("arialbd.ttf", font_size_addr)
        except Exception:
            font_addr = ImageFont.load_default()
        try:
            font_meta = ImageFont.truetype("arial.ttf", font_size_meta)
        except Exception:
            font_meta = ImageFont.load_default()
        text_x = 32
        text_y = wx_y + wx_icon_size + 12
        max_addr_width = overlay_width - 64
        addr_font_size = font_size_addr
        addr_font = font_addr
        # Shrink font if address is too wide
        while True:
            bbox = addr_font.getbbox(address)
            w = bbox[2] - bbox[0]
            if w <= max_addr_width or addr_font_size <= 12:
                break
            addr_font_size -= 2
            try:
                addr_font = ImageFont.truetype("arialbd.ttf", addr_font_size)
            except Exception:
                addr_font = ImageFont.load_default()
        y_addr_end = draw_wrapped_text(draw, address, addr_font, text_x, text_y, max_addr_width, (255,255,255,255))
        # Date/time
        draw.text((text_x, y_addr_end + 2), f"{date} {time}", font=font_meta, fill=(220,220,220,230))
        # Lat/lon
        draw.text((text_x, y_addr_end + 2 + font_size_meta + 6), f"{latitude:.5f}, {longitude:.5f}", font=font_meta, fill=(180,180,180,210))
        # --- Composite overlay onto image ---
        out_img = img.convert("RGBA")
        out_img.alpha_composite(overlay, (width - overlay_width, 0))
        return out_img.convert("RGB")


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
    def to_deg(value, ref):
        deg = int(abs(value))
        min_ = int((abs(value) - deg) * 60)
        sec = float((abs(value) - deg - min_ / 60) * 3600)
        return ((deg, 1), (min_, 1), (int(sec * 100), 100))
    exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = b'N' if latitude >= 0 else b'S'
    exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = to_deg(latitude, 'lat')
    exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = b'E' if longitude >= 0 else b'W'
    exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = to_deg(longitude, 'lon')
    # DateTime
    dt_str = f"{date} {time}"
    dt_fmt = "%Y-%m-%d %H:%M"
    try:
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
