from pathlib import Path
import json
import pypdfium2 as pdfium
from pypdf import PdfReader
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(r'D:\PycharmProjects\PythonProject\ILGS_release-main\output\manuscript\unified_ipr_20261015\render')
pdf = pdfium.PdfDocument(ROOT / 'manuscript.pdf')
reader = PdfReader(ROOT / 'manuscript.pdf')
report = []
for i, page in enumerate(pdf):
    pix = page.render(scale=1.65).to_pil()
    path = ROOT / f'page-{i+1:02d}.png'
    pix.save(path)
    text = reader.pages[i].extract_text()
    report.append({'page': i+1, 'text': text})
    lines = text.splitlines()
    preview = f"{i+1} | {' / '.join(lines[:2])} | {' / '.join(lines[-2:])}"
    print(preview.encode('utf-8', 'backslashreplace').decode('utf-8'))
for start in range(0, len(pdf), 4):
    sheet = Image.new('RGB', (1000, 1480), '#cfcfcf')
    draw = ImageDraw.Draw(sheet)
    for n, i in enumerate(range(start, min(start+4,len(pdf)))):
        img = Image.open(ROOT / f'page-{i+1:02d}.png')
        img.thumbnail((480, 705))
        x, y = (n%2)*500+10, (n//2)*740+25
        sheet.paste(img, (x,y))
        draw.text((x, y-18), str(i+1), fill='black')
    sheet.save(ROOT / f'sheet-{start//4+1}.png')
(ROOT / 'page_text.json').write_text(json.dumps(report,ensure_ascii=True,indent=2),encoding='utf-8')
print('Pages:', len(pdf))
