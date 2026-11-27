"""3일차 파트 2의 실습 노트북과 풀이 노트북을 만든다.

사용법: python make_nb_day3_part2.py
출력: 노트북/3일차_02_실습.ipynb, 노트북/3일차_02_실습_풀이.ipynb

노트북은 노트북/ 폴더에서 실행한다(llm.py, embed.py, checks_d3_2.py, data/ 가 같은 폴더에 있다).
"""
from make_nb_day3 import SETUP_AFTER, SETUP_COMMON, SETUP_KEYS, SETUP_MD, TODO, code, md, save

PRACTICE_INTRO = '''
# 3일차 파트 2 실습: 문서 처리 파이프라인

실습은 하나입니다(실습 2). 처음 보는 원본 문서 12건을 청크로 만드는 함수를 직접 작성합니다.
`NotImplementedError`가 있는 곳과 빈 칸을 직접 채웁니다. 막히면 힌트를 펼쳐 보고, 다 한 뒤에 `3일차_02_실습_풀이.ipynb`와 비교합니다.
임베딩 모델은 PC에서 실행합니다. API 호출은 준비 셀의 연결 확인 한 번뿐입니다.
'''

SOLUTION_INTRO = '''
# 3일차 파트 2 실습 풀이

`3일차_02_실습.ipynb`의 풀이와 해설입니다. 풀이는 하나의 예시이며, 테스트 셀을 통과한다면 다르게 작성해도 됩니다.
'''

COMMON_MD = '''
## 실습 준비

아래 셀은 실습에 쓰는 도구를 불러오고 함수를 정의합니다. 그대로 실행합니다. 재료는 `data/3일차/docs_raw_m2/`(원본 문서 10건)와 `data/3일차/docs_raw_m2_ext/`(열리지 않는 파일 2건)입니다. 예제와 다른 문서입니다. 이 실습에는 `pypdf`, `python-docx`, `openpyxl`, `pandas`, `sentence-transformers`와 임베딩 모델이 필요합니다. 설치와 모델 준비는 교재의 3일차 "실습 환경 준비"를 따릅니다. 위의 설치 명령에 없는 패키지는 그곳의 명령으로 설치합니다.

| 이름 | 내용 |
| --- | --- |
| `read_pdf(path)`, `read_docx(path)`, `read_md(path)` | PDF, DOCX, MD 파일의 글을 문자열로 돌려줍니다. MD는 맨 앞의 front matter를 뺀 본문을 돌려줍니다. 열리지 않으면 오류를 발생시킵니다 |
| `chunk_fixed(text, size)` | 글자 수로 자른 청크의 목록을 돌려줍니다 |
| `repeated_lines(line_lists)` | 전체 문서의 80%를 넘는 문서에 나오는 줄을 돌려줍니다. 반복 줄의 후보입니다 |
'''

COMMON_CELL = '''
# 실습 준비
import re
from collections import Counter
from pathlib import Path

import pandas as pd
from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

import checks_d3_2

RAW2 = f'{DATA}/docs_raw_m2'
EXT2 = f'{DATA}/docs_raw_m2_ext'
CONTROL = re.compile(r'[\\x00-\\x08\\x0b-\\x1f\\x7f]')


def read_pdf(path):
    return '\\n'.join(page.extract_text() for page in PdfReader(path).pages)


def read_docx(path):
    return '\\n'.join(paragraph.text for paragraph in Document(path).paragraphs)


def read_md(path):
    text = open(path, encoding='utf-8').read()
    if text.startswith('---\\n'):                     # front matter는 본문이 아니므로 뺍니다
        text = text[4:].partition('\\n---\\n')[2]
    return text


def chunk_fixed(text, size=300):
    return [text[start:start + size] for start in range(0, len(text), size) if text[start:start + size].strip()]


def repeated_lines(line_lists, ratio=0.8):
    counter = Counter(line for lines in line_lists for line in set(lines))
    return [line for line, count in counter.items() if count > len(line_lists) * ratio]


files = sorted(path for path in Path(RAW2).rglob('*') if path.is_file())
print(f'{len(files)}건:', [path.name for path in files])
'''

