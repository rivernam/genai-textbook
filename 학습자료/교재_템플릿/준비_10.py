# 설치: python -m pip install pypdf sentence-transformers
# 10장의 예제와 실습이 쓰는 문서 코퍼스(가상 회사 문서 120건)와 검색 함수입니다
import csv
import html
import re
from collections import Counter
from pathlib import Path

import numpy as np
from pypdf import PdfReader

import embed

CORPUS = Path(DATA) / 'corpus'
with open(f'{DATA}/corpus_목록.csv', encoding='utf-8-sig') as file:
    CATALOG = {row['id']: row for row in csv.DictReader(file)}    # 문서 번호별 메타데이터(제목, 종류, 관리 부서, 상태 등)


def read_doc(doc_id):
    """문서 하나의 본문 글을 돌려줍니다. Markdown은 front matter를 빼고, PDF와 HTML은 글만 뽑습니다(8장)"""
    path = CORPUS / CATALOG[doc_id]['file']
    if path.suffix == '.pdf':
        return '\n'.join(page.extract_text() for page in PdfReader(path).pages)
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.html':
        text = re.sub(r'<(script|style|nav|footer)\b.*?</\1>', ' ', text, flags=re.S)   # 메뉴와 꼬리말을 뺍니다
        text = re.sub(r'<[^>]+>', ' ', text)
        return html.unescape(re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', text)).strip())
    return re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S).strip()


def make_chunks(size=500, overlap=100):
    """유효한 문서를 글자 수 기준으로 잘라 청크 목록을 만듭니다. 청크마다 문서 번호와 제목을 붙입니다"""
    chunks = []
    for doc_id, row in CATALOG.items():
        if row['status'] != '유효':                   # 폐기된 구판은 검색 대상에서 뺍니다(8장 메타데이터 필터)
            continue
        text = read_doc(doc_id)
        for start in range(0, max(len(text) - overlap, 1), size - overlap):
            chunks.append({'id': doc_id, 'text': f"{row['title']}\n{text[start:start + size]}"})
    return chunks


CHUNKS = make_chunks()
VECTORS = embed.passages([chunk['text'] for chunk in CHUNKS])     # 처음 한 번 1~2분 걸립니다


def search(question, k=5):
    """질문과 코사인 유사도가 높은 청크 k개를 돌려줍니다(7장 임베딩 검색)"""
    scores = VECTORS @ embed.query(question)
    return [dict(CHUNKS[index], score=float(scores[index])) for index in np.argsort(-scores)[:k]]


RAG_SYSTEM = '너는 후공정 라인의 사내 문서 도우미다. 주어진 문서에 근거가 있는 것만 답하고, 근거 문서 번호를 적는다.'

# 위키 편집 규칙. 코딩 에이전트로 위키를 만들 때는 이 글을 규칙 파일(14장)에 적습니다
WIKI_RULES = """너는 사내 문서로 위키를 만들고 고치는 편집자다. 다음 규칙을 지킨다.
1. 원본에 있는 내용만 쓴다. 원본에서 확인할 수 없는 내용은 쓰지 않는다.
2. 사실을 적은 문장마다 끝에 출처 문서 번호를 [QIR-2025-031]처럼 붙인다.
3. 원본끼리 값이나 기준이 다르면 한쪽으로 정하지 않는다. 그 문장 앞에 [검토 필요]를 붙이고 양쪽 값과 출처를 모두 적는다.
4. 페이지는 Markdown으로 쓰고 "## 요약", "## 경과", "## 현재 기준", "## 관련 문서" 절을 둔다.
5. 다른 위키 페이지가 될 만한 낱말은 [[페이지 이름]]으로 잇는다."""

