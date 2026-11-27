# 설치: python -m pip install pypdf beautifulsoup4 transformers
# 13장과 관통 프로젝트 5단계에서 씁니다. 예제 13-1은 1장의 토크나이저만 씁니다(모델은 내려받지 않습니다)
import embed
from doc_tools import CATALOG, TOOLS, read_doc, search_docs   # 사내 문서 120건의 검색과 읽기, 도구 정의(노트북/doc_tools.py)

LOCAL_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
embed.ask_endpoint(LOCAL_MODEL)          # 토크나이저가 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL)


# 관통 프로젝트 1, 2단계의 풀이가 쓰는 것입니다(5장, 6장의 준비 코드와 같습니다)
import csv
import random

with open(f'{DATA}/문의.csv', encoding='utf-8') as file:
    inquiries = list(csv.DictReader(file))        # 문의 60건. 열: 번호, 문의, 라벨, 긴급, 비고
LABELS = ['설비 이상', '품질', '안전', '문서와 데이터 요청']
PRICES = {'소형': {'input': 0.10, 'output': 0.50}, '기본': {'input': 2.00, 'output': 10.00},
          '대형': {'input': 4.00, 'output': 20.00}}   # 100만 토큰당 단가(달러). 5장과 같습니다(2026-11 확인)


def cost(reply, tier):
    """응답 하나의 요금(달러). 입력 토큰과 출력 토큰(thinking 포함)에 각각의 단가를 곱해 더합니다"""
    price = PRICES[tier]
    return (reply.input_tokens * price['input'] + reply.output_tokens * price['output']) / 1_000_000


print(f'문서 {len(CATALOG)}건, 도구 {[tool["name"] for tool in TOOLS]}, 토크나이저 {LOCAL_MODEL}')
