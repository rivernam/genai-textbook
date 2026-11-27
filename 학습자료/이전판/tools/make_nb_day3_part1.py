"""3일차 파트 1의 실습 노트북과 풀이 노트북을 만든다.

사용법: python make_nb_day3_part1.py
출력: 노트북/3일차_실습.ipynb, 노트북/3일차_실습_풀이.ipynb

VectorIndex 클래스는 원고(원고/3일차/01_벡터_DB와_RAG의_구조.md)의 예제 1-2에서 그대로 가져온다.
노트북은 노트북/ 폴더에서 실행한다(llm.py, embed.py, checks_d3.py, data/가 같은 폴더에 있다).
"""
import re
from pathlib import Path

from make_nb_day3 import SETUP_AFTER, SETUP_COMMON, SETUP_KEYS, SETUP_MD, TODO, code, md, save

MANUSCRIPT_1 = Path(__file__).resolve().parents[1] / '원고' / '3일차' / '01_벡터_DB와_RAG의_구조.md'


def vector_index_source():
    """원고의 예제 1-2에 있는 VectorIndex 클래스 코드를 그대로 가져온다(코드는 원고 한 곳에만 둔다)."""
    text = MANUSCRIPT_1.read_text(encoding='utf-8')
    found = re.search(r'```python\n# 예제 1-2 \(VectorIndex 클래스\)\n(.*?)\n```', text, flags=re.S)
    return found.group(1)


P1_INTRO = '''
# 3일차 파트 1 실습: 벡터 DB와 RAG의 구조

실습은 하나입니다(실습 1). 변경 목록을 벡터 인덱스에 반영하는 함수를 직접 작성하고, 일부를 빠뜨렸을 때 검색 결과가 어떻게 달라지는지 읽습니다.
`NotImplementedError`가 있는 곳을 직접 채웁니다. 막히면 힌트를 펼쳐 보고, 다 한 뒤에 `3일차_실습_풀이.ipynb`와 비교합니다.
테스트 셀은 임베딩 모델을 부르지 않고 작은 임시 인덱스로 함수를 검사합니다. 실제 문서를 반영하는 셀에서만 임베딩 모델을 실행합니다.
이 실습은 생성 모델 API를 쓰지 않습니다. "준비 (2)" 셀 끝의 연결 확인이 실패해도 그 앞에서 만든 `DATA`, `CORPUS`, `embed`는 그대로 쓸 수 있으므로 계속 진행합니다.
'''

P1_SOLUTION_INTRO = '''
# 3일차 파트 1 실습 풀이

`3일차_실습.ipynb`의 풀이와 해설입니다. 풀이는 하나의 예시이며, 테스트 셀을 통과한다면 다르게 작성해도 됩니다.
'''

P1_COMMON_MD = '''
## 실습 준비

아래 셀은 실습이 쓰는 재료와 클래스를 만듭니다. 그대로 실행합니다. 문서 253건의 임베딩을 계산하므로 GPU가 없는 PC에서는 수십 초가 걸리기도 합니다(교재를 만든 PC에서 같은 계산을 한 예제 1-1은 24초였습니다. 값은 PC와 실행할 때마다 다릅니다). 이 실습에는 `numpy`, `sentence-transformers`와 임베딩 모델이 필요합니다. 두 패키지는 위 "준비 (2)" 셀 안의 `# 설치:` 주석에 있는 명령으로 설치합니다. 임베딩 모델 준비는 교재 3일차의 "실습 환경 준비"를 따릅니다.

| 이름 | 내용 |
| --- | --- |
| `VectorIndex` | 교재 예제 1-2의 클래스입니다. 벡터, 문서 번호, 본문을 한 객체에 두고 `replace`, `add`, `remove`, `search`, `rank_of`를 제공합니다 |
| `BASE` | 변경을 반영하기 전의 인덱스(문서 253건)입니다. 실습에서는 복사본에 반영해 `BASE`를 그대로 둡니다 |
| `embed_text(text)` | 글 한 건을 벡터로 바꿉니다 |
| `report(index, label)` | 질문 6개의 정답 순위와 1위 문서를 출력합니다 |
'''

