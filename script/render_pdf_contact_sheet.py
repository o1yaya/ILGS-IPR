import argparse
import math

import pypdfium2 as pdfium
from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("output")
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--thumb-width", type=int, default=280)
    args = parser.parse_args()

    document = pdfium.PdfDocument(args.pdf)
    gap = 18
    label_height = 28
    first_page = document[0].render(scale=0.6).to_pil().convert("RGB")
    thumb_height = round(first_page.height * args.thumb_width / first_page.width)
    rows = math.ceil(len(document) / args.columns)
    canvas_width = args.columns * (args.thumb_width + gap) + gap
    canvas_height = rows * (thumb_height + label_height + gap) + gap
    canvas = Image.new("RGB", (canvas_width, canvas_height), "#dddddd")
    draw = ImageDraw.Draw(canvas)

    for index in range(len(document)):
        page = document[index].render(scale=0.6).to_pil().convert("RGB")
        page = page.resize((args.thumb_width, thumb_height))
        x = gap + (index % args.columns) * (args.thumb_width + gap)
        y = gap + (index // args.columns) * (thumb_height + label_height + gap)
        draw.text((x, y + 5), f"Page {index + 1}", fill="black")
        canvas.paste(page, (x, y + label_height))

    canvas.save(args.output)
    print(f"Rendered {len(document)} pages to {args.output}")


if __name__ == "__main__":
    main()
