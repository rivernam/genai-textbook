# 파트 3. 첫 RAG 완성

파트 1에서는 벡터 인덱스를 파일로 저장하고 고치는 방법을 다뤘고, 파트 2에서는 문서를 청크로 자르고 메타데이터를 붙이는 함수를 만들었습니다. 이 파트에서는 그것들을 모아 RAG를 완성합니다. 질문을 검색하고, 찾은 문서를 프롬프트에 넣고, 출처가 붙은 응답을 받습니다. 그리고 RAG가 오류 없이 틀리는 경우를 일부러 만들어 보고, 응답이 이상할 때 어디부터 확인하는지 정합니다.

이 파트를 마치면 다음을 할 수 있습니다.

1. 검색 결과를 프롬프트에 넣어 응답과 출처를 받고, 문서 없이 물었을 때의 응답과 비교해 달라진 점을 말합니다.
2. RAG 프롬프트를 역할 지정, 검색 결과, 출력 규칙, 근거 없음 규칙(예제 3-3에서 설명합니다)으로 구성하고, 근거 없음 규칙을 뺐을 때 생기는 일을 보여 줍니다.
3. 출처가 안정적으로 붙으려면 검색 결과의 청크마다 문서 번호를 붙이는 것과 출력 규칙에서 요구하는 것이 모두 필요하다는 점을 실행해 확인합니다.
4. RAG가 오류 없이 틀리는 세 경우(관련 없는 문서가 상위를 채움, 버전 충돌, 절이 문서의 맥락을 잃음)를 증상으로 알아보고 각각의 대책을 적용해 효과를 확인합니다.
5. 응답이 이상할 때 검색 결과부터 확인하는 진단 함수를 작성하고, 점수만으로는 답이 있는 질문과 없는 질문을 구분할 수 없다는 점을 설명합니다.
6. 새 문서 묶음으로 RAG를 구성해 질문을 진단하고, 구판이 섞였을 때 고칩니다.

예제의 실행 결과는 2026-11-26에 실행한 값이고, 학습 노트북을 실행한 출력을 그대로 실었습니다. 모델의 응답은 실행할 때마다 조금씩 다릅니다. 검색 결과(점수, 문서, 절)는 인덱스가 같으면 거의 같은 값이 나옵니다. 이 파트의 예제는 LLM API를 약 40회 호출하므로 API 요금이 듭니다. 응답이 실행마다 다른 예제는 같은 요청을 세 번씩 보내 결과를 셉니다.

## 이 파트에서 만드는 것 {추가}

:::요점
질문을 넣으면 검색 결과 청크 네 건을 찾고, 그 청크를 프롬프트에 넣어 문서 번호가 붙은 응답을 받는 RAG를 만듭니다. 응답이 틀렸을 때 원인을 찾는 진단 함수도 만듭니다.
:::

재료는 2일차와 같은 가상 공장 문서 253건과 각 문서의 메타데이터(문서 번호, 버전, 유형, 날짜)를 적은 목록 파일입니다. 실습에서는 새 문서 12건과 구판 1건을 씁니다. 입력은 질문 한 건이고 출력은 검색 결과와 응답입니다.

| 구분 | 항목 | 내용 |
| --- | --- | --- |
| 입력 | 질문 | 에치 장비 ESC 온도 상한이 몇 도이고, 초과하면 어떻게 조치해야 하나요? |
| 검색 결과 1위 | 문서와 절 | `SOP-ETCH-007_v2.1` 초과 시 조치 절차 (점수 0.890) |
| 검색 결과 2위 | 문서와 절 | `SOP-ETCH-007_v2.1` 관리 기준 (0.887) |
| 검색 결과 3위 | 문서와 절 | `QIR-2026-0712_v1.0` 현상 (0.880) |
| 검색 결과 4위 | 문서와 절 | `SOP-ETCH-007_v2.1` 문서 첫머리 (0.879) |
| 출력 | 응답 | 상한 62.0°C, 5분 이상 초과하면 챔버 인터락이 작동한다는 것, 초과 시 조치 절차 세 단계를 `[SOP-ETCH-007_v2.1]` 출처와 함께 답함 |

이 파트는 다음 순서로 진행합니다.

1. 파트 1과 2의 부품(문서 구조로 자르기, 메타데이터, 임베딩, 검색)을 모아 청크 인덱스를 만듭니다.
2. 검색 결과를 프롬프트에 넣고 응답을 받습니다.
3. RAG 프롬프트를 네 요소로 구성하고, 출처를 붙이게 하는 방법을 확인합니다.
4. RAG가 오류 없이 틀리는 세 경우를 일부러 만들어 고칩니다.
5. 응답을 믿어도 되는지 확인하는 진단 함수를 만들고 질문 여섯 개로 테스트합니다.

## 청크 인덱스 만들기 {원본 p.208-213}

:::요점
문서를 절 단위 청크로 자르고 메타데이터를 붙여 임베딩하면, 문서 한 건이 아니라 절 단위로 검색됩니다. 검색은 점수가 높은 청크를 돌려주고, 메타데이터로 검색할 문서의 유형을 제한할 수 있습니다.
:::

2일차에서는 문서 한 건이 검색의 단위였습니다. 이번에는 문서를 `## `로 시작하는 절 단위로 잘라 청크로 만들고, 청크마다 문서 목록 파일(`corpus_manifest.csv`)의 메타데이터를 붙입니다. 이렇게 하면 질문에 맞는 절만 프롬프트에 넣을 수 있고, 어느 문서의 어느 절인지도 알 수 있습니다. 문서의 첫 조각은 제목과 문서 정보(적용 장비, 개정일 등)가 있는 줄까지만 둡니다. 첫 조각의 8줄과 청크 본문의 1,200자는 이 코퍼스보다 긴 문서가 들어올 때를 대비한 상한입니다. 이 코퍼스에서는 첫 조각이 가장 길어도 7줄이고 청크가 가장 길어도 304자여서, 실제로 잘리는 청크는 없습니다. 임베딩 모델은 최대 입력 길이(512토큰, 파트 1)를 넘는 부분을 벡터에 반영하지 않으므로, 다른 문서에 쓸 때는 청크의 토큰 수를 확인합니다.

:::예제 3-1 청크 인덱스 만들기
```python
# 예제 3-1 (청크 인덱스를 만드는 부품)
import csv
import re
import unicodedata
from collections import namedtuple

Chunk = namedtuple('Chunk', 'doc_id version type date section text')
Hit = namedtuple('Hit', 'score doc_id version type date section text')
ChunkIndex = namedtuple('ChunkIndex', 'chunks vectors')


def read_manifest(path):
    """문서 목록 파일을 {파일 이름: 메타데이터}로 읽습니다."""
    with open(path, encoding='utf-8-sig') as file:
        return {unicodedata.normalize('NFC', row['file']): row for row in csv.DictReader(file)}


def build_chunks(folder, manifest):
    """문서를 '## ' 절 단위로 잘라 메타데이터를 붙인 Chunk 목록을 돌려줍니다."""
    chunks = []
    for raw in sorted(os.listdir(folder)):
        file = unicodedata.normalize('NFC', raw)         # 한글 파일 이름을 목록 파일의 이름과 같은 형태로 맞춥니다
        if not file.endswith('.md'):
            continue
        meta = manifest[file]
        head, *sections = re.split(r'\n(?=## )', open(f'{folder}/{raw}', encoding='utf-8').read())
        for part in [head] + sections:
            part = part.strip()
            if not part:
                continue
            if sections and part == head.strip():
                part = '\n'.join(part.splitlines()[:8])      # 첫 조각은 제목과 문서 정보 줄까지만 둡니다
            title = part.splitlines()[0].lstrip('# ').strip()
            chunks.append(Chunk(meta['doc_id'], meta['version'], meta['type'], meta['date'], title, part[:1200]))
    return chunks


def build_index(folder, manifest):
    chunks = build_chunks(folder, manifest)
    return ChunkIndex(chunks, embed.passages([chunk.text for chunk in chunks]))


def search(index, question, k=4, exclude_types=()):
    """질문과 가까운 청크를 점수가 높은 순으로 k건 찾습니다. exclude_types에 든 유형의 문서는 뺍니다."""
    allowed = [row for row, chunk in enumerate(index.chunks) if chunk.type not in exclude_types]
    scores = index.vectors[allowed] @ embed.query(question)
    return [Hit(round(float(scores[row]), 3), *index.chunks[allowed[row]])
            for row in np.argsort(-scores, kind='stable')[:k]]


def show(hits):
    for hit in hits:
        print(f'  {hit.score:.3f} {hit.doc_id}_{hit.version} ({hit.section[:22]})')


manifest = read_manifest('data/2일차/corpus_manifest.csv')
full = build_index(CORPUS, manifest)
print(f'청크 {len(full.chunks)}, 인덱스 {full.vectors.shape}')
print({**full.chunks[0]._asdict(), 'text': full.chunks[0].text[:30] + '...'})
```

질문을 검색해 봅니다. 두 번째 검색은 회의록을 제외합니다.

```python
# 예제 3-1 (검색해 봅니다)
QUESTION = '에치 장비 ESC 온도 상한이 몇 도이고, 초과하면 어떻게 조치해야 하나요?'
hits = search(full, QUESTION, k=4)
show(hits)
print('--- 회의록을 제외하고 같은 질문을 검색합니다')
show(search(full, QUESTION, k=4, exclude_types=['회의록']))
```
:::

