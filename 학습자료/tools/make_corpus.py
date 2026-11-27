"""문서 코퍼스의 PDF, HTML 문서와 문서 목록을 만든다.

사용법: python tools/make_corpus.py
입력:  작업/코퍼스_원본/*.md    PDF, HTML로 낼 문서의 원본(front matter의 format이 pdf, pdf-scan, html)
       노트북/data/corpus/*.md  Markdown 문서(직접 작성한 것을 그대로 둔다)
출력:  노트북/data/corpus/<id>.pdf, <id>.html
       노트북/data/corpus_목록.csv  모든 문서의 메타데이터(문서 번호, 개정, 상태 등)

문서 내용은 모두 직접 작성했다. 이 스크립트는 형식만 바꾼다. PDF를 만들려면 fpdf2와
맑은 고딕 글꼴(C:/Windows/Fonts/malgun.ttf)이 필요하다. 교재 독자는 이 스크립트를 실행하지 않는다.

format 값
  pdf       글자가 든 PDF. 쪽마다 머리말(문서 번호)과 꼬리말(쪽 번호)을 넣는다
  pdf-scan  글자를 그림으로 그린 PDF(스캔본 흉내). PDF에서 글자를 뽑을 수 없다
  html      사내 위키에서 내보낸 HTML 흉내. 메뉴와 꼬리말이 본문 앞뒤에 붙는다
원본에서 "[흰 글씨] "로 시작하는 줄은 PDF에 흰색 작은 글씨로 넣는다(15장의 오염 문서).
"""
import csv
import datetime
import html
import io
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '작업' / '코퍼스_원본'
CORPUS = ROOT / '노트북' / 'data' / 'corpus'
MANIFEST = ROOT / '노트북' / 'data' / 'corpus_목록.csv'
FONT = 'C:/Windows/Fonts/malgun.ttf'
FONT_BOLD = 'C:/Windows/Fonts/malgunbd.ttf'
WHITE = '[흰 글씨] '
FIELDS = ['id', 'file', 'format', 'doc_no', 'title', 'type', 'dept', 'revision', 'date', 'status', 'superseded_by']
FIXED_DATE = datetime.datetime(2026, 11, 27, tzinfo=datetime.timezone.utc)


def split_front_matter(text):
    """'---'로 둘러싼 front matter를 dict로, 나머지를 본문으로 돌려준다."""
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise ValueError('front matter가 없습니다')
    meta = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(':')
        meta[key.strip()] = value.strip()
    return meta, text[match.end():]


def blocks(body):
    """Markdown 본문을 (종류, 내용) 목록으로 나눈다. 이 코퍼스에 쓴 문법만 다룬다."""
    result, paragraph, table = [], [], []

    def flush():
        if paragraph:
            result.append(('p', ' '.join(paragraph)))
            paragraph.clear()
        if table:
            rows = [[cell.strip() for cell in line.strip().strip('|').split('|')] for line in table]
            result.append(('table', [row for row in rows if not all(set(cell) <= {'-'} for cell in row)]))
            table.clear()

    for line in body.splitlines():
        if line.startswith('|'):
            if paragraph:
                flush()
            table.append(line)
            continue
        if table:
            flush()
        if not line.strip():
            flush()
        elif line.startswith('# '):
            flush()
            result.append(('h1', line[2:]))
        elif line.startswith('## '):
            flush()
            result.append(('h2', line[3:]))
        elif re.match(r'(- |\d+\. )', line):
            flush()
            result.append(('li', line))
        elif line.startswith(WHITE):
            flush()
            result.append(('white', line[len(WHITE):]))
        else:
            paragraph.append(line.strip())
    flush()
    return result


def make_pdf(meta, body, path):
    from fpdf import FPDF

    class Document(FPDF):
        def header(self):
            self.set_font('malgun', size=8)
            self.set_text_color(90, 90, 90)
            self.cell(0, 6, f"{meta['doc_no']}  개정 {meta['revision']}  {meta['dept']}  사내 한정", align='R')
            self.ln(10)

        def footer(self):
            self.set_y(-12)
            self.set_font('malgun', size=8)
            self.set_text_color(90, 90, 90)
            self.cell(0, 6, f'{self.page_no()}/{{nb}}  출력본은 최신 개정본이 아닐 수 있습니다', align='C')

    pdf = Document(format='A4')
    pdf.set_creation_date(FIXED_DATE)
    pdf.set_title(meta['title'])
    pdf.add_font('malgun', fname=FONT)
    pdf.add_font('malgun', style='B', fname=FONT_BOLD)
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()
    for kind, content in blocks(body):
        pdf.set_text_color(0, 0, 0)
        if kind == 'h1':
            pdf.set_font('malgun', 'B', 16)
            pdf.multi_cell(0, 9, content)
            pdf.ln(3)
        elif kind == 'h2':
            pdf.ln(2)
            pdf.set_font('malgun', 'B', 12)
            pdf.multi_cell(0, 7, content)
            pdf.ln(1)
        elif kind == 'table':
            pdf.set_font('malgun', size=9)
            with pdf.table(line_height=6, text_align='LEFT') as table:
                for row in content:
                    cells = table.row()
                    for cell in row:
                        cells.cell(cell)
            pdf.ln(2)
        elif kind == 'white':
            pdf.set_font('malgun', size=5)
            pdf.set_text_color(255, 255, 255)
            pdf.multi_cell(0, 3, content)
        else:
            pdf.set_font('malgun', size=10)
            pdf.multi_cell(0, 6, content)
            pdf.ln(1 if kind == 'li' else 2)
    pdf.output(str(path))


