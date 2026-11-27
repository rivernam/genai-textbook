# 설치: python -m pip install sentence-transformers rank-bm25 pypdf
# 8장과 관통 프로젝트 3단계에서 씁니다. 문서를 읽고, 청크로 나누고, 검색하는 함수는 같은 폴더의 corpus.py에 있습니다
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


def rag_prompt(question, hits, with_meta=True):
    """검색한 청크를 번호와 함께 RAG_PROMPT에 넣습니다. with_meta가 참이면 청크마다 상태, 개정, 날짜를 붙입니다"""
    blocks = []
    for hit in hits:
        meta = f" (상태 {hit['status']}, 개정 {hit['revision']}, {hit['date']})" if with_meta else ''
        blocks.append(f"[{hit['chunk_id']}]{meta}\n{hit['text']}")
    return RAG_PROMPT.format(context='\n\n'.join(blocks), question=question)


print(f'문서 {len(catalog)}건, 청크 {len(chunks)}개, 글을 뽑지 못한 문서 {failed}')