문서 253건이 청크 757개가 됐습니다. 문서 한 건이 평균 세 개 정도의 절로 나뉩니다. 검색 결과 네 건은 절 단위입니다. 같은 문서 `SOP-ETCH-007_v2.1`의 절 세 개가 위에 올라왔습니다. 같은 문서의 여러 절이 상위에 오면 그 문서를 찾았다는 뜻입니다. 필요한 절이 모두 들어왔다는 뜻은 아닙니다(예제 3-7). 품질 이슈 보고서 `QIR-2026-0712`도 섞였습니다. 같은 설비의 사례여서 관련은 있지만 기준을 정한 문서는 아닙니다. 회의록을 제외해도 이 질문의 결과는 같았습니다. 상위 네 건에 회의록이 없었기 때문입니다.

## 검색 결과를 넣어 응답 받기 {원본 p.218-226}

:::요점
검색 결과를 문서 번호와 함께 프롬프트에 넣으면 사내 기준의 숫자가 있고 출처가 붙은 응답이 나옵니다. 검색 결과를 많이 넣는다고 응답이 나아지지 않습니다. 응답이 나아지려면 필요한 청크가 들어 있어야 합니다.
:::

2일차 파트 3의 예제 3-1에서 비슷한 질문(ESC 온도 정상 운전 범위)을 근거 없이 보내면 사내 값을 알 수 없다고 답하는 것을 확인했습니다. 이번에는 예제 3-1의 질문을 검색 결과 네 건과 함께 보냅니다. 먼저 이 질문을 근거 없이 보낸 응답을 봅니다. 질문에 "우리 공장 기준으로"를 붙였습니다.

:::예제 3-2 검색 결과를 넣어 응답 받기
```python
# 예제 3-2 (검색 결과 없이 묻습니다)
baseline = llm.ask(f'우리 공장 기준으로 답해 주세요. {QUESTION}', model='기본', max_tokens=800)
print(baseline.text[:400])
```

검색 결과 네 건의 앞에 `[문서번호_버전] (절)` 꼴의 머리글을 붙여 프롬프트에 넣고 묻습니다. 머리글은 청크가 어느 문서의 어느 절인지 알리는 한 줄입니다.

```python
# 예제 3-2 (검색 결과 4건을 넣어 묻습니다)
def format_results(hits):
    """검색 결과에 [문서번호_버전] (절) 머리글을 붙여 프롬프트에 넣을 글로 만듭니다."""
    return '\n\n'.join(f'[{hit.doc_id}_{hit.version}] ({hit.section})\n{hit.text}' for hit in hits)


def simple_prompt(hits, question):
    return ('다음 사내 문서만 근거로 답해 주세요. 근거로 쓴 문서 번호를 [ ] 안에 함께 적어 주세요.\n\n'
            f'{format_results(hits)}\n\n질문: {question}')


answer = llm.ask(simple_prompt(hits, QUESTION), model='기본', max_tokens=800)
print(answer.text)
print('입력 토큰', answer.input_tokens)
```

검색 결과의 건수 `k`를 1, 4, 12로 바꿔 응답을 비교합니다.

```python
# 예제 3-2 (k를 바꿔 봅니다)
for k in [1, 4, 12]:
    hits_k = search(full, QUESTION, k=k)
    reply = llm.ask(simple_prompt(hits_k, QUESTION), model='기본', max_tokens=800)
    found = sorted({hit.doc_id for hit in hits_k})
    print(f'k={k:<2d} 입력 {reply.input_tokens:5d}토큰, 응답 {len(reply.text):4d}자, 문서 {found}')
    print('   ', reply.text[:90].replace('\n', ' '))
```
:::

근거 없이 보낸 응답은 이 공장의 상한 온도를 알 수 없다고 답하고, 상한이 장비사와 공정, 레시피에 따라 다르다는 점과 확인할 곳을 안내했습니다. 검색 결과 네 건을 넣자 응답은 정상 운전 범위 58.0~62.0°C, 상한 62.0°C, 5분 이상 초과하면 챔버 인터락이 작동한다는 것, 초과 시 조치 절차를 `[SOP-ETCH-007_v2.1]` 출처와 함께 답했습니다. 입력은 766토큰으로, 문서 253건 전체(3일차 파트 1의 예제 1-4의 추정으로 약 68,000토큰)의 1% 남짓입니다.

`k`를 바꾼 결과는 다음과 같습니다.

- **k=1**: 입력은 347토큰입니다. 1위 청크가 초과 시 조치 절차 절이어서 상한값이 든 관리 기준 절이 빠졌고, 응답은 상한값이 제공된 문서에 없어 확인할 수 없다고 답했습니다. 정답 문서는 찾았는데 필요한 절이 검색 결과에 없었던 경우입니다.
- **k=4**: 필요한 절이 모두 들어와 응답이 상한과 조치를 답했습니다.
- **k=12**: 입력은 1,780토큰으로 k=4의 2.3배입니다. 늘어난 청크 여덟 건에는 `SOP-ETCH-007`과 `QIR-2026-0712`의 다른 절도 있고, `MAN-006`, `SOP-CVD-010` 같은 다른 문서도 섞였습니다. 응답은 k=4와 같은 값(62.0°C)을 답했습니다.

k를 1에서 4로 늘리자 필요한 절이 들어와 응답이 나아졌습니다. 4에서 12로 늘렸을 때는 입력 토큰만 2.3배가 되고 응답은 같았습니다. `k`는 필요한 청크가 들어오는 가장 작은 값으로 정합니다. 2일차에서 측정한 recall@3 같은 값을 보고 정하고, 처음에는 3~5로 시작해 실패한 사례를 보며 조정합니다.

## RAG 프롬프트의 네 요소 {원본 p.227-235}

:::요점
RAG 프롬프트는 역할 지정, 검색 결과, 출력 규칙, 근거 없음 규칙으로 이루어집니다. 근거 없음 규칙이 없으면 검색 결과에 없는 대상의 질문에 비슷한 다른 대상의 기준을 덧붙인 응답이 나올 수 있습니다.
:::

1일차에서는 프롬프트를 역할 지정, 맥락, 형식, 제약, 예시의 다섯 요소로 나눴습니다. RAG 프롬프트는 이 가운데 역할 지정, 형식, 제약을 쓰고, 처리할 재료로 검색 결과를 넣습니다. 1일차에서는 재료(회의록)를 사람이 붙여 넣었고, RAG에서는 검색이 채웁니다.

| 1일차의 요소 | RAG 프롬프트의 요소 | 이 파트의 문장 |
| --- | --- | --- |
| 역할 지정 | 역할 지정 | 너는 사내 공정기술 담당자다 |
| 요소가 아닌 재료(1일차의 회의록) | 검색 결과 | `[검색 결과]` 아래에 검색한 청크 |
| 형식 | 출력 규칙 | 문장마다 근거 `[문서번호]`를 붙인다 |
| 제약 | 근거 없음 규칙 | 검색 결과에 없으면 "사내 문서에서 근거를 찾지 못했습니다"라고만 답한다 |

[[근거 없음 규칙]]은 검색 결과에 근거가 없으면 찾지 못했다고만 답하게 하는 프롬프트의 제약입니다. 검색은 질문과 가장 가까운 청크를 항상 돌려줍니다. 그 청크에 답이 없어도 모델이 받는 것은 비슷한 내용의 청크입니다. 규칙이 없으면 그 청크의 내용을 근거로 한 응답이 나올 수 있습니다.

:::예제 3-3 근거 없음 규칙을 넣고 빼기
```python
# 예제 3-3 (RAG 프롬프트의 네 요소)
RULE = "검색 결과에 없으면 '사내 문서에서 근거를 찾지 못했습니다' 라고만 답한다."
TEMPLATE = ('너는 사내 공정기술 담당자다.\n'                    # 역할 지정
            '아래 사내 문서만 근거로 답한다.\n\n'
            '[검색 결과]\n{results}\n\n'                       # 재료: 검색이 채웁니다
            '규칙: 문장마다 근거 [문서번호]를 붙인다.\n'          # 형식
            '{rule}\n\n'                                       # 제약: 근거 없음 규칙
            '질문: {question}')


def build_prompt(hits, question, use_rule=True):
    return TEMPLATE.format(results=format_results(hits), rule=RULE if use_rule else '', question=question)


def ask(question, k=4, exclude_types=(), use_rule=True, index=None):
    """검색하고 프롬프트를 만들어 모델에 보냅니다. (응답 글, 검색 결과)를 돌려줍니다."""
    hits = search(index or full, question, k, exclude_types)
    reply = llm.ask(build_prompt(hits, question, use_rule), model='기본', max_tokens=800)
    return reply.text, hits


print(build_prompt(search(full, 'ETCH-07 호기 ESC 온도 기준은?', k=1), 'ETCH-07 호기 ESC 온도 기준은?'))
```

코퍼스에 없는 호기(ETCH-07)의 기준을 규칙이 있을 때와 없을 때 묻습니다. 문서에는 ETCH-01부터 ETCH-06까지만 있습니다.

```python
# 예제 3-3 (근거 없음 규칙을 넣고 뺍니다)
for use_rule in [True, False]:
    text, found = ask('ETCH-07 호기 ESC 온도 기준은?', use_rule=use_rule)
    print(f"근거 없음 규칙 {'있음' if use_rule else '없음'}, 검색 결과 최고 점수 {found[0].score}")
    print(text)
    print()
```
:::

위에서 출력한 프롬프트는 역할 지정, 검색 결과, 출력 규칙, 근거 없음 규칙, 질문의 순서입니다. 규칙은 검색 결과 바로 뒤, 질문 바로 앞에 있습니다. Anthropic의 프롬프트 작성 가이드는 긴 문서(20,000토큰 이상)를 다룰 때 문서를 프롬프트 앞쪽에 두고 질문과 지시는 그 뒤에 두라고 권장합니다. 이 파트의 프롬프트는 그보다 훨씬 짧고, 규칙의 위치를 바꿔 비교하지는 않았습니다(가이드는 2026-11-26 확인).

