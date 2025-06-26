from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from io import BytesIO
from typing import Optional
import requests
import piexif


def overlay_with_map_and_info(img: Image.Image, latitude: float, longitude: float, date: str, time: str, map_image_path: Optional[str] = None) -> Image.Image:
    """
    Overlay a semi-circular/rounded rectangle with map, date, time, and location at the bottom of the image.
    If map_image_path is provided, use it as the map overlay (screenshot from frontend, e.g. #map), else generate OSM static map with pin.
    """
    # Use screenshot if provided
    if map_image_path:
        try:
            map_img = Image.open(map_image_path).convert("RGBA")
        except Exception:
            map_img = Image.new("RGBA", (340, 180), (200, 200, 200, 255))
        # No pin or OSM download if screenshot is provided
    else:
        # Fallback: Download static map image (OSM Static Map, no API key required)
        map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={latitude},{longitude}&zoom=10&size=340x180&maptype=mapnik"
        try:
            resp = requests.get(map_url, timeout=5)
            resp.raise_for_status()
            map_img = Image.open(BytesIO(resp.content)).convert("RGBA")
        except Exception:
            map_img = Image.new("RGBA", (340, 180), (200, 200, 200, 255))
        # Draw a red pin at the center of the map image
        pin_x = map_img.width // 2
        pin_y = map_img.height // 2
        pin_radius = max(10, map_img.height // 12)
        pin_color = (220, 40, 40, 255)
        pin_outline = (255, 255, 255, 255)
        draw_map = ImageDraw.Draw(map_img)
        draw_map.ellipse([
            (pin_x - pin_radius, pin_y - pin_radius),
            (pin_x + pin_radius, pin_y + pin_radius)
        ], fill=pin_color, outline=pin_outline, width=3)
        triangle = [
            (pin_x, pin_y + pin_radius),
            (pin_x - pin_radius // 2, pin_y + pin_radius * 2),
            (pin_x + pin_radius // 2, pin_y + pin_radius * 2)
        ]
        draw_map.polygon(triangle, fill=pin_color)
    # Add rounded corners to map
    corner_radius = 22
    mask = Image.new("L", map_img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), map_img.size], radius=corner_radius, fill=255)
    map_img.putalpha(mask)
    # Add border to map
    border_width = 4
    bordered_map = Image.new("RGBA", (map_img.width + 2*border_width, map_img.height + 2*border_width), (0,0,0,0))
    border_draw = ImageDraw.Draw(bordered_map)
    border_draw.rounded_rectangle(
        [(0, 0), (bordered_map.width-1, bordered_map.height-1)],
        radius=corner_radius+border_width,
        fill=(40, 40, 40, 220)
    )
    bordered_map.paste(map_img, (border_width, border_width), map_img)
    # Add shadow
    shadow = Image.new("RGBA", (bordered_map.width+8, bordered_map.height+8), (0,0,0,0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [(4, 4), (shadow.width-4, shadow.height-4)],
        radius=corner_radius+border_width+2,
        fill=(0,0,0,90)
    )
    shadow.paste(bordered_map, (4,4), bordered_map)
    # Prepare overlay
    width, height = img.size
    overlay_height = int(height * 0.28)
    overlay = Image.new("RGBA", (width, overlay_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Draw semi-transparent rounded rectangle
    radius = overlay_height // 2
    draw.rounded_rectangle([(0, 0), (width, overlay_height)], radius=radius, fill=(30, 30, 30, 180))
    # Paste map (with shadow) on left, vertically centered
    map_target_height = overlay_height - 24
    from PIL import Image as PILImage
    map_target_width = int(shadow.width * (map_target_height / shadow.height))
    map_resized = shadow.resize((map_target_width, map_target_height), resample=PILImage.Resampling.LANCZOS)
    map_y = (overlay_height - map_target_height) // 2
    overlay.paste(map_resized, (16, map_y), map_resized)
    # Add text (date, time, lat/lon)
    font_size = max(18, overlay_height // 7)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    text_x = map_target_width + 36
    text_y = map_y + 8
    text_color = (255, 255, 255, 230)
    draw.text((text_x, text_y), f"Date: {date}", font=font, fill=text_color)
    draw.text((text_x, text_y + font_size + 6), f"Time: {time}", font=font, fill=text_color)
    draw.text((text_x, text_y + 2 * (font_size + 6)), f"Lat: {latitude:.5f}", font=font, fill=text_color)
    draw.text((text_x, text_y + 3 * (font_size + 6)), f"Lon: {longitude:.5f}", font=font, fill=text_color)
    # Composite overlay onto image
    out_img = img.convert("RGBA")
    out_img.alpha_composite(overlay, (0, height - overlay_height))
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
