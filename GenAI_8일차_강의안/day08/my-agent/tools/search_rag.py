# 설비 문서 검색 도구. 문서 본문을 절 단위로 찾습니다
# 사용: python tools/search_rag.py "캐필러리 교체 주기" [개수]    SL-PKG 설비 문서 23건(data/docs)
#   청크는 3일차와 같이 ## 절 단위로 자르고, 순위는 4일차 키워드 검색(BM25, 단어 + 두 글자 조각)으로 매깁니다
#   결과의 doc_id와 version이 근거 문서번호입니다
import csv, math, os, re, sys, unicodedata
from collections import Counter
from _common import show, path

args = sys.argv[1:]
src = 'docs'
if args[:1] == ['--docs']:
    src = {'mission': 'docs'}.get(args[1], args[1])
    args = args[2:]
k = int(args[-1]) if len(args) > 1 and args[-1].isdigit() else 4
query = ' '.join(args[:-1] if len(args) > 1 and args[-1].isdigit() else args)
manifest = 'docs_manifest.csv'
META = {unicodedata.normalize('NFC', r['file']): r
        for r in csv.DictReader(open(path('data', manifest), encoding='utf-8-sig'))}

chunks = []                       # (doc_id, version, type, date, section, text)
for fn in sorted(os.listdir(path('data', src))):
    fn = unicodedata.normalize('NFC', fn)
    if not fn.endswith('.md') or fn not in META:
        continue
    m = META[fn]
    head, *secs = re.split(r'\n(?=## )', open(path('data', src, fn), encoding='utf-8').read())
    for s in [head] + secs:
        s = s.strip()
        if secs and s == head.strip():
            s = '\n'.join(s.splitlines()[:8])          # 머리 청크는 제목, 메타까지만
        chunks.append((m['doc_id'], m['version'], m['type'], m['date'],
                       s.splitlines()[0].lstrip('# ').strip(), s[:1200]))
TITLE = {}
for c in chunks:
    TITLE.setdefault((c[0], c[1]), c[4])                 # 첫 청크의 절 제목 = 문서 제목


def tok(s):                                               # 4일차 키워드 검색과 같은 토큰 나누기
    s = re.sub(r'[^\w가-힣]+', ' ', s.lower())
    out = []
    for w in s.split():
        out.append(w)
        if len(w) > 2 and re.match(r'^[가-힣]+$', w):
            out += [w[i:i + 2] for i in range(len(w) - 1)]
    return out


docs = [tok(TITLE[c[0], c[1]] + ' ' + c[5]) for c in chunks]
N, avg = len(docs), sum(map(len, docs)) / len(docs)
df = Counter(t for d in docs for t in set(d))
idf = {t: math.log((N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
floor = 0.25 * sum(idf.values()) / len(idf)               # 흔한 단어의 음수 idf를 바닥값으로(rank_bm25와 같음)
idf = {t: (v if v > 0 else floor) for t, v in idf.items()}
qt = tok(query)
scores = []
for d in docs:
    tf = Counter(d)
    s = sum(idf.get(t, 0) * tf[t] * 2.5 / (tf[t] + 1.5 * (0.25 + 0.75 * len(d) / avg)) for t in qt)
    scores.append(s)
top = sorted(range(N), key=lambda i: -scores[i])[:k]
show({'docs': src, 'chunks': N,
      'hits': [{'doc_id': chunks[i][0], 'version': chunks[i][1], 'type': chunks[i][2], 'date': chunks[i][3],
                'section': chunks[i][4], 'score': round(scores[i], 2), 'text': chunks[i][5][:600]}
               for i in top]})