규칙을 넣었을 때 응답은 "사내 문서에서 근거를 찾지 못했습니다" 한 문장이었습니다. 규칙을 뺐을 때 응답은 ETCH-07 호기의 기준은 제공된 문서에서 확인되지 않는다고 시작했지만, 이어서 ETCH-01~06 호기의 정상 운전 범위(58.0~62.0°C)와 상한 62.0°C를 참고로 덧붙이고 `[SOP-ETCH-007_v2.1]` 출처를 붙였습니다. 응답은 이 값을 ETCH-07에 그대로 적용해도 되는지는 문서만으로 판단할 수 없다고도 썼습니다. 그래도 응답에 숫자와 출처가 붙어 있으므로, 앞부분만 읽은 현장 작업자는 ETCH-07에도 같은 기준이 적용된다고 받아들일 수 있습니다. 두 응답은 한 번씩 실행한 결과이고, 규칙이 없을 때 다른 호기의 기준을 덧붙이는지는 실행마다 다를 수 있습니다.

이 질문의 검색 결과 최고 점수는 0.912로, 앞의 정상 질문(0.890)보다 높습니다. 코퍼스에 없는 호기를 물어도 검색은 ETCH-01~06의 문서를 높은 점수로 찾습니다. 점수로는 답이 있는 질문인지 알 수 없고, 답이 없는 질문을 막는 것은 근거 없음 규칙입니다.

## 출처 표기 {원본 p.236-237}

:::요점
출처가 안정적으로 붙게 하려면 검색 결과의 청크마다 문서 번호를 앞에 붙이고, 출력 규칙에서도 문장마다 그 번호를 붙이라고 요구합니다. 이 예제에서는 한쪽만 했을 때 대괄호 출처가 붙지 않거나(청크 표시만), 붙어도 인용한 번호가 모두 한 문서의 번호였습니다(규칙만).
:::

[[출처 표기]]가 없는 응답은 사람이 원문과 대조할 수 없어서 쓰기 어렵습니다. 최소한 문서 번호가 있어야 하고, 개정본이 있는 문서에는 버전도 필요합니다. 버전이 없으면 구판과 개정판 가운데 어느 쪽을 인용했는지 알 수 없습니다.

출처를 붙이게 하는 방법이 두 가지 있습니다. 청크마다 문서 번호를 앞에 붙여 프롬프트에 넣는 방법과, 출력 규칙으로 요구하는 방법입니다. 청크에 문서 번호가 없으면 모델이 번호를 알 수 있는 곳은 본문에 적힌 번호뿐이고, 규칙이 없으면 모델이 번호를 알아도 응답에 적지 않을 수 있습니다. 세 가지 조합을 각각 세 번씩 보내, 대괄호로 표기한 출처의 개수를 세고 인용한 문서 번호를 모읍니다.

:::예제 3-4 출처를 붙이게 하는 두 가지
```python
# 예제 3-4
def plain_results(hits):
    return '\n\n'.join(hit.text for hit in hits)           # 문서 번호 없이 본문만 붙입니다


variants = {
    '규칙만': (plain_results, '규칙: 문장마다 근거 문서 번호를 [ ] 안에 붙인다.'),
    '청크 표시만': (format_results, ''),
    '둘 다': (format_results, '규칙: 문장마다 근거 [문서번호]를 붙인다.'),
}
for label, (formatter, rule) in variants.items():
    prompt = f'아래 사내 문서만 근거로 답한다.\n\n{formatter(hits)}\n\n{rule}\n\n질문: {QUESTION}'
    counts, cited = [], set()
    for _ in range(3):
        text = llm.ask(prompt, model='기본', max_tokens=800).text
        ids = re.findall(r'\[([A-Z]+-[^\]]+)\]', text)
        counts.append(len(ids))
        cited |= set(ids)
    print(f'{label:8s} 출처 표기 개수 (3회): {counts}, 인용한 문서 번호 {sorted(cited)}')
```
:::

**규칙만** 줬을 때는 출처 표기가 세 번 모두 5~7개 붙었지만, 인용한 문서 번호는 `SOP-ETCH-007` 하나뿐이었습니다. 청크에 문서 번호가 없고 첫머리 청크의 제목 줄에만 번호가 있어서, 모델은 그 번호를 출처로 썼습니다. 검색 결과에는 `QIR-2026-0712`의 청크도 있었지만 한 번도 인용되지 않았습니다. 출처가 붙었어도 어느 문서에서 온 내용인지 정확하다고 볼 수 없습니다.

**청크 표시만** 했을 때는 세 번 모두 대괄호로 표기한 출처가 하나도 없었습니다(대괄호 밖에서 번호를 언급했는지는 세지 않았습니다). 이 예제에서는 요구가 없을 때 대괄호 출처를 붙이지 않았습니다.

**둘 다** 했을 때는 출처 표기가 6~7개 붙었고, 인용한 문서가 `SOP-ETCH-007_v2.1`과 `QIR-2026-0712_v1.0` 두 개로, 버전까지 정확히 표기됐습니다.

출처에는 세 수준이 있습니다. 문서 번호만 적는 것이 최소한이고, 개정본이 있는 문서에는 문서 번호와 버전(`SOP-ETCH-012_v2.0`)을 적어야 합니다. 원문의 해당 절로 이동하는 링크까지 달면 확인이 가장 쉽습니다.

## RAG가 오류 없이 틀리는 세 경우 {원본 p.238-273}

:::요점
RAG는 오류 없이 그럴듯하게 틀립니다. 틀리는 경우는 관련 없는 문서가 상위를 채움, 버전 충돌, 절이 문서의 맥락을 잃음의 세 가지입니다. 모두 검색 결과에서 원인이 드러나므로 응답이 이상하면 검색 결과부터 확인합니다.
:::

RAG는 틀려도 오류가 나지 않습니다. 2일차 파트 1의 [[조용한 실패]]에 해당합니다. 응답은 그럴듯하게 나오고 출처까지 붙을 수 있습니다. 틀린 응답을 고치려면 원인이 검색에 있는지 생성에 있는지부터 판단해야 합니다. 먼저 검색 결과가 질문에 맞는지 봅니다. 여기서 "맞다"는 필요한 청크가 있고, 관련 없는 청크와 구판이 없다는 뜻입니다. 검색 결과가 맞는데 응답이 틀렸으면 프롬프트(생성)를 고칩니다. 검색 결과가 맞지 않으면 프롬프트를 고쳐도 근거가 늘지 않으므로 검색이나 인덱싱을 고칩니다. 코퍼스에 답이 없는 질문은 검색을 고쳐도 답할 수 없습니다. 이때는 근거 없음 규칙으로 찾지 못했다고 답하게 합니다. 아래 그림은 이 판단과 세 경우를 한 장에 정리한 것입니다.

