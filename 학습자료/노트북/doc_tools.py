"""사내 문서 코퍼스(data/corpus)를 읽고 검색하는 함수와 그 도구 정의.

13장 "AI 에이전트"의 예제와 관통 프로젝트 5, 6단계에서 씁니다. 문서는 모두 가상 회사의 문서입니다.

    TOOLS                  에이전트에 줄 도구 정의 두 개(search_docs, read_doc). llm.send()의 tools 인자 형식
    search_docs(query)     검색어와 겹치는 낱말 조각이 많은 문서부터 5건의 요약을 돌려줍니다(키워드 검색)
    read_doc(doc_id)       문서 하나의 본문을 돌려줍니다
    CATALOG                문서 번호를 키로 한 문서 목록(corpus_목록.csv의 행)

PDF와 HTML 문서를 읽으려면 pypdf와 beautifulsoup4가 필요합니다.
    python -m pip install pypdf beautifulsoup4
"""
import csv
import math
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'
MAX_CHARS = 4000           # read_doc이 돌려주는 본문의 최대 글자 수. 도구 결과도 입력 토큰이 되므로 제한합니다

with open(DATA / 'corpus_목록.csv', encoding='utf-8-sig') as file:     # 엑셀에서 열리도록 BOM이 붙어 있습니다
    CATALOG = {row['id']: row for row in csv.DictReader(file)}


def _read_text(row):
    """문서 파일에서 글을 뽑습니다. Markdown은 front matter를 빼고, HTML은 태그를 빼고, PDF는 쪽마다 글을 뽑습니다"""
    path = DATA / 'corpus' / row['file']
    if row['format'] == 'md':
        text = path.read_text(encoding='utf-8')
        return re.sub(r'\A---\n.*?\n---\n', '', text, flags=re.S).strip()
    if row['format'] == 'html':
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        for tag in soup(['script', 'style']):
            tag.decompose()
        return re.sub(r'\n\s*\n+', '\n', soup.get_text('\n')).strip()
    from pypdf import PdfReader
    return '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages).strip()


TEXTS = {doc_id: _read_text(row) for doc_id, row in CATALOG.items()}


def _terms(text):
    """검색에 쓰는 낱말 조각. 한글은 두 글자씩 끊고, 영문과 숫자는 코드(E-2210, W-07)째로 씁니다"""
    terms = []
    for word in re.findall(r'[A-Za-z0-9]+(?:[-.][A-Za-z0-9]+)*|[가-힣]+', text.lower()):
        if re.fullmatch(r'[가-힣]{2,}', word):
            terms += [word[i:i + 2] for i in range(len(word) - 1)]
        else:
            terms.append(word)
    return terms


_COUNTS = {doc_id: Counter(_terms(f"{doc_id} {CATALOG[doc_id]['title']}\n{text}")) for doc_id, text in TEXTS.items()}
_LENGTH = {doc_id: sum(counts.values()) for doc_id, counts in _COUNTS.items()}
_AVERAGE = sum(_LENGTH.values()) / len(_LENGTH)
_DF = Counter(term for counts in _COUNTS.values() for term in counts)


def _score(query_terms, doc_id, k1=1.2, b=0.75):
    """BM25 점수(7장에서 설명합니다). 드문 낱말이 많이 겹칠수록 높습니다"""
    counts, total = _COUNTS[doc_id], 0.0
    for term in set(query_terms):
        if term in counts:
            idf = math.log(1 + (len(_COUNTS) - _DF[term] + 0.5) / (_DF[term] + 0.5))
            tf = counts[term]
            total += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * _LENGTH[doc_id] / _AVERAGE))
    return total


def _best_line(doc_id, query_terms):
    """본문에서 검색어 조각이 가장 많이 든 줄을 160자까지 돌려줍니다"""
    wanted = set(query_terms)
    lines = [line.strip() for line in TEXTS[doc_id].splitlines() if line.strip()]
    best = max(lines, key=lambda line: len(wanted & set(_terms(line))), default='')
    return best[:160]


def _header(doc_id):
    row = CATALOG[doc_id]
    return (f"[{doc_id}] {row['title']} ({row['type']}, {row['dept']}, 개정 {row['revision']}, "
            f"{row['date']}, {row['status']})")


def search_docs(query, k=5):
    """검색어와 관련이 높은 문서 k건의 머리글(번호, 제목, 종류, 부서, 개정, 날짜, 상태)과 본문 한 줄을 돌려줍니다"""
    query_terms = _terms(query)
    if not query_terms:
        raise ValueError('검색어가 비어 있습니다')
    scored = sorted(((_score(query_terms, doc_id), doc_id) for doc_id in TEXTS), reverse=True)
    found = [doc_id for score, doc_id in scored[:k] if score > 0]
    if not found:
        return '검색 결과가 없습니다.'
    return '\n'.join(f'{_header(doc_id)}\n  {_best_line(doc_id, query_terms)}' for doc_id in found)


def read_doc(doc_id):
    """문서 번호로 문서 하나의 머리글과 본문을 돌려줍니다. 본문이 길면 MAX_CHARS 글자에서 자릅니다"""
    if doc_id not in TEXTS:
        raise ValueError(f'없는 문서 번호입니다: {doc_id}. search_docs 결과에 나온 번호만 쓸 수 있습니다')
    text = TEXTS[doc_id] or '(본문에서 글을 뽑지 못했습니다. 스캔한 문서일 수 있습니다)'
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + f'\n(이하 생략. 전체 {len(TEXTS[doc_id]):,}자)'
    return f'{_header(doc_id)}\n{text}'


TOOLS = [
    {'name': 'search_docs',
     'description': ('후공정 회사의 사내 문서 120건(작업 표준, 설비 매뉴얼, 품질 이슈 보고서, 회의록, 공지, 교육 자료, '
                     '안전 규정)을 키워드로 검색한다. 관련이 높은 순서로 5건의 문서 번호, 제목, 종류, 부서, 개정, 날짜, '
                     '상태(유효 또는 폐기)와 본문 한 줄을 돌려준다. 본문 전체는 돌려주지 않으므로 read_doc으로 읽는다. '
                     '검색어는 문서에 나올 법한 낱말로 짧게 쓴다.'),
     'input_schema': {'type': 'object', 'properties': {
         'query': {'type': 'string', 'description': '검색어. 예: 와이어 풀 강도 하한'}},
         'required': ['query']}},
    {'name': 'read_doc',
     'description': '문서 번호로 사내 문서 하나의 본문을 읽는다. search_docs 결과에 나온 문서 번호만 쓴다.',
     'input_schema': {'type': 'object', 'properties': {
         'doc_id': {'type': 'string', 'description': '문서 번호. 예: SOP-WB-001'}},
         'required': ['doc_id']}},
]
