import pytest
from core.utils import embed_metadata
import os

def test_embed_metadata(tmp_path):
    # Create a simple image
    from PIL import Image
    img_path = tmp_path / "test.jpg"
    img = Image.new('RGB', (10, 10), color='red')
    img.save(img_path)
    out_path = tmp_path / "out.jpg"
    # Run embedding
    embed_metadata(str(img_path), str(out_path), 12.34, 56.78, "2024-01-01", "12:34")
    assert os.path.exists(out_path)
    # Optionally, check EXIF (not required for minimal test)