<figure>
<svg viewBox="0 0 680 330" role="img" aria-label="응답이 이상할 때의 판단. 검색 결과가 질문에 맞는 청크로만 이루어졌으면 생성의 문제이므로 프롬프트를 고친다. 그렇지 않으면 검색과 인덱싱의 문제이고, 관련 없는 문서가 상위를 채우는 경우, 버전 충돌, 절이 문서의 맥락을 잃는 경우의 세 가지가 있으며 각각 질문 구체화와 유형 제한, 구판 제외와 버전 표기, 제목을 붙여 임베딩으로 고친다. 코퍼스에 답이 없는 질문은 검색 결과가 맞지 않아도 검색을 고쳐서는 답할 수 없으므로, 근거 없음 규칙으로 찾지 못했다고 답하게 한다.">
<rect x="240" y="8" width="200" height="40" rx="8" fill="var(--sheet)" stroke="var(--line)"/>
<text x="340" y="33" text-anchor="middle" fill="var(--ink)" font-size="14" font-weight="700">응답이 이상하다</text>
<line x1="340" y1="48" x2="340" y2="62" stroke="var(--ink-soft)" stroke-width="2"/>
<polygon points="340,70 335,60 345,60" fill="var(--ink-soft)"/>
<rect x="210" y="70" width="260" height="44" rx="8" fill="var(--sheet)" stroke="var(--line)"/>
<text x="340" y="97" text-anchor="middle" fill="var(--ink)" font-size="14" font-weight="700">검색 결과가 질문에 맞는가?</text>
<line x1="260" y1="114" x2="120" y2="164" stroke="var(--amber)" stroke-width="2"/>
<polygon points="114,166 120,156 126,166" fill="var(--amber)"/>
<text x="168" y="134" text-anchor="middle" fill="var(--ink-soft)" font-size="12">맞다</text>
<rect x="10" y="168" width="185" height="112" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/>
<text x="102" y="196" text-anchor="middle" fill="var(--ink)" font-size="14" font-weight="700">생성의 문제</text>
<text x="102" y="220" text-anchor="middle" fill="var(--ink)" font-size="12">프롬프트를 고칩니다</text>
<text x="102" y="240" text-anchor="middle" fill="var(--ink-soft)" font-size="12">출력 규칙, 근거 없음 규칙</text>
<line x1="420" y1="114" x2="420" y2="146" stroke="var(--teal)" stroke-width="2"/>
<text x="470" y="134" text-anchor="middle" fill="var(--ink-soft)" font-size="12">맞지 않다</text>
<text x="440" y="160" text-anchor="start" fill="var(--ink-soft)" font-size="12">검색과 인덱싱의 문제: 세 가지</text>
<line x1="280" y1="170" x2="600" y2="170" stroke="var(--teal)" stroke-width="2"/>
<line x1="420" y1="146" x2="420" y2="170" stroke="var(--teal)" stroke-width="2"/>
<line x1="280" y1="170" x2="280" y2="180" stroke="var(--teal)" stroke-width="2"/>
<polygon points="280,184 275,176 285,176" fill="var(--teal)"/>
<rect x="205" y="184" width="150" height="96" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="280" y="206" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">관련 없는 문서가</text>
<text x="280" y="224" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">상위를 채움</text>
<text x="280" y="248" text-anchor="middle" fill="var(--ink-soft)" font-size="12">대책: 질문 구체화,</text>
<text x="280" y="266" text-anchor="middle" fill="var(--ink-soft)" font-size="12">유형 제한</text>
<line x1="440" y1="170" x2="440" y2="180" stroke="var(--teal)" stroke-width="2"/>
<polygon points="440,184 435,176 445,176" fill="var(--teal)"/>
<rect x="365" y="184" width="150" height="96" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="440" y="206" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">버전 충돌</text>
<text x="440" y="248" text-anchor="middle" fill="var(--ink-soft)" font-size="12">대책: 구판 제외,</text>
<text x="440" y="266" text-anchor="middle" fill="var(--ink-soft)" font-size="12">버전 표기</text>
<line x1="600" y1="170" x2="600" y2="180" stroke="var(--teal)" stroke-width="2"/>
<polygon points="600,184 595,176 605,176" fill="var(--teal)"/>
<rect x="525" y="184" width="150" height="96" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="600" y="206" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">절이 문서의</text>
<text x="600" y="224" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">맥락을 잃음</text>
<text x="600" y="248" text-anchor="middle" fill="var(--ink-soft)" font-size="12">대책: 제목을 붙여</text>
<text x="600" y="266" text-anchor="middle" fill="var(--ink-soft)" font-size="12">임베딩</text>
<rect x="205" y="292" width="470" height="30" rx="8" fill="var(--sheet)" stroke="var(--teal)" stroke-dasharray="5 4"/>
<text x="440" y="312" text-anchor="middle" fill="var(--ink)" font-size="12">코퍼스에 답이 없으면 검색을 고쳐도 답할 수 없음: 근거 없음 규칙으로 처리</text>
</svg>
<figcaption>응답이 이상하면 먼저 검색 결과가 질문에 맞는지 봅니다. 검색 결과가 맞으면 주황색 상자의 생성 문제입니다. 검색 결과가 맞지 않으면 청록색 상자의 세 가지 가운데 하나입니다. 코퍼스에 답이 없는 질문은 검색을 고쳐도 답할 수 없으므로, 청록색 점선 상자처럼 근거 없음 규칙으로 찾지 못했다고 답하게 합니다. 하이브리드 검색과 리랭킹으로 검색을 개선하는 방법은 4일차에서 다룹니다.</figcaption>
</figure>

세 경우를 직접 만들어 봅니다. 예제 3-5와 3-6의 앞부분은 `full` 인덱스(청크 757개)를 쓰고, 예제 3-6의 끝에서 구판을 뺀 `current` 인덱스(청크 754개)를 만들어 예제 3-7에서 씁니다.

### 관련 없는 문서가 상위를 채움

질문이 넓으면 질문에 특히 가까운 청크가 없어서, 상위 청크의 점수가 서로 비슷해질 수 있습니다. 이 코퍼스에서는 회의록의 "논의 사항" 절 여러 건이 비슷한 점수로 상위를 채웠습니다. 회의록이 올라온 이유는 확인하지 않았습니다. 질문을 구체화하거나 문서 유형을 제한해 봅니다.

:::예제 3-5 질문이 넓을 때
```python
# 예제 3-5
from collections import Counter

QUESTION_WIDE = '최근 에치 장비들에서 있었던 센서 관련 품질 이슈를 정리해 주세요.'
QUESTION_NARROW = 'ETCH-03 호기 파티클 급증의 원인과 조치를 알려주세요'

for label, question, k, exclude in [('넓은 질문', QUESTION_WIDE, 6, ()),
                                    ('구체적인 질문', QUESTION_NARROW, 4, ()),
                                    ('넓은 질문, 회의록 제외', QUESTION_WIDE, 6, ('회의록',))]:
    text, found = ask(question, k=k, exclude_types=exclude)
    print(f'=== {label}, 최고 점수 {found[0].score}, 1위와 {k}위의 점수 차 {found[0].score - found[-1].score:.3f}, '
          f'유형 {dict(Counter(hit.type for hit in found))}')
    show(found)
    print('응답:', text[:200].replace('\n', ' '))

scores = full.vectors @ embed.query(QUESTION_NARROW)
order = list(np.argsort(-scores, kind='stable'))
cause_row = next(row for row, chunk in enumerate(full.chunks)
                 if chunk.doc_id == 'QIR-2026-0800' and chunk.section == '원인 분석')
print('구체적인 질문에서 원인이 적힌 절(QIR-2026-0800 원인 분석)의 순위:', order.index(cause_row) + 1)
```
:::

넓은 질문은 검색 결과 여섯 건이 모두 회의록이고, 점수가 0.868에서 0.863으로 서로 가까웠습니다(1위와 6위의 점수 차 0.005). 질문에 특히 가까운 청크가 없었습니다. 응답은 근거를 찾지 못했다고 답했습니다. 회의록을 제외하면 품질 이슈 보고서와 공정 스펙이 올라오지만 점수가 0.857에서 0.855로 더 가까워지고(점수 차 0.002), 응답은 그대로 근거를 찾지 못했다고 답했습니다. 문서 유형을 제한하면 후보는 줄지만, 넓은 질문에 뚜렷하게 가까운 청크가 생기지는 않습니다.

호기와 현상을 쓴 구체적인 질문은 품질 이슈 보고서 네 건이 올라오고 최고 점수가 0.922로 높아졌습니다. 1위와 4위의 점수 차는 0.022로, 넓은 질문의 1위와 4위의 점수 차(약 0.003)보다 큽니다. 그런데 응답은 조치(영향 로트 전량 홀드)는 답했지만 원인은 근거를 찾지 못했다고 답했습니다. 원인이 적힌 `QIR-2026-0800`의 "원인 분석" 절이 이 질문에서 270위였기 때문입니다. 질문을 구체화하면 문서는 찾지만, 그 문서의 어느 절이 상위에 오는지는 절의 내용이 질문과 얼마나 가까운지에 달려 있습니다. 이것이 세 번째 경우이고, 제목을 붙이면 이 절의 순위가 어떻게 되는지는 예제 3-7에서 확인합니다.

### 버전 충돌

[[버전 충돌]]은 같은 문서의 구판과 개정판이 모두 검색 대상이어서 구판의 값이 응답에 섞이는 것입니다. 구판(v1.2)과 개정판(v2.0)이 인덱스에 모두 있으면 검색은 둘을 구분하지 못합니다. 두 판은 숫자 몇 개만 다른 같은 글이어서 벡터가 거의 같습니다. 다음 코드는 두 판의 같은 절을 비교하고, 검색 결과의 표기와 프롬프트의 규칙, 인덱스 구성을 바꿔 가며 응답에 어느 값이 나오는지 셉니다.

:::예제 3-6 구판과 개정판이 함께 있을 때
```python
# 예제 3-6 (두 판은 얼마나 닮았나)
import difflib

QUESTION_HE = '에치 웨이퍼 클램핑 시 He 배면압 기준은?'
show(search(full, QUESTION_HE))

pair = {chunk.version: chunk for chunk in full.chunks if chunk.doc_id == 'SOP-ETCH-012' and chunk.section == '설정 기준'}
old_text, new_text = pair['v1.2'].text, pair['v2.0'].text
common = sum(block.size for block in difflib.SequenceMatcher(None, old_text, new_text).get_matching_blocks())
vector_old, vector_new = embed.passages([old_text, new_text])
print(f'공통 {common}자, v1.2 {len(old_text)}자, v2.0 {len(new_text)}자, 두 절 사이 유사도 {float(vector_old @ vector_new):.3f}')
print(old_text)
print(new_text)
```

검색 결과는 같게 두고 프롬프트만 바꿔, 응답의 첫 문단에 나오는 값을 셉니다. 각각 세 번씩 보냅니다. 개정판의 값은 8.0 Torr이고 구판의 값은 6.0 Torr입니다. 응답이 구판을 이전 버전으로 언급하더라도, 첫 문단에서 현행 값으로 내세운 것이 무엇인지를 봅니다. 응답이 굵은 제목 한 줄로 시작하면 첫 문단에 값이 없을 수 있으므로, 첫 문단의 앞 60자도 함께 출력해 무엇이 적혀 있었는지 확인합니다.