P2_MD = '''
## 실습 2 새 원본 문서를 청크로 만드는 함수 작성하기

**목적** 처음 보는 문서 묶음에서 반복 줄을 찾아 지우고, 엑셀의 장식 줄을 건너뛰고, 열리지 않는 파일을 실패 목록에 남기는 파이프라인 함수를 직접 작성합니다.

**재료** `data/3일차/docs_raw_m2/`의 원본 문서 10건(PDF 4, DOCX 4, XLSX 1, MD 1)과 `docs_raw_m2_ext/`의 파일 2건, 질문 5개(`실습2_질문_5.csv`. 정답 문서를 맞히는 데 씁니다). 예제의 문서와 반복 줄의 종류가 다릅니다.

**할 일**

1. 후보 셀을 실행해 PDF와 DOCX에서 80%를 넘는 문서에 나오는 줄을 봅니다. 그 줄을 눈으로 읽고, 어느 줄이 반복되는 노이즈인지 판단해 `NOISE_WORDS`에 낱말을 적습니다. 후보에 없는 반복 줄이 있는지도 문서의 원문을 읽어 확인합니다.
2. 함수 네 개를 작성합니다.
   - `find_header_row(rows)`: `rows`는 엑셀의 각 줄을 튜플로 만든 목록입니다. 모든 칸이 채워진 첫 줄의 위치(첫 줄이 0)를 돌려줍니다. 그런 줄이 없으면 `None`입니다. 비어 있는 칸은 `None`이나 빈 문자열입니다.
   - `read_xlsx(path)`: 열 이름 줄을 `find_header_row()`로 찾고, 그 아래 줄마다 한 줄 문장(`열 이름 값, 열 이름 값, ...`)을 만들어 줄바꿈으로 이은 문자열을 돌려줍니다. 비어 있는 칸은 문장에 쓰지 않습니다.
   - `drop_noise(lines, words)`: 줄의 목록에서 노이즈를 지우고 `(남긴 줄의 목록, 지운 줄 수)`를 돌려줍니다. 줄에서 공백을 모두 뺀 글에 `words`의 낱말(공백을 뺀 글)이 들어 있거나, 줄 전체가 `- 1 -` 꼴의 쪽번호이면 노이즈입니다. 쪽번호가 `…확인하십시오. -1-`처럼 다른 글 끝에 붙어 나오는 줄은 이 규칙으로는 지울 수 없으므로 낱말로 지웁니다. (참고: 교재 예제 2-2의 `is_noise`, `PAGE_NUMBER`)
   - `process(folder, words, size)`: 폴더 아래의 모든 파일을 열어 청크 목록과 처리 보고를 돌려줍니다. 청크는 `{'doc_id': 파일 이름에서 확장자를 뺀 것, 'text': 청크}`입니다. 처리 보고는 `{'열린 파일': 건수, '지운 줄': 건수, '실패': [(파일 이름, 오류 이름), ...]}`입니다. 파일이 열리지 않으면 실패 목록에 남기고 나머지를 계속 처리합니다. 제어 문자는 준비 셀의 `CONTROL`로 지웁니다. 노이즈 규칙(`drop_noise()`)은 엑셀을 뺀 형식(PDF, DOCX, MD)에 적용합니다. 엑셀의 행 문장은 표의 데이터이므로, 노이즈 낱말과 같은 글이 들어 있어도 지우면 안 됩니다(교재 예제 2-7에서는 열 이름 `문서번호`가 노이즈 낱말과 겹쳐, 규칙을 엑셀에도 적용하면 공정 스펙 30행이 모두 노이즈로 판정됐습니다). 지운 줄 수는 노이즈로 판정한 줄의 수이고, 빈 줄은 세지 않습니다. (참고: 교재 예제 2-7의 `process`)
3. 테스트 셀을 실행합니다.
4. 측정 셀을 실행해 문서 10건을 처리하고 청크 크기 100자와 400자의 recall@1, recall@3을 측정합니다. 나머지 2건(`docs_raw_m2_ext/`)은 처리 보고의 실패 목록으로 확인합니다.

**완료 기준** 테스트 셀이 "실습 2 통과"를 출력합니다. 측정 결과의 숫자와 함께, 이 숫자만으로 청크 크기를 고를 수 있는지 한 줄로 판단을 적습니다.

<details><summary>힌트 1</summary>

PDF의 "기밀" 줄은 `pypdf`로 뽑으면 글자 사이에 공백이 들어 있습니다(`기 밀 · 내 부 …`). `'기밀' in line`은 거짓입니다. 줄과 낱말에서 공백을 모두 뺀 뒤 비교합니다. `''.join(line.split())`이 공백을 모두 뺍니다.
</details>

<details><summary>힌트 2</summary>

`find_header_row()`의 "모든 칸이 채워졌다"는 `all(cell not in (None, '') for cell in row)`입니다. `read_xlsx()`는 `load_workbook(path).active.iter_rows(values_only=True)`로 줄을 읽어 `rows = list(...)`로 만든 뒤 열 이름 줄 아래를 순서대로 처리합니다.
</details>

<details><summary>힌트 3</summary>

`process()`는 `sorted(Path(folder).rglob('*'))`로 모든 파일을 순서대로 보고, `path.suffix.lower()`로 형식을 가립니다. 엑셀이면 `drop_noise()`를 부르지 않고 지운 줄을 0줄로 둡니다. 파일을 여는 코드를 `try`로 감싸 `except Exception as error`에서 `type(error).__name__`을 실패 목록에 적습니다.
</details>
'''

