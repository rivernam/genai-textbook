"""3일차 파트 3의 실습 노트북과 풀이 노트북을 만든다.

사용법: python make_nb_day3_part3.py
출력: 노트북/3일차_03_실습.ipynb, 노트북/3일차_03_실습_풀이.ipynb

청크 인덱스를 만드는 부품(Chunk, Hit, ChunkIndex, read_manifest, build_chunks, build_index, search, show)은
원고(원고/3일차/03_첫_RAG_완성.md)의 예제 3-1에서 그대로 가져온다(코드는 원고 한 곳에만 둔다).
노트북은 노트북/ 폴더에서 실행한다(llm.py, embed.py, checks_d3_3.py, data/ 가 같은 폴더에 있다).
"""
import re
from pathlib import Path

from make_nb_day3 import SETUP_AFTER, SETUP_COMMON, SETUP_KEYS, SETUP_MD, TODO, code, md, save

MANUSCRIPT_3 = Path(__file__).resolve().parents[1] / '원고' / '3일차' / '03_첫_RAG_완성.md'


def parts_source():
    """원고의 예제 3-1에서 인덱스를 만드는 부품의 정의를 그대로 가져온다(실행 부분은 뺀다)."""
    text = MANUSCRIPT_3.read_text(encoding='utf-8')
    found = re.search(r'```python\n# 예제 3-1 \(청크 인덱스를 만드는 부품\)\n(.*?)\n```', text, flags=re.S)
    return found.group(1).split('\n\nmanifest = read_manifest(')[0]


def titles_source():
    """원고의 예제 3-7에서 제목을 붙여 임베딩하는 함수 with_titles의 정의를 그대로 가져온다."""
    text = MANUSCRIPT_3.read_text(encoding='utf-8')
    found = re.search(r'```python\n# 예제 3-7 \(제목을 붙여 임베딩합니다\)\n(.*?)\n```', text, flags=re.S)
    return found.group(1).split('\n\ntitled = with_titles(current)')[0]


P3_INTRO = '''
# 3일차 파트 3 실습: 첫 RAG 완성

실습은 하나입니다(실습 3). 검색 결과로 프롬프트를 만드는 함수와 구판 청크를 제외하는 함수를 직접 작성하고, 새 문서 묶음으로 RAG를 돌려 봅니다.
`NotImplementedError`가 있는 곳을 직접 채웁니다. 막히면 힌트를 펼쳐 보고, 다 한 뒤에 `3일차_03_실습_풀이.ipynb`와 비교합니다.
테스트 셀은 임베딩 모델도 API도 부르지 않고 작은 입력으로 함수를 검사합니다. 준비 셀의 연결 확인을 빼면, 마지막 세 셀에서만 모델을 호출합니다(모두 여덟 번).
'''

P3_SOLUTION_INTRO = '''
# 3일차 파트 3 실습 풀이

`3일차_03_실습.ipynb`의 풀이와 해설입니다. 풀이는 하나의 예시이며, 테스트 셀을 통과한다면 다르게 작성해도 됩니다.
'''

P3_COMMON_MD = '''
## 실습 준비

아래 셀은 실습이 쓰는 재료와 함수를 만듭니다. 그대로 실행합니다. 교재 예제 3-1의 함수(`read_manifest`, `build_index`, `search`, `show`)와 새 문서 묶음의 인덱스를 만듭니다.

| 이름 | 내용 |
| --- | --- |
| `Chunk`, `Hit`, `ChunkIndex` | 청크, 검색 결과 한 건, 청크 목록과 벡터를 묶은 인덱스입니다 |
| `search(index, question, k)` | 질문과 가까운 청크 k건을 `Hit` 목록으로 돌려줍니다 |
| `with_titles(index)` | 청크 앞에 문서 제목을 붙여 다시 임베딩한 인덱스를 돌려줍니다(교재 예제 3-7) |
| `RULE` | 근거 없음 규칙의 문장입니다 |
| `base` | 새 문서 12건의 청크 인덱스(39청크)입니다. 문서 제목을 붙여 임베딩했고, 구판은 들어 있지 않습니다 |
'''

P3_COMMON_CELL = '''
# 실습 준비
import shutil
import tempfile

import checks_d3_3

__PARTS__


__TITLES__

RULE = "검색 결과에 없으면 '사내 문서에서 근거를 찾지 못했습니다' 라고만 답한다."
manifest_m3 = read_manifest(f'{DATA}/corpus_m3_manifest.csv')
base = with_titles(build_index(f'{DATA}/corpus_m3', manifest_m3))
print(f"새 문서 {len(os.listdir(f'{DATA}/corpus_m3'))}건, 청크 {len(base.chunks)}, 인덱스 {base.vectors.shape}")
'''