```python
# 예제 3-6 (프롬프트를 바꿔 봅니다)
def first_paragraph_values(text):
    """응답의 첫 문단에 나온 값을 돌려줍니다. 응답이 현행 값으로 내세운 것이 무엇인지 봅니다."""
    first = text.strip().split('\n\n')[0]
    return '/'.join(value for value in ['8.0', '6.0'] if value in first) or '값 없음'


def run_three(label, prompt):
    """같은 프롬프트를 세 번 보내 첫 문단의 값을 출력합니다. 첫 문단의 앞 60자도 함께 출력합니다."""
    texts = [llm.ask(prompt, model='기본', max_tokens=500).text for _ in range(3)]
    print(f'{label:24s} 응답의 첫 문단에 나온 값(3회): {[first_paragraph_values(text) for text in texts]}')
    for text in texts:
        print('    첫 문단:', text.strip().split('\n\n')[0][:60].replace('\n', ' '))


hits_he = search(full, QUESTION_HE)
without_version = '\n\n'.join(f'[{hit.doc_id}] ({hit.section})\n{hit.text}' for hit in hits_he)   # 버전을 뺀 문서 번호
rule_latest = RULE + ' 같은 문서의 여러 판이 있으면 버전이 높은 것을 따른다.'
prompts = {
    'A 버전 표기 있음': TEMPLATE.format(results=format_results(hits_he), rule=RULE, question=QUESTION_HE),
    'B 버전 표기 없음': TEMPLATE.format(results=without_version, rule=RULE, question=QUESTION_HE),
    'C 버전 표기 있음, 최신 버전 규칙': TEMPLATE.format(results=format_results(hits_he), rule=rule_latest, question=QUESTION_HE),
}
for label, prompt in prompts.items():
    run_three(label, prompt)
```

구판을 인덱스에서 빼는 방법도 확인합니다. 같은 문서 번호의 청크 가운데 버전이 가장 높은 것만 남깁니다.

```python
# 예제 3-6 (구판을 인덱스에서 뺍니다)
def version_key(chunk):
    return tuple(int(number) for number in chunk.version.lstrip('v').split('.'))


def latest_version_rows(chunks):
    """같은 문서 번호의 청크 가운데 버전이 가장 높은 것의 행 번호를 돌려줍니다."""
    latest = {}
    for chunk in chunks:
        latest[chunk.doc_id] = max(latest.get(chunk.doc_id, (0,)), version_key(chunk))
    return [row for row, chunk in enumerate(chunks) if version_key(chunk) == latest[chunk.doc_id]]


rows = latest_version_rows(full.chunks)
current = ChunkIndex([full.chunks[row] for row in rows], full.vectors[rows])
print('청크', len(full.chunks), '→', len(current.chunks))
show(search(current, QUESTION_HE))
prompt_current = build_prompt(search(current, QUESTION_HE), QUESTION_HE)
run_three('D 구판 제외', prompt_current)
```
:::

검색 결과 네 건에서 `SOP-ETCH-012`의 v2.0과 v1.2는 "설정 기준" 절이 둘 다 0.926, 첫머리 절이 둘 다 0.868로 같은 점수입니다. 두 절은 95자 가운데 93자가 같고, 다른 것은 6.0과 8.0, ±0.5와 ±0.4의 숫자뿐입니다. 임베딩의 유사도가 0.999여서 검색은 두 판을 같은 글로 취급하고, 어느 판이 현행인지 구분하지 못합니다.

프롬프트를 바꾼 결과는 다음과 같습니다. 각각 세 번씩 보냈습니다.

- **A 버전 표기 있음**: 첫 문단에 세 번 모두 8.0만 있었습니다.
- **B 버전 표기 없음**: 세 번 모두 첫 문단에 값이 없었습니다. 출력의 "첫 문단" 줄을 보면 세 번 모두 He 배면압 값이 두 가지로 나와 있어 하나로 확정할 수 없다는 내용입니다. 제목 줄 때문에 값이 빠진 것이 아니라, 모델이 두 값 가운데 하나를 고르지 않았습니다.
- **C 버전 표기 있음, 최신 버전 규칙**: 세 번 모두 8.0이었습니다. A도 세 번 모두 8.0이어서 규칙 문장의 효과는 이 비교로 판단할 수 없습니다.
- **D 구판 제외**: 세 번 모두 8.0 Torr였습니다.

검색이 구판과 개정판을 구분하지 못해도, 프롬프트에 넣는 청크에 버전을 표시하면 첫 문단에 개정판의 값만 나왔고, 표시를 빼면 모델이 두 값 가운데 하나를 고르지 못했습니다. 이 표시는 인덱싱에서 붙인 메타데이터를 프롬프트로 옮긴 것입니다. 다만 개정판의 제목에도 "(개정판)"이라는 말이 있어서, 버전 표기만의 효과라고 단정하지는 않습니다. 구판이 검색 결과 네 건 가운데 두 건을 차지해 같은 절을 중복해서 보여 주므로, 구판은 인덱스에서 빼는 것이 가장 확실합니다. 구판을 빼자 청크가 757개에서 754개로 줄고, 검색 결과에서 `SOP-ETCH-012`가 v2.0만 남았습니다. 구판을 빼는 일은 문서를 관리하는 담당자와 합의해야 합니다.

### 절이 문서의 맥락을 잃음

청크 하나만 놓고 보면 어느 문서의 절인지 알 수 없습니다. "시정 조치" 절에는 원인과 조치가 적혀 있지만 어느 설비의 어느 사건인지는 문서 제목에 있습니다. 제목이 없는 청크의 벡터에는 설비와 사건이 반영되지 않아서, 그 설비와 사건을 묻는 질문과의 유사도가 낮아지고 검색 결과에 들어오지 못합니다. 청크 앞에 문서 제목을 붙여 임베딩하면 해결됩니다.

:::예제 3-7 문서 제목을 붙여 임베딩하기
```python
# 예제 3-7
QUESTION_CAUSE = 'ETCH-04 호기 ESC 온도 드리프트 원인과 재발 방지 조치는?'
text, found = ask(QUESTION_CAUSE, index=current)
show(found)
print('응답:', text[:300].replace('\n', ' '))


def rank_of_section(index, question, doc_id, section):
    """문서 번호와 절 제목으로 청크를 찾아 (순위, 점수)를 돌려줍니다."""
    scores = index.vectors @ embed.query(question)
    for rank, row in enumerate(np.argsort(-scores, kind='stable'), 1):
        chunk = index.chunks[row]
        if chunk.doc_id == doc_id and chunk.section == section:
            return rank, round(float(scores[row]), 3)


print('제목을 붙이기 전, 시정 조치 절의 순위:', rank_of_section(current, QUESTION_CAUSE, 'QIR-2026-0712', '시정 조치'))
```

문서 제목을 청크 앞에 붙여 다시 임베딩합니다. 청크의 본문은 그대로 두고 임베딩할 글에만 제목을 더합니다.

```python
# 예제 3-7 (제목을 붙여 임베딩합니다)
def with_titles(index):
    """청크 앞에 문서 제목을 붙여 다시 임베딩한 인덱스를 돌려줍니다. 청크의 본문은 그대로입니다."""
    title_of = {}
    for chunk in index.chunks:
        title_of.setdefault((chunk.doc_id, chunk.version), chunk.section)      # 문서의 첫 청크의 제목이 문서 제목입니다
    return ChunkIndex(index.chunks, embed.passages(
        [f'{title_of[chunk.doc_id, chunk.version]} · {chunk.section}\n{chunk.text}' for chunk in index.chunks]))


titled = with_titles(current)
print('제목을 붙인 뒤, 시정 조치 절의 순위:', rank_of_section(titled, QUESTION_CAUSE, 'QIR-2026-0712', '시정 조치'))

QUESTION_PARTICLE = 'ETCH-03 호기 파티클 급증의 원인과 조치를 알려주세요'      # 예제 3-5의 구체적인 질문
for label, index in [('제목 없음', current), ('제목 붙임', titled)]:
    rank, score = rank_of_section(index, QUESTION_PARTICLE, 'QIR-2026-0800', '원인 분석')
    print(f'{label}, QIR-2026-0800 원인 분석 절 {rank}위 ({score})')

text, found = ask(QUESTION_CAUSE, index=titled)
show(found)
print('응답:', text[:300].replace('\n', ' '))

QUESTION_SEASONING = '시즈닝 런은 더미 웨이퍼 몇 장으로 하나요?'
for label, index in [('제목 없음', current), ('제목 붙임', titled)]:
    print(label, [(hit.doc_id, hit.type) for hit in search(index, QUESTION_SEASONING)])
```
:::

제목을 붙이기 전에 원인과 재발 방지 조치가 적힌 `QIR-2026-0712`의 "시정 조치" 절은 청크 754개 가운데 292위(0.823)여서 검색 결과 네 건에 들어오지 못했습니다. 응답은 현상만 답하고 원인은 근거를 찾지 못했다고 했습니다. 제목을 붙여 임베딩하자 이 절이 4위(0.873)로 올라와 검색 결과에 들어왔고, 응답이 원인(칠러 배관의 부분 폐색)과 재발 방지 조치(일 단위 온도 추이 감시를 `SOP-ETCH-007`에 반영)를 출처와 함께 답했습니다. 프롬프트 템플릿은 바꾸지 않았고, 임베딩할 글에 제목을 더한 것이 전부입니다.

