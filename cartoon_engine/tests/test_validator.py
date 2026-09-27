from pathlib import Path
from PIL import Image
from cartoon_engine.frame_validator import validate_image

def test_validator(tmp_path):
    p=Path(tmp_path)/"x.png"
    Image.new("RGB",(64,64)).save(p)
    r=validate_image(p,64,64)
    assert r["verified"] is True
    assert r["sha256"]
