"""2일차 파트 3의 실습 노트북과 풀이 노트북을 만든다.

사용법: python make_nb_day2_part3.py
출력: 노트북/2일차_03_실습.ipynb, 노트북/2일차_03_실습_풀이.ipynb

노트북은 노트북/ 폴더에서 실행한다(llm.py, embed.py, checks3.py, data/ 가 같은 폴더에 있다).
"""
from make_nb_day2 import SETUP_AFTER, SETUP_COMMON, SETUP_KEYS, SETUP_MD, TODO, code, md, save

PRACTICE_INTRO = '''
# 2일차 파트 3 실습: RAG의 원리와 임베딩 검색

실습은 두 개입니다(실습 8, 9). 실습 8에서는 검색 함수와 측정 함수를 직접 작성해 두 검색 방법을 비교합니다. 실습 9에서는 검색 1위 문서를 열어 판정하고 질문을 고쳐 씁니다.
`NotImplementedError`가 있는 곳과 빈 칸을 직접 채웁니다. 막히면 힌트를 펼쳐 보고, 다 한 뒤에 `2일차_03_실습_풀이.ipynb`와 비교합니다.
임베딩 모델은 PC에서 실행합니다. 준비 셀의 연결 확인 한 번 외에는 API를 부르지 않습니다.
'''

SOLUTION_INTRO = '''
# 2일차 파트 3 실습 풀이

`2일차_03_실습.ipynb`의 풀이와 해설입니다. 풀이는 하나의 예시이며, 테스트 셀을 통과한다면 다르게 작성해도 됩니다.
'''

COMMON_MD = '''
## 실습 준비

아래 셀은 두 실습이 함께 쓰는 재료와 함수입니다. 그대로 실행합니다. 문서 253건의 임베딩을 계산하므로 시간이 걸립니다. 교재를 만들 때 쓴 PC에서는 17초가 걸렸고, PC에 따라 다릅니다.

임베딩 모델을 처음 쓰는 PC에서는 모델을 내려받습니다. 사내에서는 환경 변수 `HF_ENDPOINT`에 사내 Hugging Face 프록시 주소를 넣고 Jupyter를 시작합니다. 설정하지 않았다면 아래 셀이 주소를 물어봅니다. 입력한 주소는 화면에 보이지 않고 노트북 파일에도 저장되지 않습니다. 자세한 설정 방법은 교재 "실습 환경 준비"의 "임베딩 모델 준비" 절에 있습니다.

| 이름 | 내용 |
| --- | --- |
| `names`, `docs` | 문서 번호의 목록과, 같은 순서의 본문 목록(253건) |
| `keyword_scores(question)` | 글자 단위 TF-IDF로 계산한 문서 253건의 점수 배열 |
| `embedding_scores(question)` | 임베딩의 코사인 유사도로 계산한 문서 253건의 점수 배열 |
'''

COMMON_CELL = '''
# 실습 준비
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

import checks3
import embed

CORPUS = f'{DATA}/corpus'
names = sorted(file[:-3] for file in os.listdir(CORPUS) if file.endswith('.md'))
docs = [open(f'{CORPUS}/{name}.md', encoding='utf-8').read() for name in names]

embed.load()                                          # 임베딩 모델을 불러옵니다
index = embed.passages(docs)                          # 문서 253건의 벡터 인덱스
char_tfidf = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 3))
char_matrix = char_tfidf.fit_transform(docs)


def keyword_scores(question):
    """글자 단위 TF-IDF 점수. 문서 253건의 점수 배열을 돌려줍니다."""
    return (char_matrix @ char_tfidf.transform([question]).T).toarray().ravel()


def embedding_scores(question):
    """임베딩의 코사인 유사도. 문서 253건의 점수 배열을 돌려줍니다."""
    return index @ embed.query(question)


print(f'문서 {len(docs)}건, 인덱스 {index.shape}')
'''

