# 사내 문서 검색 도구 (7일차 search_docs와 같은 간이판). 사용: python tools/search_docs.py "질문" [개수]
#   질문과 겹치는 단어 수로 문서를 고릅니다. 문서 ID를 알면 --id로 원문 전체를 봅니다
#   python tools/search_docs.py --id MTG-2025-W01
import json, sys
from _common import show, path

# 1. 문서 청크를 읽습니다 (6일차 자료 + 8일차 미션 문서)
chunks = json.load(open(path('data', 'chunks6.json'), encoding='utf-8'))
chunks += json.load(open(path('data', 'mission_docs8.json'), encoding='utf-8'))
args = sys.argv[1:]

# 2. --id 면 그 문서의 청크를 모두 이어 붙여 원문 전체를 보여 줍니다
if args[:1] == ['--id']:
    doc_id = args[1]
    parts = [chunk['text'] for chunk in chunks if chunk['doc_id'] == doc_id]
    if parts:
        show({'doc_id': doc_id, 'text': '\n\n'.join(parts)})
    else:
        show({'error': f'{doc_id} 문서가 없습니다'})
    sys.exit(0)

# 3. 마지막 인자가 숫자면 보여 줄 개수(기본 3건), 나머지가 질문입니다
if len(args) > 1 and args[-1].isdigit():
    hit_count, question_words = int(args[-1]), args[:-1]
else:
    hit_count, question_words = 3, args
question_set = set(' '.join(question_words).replace('?', ' ').split())

# 4. 문서마다 첫 청크 하나만 씁니다 (간이판)
docs = {}
for chunk in chunks:
    docs.setdefault(chunk['doc_id'], chunk)


def overlap(doc):
    """문서 제목과 본문 앞 400자에서 질문과 겹치는 단어 수를 돌려줍니다."""
    doc_words = set((doc['title'] + ' ' + doc['text'][:400]).split())
    return len(question_set & doc_words)


# 5. 겹치는 단어가 많은 순으로 상위 hit_count 건. 본문은 앞 160자만 보여 줍니다
ranked = sorted(docs.values(), key=overlap, reverse=True)
hits = [{'doc_id': doc['doc_id'], 'version': doc.get('version'), 'type': doc.get('type'),
         'section': doc['title'], 'text': doc['text'][:160]} for doc in ranked[:hit_count]]
show({'hits': hits})