# 품질 이슈 보고서에서 뽑을 개체와 관계(온톨로지). 사람이 먼저 정합니다
RELATIONS = ['제품', '발생 설비', '담당 부서', '개정 문서', '상태']
ONTOLOGY = """개체 종류
- 보고서: 품질 이슈 보고서. QIR-2026-014처럼 문서 번호로 적는다
- 제품: QX48, SP8, BG256처럼 제품 코드로 적는다
- 설비: W-07처럼 설비 번호만 적는다. "와이어 본더" 같은 설비 이름은 붙이지 않는다
- 부서: 조립기술팀처럼 팀 이름만 적는다
- 문서: SOP-PL-001처럼 문서 번호만 적는다
관계(주어 → 대상)
- 제품: 보고서 → 불량이 난 제품
- 발생 설비: 보고서 → 불량이 난 설비. 설비가 여럿이면 하나씩 따로 적는다
- 담당 부서: 보고서 → 담당자의 부서
- 개정 문서: 보고서 → 재발 방지를 위해 새로 만들거나 고친 문서
- 상태: 보고서 → "진행 중" 또는 "종결"
규칙: 원본에 적힌 관계만 뽑는다. 해당하는 값이 원본에 없으면 그 관계는 만들지 않는다."""
TRIPLE_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['triples'],
    'properties': {'triples': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['주어', '관계', '대상'],
        'properties': {'주어': {'type': 'string'}, '관계': {'type': 'string', 'enum': RELATIONS},
                       '대상': {'type': 'string'}}}}}}

# 사람이 원본을 읽고 정한 정답 트리플(실습 10-2). 보고서마다 (제품, 담당 부서, 상태, 발생 설비, 개정 문서)
_ANSWERS = {
    'QIR-2025-031': ('QX48', '몰딩기술팀', '종결', 'M-02', 'SOP-MD-001'),
    'QIR-2025-044': ('BG256', '웨이퍼가공팀', '종결', 'D-03', 'MAN-DS-001 SOP-DC-001'),
    'QIR-2026-002': ('QX48', '몰딩기술팀', '종결', 'T-02', 'SOP-TF-001 MAN-TF-001'),
    'QIR-2026-004': ('SP8', '조립기술팀', '종결', 'W-05', ''),
    'QIR-2026-007': ('QX48', '몰딩기술팀', '종결', 'M-01', 'SOP-MD-002'),
    'QIR-2026-009': ('QX48', '품질보증팀', '종결', 'H-04', 'SOP-ESD-001'),
    'QIR-2026-011': ('QX48', '조립기술팀', '종결', 'B-02', 'MAN-DB-001'),
    'QIR-2026-012': ('QX48', '몰딩기술팀', '종결', 'L-02', ''),
    'QIR-2026-013': ('SP8', '조립기술팀', '종결', 'B-05', ''),
    'QIR-2026-014': ('QX48', '조립기술팀', '종결', 'W-07', 'SOP-PL-001 MAN-WB-001'),
    'QIR-2026-015': ('QX48', '테스트기술팀', '종결', 'H-07', 'SOP-PT-002 SOP-PT-001'),
    'QIR-2026-016': ('BG256', '조립기술팀', '종결', 'A-01', 'MAN-BA-001 SOP-BA-001'),
    'QIR-2026-017': ('BG256', '품질보증팀', '종결', 'DC-03', 'SOP-MS-001'),
    'QIR-2026-018': ('BG256', '몰딩기술팀', '진행 중', 'M-03', ''),
    'QIR-2026-019': ('QX48', '몰딩기술팀', '진행 중', 'M-01 M-02', ''),
    'QIR-2026-020': ('SP8', '웨이퍼가공팀', '진행 중', 'G-02', ''),
    'QIR-2026-021': ('BG256', '조립기술팀', '진행 중', 'A-01', ''),
    'QIR-2026-022': ('SP8', '품질보증팀', '진행 중', '', ''),
}
ANSWER_TRIPLES = {(report, relation, target)
                  for report, (product, dept, status, equipment, docs) in _ANSWERS.items()
                  for relation, targets in [('제품', product), ('담당 부서', dept), ('상태', status),
                                            ('발생 설비', equipment), ('개정 문서', docs)]
                  for target in ([targets] if relation in ('제품', '담당 부서', '상태') else targets.split())}


print(f'문서 {len(CATALOG)}건, 청크 {len(CHUNKS)}개')
