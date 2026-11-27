# 9장 검색과 RAG의 평가와 개선

강의 4일차 파트 1과 파트 2에 해당합니다.

8장의 RAG(retrieval-augmented generation)는 질문 몇 개에서는 잘 답했습니다. 하지만 몇 개를 눈으로 확인해서는 고친 것이 나아졌는지 나빠졌는지 알 수 없습니다. 이 장은 평가셋으로 검색과 답을 숫자로 측정하는 방법, 측정 결과를 보고 검색을 고치는 방법(하이브리드 검색, 리랭킹, 질의 재작성), 그리고 실패를 나눠 다음에 고칠 곳을 고르는 방법을 설명합니다.

## 학습 목표

1. 평가셋에 무엇을 넣어야 하는지 설명하고, recall@k와 MRR(mean reciprocal rank)로 검색을 측정할 수 있습니다.
2. 하이브리드 검색의 RRF(reciprocal rank fusion)가 점수 대신 순위를 합치는 이유와, 리랭킹에 쓰는 크로스 인코더가 바이 인코더보다 정확하지만 느린 이유를 설명할 수 있습니다.
3. 질의 재작성이 어떤 질문에서 검색을 돕고 어떤 비용이 드는지 설명할 수 있습니다.
4. 답의 정답성과 충실도를 LLM(large language model)으로 채점하고(LLM-as-a-judge), 채점 결과를 그대로 믿으면 안 되는 이유를 설명할 수 있습니다.
5. 실패한 질문을 검색 성공 여부와 답의 정답 여부로 나눠 다음에 고칠 곳을 고를 수 있습니다.

예제 9-1과 9-2는 PC에서만 실행하고, 예제 9-3은 API(application programming interface)로 LLM을 호출합니다. 문서 코퍼스, 청크, 검색기는 8장 "RAG"와 같습니다. 리랭커의 실행 시간은 PC에 따라, 모델의 응답과 채점은 실행할 때마다 교재와 다를 수 있습니다.

## 평가셋

:::요점
실제로 들어올 질문의 유형을 고루 넣고, 문서에 답이 없는 질문도 넣어야 검색기나 프롬프트를 바꿀 때마다 같은 기준으로 비교할 수 있습니다.
:::

[[평가셋]](evaluation set)은 질문, 정답 문서, 정답을 짝지어 둔 묶음입니다. 검색기, 청크 크기, top-k, 프롬프트를 바꿀 때마다 같은 평가셋으로 측정해야 바꾼 것의 효과를 숫자로 비교할 수 있습니다. 이 교재의 평가셋(`evalset.json`)은 질문 62개이고, 질문마다 다음을 적어 두었습니다.

| 키 | 뜻과 쓰임 |
| --- | --- |
| `docs` | [[정답 문서]](gold document)의 id 목록. 검색 결과를 채점할 때 씁니다 |
| `answer` | 사람이 쓴 정답 문장. LLM 채점의 기준 답입니다 |
| `key` | 맞는 답에 반드시 들어가는 핵심어 목록. 답을 문자열 비교로 채점할 때 씁니다 |
| `evidence` | 정답 문서마다 답이 적힌 문장. 검색한 청크에 답이 들어 있었는지 확인할 때 씁니다 |
| `need_all` | 참이면 정답 문서를 모두 찾아야 답할 수 있습니다 |
| `type` | 질문 유형. 유형마다 결과를 나눠 봅니다 |

평가셋을 만들 때는 다음을 지킵니다.

- **질문 유형을 고루 넣습니다.** 문서의 낱말로 묻는 질문만 넣으면 키워드 검색이 늘 더 나은 것처럼 보입니다. 이 평가셋에는 사실, 바꿔 말함, 코드, 개정, 표, 여러 문서, 충돌, 집계, 스캔, 일반(일반 지식), 오염(지시문이 숨은 문서, 15장) 질문을 넣었습니다.
- **답이 없는 질문을 넣습니다.** 문서에 답이 없을 때 모른다고 답하는지는 답이 있는 질문만으로는 측정할 수 없습니다. 이 평가셋에는 8개가 있습니다.
- **정답 문서를 사람이 확인합니다.** 같은 답이 여러 문서에 있으면 모두 적습니다. 하나만 적으면 다른 정답 문서를 찾은 검색이 틀린 것으로 채점됩니다.
- **질문은 현장의 말투로 씁니다.** LLM에게 문서를 주고 질문을 만들게 하면 빠르지만, 문서의 낱말을 그대로 쓴 질문이 많아져 실제보다 검색이 잘 되는 것처럼 보입니다. LLM이 만든 질문은 초안으로 쓰고 사람이 다듬습니다.

## 검색 지표

:::요점
recall@k는 정답 문서가 상위 k건 안에 든 질문의 비율이고, MRR은 정답 문서가 처음 나온 순위의 역수를 평균한 값입니다. RAG에서는 상위 k건만 모델에 넣으므로, 정답 문서가 k건 안에 들지 않은 질문은 검색 결과를 근거로 답할 수 없습니다.
:::

[[recall@k]]는 정답 문서가 검색 결과의 상위 k건 안에 들어 있는 질문의 비율입니다. 질문 10개 가운데 7개에서 정답 문서가 상위 3건 안에 있으면 recall@3은 0.7입니다. RAG가 청크 4개를 모델에 넣는다면, 정답 문서의 청크가 상위 4개 안에 없는 질문은 프롬프트를 어떻게 고쳐도 검색 결과를 근거로 답할 수 없습니다.

[[MRR]](mean reciprocal rank)은 질문마다 정답 문서가 처음 나온 순위의 역수(1위 1, 2위 0.5, 3위 0.33)를 구해 평균한 값입니다. 정답 문서를 찾지 못한 질문은 0으로 셉니다. recall@k가 k건 안에 들었는지만 보는 것과 달리, MRR은 1위와 3위를 구분합니다. 세 질문에서 정답 문서가 1위, 2위, 찾지 못함이면 MRR은 (1 + 0.5 + 0) / 3 = 0.5입니다.

청크 단위로 검색하면 한 문서의 청크 여러 개가 상위에 함께 나옵니다. 정답은 문서 단위로 적혀 있으므로, 청크 순위를 문서 순위로 바꾼 뒤(같은 문서의 청크는 처음 나온 순위만 남김) 지표를 계산합니다. 한 문서의 청크 여러 개가 상위를 차지하므로, 문서 단위 recall@4는 청크 4개 안에 답이 든 비율보다 높게 나옵니다. `docs_of()`가 이 일을 합니다.

