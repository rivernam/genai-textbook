"""3일차 파트 3의 재료를 노트북/data/3일차/ 에 만든다.

사용법: python make_data_day3_part3.py
원본 재료(작업/3일차/원본재료/코드)의 새 문서 12건, 구판 1건, 문서 목록을 그대로 복사하고,
원본 노트북의 질문(예제 3-4의 여섯 개, 미션 3의 다섯 개와 여섯째)을 CSV 로 옮긴다.
"""
import csv
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '작업' / '3일차' / '원본재료' / '코드'
DEST = ROOT / '노트북' / 'data' / '3일차'

# 예제 3-8: 성격이 다른 질문 여섯 개. 종류는 사람이 붙인 예상이고, k 는 검색에서 가져올 청크 수다
DIAGNOSIS_QUESTIONS = [
    ('정상', '에치 장비 ESC 온도 상한이 몇 도이고, 초과하면 어떻게 조치해야 하나요?', 4),
    ('정상', '시즈닝 런은 더미 웨이퍼 몇 장으로 하나요?', 4),
    ('질문이 넓음', '최근 에치 장비들에서 있었던 센서 관련 품질 이슈를 정리해 주세요.', 6),
    ('구판과 개정판', '에치 웨이퍼 클램핑 시 He 배면압 허용 편차는?', 4),
    ('없는 호기', 'ETCH-07 호기 ESC 온도 기준은?', 4),
    ('문서 밖', '야간조 식당 메뉴가 뭐예요?', 4),
]

# 실습 3: 새 문서 묶음(corpus_m3)의 질문. 5번은 일부러 답이 없는 질문이다
PRACTICE_QUESTIONS = [
    '확산로 보트 로딩 속도 기준이 얼마인가요?',
    'DIFF-02 산화막 두께 산포가 커진 원인과 조치는?',
    'RCP-IMP-220 의 빔 전류 목표값과 관리 한계는?',
    '이온 소스를 교체한 뒤 에이징은 몇 분 하나요?',
    'DIFF-07 호기 PM 요일은 언제인가요?',
]
PRACTICE_VERSION_QUESTION = '확산로 온도 프로파일 허용 편차는?'


def write_csv(name, header, rows):
    with open(DEST / name, 'w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def copy_folder(source, target):
    (DEST / target).mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob('*.md')):
        shutil.copyfile(path, DEST / target / unicodedata.normalize('NFC', path.name))


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    copy_folder(SOURCE / 'corpus_m3', 'corpus_m3')
    copy_folder(SOURCE / 'corpus_m3_ext', 'corpus_m3_구판')
    shutil.copyfile(SOURCE / 'corpus_m3_manifest.csv', DEST / 'corpus_m3_manifest.csv')
    write_csv('진단_질문_6.csv', ['종류', '질문', 'k'], DIAGNOSIS_QUESTIONS)
    write_csv('실습_질문_5.csv', ['질문'], [[question] for question in PRACTICE_QUESTIONS])
    print('corpus_m3', len(list((DEST / 'corpus_m3').glob('*.md'))), '건 · 구판', len(list((DEST / 'corpus_m3_구판').glob('*.md'))), '건')


if __name__ == '__main__':
    main()
