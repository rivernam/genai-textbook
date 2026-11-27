# 설비 문서 검색 도구 · 문서 본문을 절 단위로 찾습니다
# 사용: python tools/search_rag.py "캐필러리 교체 주기" [개수]    SL-PKG 설비 문서 23건(data/docs)
#   청크는 3일차와 같이 ## 절 단위로 자르고, 순위는 4일차 키워드 검색(BM25, 단어 + 두 글자 조각)으로 매깁니다
#   결과의 doc_id와 version이 근거 문서번호입니다
import csv, math, os, re, sys, unicodedata
from collections import Counter
from _common import show, path

args = sys.argv[1:]
docs_dir = 'docs'
if args[:1] == ['--docs']:
    docs_dir = {'mission': 'docs'}.get(args[1], args[1])
    args = args[2:]
top_k = int(args[-1]) if len(args) > 1 and args[-1].isdigit() else 4
query = ' '.join(args[:-1] if len(args) > 1 and args[-1].isdigit() else args)
manifest = 'docs_manifest.csv'
META = {unicodedata.normalize('NFC', row['file']): row
        for row in csv.DictReader(open(path('data', manifest), encoding='utf-8-sig'))}

chunks = []                       # (doc_id, version, type, date, section, text)
for filename in sorted(os.listdir(path('data', docs_dir))):
    filename = unicodedata.normalize('NFC', filename)
    if not filename.endswith('.md') or filename not in META:
        continue
    meta_row = META[filename]
    head, *sections = re.split(r'\n(?=## )', open(path('data', docs_dir, filename), encoding='utf-8').read())
    for section_text in [head] + sections:
        section_text = section_text.strip()
        if sections and section_text == head.strip():
            section_text = '\n'.join(section_text.splitlines()[:8])  # 머리 청크는 제목, 메타까지만
        chunks.append((meta_row['doc_id'], meta_row['version'], meta_row['type'], meta_row['date'],
                       section_text.splitlines()[0].lstrip('# ').strip(), section_text[:1200]))
TITLE = {}
for chunk in chunks:
    TITLE.setdefault((chunk[0], chunk[1]), chunk[4])     # 첫 청크의 절 제목 = 문서 제목


def tokenize(text):                                       # 4일차 키워드 검색과 같은 토큰 나누기
    text = re.sub(r'[^\w가-힣]+', ' ', text.lower())
    tokens = []
    for word in text.split():
        tokens.append(word)
        if len(word) > 2 and re.match(r'^[가-힣]+$', word):
            tokens += [word[i:i + 2] for i in range(len(word) - 1)]
    return tokens


docs = [tokenize(TITLE[chunk[0], chunk[1]] + ' ' + chunk[5]) for chunk in chunks]
n_chunks, avg_len = len(docs), sum(map(len, docs)) / len(docs)
doc_freq = Counter(term for doc in docs for term in set(doc))
idf = {term: math.log((n_chunks - freq + 0.5) / (freq + 0.5)) for term, freq in doc_freq.items()}
floor = 0.25 * sum(idf.values()) / len(idf)               # 흔한 단어의 음수 idf를 바닥값으로(rank_bm25와 같음)
idf = {term: (weight if weight > 0 else floor) for term, weight in idf.items()}
query_terms = tokenize(query)
scores = []
for doc in docs:
    term_freq = Counter(doc)
    section_text = sum(idf.get(term, 0) * term_freq[term] * 2.5 / (term_freq[term] + 1.5 * (0.25 + 0.75 * len(doc) / avg_len)) for term in query_terms)
    scores.append(section_text)
top_ids = sorted(range(n_chunks), key=lambda i: -scores[i])[:top_k]
show({'docs': docs_dir, 'chunks': n_chunks,
      'hits': [{'doc_id': chunks[i][0], 'version': chunks[i][1], 'type': chunks[i][2], 'date': chunks[i][3],
                'section': chunks[i][4], 'score': round(scores[i], 2), 'text': chunks[i][5][:600]}
               for i in top_ids]})