P2_CANDIDATES = '''
# 실습 2 (1) 반복 줄의 후보를 봅니다
pdf_lines, docx_lines = [], []
for path in files:
    if path.suffix == '.pdf':
        pdf_lines.append([line.strip() for line in read_pdf(path).split('\\n') if line.strip()])
    elif path.suffix == '.docx':
        docx_lines.append([line.strip() for line in read_docx(path).split('\\n') if line.strip()])
print('PDF 후보:', repeated_lines(pdf_lines))
print('DOCX 후보:', repeated_lines(docx_lines))
print()
print(read_pdf(f'{RAW2}/pdf/NOTI-031.pdf'))
'''

P2_WORDS_SKELETON = '''
# 실습 2 (2) 지울 줄의 낱말을 적습니다
NOISE_WORDS = []        # 예: ['무단 반출 금지']. 줄 하나를 대표하는 낱말이나 구절을 적습니다
'''

P2_WORDS_SOLUTION = '''
# 실습 2 (2) 지울 줄의 낱말을 적습니다
NOISE_WORDS = ['무단 반출 금지', '문서관리시스템', '문서번호', '기밀', '— 계속 —', 'Printed', '출력본']
'''

P2_SKELETON = f'''
# 실습 2 (3) 함수 네 개를 작성합니다
def find_header_row(rows):
    """모든 칸이 채워진 첫 줄의 위치(첫 줄이 0)를 돌려줍니다. 그런 줄이 없으면 None."""
    {TODO}


def read_xlsx(path):
    """열 이름 줄 아래의 각 줄을 '열 이름 값, 열 이름 값' 한 줄로 만들어 줄바꿈으로 이어 돌려줍니다."""
    {TODO}


def drop_noise(lines, words):
    """노이즈 줄을 지우고 (남긴 줄의 목록, 지운 줄 수)를 돌려줍니다. 공백을 뺀 글로 비교합니다."""
    {TODO}


def process(folder, words, size):
    """폴더 아래의 모든 파일을 열어 (청크 목록, 처리 보고)를 돌려줍니다."""
    {TODO}
'''

P2_SOLUTION = '''
# 실습 2 (3) 함수 네 개를 작성합니다
PAGE_NUMBER = re.compile(r'-\\s*\\d+\\s*-')


def find_header_row(rows):
    """모든 칸이 채워진 첫 줄의 위치(첫 줄이 0)를 돌려줍니다. 그런 줄이 없으면 None."""
    for position, row in enumerate(rows):
        if all(cell not in (None, '') for cell in row):
            return position
    return None


def read_xlsx(path):
    """열 이름 줄 아래의 각 줄을 '열 이름 값, 열 이름 값' 한 줄로 만들어 줄바꿈으로 이어 돌려줍니다."""
    rows = list(load_workbook(path).active.iter_rows(values_only=True))
    header_at = find_header_row(rows)
    header = rows[header_at]
    sentences = []
    for row in rows[header_at + 1:]:
        cells = [f'{column} {value}' for column, value in zip(header, row) if value not in (None, '')]
        if cells:
            sentences.append(', '.join(cells))
    return '\\n'.join(sentences)


def drop_noise(lines, words):
    """노이즈 줄을 지우고 (남긴 줄의 목록, 지운 줄 수)를 돌려줍니다. 공백을 뺀 글로 비교합니다."""
    squeezed_words = [''.join(word.split()) for word in words]
    kept = []
    for line in lines:
        squeezed = ''.join(line.split())
        if any(word in squeezed for word in squeezed_words) or PAGE_NUMBER.fullmatch(line.strip()):
            continue
        kept.append(line)
    return kept, len(lines) - len(kept)


def process(folder, words, size):
    """폴더 아래의 모든 파일을 열어 (청크 목록, 처리 보고)를 돌려줍니다."""
    chunks, report = [], {'열린 파일': 0, '지운 줄': 0, '실패': []}
    for path in sorted(Path(folder).rglob('*')):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == '.pdf':
                text = read_pdf(path)
            elif suffix == '.docx':
                text = read_docx(path)
            elif suffix == '.xlsx':
                text = read_xlsx(path)
            else:
                text = read_md(path)
        except Exception as error:                   # 열리지 않은 파일은 목록에 남기고 계속합니다
            report['실패'].append((path.name, type(error).__name__))
            continue
        lines = [CONTROL.sub('', line).strip() for line in text.split('\\n') if line.strip()]
        if suffix == '.xlsx':                         # 엑셀의 행 문장은 표의 데이터이므로 노이즈 규칙을 적용하지 않습니다
            kept, removed = lines, 0
        else:
            kept, removed = drop_noise(lines, words)
        report['열린 파일'] += 1
        report['지운 줄'] += removed
        for piece in chunk_fixed('\\n'.join(kept), size):
            chunks.append({'doc_id': path.stem, 'text': piece})
    return chunks, report
'''