P1_COMMON_CELL = '''
# 실습 준비
import copy

import checks_d3

__CLASS__

names = sorted(file[:-3] for file in os.listdir(CORPUS) if file.endswith('.md'))
docs = [open(f'{CORPUS}/{name}.md', encoding='utf-8').read() for name in names]
BASE = VectorIndex(names, docs, embed.passages(docs), embed.model_name())


def embed_text(text):
    return embed.passages([text])[0]


questions = pd.read_csv(f'{DATA}/변경_질문_6.csv', encoding='utf-8-sig', keep_default_na=False)


def report(index, label):
    print(f'{label}, 행 수 {len(index)}')
    for question, gold in zip(questions['질문'], questions['정답']):
        vector = embed.query(question)
        top = index.search(vector, 1)[0][0]
        place = f'정답 {index.rank_of(vector, gold)}위' if gold in index.names else '정답 문서 없음'
        print(f'   {question[:26]:28s} {place}, 1위 {top}')


print(f'문서 {len(BASE):,}건, 인덱스 {BASE.vectors.shape}')
'''

P1_MD = '''
## 실습 1 변경 목록을 인덱스에 반영하기

**목적** 문서의 개정, 추가, 폐기를 바뀐 행만 고쳐 반영하는 코드를 직접 작성합니다. 변경의 일부를 빠뜨리면 검색 결과가 어떻게 달라지는지 확인합니다.

**재료** `data/3일차/변경_목록.csv`(변경 아홉 건), `data/3일차/변경_문서/`(개정본과 신규 문서 4건), `data/3일차/변경_질문_6.csv`(질문 6개와 정답 문서).

**할 일** `apply_changes(index, revised, added, retired, folder, embed_text)`를 작성합니다. `index`는 `VectorIndex`이고, `revised`, `added`, `retired`는 개정, 신규, 폐기할 문서 번호의 목록입니다. 개정본과 신규 문서는 `folder`에 `문서번호.md` 파일로 있고, `embed_text(글)`은 글 한 건의 벡터를 돌려줍니다.

1. 고치기 전에 목록을 검사합니다. 개정 또는 폐기할 문서가 인덱스에 없거나, 신규로 넣을 문서가 이미 있거나, 개정과 신규의 문서 파일이 없으면 `ValueError`를 냅니다. 이때 인덱스는 아무것도 고치지 않은 상태여야 합니다.
2. 개정과 신규 문서의 벡터는 인덱스를 고치기 전에 모두 계산합니다. 임베딩 중에 오류가 나도 인덱스는 아무것도 바뀌지 않아야 합니다.
3. 개정은 `replace`, 신규는 `add`, 폐기는 `remove`로 반영합니다.
4. 개정 건수, 신규 건수, 폐기 건수, 반영 후 행 수를 `{"교체": 2, "추가": 2, "삭제": 5, "행 수": 250}` 꼴의 딕셔너리(`dict`)로 돌려줍니다. 키 이름은 이대로 씁니다(교체는 개정, 추가는 신규, 삭제는 폐기의 건수입니다).

**완료 기준** 테스트 셀이 "실습 1 통과"를 출력합니다. 반영 후 인덱스는 250행이고 벡터, 문서 번호, 본문의 개수가 같습니다. 그다음 실제 문서에 반영하는 셀과 빠뜨린 두 경우의 셀을 실행해, 아래 "적어 보기"를 채웁니다.

<details><summary>힌트 1</summary>

검사와 반영을 같은 반복문에서 하면 목록의 뒤쪽에 틀린 문서가 있을 때 앞쪽은 이미 고쳐진 뒤입니다. 검사를 모두 끝낸 뒤에 반영을 시작합니다.
</details>

<details><summary>힌트 2</summary>

파일 존재는 `os.path.exists(f'{folder}/{name}.md')`로 확인합니다. 인덱스에 있는지는 `name in index.names`입니다. `add`는 맨 아래에 행을 붙이고, 이미 있는 이름이면 `ValueError`를 냅니다.
</details>

<details><summary>힌트 3</summary>

벡터는 반영하기 전에 `{문서 번호: 벡터}` 딕셔너리로 모두 만들어 둡니다. 반영 단계에서는 이 딕셔너리만 읽습니다.
</details>

<details><summary>힌트 4</summary>

개정본의 본문은 `open(f'{folder}/{name}.md', encoding='utf-8').read()`로 읽고, 그 글을 `embed_text()`에 넣어 벡터를 받아 `index.replace(name, doc, vector)`에 넘깁니다.
</details>
'''

P1_SKELETON = f'''
# 실습 1
def apply_changes(index, revised, added, retired, folder, embed_text):
    """변경 목록을 인덱스에 반영하고 건수를 돌려줍니다. 목록이 틀렸으면 ValueError를 내고 아무것도 고치지 않습니다."""
    {TODO}
'''