<figure>
<svg viewBox="0 0 680 262" role="img" aria-label="문서 제목을 붙이기 전과 후의 검색 결과 상위 4건. 제목이 없을 때는 원인과 조치가 적힌 QIR-2026-0712의 시정 조치 절이 청크 754개 가운데 292위(0.823)로 상위 4건에 들어오지 못한다. 제목을 붙여 임베딩하면 같은 절이 4위(0.873)로 올라와 상위 4건에 들어온다.">
<text x="10" y="20" text-anchor="start" fill="var(--ink)" font-size="14" font-weight="700">제목을 붙이기 전</text>
<text x="355" y="20" text-anchor="start" fill="var(--ink)" font-size="14" font-weight="700">제목을 붙인 뒤</text>
<rect x="10" y="32" width="315" height="28" rx="6" fill="var(--sheet)" stroke="var(--line)"/>
<text x="22" y="51" text-anchor="start" fill="var(--ink)" font-size="12">1위 0.900  SOP-ETCH-007 (배경)</text>
<rect x="10" y="66" width="315" height="28" rx="6" fill="var(--sheet)" stroke="var(--line)"/>
<text x="22" y="85" text-anchor="start" fill="var(--ink)" font-size="12">2위 0.894  QIR-2026-0712 (보고 첫머리)</text>
<rect x="10" y="100" width="315" height="28" rx="6" fill="var(--sheet)" stroke="var(--line)"/>
<text x="22" y="119" text-anchor="start" fill="var(--ink)" font-size="12">3위 0.869  SOP-ETCH-007 (초과 시 조치 절차)</text>
<rect x="10" y="134" width="315" height="28" rx="6" fill="var(--sheet)" stroke="var(--line)"/>
<text x="22" y="153" text-anchor="start" fill="var(--ink)" font-size="12">4위 0.867  QIR-2025-0173 (현상)</text>
<rect x="355" y="32" width="315" height="28" rx="6" fill="var(--sheet)" stroke="var(--line)"/>
<text x="367" y="51" text-anchor="start" fill="var(--ink)" font-size="12">1위 0.899  SOP-ETCH-007 (배경)</text>
<rect x="355" y="66" width="315" height="28" rx="6" fill="var(--sheet)" stroke="var(--line)"/>
<text x="367" y="85" text-anchor="start" fill="var(--ink)" font-size="12">2위 0.892  QIR-2026-0712 (보고 첫머리)</text>
<rect x="355" y="100" width="315" height="28" rx="6" fill="var(--sheet)" stroke="var(--line)"/>
<text x="367" y="119" text-anchor="start" fill="var(--ink)" font-size="12">3위 0.892  QIR-2026-0712 (현상)</text>
<rect x="355" y="134" width="315" height="28" rx="6" fill="var(--amber-wash)" stroke="var(--amber)"/>
<text x="367" y="153" text-anchor="start" fill="var(--ink)" font-size="12" font-weight="700">4위 0.873  QIR-2026-0712 (시정 조치)</text>
<line x1="10" y1="176" x2="325" y2="176" stroke="var(--ink-soft)" stroke-width="1" stroke-dasharray="5 4"/>
<text x="10" y="194" text-anchor="start" fill="var(--ink-soft)" font-size="12">프롬프트에 넣는 검색 결과는 여기까지(상위 4건)</text>
<text x="10" y="212" text-anchor="start" fill="var(--ink-soft)" font-size="12">5위부터 291위까지 청크 287개</text>
<rect x="10" y="224" width="315" height="28" rx="6" fill="var(--amber-wash)" stroke="var(--amber)"/>
<text x="22" y="243" text-anchor="start" fill="var(--ink)" font-size="12" font-weight="700">292위 0.823  QIR-2026-0712 (시정 조치)</text>
<text x="355" y="194" text-anchor="start" fill="var(--ink-soft)" font-size="12">시정 조치 절이 상위 4건에 들어와</text>
<text x="355" y="212" text-anchor="start" fill="var(--ink-soft)" font-size="12">응답이 원인과 재발 방지 조치를 답했습니다</text>
</svg>
<figcaption>왼쪽은 청크에 문서 제목을 붙이지 않았을 때, 오른쪽은 붙여서 임베딩했을 때의 검색 결과 상위 4건입니다. 주황색 상자가 원인과 재발 방지 조치가 적힌 QIR-2026-0712의 시정 조치 절입니다. 제목이 없을 때는 청크 754개 가운데 292위였고, 제목을 붙이자 4위가 되어 프롬프트에 들어갔습니다. 문서 번호의 버전은 생략했습니다.</figcaption>
</figure>

"시정 조치" 절에는 어느 설비의 어느 사건인지가 없습니다. 그 정보는 문서 제목에 있고, 제목이 없는 청크는 "ETCH-04 호기 ESC 온도 드리프트"를 묻는 질문과 멀어집니다.

같은 방법을 예제 3-5의 구체적인 질문에 적용하면 `QIR-2026-0800`의 "원인 분석" 절이 269위(0.828)에서 8위(0.889)로 오릅니다(인덱스가 구판을 뺀 754청크여서 예제 3-5의 270위와 한 칸 다릅니다). 순위는 크게 올랐지만 상위 4건에는 들어오지 못했습니다. 제목을 붙여도 필요한 절이 검색 결과에 들어오지 않을 수 있고, 그때는 `k`를 늘려야 합니다.

제목의 효과는 원인 절 한 곳에서만 나타나지 않았습니다. "시즈닝 런은 더미 웨이퍼 몇 장으로 하나요?"의 상위 4건은 제목이 없을 때 모두 회의록이었고, 제목을 붙이자 SOP 세 건(`SOP-포토-018`, `SOP-ETCH-005`, `SOP-CVD-011`)과 회의록 한 건이 되었습니다. 시즈닝 런의 더미 웨이퍼 수는 SOP에 적혀 있습니다(예제 3-8의 응답에서 확인합니다). 제목을 붙이자 회의록 대신 SOP가 올라와 검색 결과가 좋아졌습니다. 제목을 붙이면 청크 수는 그대로이고 임베딩할 글만 길어집니다.

세 경우를 정리하면 다음과 같습니다.

| 실패 | 증상 | 원인 | 대책 |
| --- | --- | --- | --- |
| 관련 없는 문서가 상위를 채움 | 한 유형의 문서가 검색 결과를 채우고 근거를 찾지 못했다는 응답이 나옴 | 질문이 넓어 어느 문서에도 가깝지 않음 | 질문을 호기와 현상으로 구체화(문서는 찾지만 필요한 절이 들어온다는 보장은 없음), 메타데이터로 문서 유형 제한(후보는 줄지만 질문에 가까운 청크가 생기지는 않음) |
| 버전 충돌 | 응답에 값이 둘이거나 옛 값이 나옴 | 구판과 개정판이 모두 인덱스에 있고 점수가 같음 | 구판을 인덱스에서 뺌, 청크에 버전 표기 |
| 절이 문서의 맥락을 잃음 | 응답이 질문의 일부(현상)만 답하고 나머지(원인)는 근거를 찾지 못했다고 함 | 청크에 문서 제목이 없어 질문과 멀어짐 | 문서 제목을 붙여 임베딩 |

세 경우에서 응답이 이상할 때의 확인 순서는 같습니다. 먼저 검색 결과가 질문에 맞는지 봅니다. 검색 결과가 맞지 않으면 청킹과 메타데이터, 인덱스 구성을 고칩니다. 검색 결과가 맞는데 응답이 틀렸을 때만 프롬프트를 고칩니다. 하이브리드 검색과 리랭킹으로 검색 결과를 개선하는 방법은 4일차에서 다룹니다.

## 답을 믿어도 되는지 확인하기 {원본 p.274-288}

:::요점
진단 함수로 질문마다 검색 점수, 점수 차, 문서 유형, 같은 문서의 여러 판, 출처, 근거 없음 응답 여부를 한 줄에 정리합니다. 점수만으로는 답이 있는 질문과 없는 질문을 구분할 수 없으므로 이 항목들을 함께 봅니다.
:::

응답이 이상할 때마다 검색 결과를 눈으로 보는 일을 함수 하나로 묶습니다. `diagnose()`는 질문 하나를 RAG로 처리하고 (검색과 응답의 상태를 적은 딕셔너리, 응답 글)을 돌려줍니다. 구판을 뺀 `current` 인덱스에 제목을 붙인 `titled` 인덱스로 검색하므로, 앞의 예제와 점수가 조금 다릅니다. 예를 들어 없는 호기 질문의 최고 점수는 예제 3-3에서 0.912, 예제 3-8에서 0.914입니다.

- **최고 점수**와 **1위와 4위의 점수 차**: 점수가 서로 가까우면 질문에 특히 가까운 청크가 없다는 신호일 수 있습니다. 이 값만으로 판단하지는 않습니다(아래 결과를 읽는 방법).
- **유형**: 검색 결과가 한 유형으로 채워졌는지 봅니다.
- **여러 판**: 같은 문서의 여러 판이 검색 결과에 함께 들어왔는지 봅니다.
- **출처 표기**: 응답에 붙은 서로 다른 문서 번호의 개수입니다. 같은 번호를 여러 번 써도 하나로 셉니다.
- **검색 결과에 없는 인용**: 응답이 인용한 문서 번호 가운데 검색 결과에 없는 것의 개수입니다. 0이 아니면 지어낸 출처이거나 번호의 표기가 어긋난 것이므로 응답을 열어 확인합니다.
- **근거 없음**: 응답이 근거 없음 규칙의 문구를 썼는지 봅니다.

:::예제 3-8 진단 함수와 질문 여섯 개의 테스트
```python
# 예제 3-8
NO_EVIDENCE = '근거를 찾지 못했습니다'


def diagnose(question, k=4, index=None):
    """질문 하나를 RAG로 처리하고 (검색과 응답의 상태를 적은 딕셔너리, 응답 글)을 돌려줍니다."""
    text, found = ask(question, k, index=index or titled)
    shown = {f'{hit.doc_id}_{hit.version}' for hit in found} | {hit.doc_id for hit in found}
    cited = set(re.findall(r'\[([A-Z]+-[^\]\s]+)\]', text))
    versions = {(hit.doc_id, hit.version) for hit in found}
    row = {'질문': question[:20],
           '최고 점수': found[0].score,
           '1위-4위 차': round(found[0].score - found[min(3, len(found) - 1)].score, 3),
           '유형': '/'.join(hit.type for hit in found),
           '여러 판': '있음' if len(versions) > len({hit.doc_id for hit in found}) else '없음',
           '출처 표기': len(cited),
           '검색 결과에 없는 인용': len(cited - shown),
           '근거 없음': '예' if NO_EVIDENCE in text else '아니오'}
    return row, text


tests = pd.read_csv(f'{DATA}/진단_질문_6.csv', encoding='utf-8-sig')
rows, answers = [], []
for kind, question, k in zip(tests['종류'], tests['질문'], tests['k']):
    row, text = diagnose(question, k)
    rows.append({'종류': kind, **row})
    answers.append(text)

pd.set_option('display.width', 250)
pd.set_option('display.max_colwidth', 40)
print(pd.DataFrame(rows).drop(columns='질문').to_string(index=False))
for kind, text in zip(tests['종류'], answers):
    print(f'[{kind}]', text[:100].replace('\n', ' '))
```
:::