def make_scanned_pdf(meta, body, path):
    """글자를 그림으로 그려 넣은 PDF. 스캔한 결재본처럼 글자 정보가 없다."""
    from fpdf import FPDF
    from PIL import Image, ImageDraw, ImageFont

    width, height, margin = 1240, 1754, 110          # A4를 150dpi로 그린 크기
    regular = ImageFont.truetype(FONT, 26)
    bold = ImageFont.truetype(FONT_BOLD, 34)
    page = Image.new('L', (width, height), 250)
    draw = ImageDraw.Draw(page)
    y = margin
    for kind, content in blocks(body):
        if kind == 'table':
            column = (width - 2 * margin) // len(content[0])
            for row in content:
                for index, cell in enumerate(row):
                    draw.rectangle([margin + index * column, y, margin + (index + 1) * column, y + 44], outline=40)
                    draw.text((margin + index * column + 12, y + 7), cell, font=regular, fill=30)
                y += 44
            y += 20
            continue
        font = bold if kind in ('h1', 'h2') else regular
        line = ''
        for word in content.split(' '):
            if draw.textlength(line + word, font=font) > width - 2 * margin:
                draw.text((margin, y), line, font=font, fill=30)
                y += 42
                line = ''
            line += word + ' '
        draw.text((margin, y), line, font=font, fill=30)
        y += 60 if kind in ('h1', 'h2') else 44
    page = page.rotate(0.6, fillcolor=250)            # 스캔할 때 종이가 조금 기운 것처럼
    buffer = io.BytesIO()
    page.save(buffer, format='PNG')
    pdf = FPDF(format='A4')
    pdf.set_creation_date(FIXED_DATE)
    pdf.add_page()
    pdf.image(buffer, x=0, y=0, w=210, h=297)
    pdf.output(str(path))


WIKI = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="doc-id" content="{id}">
<meta name="revision" content="{revision}">
<title>{title} - 사내 위키</title>
<style>body {{ font-family: sans-serif; max-width: 860px; margin: auto; }} table {{ border-collapse: collapse; }} td, th {{ border: 1px solid #999; padding: 4px 8px; }}</style>
</head>
<body>
<nav class="wiki-menu">사내 위키 | 홈 | 최근 바뀜 | 문서 검색 | 로그아웃</nav>
<div class="breadcrumb">홈 &gt; {type} &gt; {doc_no}</div>
<main>
<p class="doc-info">문서 번호 {doc_no} | 개정 {revision} | 관리 부서 {dept} | 시행일 {date}</p>
{content}
</main>
<footer>이 페이지는 사내 위키에서 내보냈습니다. 내보낸 뒤 바뀐 내용은 반영되지 않습니다. 문의: 생산관리팀</footer>
</body>
</html>
"""


def make_html(meta, body, path):
    import markdown
    content = markdown.markdown(body, extensions=['tables'])
    fields = {key: html.escape(value) for key, value in meta.items()}
    path.write_text(WIKI.format(content=content, **fields), encoding='utf-8')


def manifest_row(meta, path):
    row = {key: meta.get(key, '') for key in FIELDS}
    row['file'] = path.name
    row['format'] = {'.md': 'md', '.html': 'html', '.pdf': 'pdf'}[path.suffix]
    return row


def main():
    logging.getLogger('fontTools').setLevel(logging.ERROR)   # 글꼴 일부만 넣을 때 나오는 경고를 끈다
    rows = []
    for source in sorted(SOURCE.glob('*.md')):
        meta, body = split_front_matter(source.read_text(encoding='utf-8'))
        kind = meta['format']
        target = CORPUS / f"{meta['id']}.{'html' if kind == 'html' else 'pdf'}"
        {'pdf': make_pdf, 'pdf-scan': make_scanned_pdf, 'html': make_html}[kind](meta, body, target)
        rows.append(manifest_row(meta, target))
    for path in sorted(CORPUS.glob('*.md')):
        meta, _ = split_front_matter(path.read_text(encoding='utf-8'))
        rows.append(manifest_row(meta, path))
    rows.sort(key=lambda row: row['id'])
    with open(MANIFEST, 'w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    formats = {}
    for row in rows:
        formats[row['format']] = formats.get(row['format'], 0) + 1
    print(f'문서 {len(rows)}건', formats)


if __name__ == '__main__':
    sys.exit(main())