P3_MD = '''
## 실습 3 새 문서 묶음으로 RAG 구성하고 구판 제외하기

**목적** 검색 결과를 프롬프트로 만드는 일과, 구판 청크를 제외하는 일을 직접 작성합니다. 근거 없음 규칙을 뺐을 때와 구판을 넣었을 때 응답의 내용과 값이 어떻게 바뀌는지 새 문서에서 확인합니다.

**재료** `data/3일차/corpus_m3/`(확산, 이온주입 라인의 새 문서 12건), `data/3일차/corpus_m3_구판/SOP-DIFF-002_v1.0.md`(구판 1건), `data/3일차/실습_질문_5.csv`(질문 5개. 5번은 일부러 답이 없는 질문입니다).

**할 일** 함수 두 개를 작성합니다.

1. `build_prompt(hits, question, use_rule=True)`: 검색 결과 `hits`(`Hit` 목록)와 질문으로 프롬프트 글을 만듭니다.
   - 교재 예제 3-3의 `TEMPLATE`과 같은 네 요소(역할 지정, 검색 결과, 출력 규칙 "문장마다 근거 [문서번호]를 붙인다", 근거 없음 규칙)로 프롬프트를 구성합니다. 이후 셀이 이 함수로 만든 프롬프트로 LLM API를 호출하므로 출력 규칙도 넣습니다.
   - 청크마다 `[문서번호_버전] (절)` 꼴의 머리글을 앞에 붙여 순서대로 넣습니다. 예: `[SOP-DIFF-001_v1.0] (절차)`
   - `use_rule`이 참이면 근거 없음 규칙 `RULE`을 검색 결과 뒤, 질문 앞에 넣습니다. 거짓이면 넣지 않습니다.
   - 질문이 프롬프트의 맨 끝에 옵니다.
2. `latest_version_rows(chunks)`: `Chunk` 목록에서 같은 문서 번호(`doc_id`)의 청크 가운데 버전이 가장 높은 청크의 행 번호를 돌려줍니다. 버전은 `v1.10`이 `v1.9`보다 높게 숫자로 비교합니다. 판이 하나뿐인 문서는 그대로 남깁니다.

**완료 기준** 테스트 셀이 "실습 3 통과"를 출력합니다. 그다음 세 셀을 실행해 아래 "적어 보기"를 채웁니다.

<details><summary>힌트 1</summary>

`build_prompt`의 머리글은 `f'[{hit.doc_id}_{hit.version}] ({hit.section})\\n{hit.text}'`입니다. 청크 사이는 빈 줄로 구분합니다.
</details>

<details><summary>힌트 2</summary>

버전 `'v1.10'`은 `tuple(int(number) for number in version.lstrip('v').split('.'))`로 `(1, 10)`이 됩니다. 튜플끼리는 `(1, 10) > (1, 9)`처럼 비교됩니다. 문자열로 비교하면 `'v1.9' > 'v1.10'`이 됩니다.
</details>

<details><summary>힌트 3</summary>

문서 번호별로 가장 높은 버전을 먼저 구해 두고, 청크를 한 번 더 훑으며 그 버전인 청크의 행 번호를 모읍니다.
</details>
'''

P3_SKELETON = f'''
# 실습 3
def build_prompt(hits, question, use_rule=True):
    """검색 결과와 질문으로 프롬프트 글을 만듭니다."""
    {TODO}


def latest_version_rows(chunks):
    """같은 문서 번호의 청크 가운데 버전이 가장 높은 청크의 행 번호 목록을 돌려줍니다."""
    {TODO}
'''

P3_SOLUTION = '''
# 실습 3
def build_prompt(hits, question, use_rule=True):
    """검색 결과와 질문으로 프롬프트 글을 만듭니다."""
    results = '\\n\\n'.join(f'[{hit.doc_id}_{hit.version}] ({hit.section})\\n{hit.text}' for hit in hits)
    rule = RULE + '\\n' if use_rule else ''
    return ('너는 사내 공정기술 담당자다.\\n아래 사내 문서만 근거로 답한다.\\n\\n'
            f'[검색 결과]\\n{results}\\n\\n'
            f'규칙: 문장마다 근거 [문서번호]를 붙인다.\\n{rule}\\n'
            f'질문: {question}')


def version_key(chunk):
    return tuple(int(number) for number in chunk.version.lstrip('v').split('.'))


def latest_version_rows(chunks):
    """같은 문서 번호의 청크 가운데 버전이 가장 높은 청크의 행 번호 목록을 돌려줍니다."""
    latest = {}
    for chunk in chunks:
        latest[chunk.doc_id] = max(latest.get(chunk.doc_id, (0,)), version_key(chunk))
    return [row for row, chunk in enumerate(chunks) if version_key(chunk) == latest[chunk.doc_id]]
'''

