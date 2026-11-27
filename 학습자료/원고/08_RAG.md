# 8장 RAG

강의 2일차 파트 3, 3일차 파트 1~3에 해당합니다.

모델은 학습한 글에 없던 사내 기준값을 알지 못합니다. 이 장은 질문할 때마다 사내 문서를 검색해 그 내용을 입력에 넣어 주는 방법인 RAG(retrieval-augmented generation)를 설명합니다. 문서를 검색할 수 있게 준비하는 과정(파싱, 청킹, 메타데이터), 검색 결과를 넣는 프롬프트, 그리고 RAG가 오류 없이 틀린 답을 내는 경우를 차례로 다룹니다.

## 학습 목표

1. 모델이 사내 기준값을 답하지 못하는 이유와, RAG가 인덱싱, 검색, 생성의 세 단계로 이를 해결하는 구조를 설명할 수 있습니다.
2. PDF, HTML, 스캔 문서에서 글을 뽑을 때 생기는 문제(노이즈, 깨진 표, 글자 없는 쪽)를 설명할 수 있습니다.
3. 문서를 청크로 나누는 이유를 임베딩 모델의 최대 입력 길이와 평균 풀링으로 설명하고, 메타데이터로 검색 범위를 좁힐 수 있습니다.
4. 근거 없음 규칙과 출처 표기를 넣은 RAG 프롬프트를 작성하고, 구판이 섞였을 때 메타데이터가 답을 어떻게 바꾸는지 확인할 수 있습니다.
5. RAG가 틀린 답을 냈을 때 검색 실패인지 생성 실패인지 나누고, 어디를 고칠지 설명할 수 있습니다.

예제 8-1과 8-4는 API(application programming interface)로 LLM(large language model)을 호출하고, 예제 8-2와 8-3은 PC에서만 실행합니다. 임베딩 모델과 문서 코퍼스는 7장 "임베딩과 의미 검색"과 같습니다. 모델의 응답은 실행할 때마다 교재와 다를 수 있습니다.

## RAG의 구조

:::요점
RAG는 질문이 올 때마다 관련 문서를 검색해 입력에 넣고, 모델이 그 글을 근거로 답하게 하는 방식입니다. 문서를 검색할 수 있게 준비하는 인덱싱은 문서가 바뀔 때만 하고, 검색과 생성은 질문마다 합니다.
:::

모델은 [[지식 기준일]](knowledge cutoff)까지 학습한 글로 답합니다. 사내 문서는 학습한 글에 없으므로, "패키지 테스트에서 로트 수율이 몇 % 미만이면 홀드하나요?"라고 물으면 모델은 업계의 일반론을 말하거나, 확인할 수 없다고 답하거나, 그럴듯한 숫자를 지어냅니다([[환각]](hallucination), 2장). 답에 필요한 글을 입력에 넣어 주면, 모델은 1장의 다음 토큰 예측 그대로 입력에 있는 값을 이어 씁니다. 이처럼 입력에 넣은 글을 근거로 응답하게 하는 것을 [[그라운딩]](grounding)이라고 합니다.

문서 전체를 매번 넣지 않는 이유는 3장 "컨텍스트"의 비용과 같습니다. 이 교재의 코퍼스 120건만 해도 질문마다 수만 토큰의 입력이 되고, 사내 문서는 보통 이보다 수천 배 많습니다. 입력이 길면 요금과 대기 시간이 늘고, 긴 입력의 가운데에 놓인 정보는 모델이 덜 정확하게 씁니다(Liu 외, 2023). 그래서 질문에 필요한 부분만 찾아 넣습니다.

[[RAG]](retrieval-augmented generation)는 질문과 관련된 문서를 검색해 입력에 넣고 응답을 생성하는 방식입니다(Lewis 외, 2020). 세 단계로 나뉩니다.

