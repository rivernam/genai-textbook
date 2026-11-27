# 5장과 관통 프로젝트 1단계에서 씁니다
import csv
import random
import re

with open(f'{DATA}/문의.csv', encoding='utf-8') as file:
    inquiries = list(csv.DictReader(file))        # 문의 60건. 열: 번호, 문의, 라벨, 긴급, 비고
LABELS = ['설비 이상', '품질', '안전', '문서와 데이터 요청']

# 100만 토큰당 단가(달러). `llm.py`가 쓰는 Anthropic 모델, 프롬프트 10만 토큰 이하 기준(2026-11 확인)
# 사내 API를 쓰면 사내 안내의 단가로 바꿉니다
PRICES = {'소형': {'input': 0.10, 'output': 0.50, 'cache_write': 0.125, 'cache_read': 0.01},
          '기본': {'input': 2.00, 'output': 10.00, 'cache_write': 2.50, 'cache_read': 0.10},
          '대형': {'input': 4.00, 'output': 20.00, 'cache_write': 5.00, 'cache_read': 0.20}}


def cost(reply, tier):
    """응답 하나의 요금(달러). 입력 토큰과 출력 토큰(thinking 포함)에 각각의 단가를 곱해 더합니다"""
    price = PRICES[tier]
    return (reply.input_tokens * price['input'] + reply.output_tokens * price['output']) / 1_000_000


def numbered(items):
    """문의 목록을 "번호: 문의" 줄로 이어 붙입니다"""
    return '\n'.join(f"{item['번호']}: {item['문의']}" for item in items)


def parse_labels(text):
    """응답에서 "Q01: 라벨" 형식의 줄을 찾아 {번호: 라벨}로 돌려줍니다"""
    found = {}
    for line in text.splitlines():
        match = re.match(r'\s*[-*]?\s*(Q\d{2})\s*[:：]\s*(.+?)\s*$', line)
        if match:
            found[match.group(1)] = match.group(2).strip()
    return found


def accuracy(predicted, items):
    """정답 라벨과 같은 건의 비율"""
    return sum(predicted.get(item['번호']) == item['라벨'] for item in items) / len(items)


print(f'문의 {len(inquiries)}건, 라벨 {LABELS}')