P3_CHECK = '''
# 실습 3 확인 (임베딩 모델도 API도 부르지 않습니다)
checks_d3_3.check_practice_3(build_prompt, latest_version_rows, RULE)
'''

P3_QUESTIONS = '''
# 실습 3 (1) 새 문서의 질문 다섯 개를 RAG로 처리합니다
practice_questions = list(pd.read_csv(f'{DATA}/실습_질문_5.csv', encoding='utf-8-sig')['질문'])


def answer(index, question, use_rule=True, k=4):
    """검색하고 build_prompt()로 프롬프트를 만들어 모델에 보냅니다. (응답 글, 검색 결과)를 돌려줍니다."""
    hits = search(index, question, k)
    return llm.ask(build_prompt(hits, question, use_rule), model='기본', max_tokens=600).text, hits


for number, question in enumerate(practice_questions, 1):
    text, hits = answer(base, question)
    print(f'{number}. {question}')
    show(hits)
    print('   응답:', text[:130].replace('\\n', ' '))
'''

P3_NO_RULE = '''
# 실습 3 (2) 5번 질문(답이 없음)을 근거 없음 규칙 없이 처리합니다
text, hits = answer(base, practice_questions[4], use_rule=False)
print('규칙 없음, 검색 결과 최고 점수', hits[0].score)
print('응답:', text[:250].replace('\\n', ' '))
'''

P3_VERSION = '''
# 실습 3 (3) 구판을 인덱스에 넣었을 때와 뺐을 때
QUESTION_VERSION = '확산로 온도 프로파일 허용 편차는?'
with tempfile.TemporaryDirectory() as folder:                 # 원본 폴더는 건드리지 않고 임시 폴더에 구판을 함께 둡니다
    for source in [f'{DATA}/corpus_m3', f'{DATA}/corpus_m3_구판']:
        for file in os.listdir(source):
            shutil.copy(f'{source}/{file}', folder)
    with_old = with_titles(build_index(folder, manifest_m3))
print(f'청크 {len(base.chunks)}개 → 구판을 넣으면 {len(with_old.chunks)}개')

rows = latest_version_rows(with_old.chunks)
without_old = ChunkIndex([with_old.chunks[row] for row in rows], with_old.vectors[rows])
for label, index in [('구판 포함', with_old), ('구판 제외', without_old)]:
    text, hits = answer(index, QUESTION_VERSION)
    print(f'{label}, 검색 결과의 판 {[f"{hit.doc_id}_{hit.version}" for hit in hits]}')
    print('   응답:', text[:160].replace('\\n', ' '))
'''

P3_ANSWER_MD = '''
**적어 보기**

- 질문 5개의 검색 결과 1위 문서와 점수. 답이 없는 5번 질문의 응답은 무엇이었는지:
- 5번 질문을 근거 없음 규칙 없이 처리했을 때 응답은 어떻게 바뀌었는지. 운영에서 무엇이 곤란해지는지:
- 구판을 넣었을 때 검색 결과 네 건에 v1.0과 v2.0이 각각 몇 건 들어왔는지, 응답의 허용 편차 값은 무엇이었는지:
- 응답이 맞게 나왔더라도 구판을 인덱스에 남겨 두면 안 되는 이유(검색 결과의 판 구성을 근거로):
'''

