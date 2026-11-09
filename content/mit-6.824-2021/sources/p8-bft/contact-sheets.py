"""Local review sheets; original pages are kept alongside them."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent / 'rendered'
for first in range(1, 24, 4):
    pages = [Image.open(root / f'slides-{n:02}.png').convert('RGB')
             for n in range(first, min(first + 4, 24))]
    width, height = pages[0].size
    sheet = Image.new('RGB', (width * 2, (height + 26) * 2), 'white')
    draw = ImageDraw.Draw(sheet)
    for i, page in enumerate(pages):
        x, y = (i % 2) * width, (i // 2) * (height + 26)
        sheet.paste(page, (x, y + 26))
        draw.text((x + 12, y + 5), f'PDF page {first+i}', fill='black')
    sheet.save(root / f'slides-sheet-{first:02}.png')