P8_MD = '''
## 실습 8 검색 함수와 측정 함수 작성하기

**목적** 점수 배열에서 순위를 구하고 recall@k를 계산하는 코드를 직접 작성합니다. 두 검색 방법을 같은 질문 세트로 측정합니다.

**재료** `data/2일차/검색_질문_실습.csv`. 질문 15개와 정답 문서 번호입니다. 교재의 예제와 겹치지 않는 질문입니다.

**할 일** 함수 세 개를 작성합니다. `scores`는 `keyword_scores()`나 `embedding_scores()`가 돌려준 점수 배열이고, `names`와 같은 순서입니다.

1. `rank_of(scores, names, gold)`: 점수가 높은 순으로 정렬했을 때 정답 문서 `gold`가 몇 위인지 돌려줍니다. 1위가 1입니다. 점수가 같은 문서는 `names`의 순서대로 순위를 매깁니다.
2. `recall_at(ranks, k)`: 순위의 목록에서 k위 안에 든 것의 비율(%)을 돌려줍니다.
3. `search(scores, names, k=3)`: 점수가 높은 순으로 상위 k건의 `(문서 번호, 점수)` 목록을 돌려줍니다. 점수는 소수 셋째 자리까지 반올림한 `float`입니다. k가 문서 수보다 크면 있는 만큼만 돌려줍니다.

**완료 기준** 테스트 셀이 "실습 8 통과"를 출력합니다. 그다음 측정 셀을 실행해 두 방법의 recall@1과 recall@3, 그리고 두 방법에서 정답 문서의 순위가 가장 크게 다른 질문을 적습니다.

<details><summary>힌트 1</summary>

`np.argsort(-scores, kind='stable')`은 점수가 높은 순으로 문서의 위치를 돌려줍니다. `kind='stable'`을 주면 점수가 같은 문서가 원래 순서를 유지합니다.
</details>

<details><summary>힌트 2</summary>

정답 문서의 위치는 `names.index(gold)`입니다. 정렬한 위치 목록에서 이 값이 몇 번째에 있는지 찾고 1을 더합니다.
</details>

<details><summary>힌트 3</summary>

`round(float(scores[position]), 3)`으로 넘파이 숫자를 파이썬의 `float`로 바꿔 반올림합니다.
</details>
'''

P8_SKELETON = f'''
# 실습 8
def rank_of(scores, names, gold):
    """점수가 높은 순으로 정렬했을 때 정답 문서가 몇 위인지 돌려줍니다."""
    {TODO}


def recall_at(ranks, k):
    """순위의 목록에서 k위 안에 든 것의 비율(%)을 돌려줍니다."""
    {TODO}


def search(scores, names, k=3):
    """점수가 높은 순으로 상위 k건의 (문서 번호, 점수) 목록을 돌려줍니다."""
    {TODO}
'''

P8_SOLUTION = '''
# 실습 8
def rank_of(scores, names, gold):
    """점수가 높은 순으로 정렬했을 때 정답 문서가 몇 위인지 돌려줍니다."""
    order = list(np.argsort(-scores, kind='stable'))      # 점수가 높은 순서의 위치. 같은 점수는 원래 순서
    return order.index(names.index(gold)) + 1


def recall_at(ranks, k):
    """순위의 목록에서 k위 안에 든 것의 비율(%)을 돌려줍니다."""
    return sum(rank <= k for rank in ranks) / len(ranks) * 100


def search(scores, names, k=3):
    """점수가 높은 순으로 상위 k건의 (문서 번호, 점수) 목록을 돌려줍니다."""
    order = np.argsort(-scores, kind='stable')[:k]
    return [(names[position], round(float(scores[position]), 3)) for position in order]
'''

P8_CHECK = '''
# 실습 8 확인 (임베딩 모델도 API도 부르지 않습니다)
checks3.check_search(rank_of, recall_at, search)
'''

P8_MEASURE = '''
# 실습 8 측정
practice = pd.read_csv(f'{DATA}/검색_질문_실습.csv')
for label, scores_of in [('키워드', keyword_scores), ('임베딩', embedding_scores)]:
    practice[label] = [rank_of(scores_of(question), names, gold)
                       for question, gold in zip(practice['질문'], practice['정답'])]
    print(f"{label} 검색: recall@1 {recall_at(practice[label], 1):.0f}%, recall@3 {recall_at(practice[label], 3):.0f}%")
print(practice[['질문', '유형', '키워드', '임베딩']].to_string(index=False))
'''

P8_ANSWER_MD = '''
**적어 보기**

- 키워드 검색의 recall@1과 recall@3:
- 임베딩 검색의 recall@1과 recall@3:
- 두 방법에서 정답 문서의 순위가 가장 크게 다른 질문과 각 순위:
- 그 질문의 정답 문서를 열어(`print(docs[names.index('문서 번호')])`) 질문과 문서의 낱말이 어떻게 다른지:
'''