P3_EXPLAIN = '''
**해설**

아래 숫자와 응답은 2026-11-24에 실행한 결과입니다. 검색 점수는 같은 임베딩 모델을 쓰면 거의 같은 값이 나오고, 응답의 문장은 실행마다 조금씩 다릅니다.

- **질문 다섯 개의 검색과 응답**: 정답이 있는 질문 네 개는 정답 문서가 1위입니다. 1번은 `SOP-DIFF-001`의 절차 절(0.872)이고 응답은 로딩 속도 "분당 100 mm 이하"입니다. 3번은 `SPEC-041`의 관리 항목 절(0.909)이고 응답은 목표값 2.4 mA, 관리 한계 ±3%입니다. 4번은 `SOP-IMP-002`의 절차 절(0.863)이고 응답은 에이징 90분입니다. 2번은 `QIR-2026-0901`의 절 네 개(0.914~0.890)가 올라왔고, 응답은 현상을 답하고 원인 항목은 문서에 따로 없다고 했습니다. 그런데 검색 결과에는 원인(끝단부 열전대 1개의 지시값이 실제보다 1.5°C 높게 나옴)과 조치(열전대 교체, 끝단부 온도 보정값 재입력)가 적힌 "시정 조치" 절이 들어 있었습니다. 검색 결과는 맞는데 응답이 원인을 빠뜨렸으므로 생성의 문제이고, 교재의 네 가지 확인 가운데 4번(빠진 답은 없는지)으로 찾아냅니다. 모든 응답에 `[문서번호_버전]` 출처가 붙었습니다.
- **5번 질문(답이 없음)**: 규칙이 있을 때 응답은 "사내 문서에서 근거를 찾지 못했습니다"였습니다. 1위는 `NOTI-041`(DIFF 라인 PM 요일 변경 공지, 0.839)입니다. 이 공지에는 DIFF-01부터 DIFF-04까지의 요일만 있고 DIFF-07은 없습니다. 규칙을 빼면 응답은 DIFF-07의 요일이 제공된 문서에서 확인되지 않는다고 시작한 뒤, `NOTI-041`의 DIFF-01과 DIFF-02는 매월 둘째 수요일, DIFF-03과 DIFF-04는 매월 둘째 목요일이라는 내용을 참고로 덧붙였습니다. 이 응답을 읽은 사람이 DIFF-07도 수요일이나 목요일이라고 받아들일 수 있습니다. 이 묶음에서는 검색 점수(0.839)가 답이 있는 질문의 점수(0.863~0.914)보다 낮았지만, 교재 예제 3-8에서는 답이 없는 질문의 점수가 답이 있는 질문보다 높았습니다. 점수만으로 답의 유무를 판단하지 않고, 근거 없음 규칙과 진단 항목으로 확인합니다.
- **구판을 인덱스에 넣었을 때**: 청크가 39개에서 43개로 늘고, 검색 결과 네 건 가운데 v2.0이 두 건, v1.0이 두 건입니다. 이번 실행의 응답은 `[SOP-DIFF-002_v2.0]`을 근거로 허용 편차 ±0.5°C를 "현행 기준"으로 답했습니다. 구판의 값(±1.0°C)은 응답에 섞이지 않았습니다. 문서마다 `[문서번호_버전]`이 붙어 있었고, 개정판 본문에도 "v1.0의 ±1.0°C에서 강화"라는 말이 있어서 버전 표기만의 효과로 단정하지는 않습니다. 한 번 실행한 결과입니다.
- **구판을 뺐을 때**: 검색 결과 네 건이 모두 v2.0이고, 응답은 같은 ±0.5°C를 답했습니다.
- **응답이 맞아도 구판을 남기면 안 되는 이유**: 검색 결과 네 건 가운데 두 건을 구판이 차지해서 같은 절이 중복되고, 값이 맞은 것은 모델이 버전 표기를 읽고 고른 결과일 뿐 검색이 보장한 것이 아닙니다. 버전 표기가 빠진 프롬프트에서는 모델이 현행 값을 하나로 내세우지 못했습니다(교재 예제 3-6). 구판은 인덱스에서 빼는 것이 가장 확실합니다.
'''

P3_MORE_MD = '''
## 더 해 보기

- `build_prompt()`의 규칙에 "같은 문서의 여러 판이 있으면 버전이 높은 것을 따른다"를 더해, 구판을 인덱스에 넣은 상태에서 응답이 어떻게 바뀌는지 세 번씩 비교합니다.
- 교재의 `diagnose()`를 새 문서 묶음에 적용해 질문 다섯 개를 한 표로 봅니다.
- 이 실습의 '할 일'을 AI 코딩 도구에 보여 주고 `build_prompt()`와 `latest_version_rows()`를 만들게 한 뒤 테스트 셀로 검사합니다. 어느 항목이 실패하는지 확인합니다.
'''


def practice_cells(solution):
    common = P3_COMMON_CELL.replace('__PARTS__', parts_source()).replace('__TITLES__', titles_source())
    cells = [md(P3_SOLUTION_INTRO if solution else P3_INTRO),
             md(SETUP_MD), code(SETUP_KEYS), code(SETUP_COMMON), md(SETUP_AFTER),
             md(P3_COMMON_MD), code(common, '실습준비'),
             md(P3_MD), code(P3_SOLUTION if solution else P3_SKELETON, '실습3'), code(P3_CHECK),
             code(P3_QUESTIONS), code(P3_NO_RULE), code(P3_VERSION),
             md(P3_EXPLAIN if solution else P3_ANSWER_MD)]
    if not solution:
        cells.append(md(P3_MORE_MD))
    return cells


if __name__ == '__main__':
    save('3일차_03_실습.ipynb', practice_cells(solution=False))
    save('3일차_03_실습_풀이.ipynb', practice_cells(solution=True))
