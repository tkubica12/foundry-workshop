"""Create ignored contact sheets from every actual PDF page for visual review."""

import json
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "instrument-corpus"


def main():
    font_path = Path("C:\\Windows\\Fonts\\segoeui.ttf")
    font = ImageFont.truetype(str(font_path), 22) if font_path.is_file() else ImageFont.load_default(size=22)
    items = json.loads((CORPUS / "catalog.json").read_text(encoding="utf-8"))["instruments"]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    visual = Image.new("RGB", (1800, 20 * 560), "#eeeeee")
    visual_draw = ImageDraw.Draw(visual)
    for i, item in enumerate(items):
        with pymupdf.open(CORPUS / "pdfs" / f'{item["slug"]}.pdf') as pdf:
            sheet = Image.new("RGB", (1500, 2200), "#eeeeee")
            draw = ImageDraw.Draw(sheet)
            draw.text((20, 10), item["name"], fill="#161616", font=font)
            for number, page in enumerate(pdf):
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(0.9, 0.9))
                bitmap = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                bitmap.thumbnail((470, 650))
                px, py = 15 + number % 3 * 500, 55 + number // 3 * 710
                sheet.paste(bitmap, (px, py))
                draw.text((px, py + 655), f"Page {number + 1}", fill="#161616", font=font)
            sheet.save(EVIDENCE / f'{item["slug"]}-contact.png')
            visual_draw.text((15, i * 560 + 5), item["name"], fill="#161616", font=font)
            for col, number in enumerate([0, 6, 7, 8]):
                pixmap = pdf[number].get_pixmap(matrix=pymupdf.Matrix(0.7, 0.7))
                bitmap = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                bitmap.thumbnail((425, 510))
                visual.paste(bitmap, (col * 450 + 10, i * 560 + 40))
    visual.save(EVIDENCE / "all-visual-pages.png")
    print("Rendered 180 PDF pages into 20 per-document contact sheets and one visual overview.")


if __name__ == "__main__":
    main()