P8_EXPLAIN = '''
**해설**

아래 숫자는 2026-11-24에 실행한 결과입니다. 같은 임베딩 모델을 쓰면 거의 같은 값이 나옵니다.

| 방법 | recall@1 | recall@3 |
| --- | --- | --- |
| 키워드 검색(글자 단위 TF-IDF) | 93% (14/15) | 100% (15/15) |
| 임베딩 검색 | 93% (14/15) | 93% (14/15) |

- 두 방법 모두 15개 가운데 14개에서 정답 문서를 1위로 찾았습니다. 교재의 예제 3-5보다 높은 것은 이 질문 세트에 문서의 제목과 같은 낱말로 물은 질문이 많기 때문입니다. 질문 세트가 어떻게 구성됐는지에 따라 recall@k가 달라지므로, 측정에 쓴 질문의 유형을 함께 봐야 합니다.
- 두 방법이 모두 1위로 찾지 못한 질문은 "CVD 장비가 새는지 점검하는 절차"입니다. 정답 문서는 "CVD 장비 리크 체크"입니다. 키워드 검색에서는 2위이고 임베딩 검색에서는 11위입니다. "새는지 점검"과 "리크 체크"는 같은 일이지만 낱말이 다릅니다. 임베딩 검색이 다른 낱말로 물은 질문을 언제나 찾는 것은 아닙니다.
- `rank_of()`에서 `kind='stable'`을 주지 않으면 점수가 같은 문서의 순서가 실행 환경에 따라 달라질 수 있습니다. 측정 코드는 같은 입력에 같은 결과를 내야 다른 실행과 비교할 수 있습니다.
- 15개는 작은 표본입니다. 질문 한 개가 약 7%포인트입니다.
'''

P9_MD = '''
## 실습 9 1위 문서를 판정하고 질문 고쳐 쓰기

**목적** 검색 1위 문서가 질문에 답하는 문서인지 본문을 읽고 판정합니다. 질문을 어떻게 쓰느냐에 따라 검색 결과가 달라지는 것을 확인합니다.

**재료** 현장 질문 3개(`data/2일차/현장_질문_6.csv`의 2, 5, 6번째 질문). 뒤의 두 질문은 앞부분에 사례 이야기가 붙어 있습니다. 실제로 묻는 것은 뒷부분입니다.

**할 일**

1. 검색 셀을 실행해 질문마다 1~3위 문서를 봅니다. 검색에는 실습 8에서 작성한 `search()`와 `embedding_scores()`를 쓰므로, 실습 8의 테스트를 통과한 뒤 실행합니다.
2. 열어 보기 셀의 `NAME`에 1위 문서의 번호를 넣어 본문을 읽습니다. 질문이 묻는 수치나 절차가 본문에 있으면 `O`, 없으면 `X`입니다. 제목과 점수만 보고 판정하지 않습니다.
3. `X`인 질문은 2위와 3위 문서도 열어 정답 문서가 몇 위인지 찾습니다.
4. 판정 셀의 `JUDGE`와 `RANK`를 채우고 실행합니다.
5. 고쳐 쓰기 셀을 실행합니다. 사례 이야기를 지운 질문과, 문서에 적힌 말로 고쳐 쓴 질문의 1~3위를 봅니다. 그다음 `REWRITTEN`의 문장을 직접 바꿔 다시 실행해 봅니다.

**완료 기준** 테스트 셀이 "실습 9 통과"를 출력합니다. 질문마다 판정의 근거가 된 문장(또는 그런 문장이 없다는 것)을 적고, 고치기 전과 후의 1위 문서와 점수를 적습니다.

<details><summary>힌트 1</summary>

1위 문서가 품질 이슈 보고서(`QIR`)나 회의록(`MTG`)이면 질문에 나온 설비 이름이나 현상이 본문에 있는지와, 질문이 묻는 기준이나 절차가 본문에 있는지를 따로 확인합니다.
</details>

<details><summary>힌트 2</summary>

`RANK`에는 `X`인 질문만 적습니다. 정답 문서가 2위면 2, 3위면 3입니다.
</details>
'''