P2_CHECK = '''
# 실습 2 확인 (임베딩 모델도 API도 부르지 않습니다)
checks_d3_2.check_pipeline(find_header_row, read_xlsx, drop_noise, process)
'''

P2_MEASURE = '''
# 실습 2 (4) 문서 10건으로 청크 크기별로 측정하고, 열리지 않는 2건의 처리 보고를 봅니다
import numpy as np

import embed

questions = pd.read_csv(f'{DATA}/실습2_질문_5.csv')
for size in [100, 400]:
    chunks, report = process(RAW2, NOISE_WORDS, size)
    vectors = embed.passages([chunk['text'] for chunk in chunks])
    recall1 = recall3 = 0
    for question, gold in zip(questions['질문'], questions['정답']):
        order = np.argsort(-(vectors @ embed.query(question)), kind='stable')
        found = [chunks[position]['doc_id'] for position in order[:3]]
        recall1 += found[0] == gold
        recall3 += gold in found
    print(f'{size}자: 청크 {len(chunks)}건, recall@1 {recall1}/5, recall@3 {recall3}/5')
print(report)
_, report_ext = process(EXT2, NOISE_WORDS, 400)
print(report_ext)
'''

P2_ANSWER_MD = '''
**적어 보기**

- `NOISE_WORDS`에 넣은 낱말과, 후보 셀이 보여 주지 않았지만 원문을 읽고 찾은 반복 줄:
- 100자와 400자의 청크 수, recall@1, recall@3:
- 이 숫자만으로 청크 크기를 고를 수 있는지, 그 이유:
- 처리 보고의 `지운 줄` 수와 `실패` 목록. `NOISE_WORDS`를 비우면 `지운 줄` 수와 recall@3이 어떻게 바뀌는지:
'''