:::예제 9-1 두 검색의 recall@k와 MRR
정답 문서가 있는 평가 질문 54개를 임베딩 검색과 키워드 검색으로 찾아, 문서 순위로 바꾼 뒤 recall@1, recall@3, recall@5, MRR을 계산합니다. 7장 예제 7-2는 질문 16개로 1위만 셌습니다. 질문 전체에서 두 검색의 차이가 얼마인지, 어느 지표에서 차이가 나는지 봅니다. API를 호출하지 않습니다.

```python
answerable = [item for item in questions.values() if item['docs']]          # 답이 없는 질문 8개는 뺍니다


def ranks_by(method):
    """질문마다 정답 문서가 처음 나온 문서 순위. 찾지 못하면 None"""
    return [first_hit(docs_of(searcher.ranking(item['question'], method, where=is_valid)), item['docs'])
            for item in answerable]


for method in ['embedding', 'keyword']:
    ranks = ranks_by(method)
    recall = {k: sum(rank is not None and rank <= k for rank in ranks) / len(ranks) for k in (1, 3, 5)}
    mrr = sum(1 / rank for rank in ranks if rank) / len(ranks)
    print(f'{method}: recall@1 {recall[1]:.2f}, recall@3 {recall[3]:.2f}, recall@5 {recall[5]:.2f}, MRR {mrr:.3f}')
    print('  5위 안에 없는 질문:', [item['id'] for item, rank in zip(answerable, ranks) if rank is None or rank > 5])
```
:::

교재의 실행에서 임베딩 검색은 recall@1 0.70, recall@5 0.91, MRR 0.799였고, 키워드 검색은 recall@1 0.67, recall@5 0.93, MRR 0.775였습니다. 1위만 보면 임베딩이, 5위 안을 보면 키워드가 조금 나았습니다. 질문 54개에서 0.03은 질문 한두 개의 차이이므로, 두 검색의 지표는 거의 같다고 봅니다.

5위 안에 정답 문서가 없는 질문은 두 검색 모두 E45, E47, E48을 포함했습니다. E47과 E48은 스캔 문서에만 답이 있어(8장) 어느 검색으로도 찾을 수 없고, E45(조립기술팀이 관리하는 설비 매뉴얼은 몇 건인가)는 문서 다섯 건을 세어야 하는 집계 질문이라 상위 몇 건을 찾는 검색으로는 답할 수 없습니다. E47과 E48은 파싱할 때 OCR(optical character recognition)로 글을 뽑아야 하고(8장), E45처럼 문서를 세는 질문은 검색이 아닌 다른 방법이 필요합니다(10장). 나머지 놓친 질문은 두 검색이 달랐습니다(임베딩은 E40, E46, 키워드는 E23).

## 하이브리드 검색과 RRF

:::요점
하이브리드 검색은 키워드 검색과 임베딩 검색의 결과를 합칩니다. 두 검색의 점수는 단위가 달라 더할 수 없으므로, RRF는 점수 대신 각 목록의 순위로 1/(60+순위)를 계산해 더합니다.
:::

두 검색은 놓치는 질문이 다릅니다(7장). 둘의 결과를 합치는 검색을 [[하이브리드 검색]](hybrid search)이라고 합니다. 점수를 그대로 더할 수는 없습니다. 임베딩의 코사인 유사도는 대부분 0.7~0.9이고, BM25 점수는 질문의 낱말 수에 따라 0부터 수십까지 나오므로, 그대로 더하면 BM25 점수가 순위를 정합니다.

[[RRF]](reciprocal rank fusion)는 점수를 버리고 순위만 씁니다(Cormack 외, 2009). 목록마다 문서의 순위 r로 1/(k + r)을 계산해 더하고, 합이 큰 순서로 줄 세웁니다. 이 k는 순위 차이를 줄이는 상수로, 검색 건수 top-k의 k와 다른 값입니다. 논문은 k=60을 썼고 이 교재의 `corpus.rrf()`도 60을 씁니다.

<figure>
<svg viewBox="0 0 680 196" role="img" aria-label="RRF 계산 예. 문서 A는 임베딩 검색 1위, 키워드 검색 10위로 1/61 + 1/70 = 0.0307입니다. 문서 B는 임베딩 3위, 키워드 2위로 1/63 + 1/62 = 0.0320입니다. 문서 C는 임베딩 2위이고 키워드 결과에 없어 1/62 = 0.0161입니다. 두 목록에서 모두 상위인 B가 1위, A가 2위, C가 3위가 됩니다.">
<text x="10" y="20" fill="var(--ink)" font-size="12" font-weight="700">문서</text><text x="120" y="20" fill="var(--ink)" font-size="12" font-weight="700">임베딩 순위</text><text x="240" y="20" fill="var(--ink)" font-size="12" font-weight="700">키워드 순위</text><text x="360" y="20" fill="var(--ink)" font-size="12" font-weight="700">RRF 점수 = 1/(60+r)의 합</text><text x="600" y="20" fill="var(--ink)" font-size="12" font-weight="700">합친 순위</text>
<rect x="10" y="32" width="660" height="40" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="24" y="57" fill="var(--ink)" font-size="12">A</text><text x="150" y="57" fill="var(--ink)" font-size="12">1위</text><text x="270" y="57" fill="var(--ink)" font-size="12">10위</text><text x="360" y="57" fill="var(--ink)" font-size="12">1/61 + 1/70 = 0.0307</text><text x="620" y="57" fill="var(--ink)" font-size="12">2위</text>
<rect x="10" y="80" width="660" height="40" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="24" y="105" fill="var(--ink)" font-size="12" font-weight="700">B</text><text x="150" y="105" fill="var(--ink)" font-size="12">3위</text><text x="270" y="105" fill="var(--ink)" font-size="12">2위</text><text x="360" y="105" fill="var(--ink)" font-size="12" font-weight="700">1/63 + 1/62 = 0.0320</text><text x="620" y="105" fill="var(--teal)" font-size="12" font-weight="700">1위</text>
<rect x="10" y="128" width="660" height="40" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="24" y="153" fill="var(--ink)" font-size="12">C</text><text x="150" y="153" fill="var(--ink)" font-size="12">2위</text><text x="270" y="153" fill="var(--amber)" font-size="12">없음</text><text x="360" y="153" fill="var(--ink)" font-size="12">1/62 = 0.0161</text><text x="620" y="153" fill="var(--ink)" font-size="12">3위</text>
<text x="340" y="190" text-anchor="middle" fill="var(--ink-soft)" font-size="12">한 목록의 1위보다 두 목록 모두의 상위가 앞에 옵니다. k=60이 1위와 10위의 차이를 줄입니다</text>
</svg>
<figcaption>RRF는 점수의 단위와 상관없이 두 목록의 순위만으로 합친 순위를 만듭니다.</figcaption>
</figure>

