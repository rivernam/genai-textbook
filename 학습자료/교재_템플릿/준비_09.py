# 설치: python -m pip install sentence-transformers rank-bm25 pypdf
# 9장과 관통 프로젝트 4단계에서 씁니다. 8장의 준비에 평가 함수와 리랭커, 채점 프롬프트를 더했습니다
import csv
import random
import re

import numpy as np

import corpus
import embed

with open(f'{DATA}/문의.csv', encoding='utf-8') as file:
    inquiries = list(csv.DictReader(file))        # 문의 60건. 관통 프로젝트 1, 2단계의 코드가 씁니다
LABELS = ['설비 이상', '품질', '안전', '문서와 데이터 요청']

# 100만 토큰당 단가(달러). 5장과 같습니다(llm.py가 쓰는 Anthropic 모델, 2026-11 확인)
PRICES = {'소형': {'input': 0.10, 'output': 0.50}, '기본': {'input': 2.00, 'output': 10.00},
          '대형': {'input': 4.00, 'output': 20.00}}


def cost(reply, tier):
    """응답 하나의 요금(달러). 입력 토큰과 출력 토큰(thinking 포함)에 각각의 단가를 곱해 더합니다"""
    price = PRICES[tier]
    return (reply.input_tokens * price['input'] + reply.output_tokens * price['output']) / 1_000_000


catalog = corpus.catalog()                               # {문서 id: 메타데이터}. 문서 120건
questions = {item['id']: item for item in corpus.evalset()}   # 평가 질문 62개
chunks, failed = corpus.load_chunks()                    # 문서마다 파싱하고 절 단위 청크로 나눕니다(corpus.py)
searcher = corpus.Search(chunks)                         # 청크마다 임베딩과 BM25 인덱스를 만듭니다. 1~2분 걸립니다


def is_valid(chunk):
    """메타데이터 필터. 폐기된 구판의 청크를 검색 대상에서 뺍니다"""
    return chunk['status'] == '유효'


RAG_PROMPT = """아래 [검색 결과]만 근거로 질문에 답하세요.
- 문장마다 근거가 된 청크의 번호를 [SOP-WB-001#3]처럼 적습니다.
- 검색 결과에 답이 없으면 "검색한 문서에서 찾지 못했습니다"라고만 답합니다.
- 검색 결과끼리 내용이 다르면 날짜가 늦은 문서를 따르고, 내용이 다르다는 것을 함께 적습니다.

[검색 결과]
{context}

[질문]
{question}"""


def context_of(hits, with_meta=True):
    """검색한 청크를 번호와 함께 이어 붙인 글. with_meta가 참이면 청크마다 상태, 개정, 날짜를 붙입니다"""
    blocks = []
    for hit in hits:
        meta = f" (상태 {hit['status']}, 개정 {hit['revision']}, {hit['date']})" if with_meta else ''
        blocks.append(f"[{hit['chunk_id']}]{meta}\n{hit['text']}")
    return '\n\n'.join(blocks)


def rag_prompt(question, hits, with_meta=True):
    """8장의 RAG 프롬프트. 검색한 청크를 RAG_PROMPT에 넣습니다"""
    return RAG_PROMPT.format(context=context_of(hits, with_meta), question=question)


def docs_of(indices):
    """청크 번호의 순위를 문서 id의 순위로 바꿉니다. 한 문서의 청크가 여러 번 나오면 처음 나온 순위만 남깁니다"""
    order = []
    for index in indices:
        if chunks[index]['doc_id'] not in order:
            order.append(chunks[index]['doc_id'])
    return order


def first_hit(order, gold):
    """문서 순위에서 정답 문서가 처음 나오는 순위. 없으면 None"""
    return next((rank for rank, doc_id in enumerate(order, 1) if doc_id in gold), None)


def load_reranker():
    """예제 9-2용. 크로스 인코더 리랭커를 PC에서 불러옵니다. 처음 한 번 수백 MB를 내려받습니다"""
    from sentence_transformers import CrossEncoder
    name = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
    embed.ask_endpoint(name)                     # 모델이 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
    return CrossEncoder(name)


def rag_answer(question, k=4):
    """8장의 RAG. 유효한 문서에서 청크 k개를 검색해 RAG_PROMPT로 묻고 (응답, 검색한 청크)를 돌려줍니다"""
    hits = searcher.search(question, k=k, where=is_valid)
    return llm.ask(rag_prompt(question, hits), model='소형', max_tokens=2000), hits


JUDGE_PROMPT = """너는 사내 문서 질의응답 시스템의 채점자다. [답]을 아래 두 기준으로 따로 채점한다.
- faithful: [답]의 내용이 모두 [검색 결과]에서 확인되면 true, 검색 결과에 없는 내용이 하나라도 있으면 false.
- correct: [답]이 [기준 답]과 같은 사실을 말하면 true. 기준 답이 "문서에 답이 없다"이면, 찾지 못했다고 답했을 때만 true.
reason에는 판정의 근거를 한 문장으로 쓴다.

[검색 결과]
{context}

[질문]
{question}

[기준 답]
{reference}

[답]
{answer}"""
JUDGE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['faithful', 'correct', 'reason'],
                'properties': {'faithful': {'type': 'boolean'}, 'correct': {'type': 'boolean'}, 'reason': {'type': 'string'}}}


print(f'문서 {len(catalog)}건, 청크 {len(chunks)}개, 글을 뽑지 못한 문서 {failed}')
