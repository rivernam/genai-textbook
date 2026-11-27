import csv
import re

with open(f'{DATA}/문의.csv', encoding='utf-8') as file:
    inquiries = list(csv.DictReader(file))        # 문의 60건. 열: 번호, 문의, 라벨, 긴급, 비고
LABELS = ['설비 이상', '품질', '안전', '문서와 데이터 요청']


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