상수 k가 크면 1위와 10위의 점수 차이가 작아지므로, 한쪽 목록에서만 1위인 문서보다 두 목록 모두에서 상위인 문서가 앞에 옵니다. 한쪽 검색만 찾은 문서도 점수를 받으므로 결과에서 사라지지 않습니다. 대신 한쪽 검색이 정답을 1위로 찾고 다른 쪽이 낮은 순위에 두면, 하이브리드의 순위는 더 잘 찾은 쪽보다 낮아질 수 있습니다.

## 리랭킹

:::요점
임베딩 검색은 질문과 문서를 따로 벡터로 만들어 비교하므로 빠르지만, 질문의 낱말과 문서의 낱말을 직접 맞대어 보지 못합니다. 리랭킹은 1차 검색이 고른 후보 수십 개만 질문과 함께 크로스 인코더에 넣어 다시 점수를 매깁니다.
:::

7장의 임베딩 모델은 질문과 문서를 따로따로 벡터로 바꾼 뒤 내적합니다. 이런 구조를 [[바이 인코더]](bi-encoder)라고 합니다. 문서의 벡터를 미리 계산해 둘 수 있어 검색이 빠르지만, 글 전체를 벡터 하나로 줄인 뒤에 비교하므로 "QIR-2026-014"와 "QIR-2026-004"처럼 한두 글자 다른 것을 구분하기 어렵습니다.

[[크로스 인코더]](cross-encoder)는 질문과 문서를 이어 붙여 트랜스포머에 한 번에 넣고, 관련도 점수 하나를 출력합니다. 어텐션이 질문의 토큰과 문서의 토큰 사이에도 계산되므로, 질문의 어느 낱말이 문서의 어느 부분과 맞는지를 직접 봅니다. 그래서 바이 인코더보다 정확하지만, 질문이 올 때마다 문서마다 트랜스포머를 한 번씩 실행해야 하므로 모든 문서에 쓸 수는 없습니다(sentence-transformers 문서).

<figure>
<svg viewBox="0 0 680 216" role="img" aria-label="바이 인코더와 크로스 인코더. 왼쪽 바이 인코더는 질문과 문서를 각각 인코더에 넣어 벡터 두 개를 만들고 내적합니다. 문서 벡터는 미리 계산해 둘 수 있습니다. 오른쪽 크로스 인코더는 질문과 문서를 이어 붙여 인코더 하나에 넣고 관련도 점수 하나를 냅니다. 질문마다 후보 문서 수만큼 실행하므로, 1차 검색이 고른 후보 10개에만 씁니다.">
<text x="10" y="20" fill="var(--ink)" font-size="12" font-weight="700">바이 인코더(1차 검색)</text>
<rect x="10" y="32" width="90" height="34" rx="6" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="55" y="54" text-anchor="middle" fill="var(--ink)" font-size="12">질문</text>
<rect x="10" y="80" width="90" height="34" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="55" y="102" text-anchor="middle" fill="var(--ink)" font-size="12">문서</text>
<rect x="120" y="32" width="90" height="34" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="165" y="54" text-anchor="middle" fill="var(--ink)" font-size="12">인코더</text>
<rect x="120" y="80" width="90" height="34" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="165" y="102" text-anchor="middle" fill="var(--ink)" font-size="12">인코더</text>
<line x1="100" y1="49" x2="120" y2="49" stroke="var(--teal)" stroke-width="2"/><line x1="100" y1="97" x2="120" y2="97" stroke="var(--teal)" stroke-width="2"/>
<line x1="210" y1="49" x2="250" y2="70" stroke="var(--teal)" stroke-width="2"/><line x1="210" y1="97" x2="250" y2="76" stroke="var(--teal)" stroke-width="2"/>
<rect x="250" y="56" width="70" height="34" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="285" y="78" text-anchor="middle" fill="var(--ink)" font-size="12">내적</text>
<text x="10" y="140" fill="var(--ink-soft)" font-size="11">문서 벡터는 미리 계산해 둡니다</text><text x="10" y="158" fill="var(--ink-soft)" font-size="11">질문마다 인코더 1번 + 행렬 곱 1번</text>
<line x1="340" y1="20" x2="340" y2="170" stroke="var(--line)"/>
<text x="360" y="20" fill="var(--ink)" font-size="12" font-weight="700">크로스 인코더(리랭킹)</text>
<rect x="360" y="56" width="140" height="34" rx="6" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="430" y="78" text-anchor="middle" fill="var(--ink)" font-size="12">질문 + 문서</text>
<line x1="500" y1="73" x2="520" y2="73" stroke="var(--teal)" stroke-width="2"/>
<rect x="520" y="56" width="80" height="34" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="560" y="78" text-anchor="middle" fill="var(--ink)" font-size="12">인코더</text>
<line x1="600" y1="73" x2="616" y2="73" stroke="var(--teal)" stroke-width="2"/>
<rect x="616" y="56" width="54" height="34" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="643" y="78" text-anchor="middle" fill="var(--ink)" font-size="12">점수</text>
<text x="360" y="140" fill="var(--ink-soft)" font-size="11">질문의 토큰과 문서의 토큰이 서로 어텐션합니다</text><text x="360" y="158" fill="var(--ink-soft)" font-size="11">질문마다 후보 수만큼 인코더를 실행합니다</text>
<text x="340" y="204" text-anchor="middle" fill="var(--ink-soft)" font-size="12">1차 검색으로 후보 10개를 고르고, 그 10개만 크로스 인코더로 다시 줄 세웁니다</text>
</svg>
<figcaption>바이 인코더는 미리 계산한 벡터로 빠르게 후보를 고르고, 크로스 인코더는 후보마다 질문과 함께 읽어 순위를 다시 정합니다.</figcaption>
</figure>