여섯 질문의 결과를 읽는 방법입니다.

- **점수만으로는 구분할 수 없습니다.** 코퍼스에 없는 호기의 질문(0.914)이 답이 있는 정상 질문(0.901, 0.840)보다 최고 점수가 높습니다.
- **근거 없음이 "예"인 세 건**은 넓은 질문, 없는 호기, 문서 밖의 질문입니다. 모델이 근거 없음 규칙으로 답을 거절한 질문들입니다. 이 세 건은 출처 표기가 0개입니다.
- **점수 차와 유형은 참고 신호입니다.** 넓은 질문(점수 차 0.008)과 문서 밖의 질문(0.002)은 점수 차가 매우 작고, 검색 결과가 품질이슈와 회의록 두 유형, 또는 공지 한 유형으로만 채워졌습니다. 그런데 없는 호기의 질문은 점수 차가 0.027로 정상 질문(0.021, 0.023)보다 크고, 정상 질문도 상위 세 건이 모두 SOP입니다. 그래서 점수 차나 유형에 기준값을 정해 답의 유무를 판단하기는 어렵습니다. 점수 차가 0.092로 큰 것은 구판을 뺀 개정판의 청크가 뚜렷하게 올라온 질문뿐입니다.
- **여러 판**은 모두 "없음"입니다. 이 인덱스는 구판을 뺀 것이기 때문입니다.
- **검색 결과에 없는 인용**은 모두 0입니다. 이번 실행에서는 지어낸 출처가 없었습니다.

"구판과 개정판" 질문의 응답은 8.0 Torr, 허용 편차 ±0.4 Torr를 `[SOP-ETCH-012_v2.0]` 출처와 함께 답했습니다. 이 진단 함수는 문자열 비교로 출처와 근거 없음을 셉니다. 모델이 규칙의 문구와 다르게 "찾지 못했다"고 쓰면 "근거 없음"을 놓칠 수 있습니다. 반대로 응답의 일부에만 근거 없음 문구가 있어도 "예"로 셉니다. 예제 3-5의 구체적인 질문처럼 조치는 답하고 원인만 근거를 찾지 못했다고 한 응답도 "예"가 됩니다. 출처는 대괄호 하나에 번호 하나를 적은 것만 셉니다. `[QIR-2026-0712, SOP-ETCH-007]`처럼 대괄호 하나에 번호를 여러 개 적은 출처는 세지 않습니다. 같은 문서를 `SOP-ETCH-012`와 `SOP-ETCH-012_v2.0`으로 다르게 적으면 둘로 셉니다.

응답을 받았을 때는 다음 네 가지를 같은 순서로 확인합니다.

1. 출처가 있습니까? 근거 없음 응답이 아닌데 출처가 없으면 지어낸 응답일 수 있습니다.
2. 그 문서가 현행입니까? 버전과 날짜를 봅니다. 구판이면 인덱스에서 구판을 빼도록 문서 관리 담당자에게 요청합니다.
3. 인용한 내용이 검색 결과에 실제로 있습니까? 인용한 문장을 검색 결과에서 찾습니다.
4. 빠진 답은 없습니까? 질문이 둘인데 하나에만 답하지는 않았는지 봅니다.

RAG를 업무에 적용할 때는 코드 밖에서 정할 일이 네 가지 있습니다.

1. 어떤 문서를 인덱스에 넣고 뺄지 정합니다. 구판과 초안은 빼는 것이 기본입니다.
2. 문서가 개정되면 언제 인덱스에 반영할지와 누가 반영할지 정합니다.
3. 누가 어느 문서를 검색할 수 있는지 정합니다.
4. 틀린 응답을 받았을 때 어디에 알릴지 정합니다. 알리는 경로가 없으면 개선이 멈춥니다.

접근 권한과 문서 갱신 운영은 이 파트에서 다루지 않습니다(원본 강의 계획에서는 5일차 주제입니다).

## 실습

실습은 `3일차_03_실습.ipynb`에서 합니다. 프롬프트를 만드는 함수와 구판을 제외하는 함수는 모델을 부르지 않는 테스트 셀로 검사합니다. 준비 셀의 연결 확인을 빼면, 마지막 세 셀에서만 모델을 호출합니다(모두 여덟 번). 풀이와 해설은 `3일차_03_실습_풀이.ipynb`에 있습니다.

:::실습 3 새 문서 묶음으로 RAG 구성하고 구판 제외하기
확산, 이온주입 라인의 새 문서 12건(`data/3일차/corpus_m3`)과 구판 1건(`data/3일차/corpus_m3_구판`)으로 RAG를 구성합니다. 검색 결과로 프롬프트를 만드는 `build_prompt()`와, 같은 문서의 구판 청크를 제외하는 `latest_version_rows()`를 직접 작성합니다. 새 문서의 질문 다섯 개를 RAG로 처리하고, 구판을 인덱스에 함께 넣었을 때와 뺐을 때를 비교합니다.

완료 기준: 테스트 셀이 "실습 3 통과"를 출력합니다. 그리고 다음을 적습니다.

- 질문 다섯 개의 1위 문서와 점수, 답이 없는 질문 5의 응답
- 질문 5를 근거 없음 규칙 없이 처리했을 때 응답이 어떻게 바뀌는지와, 운영에서 곤란한 점
- 구판을 넣었을 때와 뺐을 때 검색 결과 네 건의 판 구성과 응답의 값
- 응답이 맞아도 구판을 인덱스에 남기면 안 되는 이유
:::

## 핵심 정리

- 검색 결과를 문서 번호와 함께 프롬프트에 넣으면 사내 기준의 값과 출처가 있는 응답이 나옵니다. 검색 결과를 많이 넣는다고 나아지지 않고, 필요한 청크가 들어 있어야 나아집니다.
- RAG 프롬프트는 역할 지정, 검색 결과(재료), 출력 규칙(형식), 근거 없음 규칙(제약)으로 이루어집니다. 근거 없음 규칙이 없으면 없는 대상의 질문에 비슷한 다른 대상의 기준이 덧붙은 응답이 나올 수 있습니다.
- 출처는 청크마다 문서 번호를 붙이는 것과 출력 규칙의 요구가 모두 있어야 안정적으로 붙습니다.
- RAG는 오류 없이 틀립니다. 관련 없는 문서가 상위를 채움, 버전 충돌, 절이 문서의 맥락을 잃음의 세 경우는 모두 검색 결과에서 원인이 드러납니다.
- 응답이 이상할 때는 검색 결과가 질문에 맞는지부터 봅니다. 필요한 청크가 있고 관련 없는 청크와 구판이 없으면 검색 결과가 맞는 것입니다. 검색 결과가 맞지 않으면 청킹, 메타데이터, 인덱스를 고칩니다. 검색 결과가 맞는데 응답이 틀렸을 때만 프롬프트를 고칩니다.
- 점수만으로는 답이 있는 질문과 없는 질문을 구분할 수 없습니다. 점수 차, 유형, 여러 판, 출처, 근거 없음 응답을 함께 봅니다.

## 자가점검

**1.** RAG 프롬프트에서 근거 없음 규칙을 뺐을 때 일어나기 쉬운 일은 무엇입니까?

- A. 검색 단계에서 문서를 찾지 못해 오류가 나고 실행이 멈춘다
- B. 모델이 검색 결과를 무시하고 항상 빈 응답을 낸다
- C. 묻는 대상이 문서에 없을 때, 검색 결과에 있는 비슷한 다른 대상(예: 다른 호기)의 기준을 덧붙인 응답이 나올 수 있다
- D. 응답에 붙는 출처 표기가 더 정확해진다

:::정답
**C.** 검색은 문서에 답이 없어도 가장 가까운 청크를 돌려줍니다. 규칙이 없으면 이 예제에서는 ETCH-07의 기준은 확인되지 않는다고 말하면서도 옆 호기(ETCH-01~06)의 기준을 참고로 덧붙였습니다(예제 3-3).
:::

**2.** 응답의 문장마다 정확한 출처 문서 번호가 붙으려면 무엇이 필요합니까?

- A. 출력 규칙에 "출처를 붙여라"라고만 쓰고, 검색 결과에는 본문만 넣는다
- B. 검색 결과의 청크마다 문서 번호를 표시하기만 하면, 규칙이 없어도 문장마다 출처가 붙는다
- C. 모델의 temperature를 0으로 낮추면 출처가 빠짐없이 붙는다
- D. 검색 결과의 청크마다 앞에 문서 번호를 붙이고, 출력 규칙에서도 문장마다 그 번호를 붙이라고 요구한다

:::정답
**D.** 규칙만 주면 출처 표기는 붙지만 청크에 번호가 없어서, 예제 3-4에서는 인용한 번호가 모두 본문에 적힌 한 문서의 번호였습니다. 청크 표시만 하면 출처가 붙지 않습니다. 둘 다 있어야 문서별로 정확한 번호가 붙습니다(예제 3-4).
:::