P1_SOLUTION = '''
# 실습 1
def apply_changes(index, revised, added, retired, folder, embed_text):
    """변경 목록을 인덱스에 반영하고 건수를 돌려줍니다. 목록이 틀렸으면 ValueError를 내고 아무것도 고치지 않습니다."""
    # 반영하기 전에 모두 검사합니다. 하나라도 틀리면 인덱스를 건드리지 않습니다
    missing = [name for name in revised + retired if name not in index.names]
    existing = [name for name in added if name in index.names]
    no_file = [name for name in revised + added if not os.path.exists(f'{folder}/{name}.md')]
    if missing or existing or no_file:
        raise ValueError(f'인덱스에 없는 문서 {missing}, 이미 있는 문서 {existing}, 파일이 없는 문서 {no_file}')

    # 개정과 신규 문서의 벡터를 먼저 모두 계산합니다. 임베딩 중에 오류가 나도 인덱스는 그대로입니다
    docs_of = {name: open(f'{folder}/{name}.md', encoding='utf-8').read() for name in revised + added}
    vectors_of = {name: embed_text(doc) for name, doc in docs_of.items()}

    for name in revised:
        index.replace(name, docs_of[name], vectors_of[name])
    for name in added:
        index.add(name, docs_of[name], vectors_of[name])
    for name in retired:
        index.remove(name)
    return {'교체': len(revised), '추가': len(added), '삭제': len(retired), '행 수': len(index)}
'''

P1_CHECK = '''
# 실습 1 확인 (임베딩 모델도 API도 부르지 않습니다)
checks_d3.check_apply_changes(apply_changes, VectorIndex)
'''

P1_APPLY = '''
# 실습 1 (1) 반영하기 전과 전체를 반영한 뒤
changes = pd.read_csv(f'{DATA}/변경_목록.csv', encoding='utf-8-sig')
REVISED = list(changes[changes['종류'] == '개정']['문서'])
ADDED = list(changes[changes['종류'] == '신규']['문서'])
RETIRED = list(changes[changes['종류'] == '폐기']['문서'])


def reflect(revised, added, retired):
    """BASE의 복사본에 변경을 반영해 돌려줍니다. BASE는 그대로 둡니다."""
    trial = copy.deepcopy(BASE)
    result = apply_changes(trial, revised, added, retired, f'{DATA}/변경_문서', embed_text)
    print(result)
    return trial


report(BASE, '반영 전')
full = reflect(REVISED, ADDED, RETIRED)
report(full, '전체 반영')
'''

P1_SCENARIOS = '''
# 실습 1 (2) 일부를 빠뜨리면
# 경우 A: EHS-001의 개정을 빠뜨립니다
missed_revision = reflect(['SOP-ETCH-005'], ADDED, RETIRED)
vector = embed.query(questions['질문'][1])
top_name = missed_revision.search(vector, 1)[0][0]
print(f"경우 A, 질문 2의 1위 {top_name}, EHS-001의 순위 {missed_revision.rank_of(vector, 'EHS-001')}")
print('   1위 문서에서 "감지기"가 든 줄:',
      [line for line in missed_revision.docs[missed_revision.names.index(top_name)].split('\\n') if '감지기' in line])

# 경우 B: 폐기 다섯 건 가운데 두 건만 지웁니다
missed_retired = reflect(REVISED, ADDED, ['NOTI-001', 'NOTI-007'])
top3 = missed_retired.search(embed.query(questions['질문'][5]), 3)
print('경우 B, 질문 6의 상위 3건', top3)
print('   그 문서들의 첫 줄:', [missed_retired.docs[missed_retired.names.index(name)].splitlines()[0] for name, _ in top3])
'''

P1_ANSWER_MD = '''
**적어 보기**

- 전체를 반영한 뒤 인덱스의 행 수와, 반영한 변경의 건수(교체, 추가, 삭제):
- 경우 A에서 질문 2의 1위 문서와 EHS-001의 순위. 1위 문서에 감지기 모니터링 시간이 있었는지. 이 인덱스로 RAG를 운영하면 현장 작업자가 어떤 답을 받는지:
- 경우 B에서 질문 6의 상위 3건에 지난 셧다운 공지가 몇 건 있었는지. 폐기가 빠짐없이 반영됐는지 `apply_changes()`의 반환값에서 무엇으로 확인할 수 있는지:
'''

