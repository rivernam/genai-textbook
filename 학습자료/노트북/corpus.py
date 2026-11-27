"""문서 코퍼스(data/corpus)를 읽고, 청크로 나누고, 검색하는 함수.

7~9장의 예제와 관통 프로젝트 3, 4단계가 씁니다. 글을 벡터로 바꾸는 일은 embed.py가 맡습니다.

    catalog()                  문서 목록(corpus_목록.csv)을 {id: 메타데이터}로 읽습니다
    evalset()                  평가셋(evalset.json)의 질문 목록
    read_text(doc_id)          문서 파일에서 본문 글을 뽑습니다. 형식마다 파서가 다릅니다(8장)
    split_chunks(doc_id, text) 본문을 절 단위의 청크로 나누고 메타데이터를 붙입니다(8장)
    words(text)                키워드 검색에 쓰는 토큰 목록(7장)
    KeywordIndex, VectorIndex  키워드 검색(BM25)과 임베딩 검색의 인덱스(7장)
"""
import csv
import json
import re
from html.parser import HTMLParser
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'


def catalog():
    """문서 목록을 {id: 메타데이터}로 돌려줍니다. 열: id, file, format, doc_no, title, type, dept, revision, date, status, superseded_by"""
    with open(DATA / 'corpus_목록.csv', encoding='utf-8-sig', newline='') as file:
        return {row['id']: row for row in csv.DictReader(file)}


def evalset():
    """평가셋의 질문 목록. 키의 뜻은 data/README.md에 있습니다"""
    return json.loads((DATA / 'evalset.json').read_text(encoding='utf-8'))


# ---------- 형식마다 다른 파서 (8장) ----------

class _MainText(HTMLParser):
    """HTML의 <main> 안의 글만 모읍니다. 메뉴(nav), 경로 표시, 꼬리말(footer)은 본문이 아니므로 뺍니다.

    제목(h1~h3)은 Markdown 제목(#)으로, 표의 한 행은 칸을 " | "로 이은 한 줄로 바꿉니다.
    화면에 보이지 않게 숨긴 요소(display:none)의 글도 모읍니다. 파서는 화면을 그리지 않기 때문입니다(15장).
    """

    def __init__(self):
        super().__init__()
        self.lines, self.line, self.cells, self.depth = [], '', None, 0

    def handle_starttag(self, tag, attrs):
        if tag == 'main':
            self.depth += 1
        elif self.depth and tag in ('h1', 'h2', 'h3'):
            self.line = '#' * int(tag[1]) + ' '
        elif self.depth and tag == 'tr':
            self.cells = []

    def handle_endtag(self, tag):
        if tag == 'main':
            self.depth -= 1
        elif self.depth and tag in ('td', 'th') and self.cells is not None:
            self.cells.append(self.line.strip())
            self.line = ''
        elif self.depth and tag == 'tr':
            self.lines.append('| ' + ' | '.join(self.cells) + ' |')
            self.cells = None
        elif self.depth and tag in ('p', 'li', 'h1', 'h2', 'h3', 'div') and self.line.strip():
            self.lines.append(('- ' if tag == 'li' else '') + self.line.strip())
            self.line = ''

    def handle_data(self, data):
        if self.depth:
            self.line += re.sub(r'\s+', ' ', data)


def _pdf_text(path):
    """PDF의 쪽마다 글을 뽑고, 쪽마다 되풀이되는 머리말(첫 줄)과 꼬리말(쪽 번호 줄)을 뺍니다. 쪽은 빈 줄로 잇습니다"""
    from pypdf import PdfReader
    pages = []
    for page in PdfReader(str(path)).pages:
        lines = (page.extract_text() or '').splitlines()
        if lines and re.match(r'[A-Z]+-[\w-]+ +개정 \d+', lines[0]):        # 머리말: 문서 번호, 개정, 부서
            lines = lines[1:]
        if lines and re.match(r'\d+/\d+ ', lines[-1]):                      # 꼬리말: 쪽 번호와 안내 문구
            lines = lines[:-1]
        pages.append('\n'.join(lines))
    return '\n\n'.join(pages).strip()


def read_text(doc_id, info=None):
    """문서의 본문 글. Markdown은 front matter를 빼고, HTML은 <main>만, PDF는 머리말과 꼬리말을 뺍니다.

    스캔한 PDF처럼 글자가 그림으로만 들어 있으면 빈 문자열을 돌려줍니다.
    """
    info = info or catalog()[doc_id]
    path = DATA / 'corpus' / info['file']
    if info['format'] == 'md':
        return re.sub(r'^---\n.*?\n---\n', '', path.read_text(encoding='utf-8'), flags=re.S).strip()
    if info['format'] == 'html':
        parser = _MainText()
        parser.feed(path.read_text(encoding='utf-8'))
        return '\n'.join(parser.lines).strip()
    return _pdf_text(path)


# ---------- 청크 분할과 메타데이터 (8장) ----------