**3.** 답의 근거가 되는 내용이 검색 결과에 들어 있지 않아 RAG의 응답이 틀렸습니다. 고치는 방법 가운데 효과가 가장 적은 것은 무엇입니까?

- A. 프롬프트에 "빠짐없이 정확하게 답하라"는 지시를 더한다
- B. 청크 크기와 분할 기준을 바꿔 다시 인덱싱한다
- C. 청크에 문서 제목을 붙여 다시 임베딩한다
- D. 질문을 더 구체적으로 바꿔 검색한다

:::정답
**A.** 모델은 검색 결과에 없는 내용을 근거로 답할 수 없습니다. 지시를 더해도 근거가 늘지 않습니다. B, C, D는 근거를 검색 결과에 넣을 수 있는 방법입니다. 예제 3-5처럼 질문을 구체화해도 필요한 절이 들어오지 않을 수 있으므로, 고친 뒤에는 검색 결과로 확인합니다.
:::

**4.** 절 단위로 자른 청크 앞에 문서 제목을 붙여 임베딩하면 달라지는 것은 무엇입니까?

- A. 모든 청크에 같은 줄이 붙은 것이므로 순위는 변하지 않는다
- B. 청크만 보고도 어느 문서의 어느 절인지 알 수 있어, 문서의 맥락이 필요한 질문에서 그 절의 검색 순위가 올라갈 수 있다
- C. 생성 모델이 문서 제목을 보고 응답의 말투를 문서 양식에 맞춘다
- D. 청크 수가 절반으로 줄어 인덱스 크기가 작아진다

:::정답
**B.** 제목은 문서마다 다른 줄이어서 청크의 벡터에 문서의 맥락을 더합니다. 예제 3-7에서 원인이 적힌 절의 순위가 올라갔습니다. 청크 수와 말투는 바뀌지 않습니다.
:::

**5.** 같은 문서의 구판과 개정판이 모두 인덱스에 있을 때 일어나기 쉬운 일과 그 이유로 옳은 것은 무엇입니까?

- A. 임베딩 모델이 날짜를 읽어 개정판을 항상 위로 올리므로 문제가 생기지 않는다
- B. 구판과 개정판은 유사도 차이가 커서 구판은 검색되지 않는다
- C. 두 판의 글이 숫자 몇 개만 달라 유사도가 거의 같으므로, 구판의 옛 값이 현행 값처럼 응답에 섞일 수 있다

:::정답
**C.** 두 판의 같은 절은 숫자만 달라서 점수가 같게 나옵니다(예제 3-6). 임베딩은 어느 쪽이 최신인지 구분하지 못하므로 구판을 인덱스에서 빼거나 버전을 표기합니다.
:::

**6.** 진단 결과에서 코퍼스에 없는 호기의 질문은 최고 점수가 0.914였고, 답이 있는 정상 질문은 0.840이었습니다. 점수로 "답이 있는 질문"을 구분할 수 있습니까?

:::정답
구분할 수 없습니다. 답이 없는 질문의 1위 점수가 답이 있는 질문보다 높을 수 있습니다. 점수 차, 검색 결과의 유형, 근거 없음 응답 여부를 함께 보고, 근거 없음 규칙으로 모델이 답을 거절하게 해야 합니다(예제 3-8).
:::

**7.** 응답에 출처 문서 번호가 붙어 있고 내용도 그럴듯합니다. 이 응답이 틀릴 수 있는 이유를 하나 쓰세요.

:::정답
검색이 구판을 찾아 그 문서를 인용했을 수 있습니다. 출처가 붙어 있다는 것은 근거가 있다는 뜻일 뿐, 그 근거가 현행 문서라는 뜻은 아닙니다. 인용한 문서의 버전과 날짜, 인용한 내용이 검색 결과에 있는지를 확인합니다.
:::

**8.** RAG의 응답이 이상할 때 확인하는 순서를 쓰세요.

:::정답
먼저 검색 결과가 질문에 맞는지 봅니다. 필요한 청크가 있고 관련 없는 청크와 구판이 없어야 맞는 것입니다. 검색 결과가 맞지 않으면 청킹, 메타데이터, 인덱스 구성을 고칩니다. 검색 결과가 맞는데 응답이 틀렸을 때만 프롬프트를 고칩니다.
:::

## 원본과 달라진 점

이 파트는 원본 강의안 3일차 p.199–325를 토대로 다시 구성했습니다. 문장을 다듬은 것은 적지 않고, 내용이 달라진 것만 적습니다.

### 예제, 실습, 재료 대응

| 원본 | 교재 | 달라진 점 |
| --- | --- | --- |
| 예제 3-1 (a) 조립 셀 | 예제 3-1 | 한 셀을 여러 함수로 나누고 인덱스를 객체(`ChunkIndex`)로 묶음. 모델 호출은 `llm.ask()`로 바꿈 |
| 예제 3-1 (b)(c)(d) | 예제 3-2 | 근거 없이 묻기, 검색 결과 4건 넣기, `k` 바꾸기를 한 예제로 합침 |
| 예제 3-2 | 예제 3-3 | 프롬프트 네 요소를 1일차의 요소(역할 지정, 형식, 제약)에 대응시키고, 검색 결과는 요소가 아닌 재료로 설명함. 프롬프트를 잘라 내지 않고 전체를 출력함 |
| 없음 | 예제 3-4 | 새로 작성. 출처를 붙이게 하는 두 가지의 조합을 세 번씩 실행 |
| 예제 3-3 (a)(b)(c) | 예제 3-5 | 질문이 넓을 때와 구체적일 때, 유형 제외를 한 예제로 합침 |
| 예제 3-3 (d-)~(f) | 예제 3-6 | 버전 표기와 규칙의 효과를 세 번씩 실행해 값을 셈. 첫 문단의 앞부분도 출력함. 구판을 제외하는 함수를 작성 |
| 예제 3-3 (g-)~(h) | 예제 3-7 | 같은 질문 외에 제목 없는 인덱스와 있는 인덱스의 검색 결과를 더 비교 |
| 예제 3-4 | 예제 3-8 | 진단 함수에 "검색 결과에 없는 인용" 항목을 더함 |
| 실습 미션 3 | 실습 3 | 값 두 개를 고치는 방식을 함수 두 개 작성으로 바꿈 |
| `corpus_m3` 12건, `corpus_m3_ext` 1건, 문서 목록 | `data/3일차/corpus_m3`, `corpus_m3_구판`, `corpus_m3_manifest.csv` | 그대로 사용 |
| 예제 3-4의 질문 여섯 개, 미션 3의 질문 | `진단_질문_6.csv`, `실습_질문_5.csv` | 질문은 그대로. CSV로 옮김 |

### 추가한 내용

- "이 파트에서 만드는 것" 절.
- 출처 표기를 붙이게 하는 두 가지의 조합을 세 번씩 실행한 결과(원본은 설명만 있음).
- 진단 함수의 "검색 결과에 없는 인용" 항목.
- 제목을 붙인 인덱스가 원인 절 하나가 아니라 다른 질문(시즈닝 런)에서도 검색 결과를 바꾼다는 비교.
- 응답이 실행마다 다른 예제는 세 번씩 실행해 결과를 센 것.
- 판단 그림에 코퍼스에 답이 없는 질문의 처리(근거 없음 규칙)를 더함.
- 진단 함수가 근거 없음과 출처를 잘못 세는 경우.
- 청크를 자르는 상한(첫 조각 8줄, 본문 1,200자)이 이 코퍼스에서는 적용되지 않는다는 설명.

### 고친 내용

- "오늘 본 실패 3종 중 프롬프트로 고쳐진 것은 하나도 없었습니다"(p.305), 부록의 실패 요약(p.318) → 버전 충돌은 검색 결과의 버전 표기와 규칙으로 응답이 달라지는지 직접 세어 확인하고 결론을 고침.
- "실패 1 노이즈"(p.241-248) → 파트 2의 노이즈(반복 줄)와 같은 낱말이어서 "관련 없는 문서가 상위를 채움"으로 바꿈.
- "점수 벌어짐"(p.243) → "1위와 4위의 점수 차"로 바꿈.
- "발췌", "꼬리표", "색인", "출처 표시" → 검색 결과, 메타데이터, 인덱스, 출처 표기.
- 1일차 "네 층 프롬프트"(p.230) → 1일차의 다섯 요소 가운데 역할 지정, 형식, 제약에 대응시키고, 검색 결과는 맥락이 아니라 처리할 재료로 설명함.
- 키의 앞 7글자를 출력하는 셀(p.204-205) → 키는 일부도 출력하지 않는 규칙에 따라 싣지 않음.

### 삭제한 내용

- 파트 도입, 환경 준비(키, 클라이언트), 모델을 고르는 기준(p.199-207): 2일차 파트 1과 환경 준비 장에 있음.
- 조립 셀을 여섯 쪽에 걸쳐 보이는 설명(p.210-217): 예제에 필요한 부분씩 나눠 실음.
- 내보내기 전 확인(p.225), 답을 세 등급으로 받기(p.285), 여러 단계를 잇는 흐름(p.287): 네 가지 확인으로 합치거나 삭제함.
- Wrap-Up, 이해도 설문, 다음 일차 예고, 부록의 오류 모음과 치트시트(p.303-325): 요점은 핵심 정리와 자가점검에 반영함.
- 확장 미션 안내, 제출물, 체크포인트(p.299-302): 강의 운영 안내.
