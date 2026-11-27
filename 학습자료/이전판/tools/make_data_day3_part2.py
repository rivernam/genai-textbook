"""3일차 파트 2의 재료를 노트북/data/3일차/ 에 둔다.

사용법: python make_data_day3_part2.py
출력(노트북/data/3일차/):
  docs_raw/{pdf,docx,xlsx}   예제의 원본 문서 PDF 8건, DOCX 10건, XLSX 2건 (원본 그대로)
  docs_raw_m2/               실습 2의 원본 문서 10건 (원본 그대로)
  docs_raw_m2_ext/           일부러 깨 둔 파일 2건 (원본 그대로). 열리지 않는 파일을 실패 목록에 남기는 데 쓴다
  청크_질문_10.csv           예제 2-5의 질문 10개와 정답 문서 (원본 예제 2-4의 질문 세트)
  실습2_질문_5.csv           실습 2의 질문 5개와 정답 문서 (원본 미션 2의 질문)

docs_raw 의 MD 235건은 2일차 corpus 의 같은 이름 파일과 내용이 같아서 복사하지 않는다.
파일 이름은 NFC 로 바꿔 둔다(맥에서 만든 한글 파일 이름이 NFD 일 수 있다).
"""
import csv
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '작업' / '3일차' / '원본재료' / '코드'
OUT = ROOT / '노트북' / 'data' / '3일차'

# 원본 예제 2-4의 질문 10개. 앞의 5개는 2일차의 질문 세트와 같다.
CHUNK_QUESTIONS = [
    ('칠러가 안 도는 것 같은데 챔버가 멈추는 기준이 뭔가요', 'SOP-ETCH-007_v2.1'),
    ('에치 리크 체크는 어떻게 하나요', 'SOP-ETCH-006'),
    ('CVD 알람이 뜨면 뭘 먼저 하나요', 'SOP-CVD-009'),
    ('He 배면압 설정 기준이 어떻게 되나요', 'SOP-ETCH-012_v2.0'),
    ('포토 웨이퍼를 수동으로 넣는 절차', 'SOP-포토-013'),
    ('시즈닝 런은 왜 도나요', 'SOP-ETCH-005'),
    ('ESC 교체할 때 주의할 점', 'SOP-ETCH-004'),
    ('파티클 카운트가 올라가면 어떻게 하나요', 'SOP-ETCH-005'),
    ('가스라인 퍼지 순서', 'SOP-ETCH-003'),
    ('예방정비 주기가 어떻게 되나요', 'SOP-ETCH-002'),
]

# 원본 미션 2의 질문 5개. 정답은 docs_raw_m2 의 문서 번호다.
MISSION2_QUESTIONS = [
    ('야간조 식당은 몇 시까지 하나요?', 'NOTI-031'),
    ('조별 인원 확인은 누가 하나요?', 'EHS-021'),
    ('가스 공급 밸브는 언제 차단하나요?', 'EHS-021'),
    ('에치 챔버 세정 SOP 의 세정액 대기 시간은?', 'SOP-ETCH-013'),
    ('E-102 알람이 뜨면 먼저 뭘 하나요?', '설비알람_코드표'),
]


def copy_folder(source, target, formats=None):
    """source 의 파일을 target 으로 그대로 복사한다. formats 가 있으면 그 확장자만."""
    count = 0
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.name.startswith('.'):
            continue
        if formats and path.suffix.lower() not in formats:
            continue
        name = unicodedata.normalize('NFC', path.name)
        relative = path.relative_to(source).parent
        destination = target / relative / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        count += 1
    return count


def write_questions(name, rows):
    with open(OUT / name, 'w', encoding='utf-8-sig', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['질문', '정답'])
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print('docs_raw', copy_folder(SOURCE / 'docs_raw', OUT / 'docs_raw', {'.pdf', '.docx', '.xlsx'}))
    print('docs_raw_m2', copy_folder(SOURCE / 'docs_raw_m2', OUT / 'docs_raw_m2'))
    print('docs_raw_m2_ext', copy_folder(SOURCE / 'docs_raw_m2_ext', OUT / 'docs_raw_m2_ext'))
    write_questions('청크_질문_10.csv', CHUNK_QUESTIONS)
    write_questions('실습2_질문_5.csv', MISSION2_QUESTIONS)


if __name__ == '__main__':
    main()