P1_EXPLAIN = '''
**해설**

아래 숫자는 2026-11-24에 실행한 결과입니다. 같은 임베딩 모델을 쓰면 거의 같은 값이 나옵니다.

- 전체를 반영하면 인덱스는 253 + 2 - 5 = 250행이고, 반환값은 `{'교체': 2, '추가': 2, '삭제': 5, '행 수': 250}`입니다. 정답 문서가 있는 질문 5개는 모두 정답 문서가 1위가 됩니다. 정답이 없는 질문 6의 1위는 셧다운과 관계없는 `EHS-020`입니다. 폐기한 공지는 나오지 않지만, 검색은 답이 없어도 항상 어떤 문서를 돌려줍니다. 그래서 근거가 없을 때 모델이 답을 거절하게 하는 규칙이 필요합니다(파트 3). 반영하기 전에는 질문 2의 정답 `EHS-001`이 4위였고, 질문 3과 4의 정답 문서는 인덱스에 없었습니다.
- **경우 A**: 질문 2의 1위는 `EHS-016`이고 `EHS-001`은 4위입니다. 상위 4건은 점수가 0.885~0.886으로 거의 같아서 PC에 따라 순서가 바뀔 수 있지만, 개정 전의 `EHS-001`이 1위가 아니라는 점은 같습니다. `EHS-016` 본문에 "감지기"가 든 줄은 없습니다. 이 인덱스로 RAG를 만들면 15분 모니터링 절이 든 개정본이 인덱스에 없으므로, 모델은 그 절을 근거로 답할 수 없습니다. 모델은 근거를 찾지 못했다고 답하거나, 개정 전 문서의 내용으로 답할 수 있습니다. 현장 작업자는 개정된 안전 절차를 받지 못합니다. 응답에 오류가 나지 않으므로 인덱스가 오래됐다는 것을 응답만 봐서는 알 수 없습니다.
- **경우 B**: 폐기를 두 건만 지우면 인덱스는 253행으로 그대로이고, 질문 6의 상위 3건이 모두 지난 셧다운 공지(`NOTI-013`, `NOTI-019`, `NOTI-025`)입니다. 반환값의 `'삭제'`는 인자로 넘긴 목록의 길이일 뿐이어서, 폐기가 빠진 것은 `'행 수'`가 253이라는 것으로 알 수 있습니다. 변경 목록의 건수에서 기대하는 행 수(253 + 2 - 5 = 250)를 계산해 두고 반환값의 행 수와 비교하면 반영을 놓친 변경을 바로 찾을 수 있습니다.
- `apply_changes()`가 고치기 전에 목록을 모두 검사하는 이유는, 목록의 뒤쪽에 틀린 문서가 있을 때 앞쪽만 반영된 인덱스가 남지 않게 하기 위해서입니다. 반만 반영된 인덱스는 경우 A와 B처럼 응답에 오류 없이 옛 내용이 섞입니다.
'''

P1_MORE_MD = '''
## 더 해 보기

- `apply_changes()`에 같은 문서가 개정 목록과 폐기 목록에 함께 들어 있는 경우를 검사하는 조건을 더해 봅니다.
- 변경 목록을 AI 코딩 도구에 보여 주고 `apply_changes()`를 만들어 달라고 한 뒤, 이 실습의 테스트 셀로 검사해 봅니다. 도구가 검사 없이 한 건씩 반영하는 코드를 만들었다면 어느 테스트가 실패하는지 확인합니다.
- `변경_문서` 폴더를 임시 폴더에 복사한 뒤, 복사한 `EHS-001.md`에서 "감지기"라는 낱말을 "가스 농도 센서"로 바꿔 반영하면 질문 2의 순위가 어떻게 되는지 봅니다. 원본 재료는 고치지 않습니다.
'''


def practice_cells(solution):
    common = P1_COMMON_CELL.replace('__CLASS__', vector_index_source())
    cells = [md(P1_SOLUTION_INTRO if solution else P1_INTRO),
             md(SETUP_MD), code(SETUP_KEYS), code(SETUP_COMMON), md(SETUP_AFTER),
             md(P1_COMMON_MD), code(common, '실습준비'),
             md(P1_MD), code(P1_SOLUTION if solution else P1_SKELETON, '실습1'), code(P1_CHECK),
             code(P1_APPLY), code(P1_SCENARIOS), md(P1_EXPLAIN if solution else P1_ANSWER_MD)]
    if not solution:
        cells.append(md(P1_MORE_MD))
    return cells


if __name__ == '__main__':
    save('3일차_실습.ipynb', practice_cells(solution=False))
    save('3일차_실습_풀이.ipynb', practice_cells(solution=True))
