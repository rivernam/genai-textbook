"""강의안 PDF를 쪽 단위 텍스트(slides.txt)와 쪽 이미지(img/pNNN.png)로 뽑는다.

사용법: python extract.py <pdf> <outdir> [--images A-B]
"""
import argparse
import subprocess
from pathlib import Path

IMAGE_WIDTH = 1200


def extract_text(pdf: Path, outdir: Path) -> int:
    raw = subprocess.run(
        ['pdftotext', '-enc', 'UTF-8', '-layout', str(pdf), '-'],
        check=True, capture_output=True,
    ).stdout.decode('utf-8', errors='replace')
    pages = raw.split('\f')
    if pages and not pages[-1].strip():
        pages.pop()
    parts = [f'===== p.{i} =====\n{page.rstrip()}\n' for i, page in enumerate(pages, 1)]
    (outdir / 'slides.txt').write_text('\n'.join(parts), encoding='utf-8')
    return len(pages)


def extract_images(pdf: Path, outdir: Path, first: int, last: int) -> None:
    import pypdfium2 as pdfium

    imgdir = outdir / 'img'
    imgdir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf))
    for number in range(first, min(last, len(doc)) + 1):
        page = doc[number - 1]
        scale = IMAGE_WIDTH / page.get_width()
        page.render(scale=scale).to_pil().save(imgdir / f'p{number:03d}.png')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    parser.add_argument('outdir', type=Path)
    parser.add_argument('--images', help='이미지로 뽑을 쪽 범위. 예: 11-175')
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    count = extract_text(args.pdf, args.outdir)
    print(f'텍스트 {count}쪽')
    if args.images:
        first, last = (int(x) for x in args.images.split('-'))
        extract_images(args.pdf, args.outdir, first, last)
        print(f'이미지 p.{first}-{last}')


if __name__ == '__main__':
    main()
