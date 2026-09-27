from __future__ import annotations
from pathlib import Path
import hashlib

SUPPORTED={".png",".jpg",".jpeg",".webp"}

def validate_image(path: str|Path, expected_width: int|None=None, expected_height: int|None=None)->dict:
    p=Path(path)
    result={"path":str(p),"exists":p.exists(),"readable":False,"format_ok":False,
            "dimensions_ok":True,"sha256":None}
    if not p.exists() or p.suffix.lower() not in SUPPORTED:
        result["verified"]=False
        return result
    try:
        from PIL import Image
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            result["readable"]=True
            result["format_ok"]=im.format is not None
            if expected_width and expected_height:
                result["dimensions_ok"]=(im.width==expected_width and im.height==expected_height)
        result["sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception as exc:
        result["error"]=str(exc)
    result["verified"]=all([result["exists"],result["readable"],result["format_ok"],result["dimensions_ok"],bool(result["sha256"])])
    return result