P2_EXPLAIN = '''
**해설**

아래 숫자는 2026-11-25에 실행한 결과입니다. 모델의 응답이 아니라 검색과 문서 처리 결과이므로 같은 환경에서는 거의 같은 값이 나옵니다.

| 지울 낱말 | 지운 줄 | 100자: 청크 수 | 100자: recall@1, recall@3 | 400자: 청크 수 | 400자: recall@1, recall@3 |
| --- | --- | --- | --- | --- | --- |
| 없음 | 0줄 | 50 | 4/5, 5/5 | 15 | 3/5, 4/5 |
| 예제 2-2의 낱말 3개 | 29줄 | 38 | 4/5, 5/5 | 12 | 3/5, 5/5 |
| 풀이의 낱말 7개 | 45줄 | 33 | 4/5, 5/5 | 10 | 3/5, 4/5 |

- **후보 셀은 반복 줄 일부만 보여 줍니다.** PDF 4건의 후보 8줄에는 바닥글 두 줄(쪽번호가 줄 끝에 붙어 있습니다), "기밀" 줄, "— 계속 —" 줄, "Printed" 줄과 개정 이력 세 줄이 있습니다. 머리말 `SL-FAB 반도체 · 사내 일반 · 무단 반출 금지 문서번호 NOTI-031`은 문서 번호가 문서마다 달라서 후보에 없습니다. 후보 셀이 출력한 `NOTI-031`의 원문을 읽어야 찾을 수 있습니다. DOCX의 후보는 "※ 본 문서는 출력본입니다…" 한 줄입니다. 개정 이력 세 줄은 반복되지만 문서 내용이어서 이 풀이는 지우지 않았습니다. `계속` 같은 일반 낱말을 적으면 규칙이 본문에 같은 낱말이 든 줄도 지웁니다. 그래서 풀이는 줄에 맞는 구절(`— 계속 —`)을 적었습니다.
- **"기밀" 줄은 글자 사이에 공백이 들어 있습니다.** `기 밀  ·  내 부  검 토 용  초 안  ·  배 포  금 지`는 `'기밀' in line`으로 찾을 수 없어서, 줄과 낱말에서 공백을 뺀 글로 비교합니다.
- **쪽번호 규칙만으로는 줄을 지우지 못했습니다.** `pypdf`는 쪽번호를 바닥글 줄 끝에 붙여(`…확인하십시오. -1-`) 내므로, 쪽번호만 있는 줄이 없습니다. 낱말을 비우면 지운 줄이 0줄입니다. 바닥글의 낱말(`문서관리시스템`)을 넣어야 이 줄을 지웁니다.
- **지울수록 청크가 줄고, recall@3은 거의 변하지 않았습니다.** 100자 청크가 50건에서 33건으로 줄었지만 recall@1은 4/5, recall@3은 5/5로 그대로입니다. 반복 줄은 청크 수와 인덱스 크기를 늘립니다. 이 질문 5개에서 검색 순위를 해칠 만큼은 아니었습니다.
- **400자의 recall@3이 5/5에서 4/5로 내려간 것은 질문 한 개입니다.** 지운 줄을 늘린 쪽이 더 나쁜 결과를 냈지만, 노이즈를 더 지워서 검색이 나빠졌다고 해석할 수 없습니다. 질문 5개에서 한 개의 차이는 20%p입니다.
- **100자와 400자도 이 숫자만으로 고를 수 없습니다.** 100자의 recall@1이 4/5, 400자가 3/5로 100자가 높지만 한 문제 차이입니다. 예제 2-5에서 질문 10개와 20개로 측정한 크기의 순서가 바뀐 것과 같은 문제입니다. 크기를 정하려면 질문 세트를 늘려야 합니다.
- **엑셀에는 노이즈 규칙을 적용하지 않습니다.** 테스트가 만드는 엑셀 파일에는 알람명이 `기밀 누설`(챔버나 배관의 기밀이 깨져 공기가 새는 상태)인 행이 있습니다. 노이즈 낱말 `기밀`로 검사하면 규칙이 이 행을 지우고, 오류는 나지 않습니다. 실습 재료의 `설비알람_코드표.xlsx`에는 노이즈 낱말과 겹치는 글이 없어서, 이 규칙이 측정 숫자를 바꾸지는 않습니다.
- **`docs_raw_m2_ext/`의 두 파일은 `process()`가 실패 목록에 남깁니다.** `EHS-022.docx`는 `BadZipFile`, `NOTI-032.pdf`는 `EmptyFileError`입니다. 열린 파일이 0건이어도 오류 없이 끝나므로, 처리 보고를 읽어야 이 사실을 알 수 있습니다.
'''

MORE_MD = '''
## 더 해 보기

- `process()`가 글자가 0자인 파일도 실패 목록에 남기게 확장합니다. 스캔한 PDF가 이런 파일입니다.
- 질문을 내 업무의 말투로 다섯 개 더 만들어 `실습2_질문_5.csv`와 같은 형식으로 측정합니다. 질문이 열 개일 때 크기의 순서가 바뀌는지 봅니다.
- `process()`가 청크에 `type`(파일 이름 앞부분)과 `dept`(문서 머리말의 부서)를 붙이게 확장합니다(교재 예제 2-6).
'''


def practice_cells(solution):
    cells = [md(SOLUTION_INTRO if solution else PRACTICE_INTRO),
             md(SETUP_MD), code(SETUP_KEYS), code(SETUP_COMMON), md(SETUP_AFTER),
             md(COMMON_MD), code(COMMON_CELL, '실습준비')]
    cells += [md(P2_MD), code(P2_CANDIDATES),
              code(P2_WORDS_SOLUTION if solution else P2_WORDS_SKELETON),
              code(P2_SOLUTION if solution else P2_SKELETON, '실습2'), code(P2_CHECK), code(P2_MEASURE),
              md(P2_EXPLAIN if solution else P2_ANSWER_MD)]
    if not solution:
        cells.append(md(MORE_MD))
    return cells


if __name__ == '__main__':
    save('3일차_02_실습.ipynb', practice_cells(solution=False))
    save('3일차_02_실습_풀이.ipynb', practice_cells(solution=True))