P9_SEARCH = '''
# 실습 9 (1) 질문 3개를 검색합니다
field = pd.read_csv(f'{DATA}/현장_질문_6.csv')
MY_Q = [field['질문'][1], field['질문'][4], field['질문'][5]]


def show(question, k=3):
    """질문의 상위 k건을 순위, 점수, 문서 번호, 제목과 함께 출력하고 상위 k건의 문서 번호 목록을 돌려줍니다."""
    found = search(embedding_scores(question), names, k)
    for place, (name, score) in enumerate(found, 1):
        print(f'   {place}위 {score} {name}, {docs[names.index(name)].splitlines()[0][2:]}')
    return [name for name, _ in found]


top_lists = []                                        # 질문마다 1~3위 문서 번호
for number, question in enumerate(MY_Q, 1):
    print(number, question)
    top_lists.append(show(question))
top_names = [found[0] for found in top_lists]          # 질문마다 1위 문서 번호
'''

P9_OPEN = '''
# 실습 9 (2) 문서 번호를 넣어 본문을 읽습니다. NAME을 바꿔 가며 여러 번 실행합니다
NAME = top_names[0]
print(docs[names.index(NAME)])
'''

P9_JUDGE_SKELETON = '''
# 실습 9 (3) 판정을 적습니다
JUDGE = {}          # 예: {1: 'O', 2: 'X', 3: 'O'}. 1위 문서가 질문에 답하면 'O', 아니면 'X'
RANK = {}           # 예: {2: 3}. 'X'인 질문만. 정답 문서가 3위면 3
'''

P9_JUDGE_SOLUTION = '''
# 실습 9 (3) 판정을 적습니다
JUDGE = {1: 'X', 2: 'X', 3: 'X'}
RANK = {1: 2, 2: 2, 3: 3}
'''

P9_CHECK = '''
# 실습 9 확인 (정답 문서와 비교합니다)
checks3.check_judgement(MY_Q, top_lists, JUDGE, RANK)
'''

P9_REWRITE = '''
# 실습 9 (4) 질문을 고쳐 써서 다시 검색합니다. 처음에는 그대로 실행하고, 그다음 문장을 바꿔 봅니다
REWRITTEN = {
    '사례 이야기를 지움': ['칠러 유량이 얼마 이상이어야 정상인가요?',
                           '포토 시즈닝 런은 원래 어떻게 하나요?',
                           'CMP 알람 뜨면 1차로 뭘 봐야 하나요?'],
    '문서에 적힌 말로 고침': ['에치 장비 칠러 유량 기준',
                              '포토 장비 시즈닝 런 운영',
                              'CMP 장비 알람 1차 대응'],
}
for label, rewritten in REWRITTEN.items():
    print('=====', label)
    for number, question in enumerate(rewritten, 1):
        print(number, question)
        show(question)
'''

P9_ANSWER_MD = '''
**적어 보기**

- 질문 1의 판정과 근거 문장:
- 질문 2의 판정과 근거 문장:
- 질문 3의 판정과 근거 문장:
- 사례 이야기를 지웠을 때 1위 문서와 점수가 어떻게 바뀌었나요? 원래 1위 문서의 어떤 내용이 질문과 겹쳤나요?
- 문서에 적힌 말로 고쳤을 때 1위 점수와, 1위와 2위의 점수 차이는 어떻게 바뀌었나요?
- 검색에 넣을 질문을 어떻게 쓰면 좋은지 한 문장으로:
'''