이렇게 1차 검색으로 후보를 줄인 뒤 크로스 인코더로 순위를 다시 매기는 것을 [[리랭킹]](reranking)이라고 합니다. 예제는 MS MARCO의 질문과 문단 쌍을 여러 언어로 번역한 데이터(mMARCO)로 학습한 다국어 크로스 인코더를 씁니다(모델 카드). mMARCO에 한국어는 없지만, 기반 모델(multilingual MiniLMv2)이 여러 언어로 사전학습되어 한국어 질문에도 점수를 냅니다. 리랭킹은 1차 검색이 고른 후보 안에서만 순위를 바꾸므로, 후보에 정답이 없으면 효과가 없습니다.

:::예제 9-2 하이브리드 검색과 리랭킹
예제 9-1의 질문 54개를 하이브리드 검색(RRF)으로 찾고, 하이브리드 검색의 상위 청크 10개를 크로스 인코더로 다시 줄 세웁니다. 두 방법의 recall@1과 MRR, 질문 하나에 걸린 시간을 예제 9-1의 결과와 비교합니다. 예제 9-1을 먼저 실행합니다. 리랭커를 처음 불러올 때 모델을 내려받고, 리랭킹은 몇 분 걸립니다. API를 호출하지 않습니다.

```python
reranker = load_reranker()


def reranked(question, candidates=10):
    """하이브리드 검색의 상위 청크 candidates개를 크로스 인코더의 점수 순으로 다시 줄 세웁니다"""
    top = searcher.ranking(question, 'hybrid', where=is_valid)
    scores = reranker.predict([(question, chunks[index]['text']) for index in top[:candidates]])
    return [top[index] for index in np.argsort(-scores)] + top[candidates:]


for name, ranking in [('hybrid', lambda question: searcher.ranking(question, 'hybrid', where=is_valid)),
                      ('hybrid + rerank', reranked)]:
    started = time.time()
    ranks = [first_hit(docs_of(ranking(item['question'])), item['docs']) for item in answerable]
    print(f'{name}: recall@1 {sum(rank == 1 for rank in ranks) / len(ranks):.2f}, '
          f'MRR {sum(1 / rank for rank in ranks if rank) / len(ranks):.3f}, 질문당 {(time.time() - started) / len(ranks):.2f}초')
    print('  1위를 놓친 질문:', [(item['id'], rank) for item, rank in zip(answerable, ranks) if rank != 1])
```
:::

교재의 실행에서 하이브리드 검색은 recall@1 0.72, MRR 0.806으로 예제 9-1의 두 검색과 거의 같았습니다(임베딩 검색보다 질문 1개 많음). 리랭킹을 더하자 recall@1 0.81, MRR 0.874로 올랐습니다. 하이브리드에서 1위를 놓친 E13, E19, E25, E36, E37, E53이 리랭킹 뒤에 1위가 되었고, 반대로 E34는 1위에서 2위로 내려갔습니다. 질문 하나에 걸린 시간은 0.19초에서 2.45초로 늘었습니다. 크로스 인코더를 후보 10개에 한 번씩 실행했기 때문입니다.

집계 질문 E45(23위)와 스캔 질문 E47, E48(찾지 못함)은 리랭킹 뒤에도 그대로였습니다. 리랭킹은 후보의 순서만 바꾸므로 후보에 없는 문서는 찾지 못합니다.

## 질의 재작성

:::요점
질의 재작성은 검색하기 전에 LLM으로 질문을 문서에서 쓸 법한 표현이나 여러 개의 검색어로 바꾸는 방법입니다. 질문과 문서의 낱말이 다를 때 도움이 되지만, 질문마다 LLM 호출이 하나 늘고, 바꾼 질문이 원래 뜻에서 벗어날 수 있습니다.
:::

[[질의 재작성]](query rewriting)은 사용자의 질문을 검색에 더 알맞은 질문으로 바꾸는 일입니다. 현장의 질문은 "칩 테두리가 깨지는 건"처럼 문서와 다른 낱말을 쓰거나, 두 가지를 한 번에 묻거나, 앞 대화를 가리키는 말("그건")을 씁니다. LLM에게 질문을 주고 다음 가운데 하나를 시킵니다.

- **문서의 표현으로 바꾸기**: "칩 테두리가 깨지는" → "칩핑 허용 기준". LLM이 일반적인 공정 용어를 알고 있으면 효과가 있습니다.
- **검색어 여러 개로 나누기**: 질문 하나를 검색어 세 개로 바꿔 각각 검색하고, 세 결과를 RRF로 합칩니다.
- **가상의 답을 써서 검색하기**: 질문에 대한 답을 LLM이 지어 쓰게 하고, 그 답으로 검색합니다(HyDE(hypothetical document embeddings), Gao 외, 2022). 지어낸 답은 틀릴 수 있지만 문서와 비슷한 문체와 낱말을 쓰므로 문서와 가까운 벡터가 됩니다.

비용도 있습니다. 질문마다 LLM 호출이 하나 늘어 대기 시간과 요금이 늘고, LLM은 사내 약어나 코드의 뜻을 모르므로 "SSC"를 다른 뜻의 말로 풀어 쓰면 오히려 검색이 나빠집니다. 원래 질문의 검색 결과와 재작성한 질문의 검색 결과를 RRF로 합치면 이 위험이 줄어듭니다. 효과는 실습 9-1에서 확인합니다.

## 답 평가

:::요점
검색이 맞아도 답이 틀릴 수 있으므로 답도 따로 채점합니다. 정답성은 답이 기준 답과 같은 사실을 말하는지, 충실도는 답의 내용이 모두 검색 결과에 근거하는지를 봅니다. LLM에게 채점을 맡기면 문장으로 된 답도 채점할 수 있지만, 채점도 틀리므로 표본을 사람이 확인합니다.
:::

답을 채점하는 기준은 두 가지입니다.

- [[정답성]](correctness): 답이 기준 답과 같은 사실을 말하는지. 답이 없는 질문은 찾지 못했다고 답해야 맞은 답입니다.
- [[충실도]](faithfulness): 답의 내용이 모두 검색 결과에서 확인되는지(Es 외, 2023). 정답과 같아도 검색 결과에 없는 내용으로 답했다면 충실하지 않습니다. 이번에는 맞았어도, 검색 결과에 없는 내용으로 답하는 설정에서는 사내 기준이 일반값과 다른 질문에서 틀린 답이 나옵니다.