def split_chunks(doc_id, text, info, max_chars=600):
    """본문을 "## " 제목마다 나눈 청크의 목록. 청크마다 문서 제목과 절 제목을 앞에 붙이고 메타데이터를 답니다.

    절이 max_chars보다 길면 줄 단위로 다시 나눕니다. 제목이 없는 문서(PDF 등)는 줄 단위로만 나눕니다.
    """
    sections, heading, lines = [], '', []
    for line in text.splitlines():
        if line.startswith('## '):
            if any(part.strip() for part in lines):
                sections.append((heading, lines))
            heading, lines = line[3:].strip(), []
        elif not line.startswith('# '):
            lines.append(line)
    if any(part.strip() for part in lines):
        sections.append((heading, lines))
    chunks = []
    for heading, lines in sections:
        pieces, current = [], ''
        for line in lines:
            if current and len(current) + len(line) > max_chars:
                pieces.append(current)
                current = ''
            current += line + '\n'
        if current.strip():
            pieces.append(current)
        for piece in pieces:
            head = f"{info['doc_no']} {info['title']}" + (f' > {heading}' if heading else '')
            chunks.append({'chunk_id': f'{doc_id}#{len(chunks) + 1}', 'doc_id': doc_id, 'title': info['title'],
                           'section': heading, 'text': f'{head}\n{piece.strip()}',
                           **{key: info[key] for key in ('type', 'dept', 'revision', 'date', 'status')}})
    return chunks


# ---------- 키워드 검색과 벡터 인덱스 (7장) ----------

def words(text):
    """키워드 검색의 토큰. 공백과 문장 부호로 나눈 낱말에, 한글 낱말은 두 글자씩 겹쳐 자른 조각을 더합니다.

    형태소 분석기 없이 조사를 다루는 방법입니다. "블레이드는"과 "블레이드"는 낱말로는 다르지만
    "블레", "레이", "이드" 조각이 겹칩니다.
    """
    tokens = []
    for word in re.findall(r'[0-9A-Za-z][0-9A-Za-z.\-]*[0-9A-Za-z]|[0-9A-Za-z]|[가-힣]+', text.lower()):
        tokens.append(word)
        if re.fullmatch(r'[가-힣]{3,}', word):
            tokens += [word[i:i + 2] for i in range(len(word) - 1)]
    return tokens


class KeywordIndex:
    """키워드 검색(BM25)의 인덱스. 글마다 words()로 나눈 토큰의 빈도를 미리 세어 둡니다"""

    def __init__(self, texts, tokenize=words):
        from rank_bm25 import BM25Okapi
        self.tokenize = tokenize
        self.bm25 = BM25Okapi([tokenize(text) for text in texts])

    def scores(self, question):
        """글마다 BM25 점수. 질문의 토큰이 하나도 없는 글은 0점입니다"""
        return self.bm25.get_scores(self.tokenize(question))


class VectorIndex:
    """임베딩 검색의 인덱스. 글마다 임베딩을 미리 계산해 (글 수 × 차원) 배열로 모아 둡니다"""

    def __init__(self, texts):
        import embed
        self.vectors = embed.passages(list(texts))

    def scores(self, question):
        """글마다 질문과의 코사인 유사도. 벡터의 길이가 1이므로 내적이 곧 코사인 유사도입니다"""
        import embed
        return self.vectors @ embed.query(question)


def rrf(rankings, k=60):
    """여러 검색 결과의 순위를 RRF로 합칩니다. rankings는 id 목록의 목록이고, 합친 id 목록을 돌려줍니다(9장)"""
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item] = scores.get(item, 0.0) + 1 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


class Search:
    """청크 목록과 두 인덱스를 묶은 검색기. search()가 청크 dict의 목록을 점수 순으로 돌려줍니다"""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        texts = [chunk['text'] for chunk in self.chunks]
        self.keyword, self.vector = KeywordIndex(texts), VectorIndex(texts)

    def ranking(self, question, method='embedding', where=None):
        """조건(where)에 맞는 청크의 번호를 점수 순으로 돌려줍니다. method: embedding, keyword, hybrid"""
        import numpy as np
        allowed = [i for i, chunk in enumerate(self.chunks) if where is None or where(chunk)]
        if method == 'hybrid':
            return rrf([self.ranking(question, 'embedding', where), self.ranking(question, 'keyword', where)])
        scores = (self.vector if method == 'embedding' else self.keyword).scores(question)
        return sorted(allowed, key=lambda i: -scores[i])

    def search(self, question, k=4, method='embedding', where=None):
        """상위 k개 청크. where는 청크 dict를 받아 참과 거짓을 돌려주는 함수입니다(메타데이터 필터, 8장)"""
        return [self.chunks[i] for i in self.ranking(question, method, where)[:k]]


def load_chunks(max_chars=600):
    """코퍼스 120건을 모두 읽어 청크 목록으로 돌려줍니다. 글을 뽑지 못한 문서는 failed에 모읍니다"""
    chunks, failed = [], []
    for doc_id, info in catalog().items():
        text = read_text(doc_id, info)
        if not text:
            failed.append(doc_id)
            continue
        chunks += split_chunks(doc_id, text, info, max_chars)
    return chunks, failed