P9_EXPLAIN = '''
**해설**

아래는 2026-11-24에 실행한 결과입니다.

| 질문 | 1위 문서(점수) | 판정 | 정답 문서와 순위 |
| --- | --- | --- | --- |
| 1. 칠러 유량이 얼마 이상이어야 정상인가요? | `QIR-2026-0712` (0.811) | X | `SOP-ETCH-007_v2.1`, 2위(0.808) |
| 2. PHOTO-02 파티클이 올라서 … 포토 시즈닝 런은 원래 어떻게 하나요? | `MTG-2026-W29` (0.885) | X | `SOP-포토-018`, 2위(0.877) |
| 3. CMP-02 RCP-CMP-330 이탈 로트가 … CMP 알람 뜨면 1차로 뭘 봐야 하나요? | `QIR-2026-0281` (0.880) | X | `SOP-CMP-021`, 3위(0.873) |

- **세 질문 모두 1위 문서가 질문에 답하지 않습니다.** 질문 1의 1위인 `QIR-2026-0712`에는 "칠러 배관 부분 폐색 확인"이라는 문장이 있지만 유량의 기준은 없습니다. 기준(12 L/min 이상)은 2위인 `SOP-ETCH-007_v2.1`에 있습니다. 같은 낱말이 나온다는 것과 질문에 답한다는 것은 다릅니다.
- **질문 앞부분의 사례 이야기 때문에 다른 문서가 1위가 됩니다.** 질문 2의 1위인 `MTG-2026-W29`에는 PHOTO-01, PHOTO-04의 시즈닝 런 파티클과 필터 교체 결정이 나옵니다. 질문 3의 1위인 `QIR-2026-0281`에는 CMP-01, 로트, (티칭) 이탈이 나옵니다. 질문 앞부분의 "PHOTO-02 파티클이 올라서 필터를", "CMP-02 RCP-CMP-330 이탈 로트"와 비슷한 낱말입니다. 임베딩은 질문 전체를 벡터 하나로 바꾸므로, 묻는 것과 관계없는 앞부분도 검색 점수에 반영됩니다.
- **사례 이야기를 지우자 두 질문 모두 정답 문서가 1위가 됐습니다.** "포토 시즈닝 런은 원래 어떻게 하나요?"의 1위는 `SOP-포토-018`(0.860)이고, "CMP 알람 뜨면 1차로 뭘 봐야 하나요?"의 1위는 `SOP-CMP-021`(0.882)입니다.
- **문서에 적힌 말로 고치면 1위 점수가 높아집니다.** 사례 이야기만 지운 질문과 비교하면 "CMP 장비 알람 1차 대응"의 1위 점수는 0.882에서 0.922로, "포토 장비 시즈닝 런 운영"은 0.860에서 0.900으로 올랐습니다. 1위와 2위의 차이는 거의 그대로였습니다(CMP 0.026과 0.026, 포토 0.031과 0.030). "에치 장비 칠러 유량 기준"으로 고치자 질문 1도 정답 문서가 1위(0.878)가 됐습니다.
- **정답 문서는 세 질문 모두 3위 안에 있었습니다.** 상위 3건을 프롬프트에 넣는 RAG라면 고치기 전의 질문으로도 정답 문서가 들어갑니다. 다만 관계없는 문서 두 건도 함께 들어갑니다.

검색에 넣을 질문에는 묻는 것만 남깁니다. 배경 설명은 검색이 끝난 뒤 모델에 보내는 프롬프트에 넣습니다.
'''

MORE_MD = '''
## 더 해 보기

- 판정을 모델에게 맡겨 봅니다. 질문과 1위 문서의 본문을 `llm.ask()`로 보내 "이 문서만으로 질문에 답할 수 있으면 첫 줄에 '답할 수 있음', 없으면 '답할 수 없음'이라고 쓰고, 둘째 줄부터 근거가 된 문장을 문서에서 그대로 옮겨 적는다"고 요청합니다. 모델이 옮겨 적은 문장이 실제로 문서에 있는지 확인합니다.
- `검색_질문_실습.csv`에 내 업무의 말투로 질문을 다섯 개 더하고 정답 문서를 붙여 다시 측정합니다.
- `search()`가 돌려준 상위 3건의 본문을 프롬프트에 넣어 답하게 하는 `answer()`를 작성해 봅니다(교재의 예제 3-7).
'''


def practice_cells(solution):
    cells = [md(SOLUTION_INTRO if solution else PRACTICE_INTRO),
             md(SETUP_MD), code(SETUP_KEYS), code(SETUP_COMMON), md(SETUP_AFTER),
             md(COMMON_MD), code(COMMON_CELL, '실습준비')]
    cells += [md(P8_MD), code(P8_SOLUTION if solution else P8_SKELETON, '실습8'), code(P8_CHECK),
              code(P8_MEASURE), md(P8_EXPLAIN if solution else P8_ANSWER_MD)]
    cells += [md(P9_MD), code(P9_SEARCH), code(P9_OPEN),
              code(P9_JUDGE_SOLUTION if solution else P9_JUDGE_SKELETON, '실습9'), code(P9_CHECK),
              code(P9_REWRITE), md(P9_EXPLAIN if solution else P9_ANSWER_MD)]
    if not solution:
        cells.append(md(MORE_MD))
    return cells


if __name__ == '__main__':
    save('2일차_03_실습.ipynb', practice_cells(solution=False))
    save('2일차_03_실습_풀이.ipynb', practice_cells(solution=True))