가장 단순한 채점은 문자열 비교입니다. 평가셋의 `key`의 핵심어(예: "97%")가 모두 답에 들어 있으면 맞은 것으로 셉니다. 빠르고 매번 같은 결과가 나오지만, "97퍼센트"처럼 표기가 다르면 틀린 것으로 셉니다. 충실도는 문자열로 비교할 수 없습니다.

[[LLM-as-a-judge]]는 모델에게 채점 기준과 답을 주고 채점하게 하는 방법입니다(4장). 이 장의 채점 프롬프트(`JUDGE_PROMPT`)는 검색 결과, 질문, 기준 답, 답을 넣고 `faithful`, `correct`, `reason`을 6장의 구조화 출력으로 받습니다. 채점하는 모델도 틀리므로 다음을 지킵니다.

- 기준을 둘로 나눠 따로 판정하게 합니다. 하나로 물으면 맞지만 근거 없는 답과, 근거는 있지만 틀린 답을 구분할 수 없습니다. Zheng 외(2023)는 LLM 채점이 더 긴 답을 선호하는 경향(verbosity bias)이 있다고 보고했습니다.
- 기준 답을 함께 줍니다. 채점하는 모델도 사내 기준값을 모르기 때문입니다.
- 채점 모델에게 생성 모델이 받은 것과 같은 검색 결과를 줍니다. 채점 모델이 받은 검색 결과에 메타데이터가 없으면, 답에 적힌 개정 번호와 날짜를 근거 없는 내용으로 채점합니다. 예제 9-3은 생성과 같은 `context_of()`를 씁니다.
- 채점 결과 일부를 사람이 다시 채점해, 채점 모델과 사람의 판정이 얼마나 일치하는지 확인합니다. Zheng 외(2023)는 강한 모델의 채점이 사람과 80% 넘게 일치했다고 보고했지만, 사내 문서와 질문에서도 그런지는 직접 확인해야 합니다.
- 채점 모델, 프롬프트, 평가셋의 판을 결과와 함께 기록합니다. 채점 모델을 바꾸면 같은 답의 점수도 바뀌므로, 기록이 없으면 지난달 결과와 비교할 수 없습니다.

:::예제 9-3 정답성과 충실도 채점하기
평가 질문 8개(답이 없는 질문과 스캔 문서에만 답이 있는 질문 포함)를 8장의 RAG로 답하고, 같은 소형 모델로 정답성과 충실도를 채점합니다. 검색 결과에 정답 문서가 있었는지(찾음), 핵심어가 답에 있는지(`key`)도 함께 출력합니다. 채점 모델의 판정과 핵심어 비교가 다른 질문이 있는지 봅니다. 이 셀은 API를 16번 호출합니다.

```python
judged_rows = []
for qid in ['E06', 'E13', 'E23', 'E31', 'E41', 'E45', 'E47', 'E55']:
    item = questions[qid]
    reply, hits = rag_answer(item['question'])
    verdict = json.loads(llm.ask(JUDGE_PROMPT.format(context=context_of(hits), question=item['question'], reference=item['answer'],
                                                     answer=reply.text), model='소형', max_tokens=2000, schema=JUDGE_SCHEMA).text)
    found = any(hit['doc_id'] in item['docs'] for hit in hits) if item['docs'] else None
    has_key = all(key in reply.text for key in item['key']) if item['key'] else '찾지 못했습니다' in reply.text
    judged_rows.append({'id': qid, 'type': item['type'], 'found': found, 'key': has_key, **verdict})
    print(f"{qid}({item['type']}) 찾음 {found}, 핵심어 {has_key}, 정답성 {verdict['correct']}, 충실도 {verdict['faithful']}")
    print(f"  답: {reply.text.strip().replace(chr(10), ' ')[:110]}\n  채점 근거: {verdict['reason'][:110]}")
```
:::

교재의 실행에서 8개 가운데 정답성이 참인 것은 E06, E13, E31, E41, E55의 다섯 개였고, 채점 모델의 정답성 판정은 핵심어 비교와 모두 같았습니다. 충실도는 8개 모두 참이었습니다.

틀린 세 개는 원인이 다릅니다. E45(집계)와 E47(스캔)은 정답 문서를 찾지 못했고, 모델은 근거 없음 규칙대로 찾지 못했다고 답했습니다. 지어낸 답보다는 낫지만 질문에 답하지 못했으므로 정답성은 거짓입니다. E23은 "찾음"이 참인데도 찾지 못했다고 답했습니다. 검색 결과에 QIR-2026-014의 청크가 있었지만 원인 절 청크는 상위 4개에 들지 못했기 때문입니다. 문서 단위로 채점한 "찾음"은 필요한 절을 찾았는지까지는 알려 주지 않습니다. 평가셋의 `evidence`(답이 적힌 문장)가 검색한 청크에 들어 있는지를 보면 이 경우도 구분할 수 있습니다.

## 다음에 고칠 곳 고르기

:::요점
실패한 질문을 "검색 결과에 정답 문서가 있었는가"와 "답이 맞았는가"로 나누면 네 칸이 됩니다. 건수가 가장 많은 실패 칸부터 그 칸에 맞는 단계를 고치고, 한 번에 하나만 바꿔 같은 평가셋으로 다시 측정합니다.
:::

8장 "RAG가 틀리는 경우"의 판단 순서를 평가셋 전체에 적용하면 질문이 네 칸으로 나뉩니다.

