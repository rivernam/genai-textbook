"""3일차 파트 1의 재료를 노트북/data/3일차/ 에 만든다.

사용법: python make_data_day3.py
원본 재료(작업/3일차/원본재료/코드)의 개정본과 신규 문서 4건을 그대로 복사하고,
원본의 변경 목록과 질문 6개(3일차_미션1_재료.txt)를 CSV 로 옮긴다.
"""
import csv
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '작업' / '3일차' / '원본재료' / '코드'
DEST = ROOT / '노트북' / 'data' / '3일차'

CHANGES = [
    ('개정', 'SOP-ETCH-005', '시즈닝 런 더미 웨이퍼 25장 → 15장'),
    ('개정', 'EHS-001', '가스 감지기 15분 모니터링 절 추가'),
    ('신규', 'NOTI-101', 'ETCH-03 정기 PM 요일 화요일 → 목요일'),
    ('신규', 'SOP-ETCH-020', '에치 챔버 웻 클리닝 표준작업지침'),
] + [('폐기', f'NOTI-{number:03d}', '연말 정기 셧다운 일정 공지(지난 일정이라 내림)') for number in (1, 7, 13, 19, 25)]

# 변경을 반영한 뒤 기준의 정답 문서. 6번은 일부러 답이 없는 질문(폐기한 공지 다섯 건만 답을 가졌다)
QUESTIONS = [
    ('에치 시즈닝 런은 더미 웨이퍼 몇 장 돌리나요?', 'SOP-ETCH-005'),
    ('가스 실린더 바꾸고 감지기는 몇 분 동안 봐야 하나요?', 'EHS-001'),
    ('ETCH-03 PM 요일이 바뀐다던데 무슨 요일이에요?', 'NOTI-101'),
    ('챔버 웻 클리닝은 어떤 순서로 하나요?', 'SOP-ETCH-020'),
    ('에치 웨이퍼를 손으로 넣고 뺄 때 순서', 'SOP-ETCH-001'),
    ('연말 셧다운 일정 알려주세요', ''),
]


def write_csv(name, header, rows):
    with open(DEST / name, 'w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    (DEST / '변경_문서').mkdir(parents=True, exist_ok=True)
    for path in sorted((SOURCE / '미션1_변경문서').glob('*.md')):
        shutil.copyfile(path, DEST / '변경_문서' / unicodedata.normalize('NFC', path.name))
    write_csv('변경_목록.csv', ['종류', '문서', '내용'], CHANGES)
    write_csv('변경_질문_6.csv', ['질문', '정답'], QUESTIONS)
    print('변경 문서', len(list((DEST / '변경_문서').glob('*.md'))), '건 · 변경', len(CHANGES), '건 · 질문', len(QUESTIONS), '개')


if __name__ == '__main__':
    main()