<figure>
<svg viewBox="0 0 680 220" role="img" aria-label="RAG의 세 단계. 위 줄의 인덱싱은 문서가 바뀔 때만 합니다. 문서 120건을 파싱해 글을 뽑고, 절 단위 청크 487개로 나누고 메타데이터를 붙인 뒤, 임베딩해 벡터 인덱스에 저장합니다. 아래 줄은 질문마다 합니다. 질문으로 인덱스를 검색해 청크 4개를 고르고(검색), 청크와 질문을 RAG 프롬프트에 넣어 LLM이 출처를 붙인 답을 생성합니다(생성).">
<text x="10" y="20" fill="var(--ink)" font-size="12" font-weight="700">인덱싱: 문서가 바뀔 때만</text>
<rect x="10" y="30" width="120" height="48" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="70" y="51" text-anchor="middle" fill="var(--ink)" font-size="12">문서 120건</text><text x="70" y="68" text-anchor="middle" fill="var(--ink-soft)" font-size="11">MD, PDF, HTML</text>
<line x1="134" y1="54" x2="152" y2="54" stroke="var(--teal)" stroke-width="2"/><polygon points="152,49 160,54 152,59" fill="var(--teal)"/>
<rect x="164" y="30" width="110" height="48" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="219" y="51" text-anchor="middle" fill="var(--ink)" font-size="12">파싱</text><text x="219" y="68" text-anchor="middle" fill="var(--ink-soft)" font-size="11">본문 글 뽑기</text>
<line x1="278" y1="54" x2="296" y2="54" stroke="var(--teal)" stroke-width="2"/><polygon points="296,49 304,54 296,59" fill="var(--teal)"/>
<rect x="308" y="30" width="150" height="48" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="383" y="51" text-anchor="middle" fill="var(--ink)" font-size="12">청킹, 메타데이터</text><text x="383" y="68" text-anchor="middle" fill="var(--ink-soft)" font-size="11">절 단위 청크 487개</text>
<line x1="462" y1="54" x2="480" y2="54" stroke="var(--teal)" stroke-width="2"/><polygon points="480,49 488,54 480,59" fill="var(--teal)"/>
<rect x="492" y="30" width="178" height="48" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="581" y="51" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">벡터 인덱스</text><text x="581" y="68" text-anchor="middle" fill="var(--ink-soft)" font-size="11">임베딩 487 × 384, 메타데이터</text>
<line x1="581" y1="82" x2="581" y2="134" stroke="var(--line)" stroke-dasharray="4 3"/>
<text x="10" y="116" fill="var(--ink)" font-size="12" font-weight="700">질문마다: 검색과 생성</text>
<rect x="10" y="134" width="120" height="48" rx="6" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="70" y="163" text-anchor="middle" fill="var(--ink)" font-size="12">질문</text>
<line x1="134" y1="158" x2="152" y2="158" stroke="var(--teal)" stroke-width="2"/><polygon points="152,153 160,158 152,163" fill="var(--teal)"/>
<rect x="164" y="134" width="150" height="48" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="239" y="155" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">LLM</text><text x="239" y="172" text-anchor="middle" fill="var(--ink-soft)" font-size="11">RAG 프롬프트로 생성</text>
<line x1="318" y1="158" x2="336" y2="158" stroke="var(--teal)" stroke-width="2"/><polygon points="336,153 344,158 336,163" fill="var(--teal)"/>
<rect x="348" y="134" width="140" height="48" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="418" y="155" text-anchor="middle" fill="var(--ink)" font-size="12">답과 출처</text><text x="418" y="172" text-anchor="middle" fill="var(--ink-soft)" font-size="11">[SOP-PT-001#4]</text>
<rect x="510" y="134" width="160" height="48" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="590" y="155" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">검색</text><text x="590" y="172" text-anchor="middle" fill="var(--ink-soft)" font-size="11">상위 청크 4개</text>
<polyline points="70,186 70,204 590,204 590,186" fill="none" stroke="var(--amber)" stroke-width="1.5"/>
<polyline points="510,150 330,120 239,130" fill="none" stroke="var(--teal)" stroke-width="1.5" stroke-dasharray="5 3"/>
<text x="400" y="118" fill="var(--teal)" font-size="11">청크와 질문을 프롬프트에 넣음</text>
<text x="330" y="216" text-anchor="middle" fill="var(--amber)" font-size="11">질문으로 인덱스를 검색</text>
</svg>
<figcaption>인덱싱은 문서가 바뀔 때만 하고, 질문이 오면 검색한 청크를 프롬프트에 넣어 생성합니다.</figcaption>
</figure>

- **인덱싱**: 문서에서 글을 뽑고(파싱), 검색 단위로 자르고(청킹), 임베딩해 벡터 인덱스에 저장합니다. 이 장의 "문서 파싱", "청킹", "메타데이터" 절이 이 단계입니다.
- **검색**: 질문으로 인덱스를 검색해 상위 몇 건을 고릅니다. 검색 방법은 7장에서 다뤘습니다. 프롬프트에 넣을 검색 결과의 건수를 [[top-k]]라고 하고, 이 장의 예제는 4건을 넣습니다.
- **생성**: 검색 결과와 질문을 프롬프트에 넣어 모델이 답하게 합니다. 프롬프트는 "RAG 프롬프트" 절에서 설명합니다.

:::예제 8-1 검색 없이 묻기와 검색 결과를 넣어 묻기
사내 문서에만 답이 있는 평가 질문 두 개를 검색 없이 한 번, 유효한 문서에서 검색한 청크 4개를 넣어 한 번 보냅니다. 검색 없이 물었을 때 모델이 무엇이라고 답하는지, 검색 결과를 넣었을 때 정답 값과 출처가 나오는지 봅니다. 이 셀은 API를 4번 호출합니다.

```python
for qid in ['E06', 'E24']:
    question = questions[qid]['question']
    alone = llm.ask(question, model='소형', max_tokens=2000)              # 검색 없이 묻습니다
    hits = searcher.search(question, k=4, where=is_valid)                 # 유효한 문서의 청크 상위 4개
    grounded = llm.ask(rag_prompt(question, hits), model='소형', max_tokens=2000)
    print(f"{qid} {question} (정답: {questions[qid]['answer']})")
    print('  검색 없이:', alone.text.strip().replace('\n', ' ')[:180])
    print('  검색한 청크:', [hit['chunk_id'] for hit in hits])
    print(f'  검색 결과를 넣어(입력 {grounded.input_tokens:,}토큰):', grounded.text.strip().replace('\n', ' ')[:180])
```
:::

교재의 실행에서 검색 없이 물었을 때 모델은 두 질문 모두 값을 지어내지 않고, 회사마다 다르다거나 기록을 볼 수 없다고 답했습니다. 1장 "LLM은 어떻게 글을 만드는가"의 샘플링 때문에 다시 실행하면 그럴듯한 숫자가 나올 수도 있습니다. 검색 결과를 넣자 두 질문 모두 정답 값(97%, 11.5km)과 출처([SOP-PT-001#4], [QIR-2025-044#3])가 나왔습니다. 입력은 청크 4개와 지시를 합쳐 1,091토큰(E06)이었습니다.

## 문서 파싱

:::요점
문서 파일에서 본문 글을 뽑는 방법은 형식마다 다릅니다. HTML의 메뉴와 꼬리말, PDF의 쪽마다 반복되는 머리말처럼 본문이 아닌 줄을 빼야 하고, 글자를 그림으로 담은 스캔 PDF에서는 글이 하나도 나오지 않습니다.
:::

[[파싱]](parsing)은 파일을 해석해 프로그램이 다루는 글로 바꾸는 일입니다. 이 교재의 코퍼스는 Markdown 109건, PDF 6건, HTML 5건이고, `corpus.read_text()`가 형식마다 다른 방법으로 본문을 뽑습니다. PDF의 글자 층(text layer)은 글자를 문자 코드로 저장한 부분이고, 스캔 PDF는 쪽마다 그림만 저장해 글자 층이 없습니다.

| 형식 | 글을 뽑는 방법 | 생기는 문제 |
| --- | --- | --- |
| Markdown | 파일을 그대로 읽고, 맨 앞의 [[front matter]]는 본문에서 뺍니다 | 거의 없습니다 |
| HTML | 태그를 해석해 `<main>` 안의 글만 모읍니다. 표의 행은 칸을 이은 한 줄로 바꿉니다 | 메뉴, 경로 표시, 꼬리말이 모든 문서에 붙어 있습니다 |
| PDF | 쪽마다 글자 층(text layer)의 글을 뽑습니다(pypdf) | 쪽마다 머리말과 꼬리말이 반복되고, 표의 칸이 줄 단위로 흩어집니다 |
| 스캔 PDF | 글자 층이 없어 글이 나오지 않습니다 | OCR(optical character recognition)이 필요합니다 |

본문이 아닌데 문서마다 되풀이되는 줄을 [[노이즈]](noise)라고 합니다. 노이즈를 남기면 여러 문서의 청크에 같은 글이 들어가고, 7장의 평균 풀링 때문에 그 청크들의 벡터에 같은 글의 성분이 더해져 벡터끼리 비슷해집니다. 그러면 질문과 관련된 청크와 관련 없는 청크의 유사도 차이가 줄어듭니다.

PDF는 화면에 글자를 어디에 그릴지 적은 형식이고, 글의 순서나 표의 구조를 저장하지 않습니다. 그래서 표의 한 칸에 든 글이 여러 줄이면 다른 칸의 글과 섞여 뽑힐 수 있습니다. 표가 중요한 문서는 원본(DOCX, XLSX, HTML)이 있으면 원본에서 뽑는 편이 낫습니다. 스캔한 문서는 글자를 그림으로만 담고 있으므로 [[OCR]](optical character recognition)로 그림에서 글자를 인식해야 글을 얻습니다. 이 교재는 OCR을 다루지 않으므로 스캔 문서 EHS-010은 검색 대상에서 빠집니다.

:::예제 8-2 형식마다 다른 파싱
HTML 문서 하나와 PDF 문서 두 개(표가 든 매뉴얼, 스캔 문서)를 단순한 방법(HTML은 태그만 지우기, PDF는 모든 쪽의 글자 층)으로 뽑은 글과 `corpus.read_text()`가 뽑은 본문을 비교합니다. 글자 수가 얼마나 줄었는지, 본문에서 뺀 줄이 무엇인지, 스캔 문서에서 몇 글자가 나오는지 봅니다. API를 호출하지 않습니다.

```python
from pypdf import PdfReader

for doc_id in ['EDU-003', 'MAN-WB-001', 'EHS-010']:
    info = catalog[doc_id]
    path = f"{DATA}/corpus/{info['file']}"
    if info['format'] == 'html':
        raw = re.sub(r'<[^>]+>', '', open(path, encoding='utf-8').read())     # 태그만 지운 글
    else:
        raw = '\n'.join(page.extract_text() for page in PdfReader(path).pages)  # 모든 쪽의 글자 층
    body = corpus.read_text(doc_id)
    removed = [line.strip() for line in raw.splitlines() if line.strip() and line.strip() not in body]
    print(f"{doc_id}({info['format']}): 단순 추출 {len(raw.strip()):,}자, 본문 {len(body):,}자")
    print('  본문에서 뺀 줄:', removed[:4])
```
:::

교재의 실행에서 HTML 문서 EDU-003은 태그만 지운 글 896자가 본문 667자로 줄었습니다. 뺀 줄은 페이지 제목, CSS 스타일, 위키 메뉴, 경로 표시였습니다. PDF 문서 MAN-WB-001은 1,266자가 1,149자로 줄었고, 뺀 줄은 쪽마다 반복된 머리말("MAN-WB-001 개정 3 조립기술팀 사내 한정")과 꼬리말("1/2 출력본은 최신 개정본이 아닐 수 있습니다")이었습니다. 스캔 문서 EHS-010에서는 두 방법 모두 0자였습니다. 이 문서에만 답이 있는 평가 질문 두 개(E47, E48)는 이 시스템으로 답할 수 없습니다.

## 청킹

:::요점
문서를 통째로 벡터 하나로 만들면 512토큰을 넘는 뒷부분이 잘려 벡터에 반영되지 않고, 여러 주제가 평균되어 어느 질문과도 뚜렷하게 가깝지 않은 벡터가 됩니다. 그래서 문서를 절 단위의 청크로 나누고, 청크마다 문서 번호, 제목, 절 제목을 앞에 붙여 청크만 보고도 무엇에 관한 글인지 알 수 있게 합니다.
:::

[[청크]](chunk)는 문서를 검색 단위로 자른 조각이고, 문서를 청크로 자르는 일을 [[청킹]](chunking)이라고 합니다. 벡터 인덱스의 행 하나가 청크 하나입니다. 문서를 통째로 임베딩하지 않고 자르는 이유는 세 가지입니다.

- 임베딩 모델의 [[최대 입력 길이]](maximum sequence length)를 넘는 부분은 잘려서 벡터에 반영되지 않습니다. 이 교재의 코퍼스에서도 문서 10건이 512토큰을 넘습니다.
- 임베딩은 토큰 벡터의 평균입니다(7장). 512토큰 안에 들어가는 문서라도 절이 여럿이면 벡터는 그 절들의 평균입니다. 그래서 "마킹"만 묻는 질문과의 유사도는 마킹 절 하나로 만든 벡터보다 낮습니다.
- 모델에 넣는 글이 짧아집니다. 질문에 필요한 절만 넣으면 입력 토큰이 줄고, 관련 없는 내용이 섞이지 않습니다.

:::예제 8-3 512토큰 뒤의 내용은 벡터에 없다
가장 긴 문서 EDU-001(후공정 개요)의 토큰 수를 세고, 문서 전체로 만든 벡터와 앞부분만으로 만든 벡터를 비교합니다. 두 벡터의 유사도가 1.0이면 뒷부분은 벡터에 아무 영향을 주지 않은 것입니다. 뒷부분의 마킹 절을 묻는 질문이 문서 전체 벡터와 마킹 절 청크 가운데 어느 쪽에 더 가까운지도 봅니다. API를 호출하지 않습니다.

```python
text = corpus.read_text('EDU-001')
tokenizer = embed.load().tokenizer
cut = text.index('## 7.')                                         # 1~6절까지만 남긴 앞부분
print(f"EDU-001 전체 {len(tokenizer(text)['input_ids']):,}토큰, 1~6절 {len(tokenizer(text[:cut])['input_ids']):,}토큰"
      f"(최대 입력 길이 {embed.load().max_seq_length}토큰)")
whole, front = embed.passages([text, text[:cut]])
print(f'문서 전체 벡터와 1~6절 벡터의 유사도: {whole @ front:.4f}')
question = embed.query('패키지 윗면에 레이저로 무엇을 새기나요?')
marking = next(chunk for chunk in chunks if chunk['doc_id'] == 'EDU-001' and chunk['section'].startswith('9.'))
print(f"질문과 문서 전체 벡터: {whole @ question:.3f}, 질문과 마킹 절 청크: {embed.passages([marking['text']])[0] @ question:.3f}")
print('마킹 절 청크:', marking['text'][:80])
```
:::

교재의 실행에서 EDU-001은 1,285토큰이고, 마킹 절보다 훨씬 앞인 "6. 몰딩"까지만 해도 859토큰으로 최대 입력 길이 512토큰을 넘었습니다. 그래서 문서 전체로 만든 벡터와 "6. 몰딩"까지로 만든 벡터의 유사도가 1.0000으로, 두 벡터가 같았습니다. 512번째 토큰 뒤의 내용("4. 다이 어태치" 중간부터 문서 끝까지, 마킹 절 포함)은 이 벡터에 반영되지 않았다는 뜻입니다. 마킹을 묻는 질문과의 유사도는 문서 전체 벡터가 0.828, 마킹 절 청크가 0.878이었습니다. 마킹 내용이 실제로 벡터에 들어 있는 것은 청크 쪽뿐입니다.

### 청크를 나누는 기준

청크를 나누는 기준은 세 가지가 흔합니다.

- **글자 수**: 정해진 글자 수마다 자릅니다. 구현이 쉽지만 문장이나 표의 중간에서 잘립니다. 잘린 문장이 양쪽 청크에서 모두 뜻을 잃지 않게, 앞 청크의 끝부분을 다음 청크의 앞에도 넣는 [[중첩]](overlap)을 흔히 둡니다.
- **문장**: 문장 경계에서 자르고, 정해진 길이가 찰 때까지 문장을 모읍니다.
- **문서 구조**: 제목(Markdown의 `##`, HTML의 `<h2>`)마다 자릅니다. 절 하나가 주제 하나인 문서에서 청크 하나가 주제 하나가 됩니다.

이 교재의 `corpus.split_chunks()`는 문서 구조로 자르고, 절이 600자를 넘으면 줄 단위로 다시 나눕니다. 코퍼스 120건 가운데 글을 뽑은 119건이 청크 487개가 됩니다. 제목이 없는 PDF는 줄 단위로만 나뉩니다.

청크가 작을수록 검색은 정밀해지지만, 청크 하나만 봐서는 무엇에 관한 글인지 알 수 없습니다. 품질 이슈 보고서의 "원인" 절에는 "세정 후 9시간이 지나 본딩해"라는 내용만 있고 어느 보고서인지는 적혀 있지 않습니다. 그래서 청크마다 문서 번호, 문서 제목, 절 제목을 첫 줄에 붙입니다(`QIR-2026-014 W-07 NSOP 증가 > 원인`). 이 첫 줄도 임베딩에 들어가므로 "QIR-2026-014의 원인"을 묻는 질문과 이 청크가 가까워집니다(실습 8-1). 알맞은 청크 크기는 문서와 질문에 따라 다르므로, 후보 몇 가지를 평가 질문으로 측정해 고릅니다(9장).

## 메타데이터

:::요점
청크에 문서 번호, 상태, 개정, 날짜, 부서 같은 메타데이터를 붙여 두면 폐기된 구판을 검색 대상에서 빼거나, 모델에게 어느 문서가 최신인지 알려 줄 수 있습니다. 유사도는 내용이 비슷한지만 알려 주고, 그 문서가 지금 유효한지는 알려 주지 않습니다.
:::

[[메타데이터]](metadata)는 청크에 붙이는 문서 번호, 개정 번호, 상태(유효, 폐기), 유형, 날짜, 부서 같은 정보입니다. 메타데이터는 문서 목록(`corpus_목록.csv`)에 문서마다 한 행씩 있고(Markdown 문서는 front matter에도 같은 값이 있습니다), `split_chunks()`가 이 값을 청크마다 붙입니다. 쓰는 곳은 두 가지입니다.

- **검색 범위 좁히기**: 조건에 맞는 청크 안에서만 검색합니다. `searcher.search(question, where=is_valid)`는 상태가 "유효"인 청크만 검색합니다. 15장의 권한 필터도 같은 방식입니다.
- **프롬프트에 넣기**: 청크와 함께 개정 번호와 날짜를 넣어, 검색 결과끼리 값이 다를 때 모델이 최신 문서를 고를 수 있게 합니다. 사람이 원문을 찾아 확인할 수 있게 출처 번호도 붙입니다.

같은 문서의 구판과 신판은 대부분의 문장이 같으므로 유사도도 거의 같습니다. 이 코퍼스의 다섯 문서는 구판이 함께 남아 있고, 구판과 신판은 관리 기준값 하나만 다릅니다. 두 판이 모두 검색되어 구판의 값이 답에 섞이는 것을 [[버전 충돌]](version conflict)이라고 합니다. 유사도로는 이 둘을 구분할 수 없으므로 메타데이터로 구분합니다.

## RAG 프롬프트

:::요점
RAG 프롬프트에는 검색 결과만 근거로 답하라는 지시, 근거가 없으면 찾지 못했다고만 답하라는 규칙, 출처 번호를 적으라는 지시를 넣습니다. 검색 결과에는 청크 번호와 메타데이터를 함께 넣어, 모델이 출처를 적고 최신 문서를 고를 수 있게 합니다.
:::

이 장의 예제가 쓰는 프롬프트(`RAG_PROMPT`)는 다음과 같습니다. 4장 "프롬프트 설계"의 요소로 보면, 검색 결과가 모델이 읽을 입력이고, 첫 줄의 "검색 결과만 근거로"와 "-"로 시작하는 세 줄이 [[제약]](constraint)입니다.

```text
아래 [검색 결과]만 근거로 질문에 답하세요.
- 문장마다 근거가 된 청크의 번호를 [SOP-WB-001#3]처럼 적습니다.
- 검색 결과에 답이 없으면 "검색한 문서에서 찾지 못했습니다"라고만 답합니다.
- 검색 결과끼리 내용이 다르면 날짜가 늦은 문서를 따르고, 내용이 다르다는 것을 함께 적습니다.

[검색 결과]
[SOP-PT-001#4] (상태 유효, 개정 3, 2026-05-25)
SOP-PT-001 패키지 테스트 작업 표준 > 4. 수율 관리
- 로트 수율이 97% 미만이면 로트를 홀드하고 테스트기술팀과 품질보증팀에 알린다.
…

[질문]
패키지 테스트에서 로트 수율이 몇 % 미만이면 로트를 홀드하나요?
```

- **검색 결과만 근거로**: 이 지시가 없으면 모델은 검색 결과와 학습한 일반 지식을 섞어 답합니다. 사내 기준과 업계 일반값이 다르면 어느 쪽을 말한 것인지 알 수 없습니다.
- **[[근거 없음 규칙]]**: 검색은 답이 없는 질문에도 상위 청크를 돌려줍니다(7장). 이 규칙이 없으면 모델은 관련은 있지만 답은 아닌 청크(예: 제품 QX64의 금형 온도를 물었는데 다른 제품 QX48의 값으로 답함)로 답을 지어냅니다. 정해진 문구로 답하게 하면 코드가 그 문구를 찾아 "답 없음"으로 집계할 수 있습니다.
- **[[출처 표기]](citation)**: 답의 문장마다 근거가 된 청크 번호를 적게 합니다. 사람이 원문을 열어 확인할 수 있고, 코드는 적힌 번호가 실제로 검색한 청크인지 검사할 수 있습니다.
- **충돌 처리**: 검색 결과끼리 값이 다를 때 고르는 기준을 적습니다. 기준은 메타데이터의 날짜가 있어야 쓸 수 있습니다.

질문은 검색 결과 뒤, 프롬프트의 맨 끝에 둡니다. 긴 검색 결과를 읽은 뒤 바로 질문이 나오도록 하기 위해서입니다. 검색 결과를 많이 넣을수록 근거를 놓칠 가능성은 줄지만, 입력 토큰이 늘고 관련 없는 청크가 섞여 모델이 질문과 관계없는 청크의 값을 쓸 가능성이 커집니다. top-k도 청크 크기처럼 평가 질문으로 측정해 정합니다(9장).

:::예제 8-4 구판이 섞였을 때
구판이 따로 남아 있는 문서의 기준값을 묻는 질문 두 개(E28 컴파운드 해동 시간, E31 리드 코플래너리티)를 세 가지 방법으로 보냅니다. (가) 구판까지 검색하고 청크 글만 넣기, (나) 구판까지 검색하고 청크에 상태, 개정, 날짜를 붙여 넣기, (다) 유효한 문서만 검색하기. 응답에 신판의 값과 구판의 값 가운데 무엇이 나오는지 봅니다. 이 셀은 API를 6번 호출합니다.

```python
values = {'E28': ('6시간', '4시간'), 'E31': ('0.08mm', '0.10mm')}       # (신판의 값, 구판의 값)
for qid, (new, old) in values.items():
    question = questions[qid]['question']
    everything = searcher.search(question, k=4)                         # 구판도 검색 대상에 둡니다
    print(f'{qid} {question}\n  구판까지 검색한 청크: {[hit["chunk_id"] for hit in everything]}')
    for name, hits, with_meta in [('(가) 구판 포함, 메타데이터 없음', everything, False),
                                  ('(나) 구판 포함, 메타데이터 있음', everything, True),
                                  ('(다) 유효한 문서만 검색', searcher.search(question, k=4, where=is_valid), True)]:
        reply = llm.ask(rag_prompt(question, hits, with_meta), model='소형', max_tokens=2000)
        print(f'  {name}: 신판 값 {new in reply.text}, 구판 값 {old in reply.text}')
        print('    ', reply.text.strip().replace('\n', ' ')[:150])
```
:::

교재의 실행에서 (가)는 두 질문 모두 맞는 답을 내지 못했습니다. E28은 구판(`SOP-MD-002_R1`)의 4시간으로 답하고 신판의 6시간은 다른 문서의 값으로 덧붙였고, E31은 "0.10mm 또는 0.08mm"라고 답해 하나를 고르지 못했습니다. 청크 번호의 `_R1`, `_R3`만으로는 모델이 어느 쪽이 폐기된 문서인지 알 수 없습니다. (나)는 두 질문 모두 신판의 값을 답하고, 구판의 값은 폐기된 이전 개정의 값이라고 밝혔습니다. (다)는 구판이 검색되지 않으므로 신판의 값만 나왔습니다.

(나)와 (다)는 모두 맞았습니다. 다만 (나)는 프롬프트의 충돌 처리 기준을 모델이 따랐기 때문에 맞은 것이므로, 다른 질문이나 다음 실행에서는 따르지 않을 수 있습니다. (다)는 구판을 모델에 아예 보내지 않으므로 그 가능성이 없습니다. 폐기된 문서는 검색 대상에서 빼고, 유효한 문서끼리 값이 다를 때 모델이 최신 문서를 고를 수 있게 메타데이터를 함께 넣습니다.

## RAG가 틀리는 경우

:::요점
RAG가 틀릴 때는 오류 없이 그럴듯한 답을 냅니다. 틀린 답을 보면 먼저 검색 결과에 근거가 있었는지 확인하고, 없었으면 검색을, 있었으면 프롬프트나 메타데이터를 고칩니다.
:::

RAG의 답이 틀렸을 때 프롬프트부터 고치면 원인을 놓치기 쉽습니다. 모델은 넣어 준 글만 볼 수 있으므로, 검색 결과에 근거가 없으면 어떤 프롬프트로도 맞는 답을 낼 수 없습니다. 그래서 검색 결과를 먼저 확인합니다.

<figure>
<svg viewBox="0 0 680 238" role="img" aria-label="RAG의 답이 틀렸을 때 원인을 나누는 순서. 먼저 검색 결과에 답의 근거가 있었는지 봅니다. 없었으면 검색 실패이고, 원인은 문서에 답이 없음, 파싱 실패(스캔 문서), 청크에 맥락이 없음, 질문과 문서의 낱말 차이입니다. 있었으면 생성 실패이고, 원인은 구판의 값을 고름, 근거 밖의 내용을 덧붙임, 문서끼리 충돌을 처리하지 못함, 문서에 숨은 지시를 따름(15장)입니다. 검색 실패는 인덱싱과 검색을, 생성 실패는 프롬프트와 메타데이터를 고칩니다.">
<rect x="230" y="10" width="220" height="44" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="340" y="30" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">틀린 답</text><text x="340" y="46" text-anchor="middle" fill="var(--ink)" font-size="11">검색 결과에 답의 근거가 있었나?</text>
<polyline points="290,54 160,80" fill="none" stroke="var(--amber)" stroke-width="2"/><text x="150" y="66" fill="var(--amber)" font-size="11" font-weight="700">없었다</text>
<polyline points="390,54 520,80" fill="none" stroke="var(--teal)" stroke-width="2"/><text x="498" y="66" fill="var(--teal)" font-size="11" font-weight="700">있었다</text>
<rect x="10" y="82" width="320" height="120" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="170" y="102" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">검색 실패</text>
<text x="24" y="124" fill="var(--ink)" font-size="11">문서에 답이 없음 → 근거 없음 규칙으로 답 없음</text><text x="24" y="144" fill="var(--ink)" font-size="11">파싱 실패(스캔 문서, 깨진 표) → 파서, OCR</text><text x="24" y="164" fill="var(--ink)" font-size="11">청크에 맥락이 없음 → 제목을 붙인 청크</text><text x="24" y="184" fill="var(--ink)" font-size="11">질문과 문서의 낱말 차이 → 검색 방법(9장)</text>
<rect x="350" y="82" width="320" height="120" rx="8" fill="var(--sheet)" stroke="var(--teal)"/><text x="510" y="102" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">생성 실패</text>
<text x="364" y="124" fill="var(--ink)" font-size="11">구판의 값을 고름 → 메타데이터 필터</text><text x="364" y="144" fill="var(--ink)" font-size="11">근거 밖의 내용을 덧붙임 → 검색 결과만 근거로</text><text x="364" y="164" fill="var(--ink)" font-size="11">문서끼리 충돌 → 날짜와 기준, 두 값을 함께</text><text x="364" y="184" fill="var(--ink)" font-size="11">문서에 숨은 지시를 따름 → 15장</text>
<text x="340" y="226" text-anchor="middle" fill="var(--ink-soft)" font-size="12">왼쪽은 인덱싱과 검색을, 오른쪽은 프롬프트와 메타데이터를 고칩니다</text>
</svg>
<figcaption>틀린 답은 검색 결과에 근거가 있었는지로 먼저 나누고, 그에 따라 고칠 단계를 정합니다.</figcaption>
</figure>

생성 실패 가운데 문서끼리의 충돌은 메타데이터 필터로 풀리지 않습니다. 이 코퍼스에서 작업 표준 SOP-MD-001은 QX48의 트랜스퍼 시간을 12초로 정하고 있고, 그보다 나중의 회의록 MTG-20261116은 11월 23일부터 14초로 바꾸기로 결정했습니다. 두 문서는 모두 유효합니다. 표준 문서가 아직 개정되지 않았을 뿐이므로, 어느 값이 맞는지는 문서 관리 규칙(회의 결정이 표준 개정 전에 효력이 있는지)에 달려 있습니다. 날짜 기준을 프롬프트에 적으면 모델은 늦은 문서의 값을 고르지만(실습 P3의 E41), 그 값이 맞는지는 문서 관리 규칙이 정합니다. RAG가 할 수 있는 일은 두 값을 함께 보여 주고 다르다는 것을 알리는 것입니다.

문서 안에 모델에게 보내는 지시문이 숨어 있으면, 그 문서가 검색될 때 지시문도 함께 입력에 들어갑니다. 이 코퍼스에도 그런 문서가 네 건 있습니다. 이 문제는 15장 "보안과 거버넌스"에서 다룹니다.

## 개념 확인 실습

실습은 장 노트북의 빈칸을 채워 실행합니다. 코드를 실행하기 전에 결과를 먼저 예측해 적고, 실행한 뒤 예측과 다른 부분을 이 장의 원리로 설명해 봅니다.

:::실습 8-1 청크에 제목이 없으면
품질 이슈 보고서 18건의 청크만 모아, 청크 첫 줄(문서 번호, 제목, 절 제목)이 있을 때와 뺐을 때 각각 벡터 인덱스를 만듭니다. 질문 "QIR-2026-014의 원인은 무엇이었나요?"로 검색했을 때 QIR-2026-014의 "원인" 절 청크가 몇 위에 오는지 두 경우 모두 먼저 `my_guess`에 적고, `bare`에 첫 줄을 뺀 청크 글의 목록을 만든 뒤 실행합니다. 두 순위의 차이를 청크 글에 무엇이 들어 있는지로 설명하면 끝납니다. API를 호출하지 않습니다.

```python
qir = [chunk for chunk in chunks if chunk['type'] == '품질 이슈 보고서']
target = next(index for index, chunk in enumerate(qir) if chunk['doc_id'] == 'QIR-2026-014' and chunk['section'] == '원인')
bare = []  # TODO: qir의 청크마다 첫 줄(문서 번호, 제목, 절 제목)을 뺀 글
my_guess = {'제목 있음': None, '제목 없음': None}  # TODO: 원인 절 청크의 순위

question = 'QIR-2026-014의 원인은 무엇이었나요?'
for name, texts in [('제목 있음', [chunk['text'] for chunk in qir]), ('제목 없음', bare)]:
    scores = corpus.VectorIndex(texts).scores(question)
    print(f'{name}: 원인 절 청크 {list(np.argsort(-scores)).index(target) + 1}위(청크 {len(texts)}개 중), 예측 {my_guess[name]}')
print('제목 없는 원인 절 청크:', bare[target] if bare else '')
```

:::풀이
청크 글의 첫 줄이 제목이므로, 첫 줄바꿈 뒤의 글만 남깁니다.

```python
qir = [chunk for chunk in chunks if chunk['type'] == '품질 이슈 보고서']
target = next(index for index, chunk in enumerate(qir) if chunk['doc_id'] == 'QIR-2026-014' and chunk['section'] == '원인')
bare = [chunk['text'].split('\n', 1)[1] for chunk in qir]
my_guess = {'제목 있음': 1, '제목 없음': 20}

question = 'QIR-2026-014의 원인은 무엇이었나요?'
for name, texts in [('제목 있음', [chunk['text'] for chunk in qir]), ('제목 없음', bare)]:
    scores = corpus.VectorIndex(texts).scores(question)
    print(f'{name}: 원인 절 청크 {list(np.argsort(-scores)).index(target) + 1}위(청크 {len(texts)}개 중), 예측 {my_guess[name]}')
print('제목 없는 원인 절 청크:', bare[target] if bare else '')
```

교재의 실행에서 원인 절 청크는 제목이 있을 때 87개 가운데 6위, 제목을 뺐을 때 73위였습니다. 제목을 뺀 청크에는 "리드 프레임을 플라즈마 세정한 뒤 9시간이 지나 본딩했다"는 내용만 있고 "QIR-2026-014"도 "원인"도 없으므로, 질문과 가까울 근거가 없습니다. 제목이 있어도 1위가 아니었던 것은 QIR-2026-014의 다른 절(현상, 개요, 조치)도 같은 문서 번호로 시작하고, 다른 보고서의 원인 절도 "> 원인"으로 끝나는 첫 줄을 갖기 때문입니다. 상위 청크들의 유사도는 0.86 안팎으로 거의 같아, 절 제목 한 낱말의 차이로는 순위가 정해지지 않았습니다. 리랭킹이 이런 차이를 구분하는 데 낫습니다(9장).
:::
:::

## 관통 프로젝트 3단계

2단계까지의 도우미는 사내 문서를 몰라 "확인할 수 없다"고 답했습니다. 3단계에서는 질문마다 사내 문서를 검색해 검색 결과를 근거로 답하고, 답에 적힌 출처를 검사합니다. 2단계의 `needs_document`가 참인 문의에만 이 함수를 쓰면 검색이 필요 없는 문의의 입력 토큰을 아낄 수 있습니다.

:::실습 P3 문서를 검색해 근거를 붙여 답하기
`answer_with_documents(question, k)`를 작성합니다. 유효한 문서에서 청크 k개를 검색하고(`searcher.search`, `is_valid`), `rag_prompt()`로 만든 프롬프트를 1단계의 `answer()`로 보냅니다. 결과 dict에 검색한 청크 번호(`hits`)와 답에 적힌 출처 번호(`sources`)를 더합니다. 상태가 "완료"인 답 가운데, 찾지 못했다는 답이 아닌데 출처가 하나도 없거나, 검색하지 않은 청크 번호를 출처로 적었으면 "확인 필요"로 바꾸고 사유를 적습니다. 평가 질문 5개의 상태, 답, 출처가 출력되면 끝납니다. 이 셀은 API를 5번 호출합니다.

완료 기준

- 질문 5개의 상태, 답 앞부분, 검색한 청크, 출처가 출력됩니다.
- 답이 없는 질문(E55)은 찾지 못했다는 답이 나오고 "확인 필요"가 되지 않습니다.

:::힌트
답에서 출처 번호는 `re.findall(r'[A-Z]+-[\w-]+#\d+', text)`로 찾을 수 있습니다. 1단계의 `answer()`는 결과의 `question`에 보낸 글(여기서는 프롬프트 전체)을 넣으므로, 질문으로 다시 바꿔 둡니다.
:::

```python
def answer_with_documents(question, k=4):
    """사내 문서를 검색해 근거를 붙여 답합니다. 1단계 answer()의 결과에 hits와 sources를 더합니다"""
    return {'question': question, 'status': '실패', 'answer': '', 'hits': [], 'sources': [], 'reason': '작성하지 않음'}  # TODO


for qid in ['E06', 'E24', 'E28', 'E41', 'E55']:
    result = answer_with_documents(questions[qid]['question'])
    print(f"[{result['status']}] {qid} {result['question']} (정답: {questions[qid]['answer']})")
    print(f"  → {result['answer'].strip().replace(chr(10), ' ')[:160]}")
    print(f"  검색 {result['hits']}, 출처 {result['sources']}, 사유 {result['reason']}")
```

:::풀이
검색, 프롬프트, 1단계의 `answer()`를 차례로 부르고, 답에 적힌 출처를 검색한 청크와 비교합니다.

```python
def answer_with_documents(question, k=4):
    """사내 문서를 검색해 근거를 붙여 답합니다. 1단계 answer()의 결과에 hits와 sources를 더합니다"""
    hits = searcher.search(question, k=k, where=is_valid)
    result = answer(rag_prompt(question, hits))
    result['question'] = question
    result['hits'] = [hit['chunk_id'] for hit in hits]
    result['sources'] = sorted(set(re.findall(r'[A-Z]+-[\w-]+#\d+', result['answer'])))
    if result['status'] == '완료' and '찾지 못했습니다' not in result['answer']:
        if not result['sources']:
            result['status'], result['reason'] = '확인 필요', '출처 없음'
        elif set(result['sources']) - set(result['hits']):
            result['status'], result['reason'] = '확인 필요', '검색하지 않은 출처'
    return result


for qid in ['E06', 'E24', 'E28', 'E41', 'E55']:
    result = answer_with_documents(questions[qid]['question'])
    print(f"[{result['status']}] {qid} {result['question']} (정답: {questions[qid]['answer']})")
    print(f"  → {result['answer'].strip().replace(chr(10), ' ')[:160]}")
    print(f"  검색 {result['hits']}, 출처 {result['sources']}, 사유 {result['reason']}")
```

교재의 실행에서 다섯 질문 모두 "완료"였습니다. E06, E24, E28은 정답 값을 출처와 함께 답했고, E28은 유효한 문서만 검색했으므로 구판의 4시간이 나오지 않았습니다. 문서끼리 충돌하는 E41은 최근 회의록의 14초를 답하고, 이전 문서의 12초와 다르다는 것을 함께 적었습니다. 답이 없는 E55는 찾지 못했다고 답했지만, "라고만 답한다"는 규칙과 달리 관련 문서의 175℃를 참고로 덧붙였습니다. 근거 없음 규칙도 지시이므로 모델이 늘 그대로 따르지는 않습니다. 출력의 사유 "end"는 1단계의 `answer()`가 종료 이유를 사유에 넣었기 때문입니다. 정확한 값을 답했는지는 이 출력만으로는 알 수 없으므로, 4단계(9장)에서 평가셋으로 측정합니다.
:::
:::

## 자가점검

**1.** 사내 기준값을 묻는 질문에 모델이 검색 없이 그럴듯한 숫자를 답했습니다. 왜 그렇습니까? RAG는 이것을 어떤 원리로 해결합니까?

:::정답
모델은 학습한 글의 패턴으로 다음 토큰을 이어 쓰는데, 사내 문서는 학습한 글에 없으므로 일반론이나 그럴듯한 숫자를 생성합니다. RAG는 질문할 때마다 관련 문서를 검색해 입력에 넣습니다. 입력에 든 값은 다음 토큰으로 이어 쓸 확률이 높으므로 모델이 그 값을 근거로 답합니다. 모델을 다시 학습시키지 않고 문서만 바꿔 최신 정보를 반영할 수 있습니다.
:::

**2.** PDF로 된 작업 표준을 검색 대상에 넣었더니 모든 청크에 "출력본은 최신 개정본이 아닐 수 있습니다"라는 줄이 들어갔습니다. 검색에 어떤 문제가 생깁니까? 스캔한 PDF는 어떤 문제가 있습니까?

:::정답
같은 줄이 모든 청크에 들어가면 평균 풀링으로 모든 청크의 벡터에 그 줄의 성분이 더해져, 관련 있는 청크와 관련 없는 청크의 유사도 차이가 줄어듭니다. 파싱할 때 이런 노이즈를 뺍니다. 스캔한 PDF는 글자 층이 없어 글이 나오지 않으므로, OCR을 거치지 않으면 그 문서는 검색되지 않고 질문에 답할 수 없습니다.
:::

**3.** 2,000토큰짜리 설비 매뉴얼을 통째로 임베딩해 인덱스에 넣었습니다. 매뉴얼 끝부분의 알람 코드표를 묻는 질문이 이 매뉴얼을 잘 찾지 못합니다. 두 가지 원인을 들고, 어떻게 고칩니까?

:::정답
첫째, 임베딩 모델의 최대 입력 길이(512토큰)를 넘는 뒷부분은 잘려 벡터에 반영되지 않으므로 알람 코드표가 벡터에 없습니다. 둘째, 문서 전체의 벡터는 여러 절의 평균이라 특정 절을 묻는 질문과의 유사도가 낮습니다. 문서를 절 단위의 청크로 나누고, 청크마다 문서 번호와 제목, 절 제목을 붙여 임베딩합니다.
:::

**4.** 와이어 풀 강도 하한을 물었더니 RAG가 "5.0gf 또는 6.0gf입니다"라고 답했습니다. 검색 결과를 열어 보니 구판과 신판의 청크가 모두 있었습니다. 어떻게 고칩니까?

:::정답
버전 충돌입니다. 유사도로는 구판과 신판을 구분할 수 없으므로 메타데이터를 씁니다. 상태가 폐기인 청크를 검색 대상에서 빼고(메타데이터 필터), 프롬프트의 검색 결과에도 개정 번호와 날짜를 붙여 모델이 최신 문서를 고를 수 있게 합니다. 구판을 남겨야 하는 경우라도 필터로 기본 검색에서는 뺍니다.
:::

**5.** RAG 프롬프트에 근거 없음 규칙이 없으면 문서에 답이 없는 질문에 어떤 답이 나올 수 있습니까? 이 규칙의 문구를 정해진 문장으로 두면 무엇이 좋습니까?

:::정답
검색은 답이 없는 질문에도 상위 청크를 돌려주므로, 모델은 관련은 있지만 답이 아닌 청크(다른 제품의 값 등)나 학습한 일반 지식으로 답을 지어낼 수 있습니다. 정해진 문장으로 답하게 하면 코드가 그 문장을 찾아 "답 없음"으로 집계하거나 사람에게 넘길 수 있습니다.
:::

**6.** RAG의 답이 틀렸습니다. 프롬프트를 고치기 전에 무엇을 먼저 확인합니까? 그 결과에 따라 고칠 곳이 어떻게 나뉩니까?

:::정답
검색 결과에 답의 근거가 되는 청크가 있었는지 먼저 확인합니다. 없었으면 검색 실패이므로 문서에 답이 있는지, 파싱과 청킹이 제대로 되었는지, 검색 방법이 질문 유형에 맞는지를 고칩니다. 있었으면 생성 실패이므로 메타데이터 필터, 근거 없음 규칙, 충돌 처리 기준 같은 프롬프트와 메타데이터를 고칩니다.
:::

## 참고 문헌

- Lewis, P. 외 (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020. arXiv:2005.11401.
- Liu, N. F. 외 (2023). Lost in the Middle: How Language Models Use Long Contexts. TACL. arXiv:2307.03172.
- intfloat/multilingual-e5-small 모델 카드: 512토큰을 넘는 입력은 잘린다(2026-11 확인).
- pypdf 문서: PDF의 글자 층에서 글을 뽑는 방법과 한계(2026-11 확인).