<figure>
<svg viewBox="0 0 680 228" role="img" aria-label="실패 유형 네 칸. 가로는 답이 맞았는가, 세로는 검색 결과에 정답 문서가 있었는가입니다. 찾고 맞음은 정상입니다. 찾고 틀림은 생성 실패로 프롬프트, 메타데이터, 모델 등급을 고칩니다. 못 찾고 틀림은 검색 실패로 파싱, 청크, 검색 방법, top-k를 고칩니다. 못 찾고 맞음은 검색 결과가 아닌 학습한 지식으로 맞힌 것이므로 정답 문서 목록이 빠짐합니다.">
<text x="250" y="20" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">답이 맞음</text><text x="530" y="20" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">답이 틀림</text>
<text x="10" y="76" fill="var(--ink)" font-size="12" font-weight="700">정답 문서</text><text x="10" y="92" fill="var(--ink)" font-size="12" font-weight="700">찾음</text>
<text x="10" y="176" fill="var(--ink)" font-size="12" font-weight="700">정답 문서</text><text x="10" y="192" fill="var(--ink)" font-size="12" font-weight="700">못 찾음</text>
<rect x="120" y="32" width="260" height="90" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="250" y="70" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">정상</text><text x="250" y="90" text-anchor="middle" fill="var(--ink-soft)" font-size="11">고칠 것 없음</text>
<rect x="390" y="32" width="280" height="90" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="530" y="62" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">생성 실패</text><text x="530" y="82" text-anchor="middle" fill="var(--ink)" font-size="11">프롬프트(근거 없음 규칙, 충돌 처리),</text><text x="530" y="100" text-anchor="middle" fill="var(--ink)" font-size="11">메타데이터, top-k, 모델 등급</text>
<rect x="120" y="132" width="260" height="90" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="250" y="162" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">못 찾고 맞음</text><text x="250" y="182" text-anchor="middle" fill="var(--ink)" font-size="11">학습한 지식으로 답했거나</text><text x="250" y="200" text-anchor="middle" fill="var(--ink)" font-size="11">정답 문서 목록이 빠짐</text>
<rect x="390" y="132" width="280" height="90" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="530" y="162" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">검색 실패</text><text x="530" y="182" text-anchor="middle" fill="var(--ink)" font-size="11">파싱, 청크, 검색 방법(하이브리드,</text><text x="530" y="200" text-anchor="middle" fill="var(--ink)" font-size="11">리랭킹, 질의 재작성), top-k</text>
</svg>
<figcaption>실패 칸마다 고칠 단계가 다르므로, 칸별 건수를 세어 가장 큰 칸부터 고칩니다.</figcaption>
</figure>

"찾음"은 문서 단위로 판정하므로, "찾고 틀림"에는 답이 적힌 청크가 프롬프트에 들지 못한 검색 실패도 섞입니다(예제 9-3의 E23). 이 칸의 질문은 먼저 `evidence`가 검색한 청크에 있었는지 확인합니다. 답이 없는 질문은 정답 문서가 없으므로 따로 셉니다. 찾지 못했다고 답하면 맞은 것이고, 그럴듯한 답을 지어내면 생성 실패입니다.

고칠 때는 다음을 지킵니다.

- **한 번에 하나만 바꿉니다.** 검색기와 프롬프트를 함께 바꾸면 어느 쪽이 효과를 냈는지 알 수 없습니다.
- **평균과 함께 질문별 변화를 봅니다.** 리랭킹으로 recall@1이 올라도, 원래 맞던 질문 몇 개가 틀리게 바뀌었을 수 있습니다. 나빠진 질문을 열어 원인을 봅니다.
- **비용도 함께 기록합니다.** 리랭킹과 질의 재작성은 질문마다 시간과 요금을 더합니다. 효과가 비용만큼 큰지는 측정한 숫자로 판단합니다.
- **평가셋에 없는 실패는 측정되지 않습니다.** 운영하면서 틀린 질문을 모아 평가셋에 더합니다. 다만 평가셋에 맞춰 여러 번 고치면 평가셋에서만 점수가 좋아질 수 있으므로, 고칠 때 보지 않은 질문을 따로 남겨 두고 마지막에 한 번 측정합니다.

## 개념 확인 실습

실습은 장 노트북의 빈칸을 채워 실행합니다. 코드를 실행하기 전에 결과를 먼저 예측해 적고, 실행한 뒤 예측과 다른 부분을 이 장의 원리로 설명해 봅니다.

:::실습 9-1 질의 재작성
하이브리드 검색에서 정답 문서가 1위에 오지 못한 질문 세 개(E13, E23, E44)를 LLM으로 검색어 세 개로 바꾸고, 원래 질문과 검색어 세 개의 검색 결과를 RRF로 합칩니다. `REWRITE_PROMPT`에 LLM에게 줄 지시를 작성하고, 질문마다 정답 문서의 순위가 오를지 `my_guess`에 먼저 적은 뒤 실행합니다. 순위가 오르거나 내린 이유를 LLM이 만든 검색어로 설명하면 끝납니다. 이 셀은 API를 3번 호출합니다.

```python
REWRITE_PROMPT = ''  # TODO: {question}을 사내 문서 검색에 쓸 검색어 세 개로 바꾸라는 지시. 한 줄에 하나씩만 출력하게 합니다
my_guess = {'E13': None, 'E23': None, 'E44': None}  # TODO: 정답 문서의 순위가 오를지('오름', '같음', '내림')

for qid in ['E13', 'E23', 'E44']:
    item = questions[qid]
    reply = llm.ask(REWRITE_PROMPT.format(question=item['question']), model='소형', max_tokens=2000)
    queries = [line.strip('-• ').strip() for line in reply.text.splitlines() if line.strip()][:3]
    before = docs_of(searcher.ranking(item['question'], 'hybrid', where=is_valid))
    after = docs_of(corpus.rrf([searcher.ranking(query, 'hybrid', where=is_valid) for query in [item['question']] + queries]))
    print(f"{qid} {item['question']}\n  검색어: {queries}")
    print(f"  정답 문서 순위 {first_hit(before, item['docs'])}위 → {first_hit(after, item['docs'])}위, 예측 {my_guess[qid]}")
```

:::풀이
검색어를 문서에서 쓸 법한 표현으로 쓰게 하고, 설명 없이 한 줄에 하나씩만 출력하게 합니다.

```python
REWRITE_PROMPT = ('반도체 후공정 회사의 사내 문서(작업 표준, 설비 매뉴얼, 품질 이슈 보고서, 회의록)를 검색하려 한다. '
                  '아래 질문을 문서에 쓰였을 법한 용어로 바꾼 검색어 세 개를 만든다. 설명 없이 한 줄에 하나씩만 출력한다.\n'
                  '질문: {question}')
my_guess = {'E13': '오름', 'E23': '같음', 'E44': '오름'}

for qid in ['E13', 'E23', 'E44']:
    item = questions[qid]
    reply = llm.ask(REWRITE_PROMPT.format(question=item['question']), model='소형', max_tokens=2000)
    queries = [line.strip('-• ').strip() for line in reply.text.splitlines() if line.strip()][:3]
    before = docs_of(searcher.ranking(item['question'], 'hybrid', where=is_valid))
    after = docs_of(corpus.rrf([searcher.ranking(query, 'hybrid', where=is_valid) for query in [item['question']] + queries]))
    print(f"{qid} {item['question']}\n  검색어: {queries}")
    print(f"  정답 문서 순위 {first_hit(before, item['docs'])}위 → {first_hit(after, item['docs'])}위, 예측 {my_guess[qid]}")
```

