from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def generate_placeholder(path: Path, text: str, size=(1024,1024)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', size, (240,240,240))
    draw = ImageDraw.Draw(img)
    msg = (text or "Generated")[:100]
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0,0), msg, font=font)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((size[0]-w)//2,(size[1]-h)//2), msg, fill=(20,20,20), font=font)
    img.save(path)