교재의 실행에서 E13은 3위에서 1위, E23은 4위에서 2위로 올랐고, E44는 4위 그대로였습니다. E13에서 LLM은 "칩 테두리가 깨지는"을 문서가 쓰는 "칩핑"으로 바꾼 검색어("백사이드 칩핑 허용 기준")를 만들었습니다. 칩핑은 업계에서 널리 쓰는 말이라 LLM이 알고 있었습니다. E23의 검색어는 모두 "QIR-2026-014 원인"을 반복해 문서 번호를 여러 번 넣은 효과를 냈습니다. E44의 검색어("두께 측정기 캘리브레이션 누락 야간 교대")는 정답 문서인 회의록의 표현과 가까워지지 않았습니다. 정답 문서인 회의록에는 원인이 "야간 교대 작업자가 보정 절차를 몰랐다"처럼 사람의 행동으로 적혀 있어, 설비 용어로 바꾼 검색어와 겹치는 낱말이 적었습니다. 질의 재작성은 LLM이 아는 말로만 바꿀 수 있습니다.
:::
:::

## 관통 프로젝트 4단계

3단계의 도우미는 질문 다섯 개에서 그럴듯하게 답했습니다. 4단계에서는 평가 질문 12개로 도우미를 측정하고, 실패를 네 칸으로 나눈 뒤, 검색 결과의 건수(k)를 바꿔 다시 측정합니다.

:::실습 P4 평가셋으로 측정하고 고치기
`evaluate(qids, k)`를 작성합니다. 질문마다 3단계의 `answer_with_documents(question, k)`로 답하고, 검색한 청크에 정답 문서가 있었는지(`found`)와 답이 맞았는지(`correct`)를 기록한 행의 목록을 돌려줍니다. 답이 맞았는지는 핵심어(`key`)가 모두 답에 들어 있는지로, 답이 없는 질문은 "찾지 못했습니다"가 답에 있는지로 정합니다. `cells()`는 행을 네 칸과 답 없음 두 칸(맞음, 틀림)으로 나눠 `{칸 이름: [질문 id]}`로 돌려줍니다. 칸 이름은 그림의 칸 이름을 씁니다. k=4와 k=8의 네 칸 건수와 요금이 출력되면 끝납니다. 이 셀은 API를 24번 호출합니다.

완료 기준

- k마다 네 칸과 답 없음 질문의 건수, 요금 합계가 출력됩니다.
- 실패한 질문의 id가 칸별로 출력됩니다.

:::힌트
청크 번호의 `#` 앞이 문서 id입니다(`'SOP-WB-001#4'.split('#')[0]`). 3단계의 결과 dict에는 `hits`(검색한 청크 번호)와 `cost`(1단계에서 계산한 요금)가 있습니다.
:::

```python
EVAL_IDS = ['E06', 'E13', 'E19', 'E23', 'E31', 'E37', 'E40', 'E41', 'E44', 'E53', 'E55', 'E58']


def evaluate(qids, k=4):
    """질문마다 {'id', 'found', 'correct', 'cost'}를 담은 행의 목록. 답이 없는 질문의 found는 None입니다"""
    return []  # TODO


def cells(rows):
    """행을 네 칸과 답 없음으로 나눠 {칸 이름: [질문 id]}로 돌려줍니다"""
    return {}  # TODO


for k in [4, 8]:
    rows = evaluate(EVAL_IDS, k)
    print(f"k={k}: 요금 {sum(row['cost'] for row in rows):.4f}달러")
    for name, ids in cells(rows).items():
        print(f'  {name} {len(ids)}건: {ids}')
```

:::풀이
`found`는 검색한 청크의 문서 id와 정답 문서를 비교하고, `correct`는 핵심어 비교로 정합니다.

```python
EVAL_IDS = ['E06', 'E13', 'E19', 'E23', 'E31', 'E37', 'E40', 'E41', 'E44', 'E53', 'E55', 'E58']


def evaluate(qids, k=4):
    """질문마다 {'id', 'found', 'correct', 'cost'}를 담은 행의 목록. 답이 없는 질문의 found는 None입니다"""
    rows = []
    for qid in qids:
        item = questions[qid]
        result = answer_with_documents(item['question'], k=k)
        searched = {hit.split('#')[0] for hit in result['hits']}
        found = bool(searched & set(item['docs'])) if item['docs'] else None
        if item['key']:
            correct = all(key in result['answer'] for key in item['key'])
        else:
            correct = '찾지 못했습니다' in result['answer']
        rows.append({'id': qid, 'found': found, 'correct': correct, 'cost': result['cost']})
    return rows


def cells(rows):
    """행을 네 칸과 답 없음으로 나눠 {칸 이름: [질문 id]}로 돌려줍니다"""
    names = {(True, True): '찾고 맞음', (True, False): '찾고 틀림(생성 실패)',
             (False, True): '못 찾고 맞음', (False, False): '못 찾고 틀림(검색 실패)'}
    grouped = {name: [] for name in names.values()}
    grouped.update({'답 없음, 맞음': [], '답 없음, 틀림': []})
    for row in rows:
        if row['found'] is None:
            grouped['답 없음, 맞음' if row['correct'] else '답 없음, 틀림'].append(row['id'])
        else:
            grouped[names[(row['found'], row['correct'])]].append(row['id'])
    return grouped


for k in [4, 8]:
    rows = evaluate(EVAL_IDS, k)
    print(f"k={k}: 요금 {sum(row['cost'] for row in rows):.4f}달러")
    for name, ids in cells(rows).items():
        print(f'  {name} {len(ids)}건: {ids}')
```

교재의 실행에서 k=4는 답이 있는 질문 10개 가운데 7개가 "찾고 맞음", E23이 "찾고 틀림", E40과 E44가 "못 찾고 틀림"이었고, 답이 없는 두 질문은 모두 찾지 못했다고 답했습니다. k=8로 늘리자 E23이 맞음으로 바뀌었습니다. 원인 절 청크가 5~8위에 있어서 k=4에서는 프롬프트에 들어가지 못했던 것입니다. 요금은 0.0045달러에서 0.0069달러로 약 50% 늘었습니다.

E40(고객사 B의 요구로 강화된 기준 두 가지)과 E44는 k=8에서도 정답 문서를 찾지 못했습니다. E40은 예제 9-1의 임베딩 검색에서 정답 문서가 5위 안에 없었고 하이브리드에서 4위, 리랭킹 뒤 3위였습니다. E44는 하이브리드 4위에서 리랭킹 뒤 2위로 올랐습니다. 3단계의 `answer_with_documents()`는 임베딩 검색만 쓰므로, 다음에 고칠 곳은 검색 방법(하이브리드 검색과 리랭킹)입니다. 그다음 같은 12개로 다시 측정합니다.
:::
:::

## 자가점검

**1.** 평가셋을 LLM에게 문서를 하나씩 주고 질문을 만들게 해서 만들었습니다. 검색의 recall@3이 0.95로 나왔습니다. 이 숫자를 그대로 믿어도 됩니까?

:::정답
그대로 믿기 어렵습니다. 문서를 보고 만든 질문은 문서의 낱말을 그대로 쓰는 경우가 많아, 현장에서 다른 낱말로 묻는 질문보다 검색이 쉽습니다. 답이 없는 질문도 들어 있지 않으므로 모른다고 답하는지도 측정되지 않습니다. 생성한 질문은 초안으로 쓰고, 현장의 말투로 고친 질문, 코드와 약어로 묻는 질문, 답이 없는 질문을 더한 뒤 사람이 정답 문서를 확인합니다.
:::

**2.** 질문 네 개에서 정답 문서의 순위가 1위, 4위, 2위, 찾지 못함이었습니다. recall@3과 MRR은 각각 얼마입니까? RAG가 상위 3건을 모델에 넣는다면 어느 지표가 답의 품질과 더 직접 관계가 있습니까?

:::정답
recall@3은 3위 안에 든 질문이 두 개(1위, 2위)이므로 0.5입니다. MRR은 (1 + 0.25 + 0.5 + 0) / 4 = 0.4375입니다. 상위 3건을 넣는다면 정답 문서가 3건 안에 드는지가 모델이 근거를 받는지를 정하므로 recall@3이 더 직접 관계가 있습니다. MRR은 근거가 프롬프트의 앞쪽에 오는지, top-k를 줄여도 되는지를 판단할 때 씁니다.
:::

**3.** 임베딩 검색의 유사도(0.84)와 BM25 점수(12.7)를 더해 하이브리드 검색을 만들었더니 결과가 키워드 검색과 거의 같았습니다. 왜 그렇습니까? RRF는 이 문제를 어떻게 피합니까?

:::정답
BM25 점수는 0부터 수십까지 퍼지고 유사도는 대부분 0.7~0.9 사이에 있으므로, 그대로 더하면 BM25 점수의 차이가 합계를 정합니다. RRF는 점수를 버리고 각 목록의 순위 r로 1/(60+r)을 계산해 더하므로, 두 검색의 점수 단위와 관계없이 두 목록이 같은 비중으로 합쳐집니다.
:::

**4.** 리랭킹을 넣었더니 recall@1은 올랐지만 질문 하나의 처리 시간이 몇 초 늘었습니다. 리랭킹이 느린 이유는 무엇이고, 모든 문서를 리랭킹하지 않는 이유는 무엇입니까?

:::정답
크로스 인코더는 질문과 문서를 이어 붙여 트랜스포머에 넣으므로, 문서의 벡터를 미리 계산해 둘 수 없고 질문마다 후보 수만큼 모델을 실행해야 합니다. 모든 문서를 리랭킹하면 문서 수만큼 실행해야 하므로, 바이 인코더나 키워드 검색으로 후보를 수십 개로 줄인 뒤 그 후보에만 씁니다. 그래서 후보에 정답이 없으면 리랭킹도 찾지 못합니다.
:::

**5.** "SSC는 몇 분 안에 끝내야 하나요?"를 질의 재작성으로 바꿨더니 검색 결과가 나빠졌습니다. 무엇이 원인일 수 있고, 어떻게 줄입니까?

:::정답
SSC는 사내 약어이므로 LLM이 뜻을 모르고, 다른 뜻의 말로 풀어 쓴 검색어를 만들었을 수 있습니다. 원래 질문의 검색 결과를 버리지 않고 재작성한 검색어의 결과와 RRF로 합치면 원래 질문으로 찾은 문서가 남습니다. 사내 약어집을 재작성 프롬프트에 넣는 방법도 있습니다.
:::

**6.** 답의 정답성은 맞았는데 충실도는 거짓으로 채점된 질문이 있습니다. 어떤 상황이고, 왜 고쳐야 합니까?

:::정답
검색 결과에는 근거가 없거나 부족했는데, 모델이 학습한 일반 지식이나 추측으로 답해 우연히 기준 답과 같았던 경우입니다. 이 질문에서는 맞았지만, 같은 프롬프트로는 사내 기준이 일반값과 다른 질문에서 틀린 답이 나옵니다. 근거 없음 규칙을 확인하고, 검색 결과에 근거가 없었다면 검색 쪽도 고칩니다.
:::

**7.** 평가 결과를 네 칸으로 나눴더니 "찾고 틀림"이 6건, "못 찾고 틀림"이 2건이었습니다. 리랭킹부터 넣는 것이 맞습니까?

:::정답
아닙니다. 리랭킹은 검색을 고치는 방법인데, 실패의 대부분은 정답 문서를 찾고도 답이 틀린 생성 실패입니다. 먼저 "찾고 틀림" 질문에서 답이 적힌 청크가 프롬프트에 들어 있었는지 확인합니다. 들어 있었다면 검색 결과와 답을 열어 구판의 값을 골랐는지, 근거 없음 규칙 때문에 답을 거부했는지, 충돌을 처리하지 못했는지 보고 프롬프트나 메타데이터를 고칩니다. 하나를 고친 뒤 같은 평가셋으로 다시 측정합니다.
:::

## 참고 문헌

- Cormack, G. V., Clarke, C. L. A. & Büttcher, S. (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. SIGIR 2009. (RRF 식과 k=60)
- sentence-transformers 문서: Retrieve & Re-Rank(바이 인코더와 크로스 인코더)(2026-11 확인).
- cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 모델 카드(mMARCO 학습 데이터, 사용법)(2026-11 확인).
- Gao, L. 외 (2022). Precise Zero-Shot Dense Retrieval without Relevance Labels. arXiv:2212.10496. (HyDE)
- Es, S. 외 (2023). Ragas: Automated Evaluation of Retrieval Augmented Generation. arXiv:2309.15217. (충실도)
- Zheng, L. 외 (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS 2023 Datasets and Benchmarks. arXiv:2306.05685.
