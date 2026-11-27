# 파트 1. LLM API 기초

채팅 화면에서는 문의를 한 건씩 붙여 넣고 응답을 눈으로 읽었습니다. 같은 일을 100건, 1,000건에 하려면 코드로 모델을 호출해야 합니다. 이 파트에서는 한 건을 호출하는 방법부터 시작해, 실패가 섞여도 끝까지 처리하는 [[배치 처리]] 코드까지 만듭니다.

이 파트를 마치면 다음을 할 수 있습니다.

1. LLM API 호출의 요청과 응답이 어떤 값으로 이루어지는지 설명하고, 코드로 직접 호출해 응답, 토큰 수, 종료 이유를 읽습니다.
2. API 서버가 대화를 기억하지 않는다는 점을 설명하고, 대화 이력을 코드로 관리하며 이력이 비용에 주는 영향을 숫자로 말합니다.
3. 토큰과 단가로 요금을 계산하고, 대량 작업을 보내기 전에 비용을 추정합니다.
4. 정답을 아는 표본으로 정확도, 시간, 요금을 측정하고, 그 결과를 근거로 모델 등급을 고릅니다.
5. 실패를 "재시도할 것", "바로 멈출 것", "오류 없이 왔지만 쓸 수 없는 것"으로 나누고 각각을 코드로 처리합니다.
6. 한 건을 처리하는 코드를 입력 검사, 재시도, 응답 검사, 실패 목록을 갖춘 배치 처리 코드로 확장합니다.

예제의 실행 결과는 Claude 모델로 학습 노트북을 실행한 출력을 그대로 실었습니다(2026-11-26 실행). 모델의 응답과 토큰 수는 실행할 때마다, 그리고 모델마다 조금씩 다릅니다.

## 이 파트에서 다루는 과제 {추가}

:::요점
반도체 공장의 현장 문의 100건을 다섯 가지로 분류하는 일을 예로 씁니다. 한 건을 호출하는 코드에서 시작해 100건을 끝까지 처리하는 코드로 넓혀 갑니다.
:::

이 파트의 예제는 과제 하나를 따라갑니다. 현장에서 들어온 문의를 읽고 종류를 분류하는 일입니다. 재료는 문의 목록(`문의_예제.csv`) 100건입니다. 문의 한 건이 한 행이고, 열은 `id`와 `문의내용` 두 개입니다.

| id | 문의내용 |
| --- | --- |
| Q001 | 3호기 PM 주기 문서는 어디에서 볼 수 있나요 |
| Q002 | 1호기 로드락 도어 인터록 알람이 세 번 연속 발생했습니다 |
| Q003 | 에치 장비별 시즈닝 런 소요 시간 평균을 알려 주세요 |

모델에는 문의 한 건과 분류 규칙을 함께 보냅니다. 모델은 다섯 가지 분류(문서안내, 절차안내, 데이터요청, 긴급, 기타) 가운데 하나와 긴급 여부를 JSON 한 줄로 응답합니다. Q002를 보냈을 때 받은 응답은 다음과 같습니다.

```
{"id": "Q002", "category": "긴급", "urgent": true}
```

[[JSON]]은 이름과 값의 쌍을 중괄호 안에 적는 텍스트 형식입니다. 프로그램이 읽기 쉬워서, 모델의 응답에서 값을 꺼내 저장하거나 조건문에 쓸 때 많이 씁니다.

문의 목록에는 실제 업무 데이터처럼 처리하기 까다로운 건을 섞어 두었습니다. 빈 문의가 2건, 250자가 넘는 긴 문의가 3건, 어느 분류인지 판단하기 어려운 문의가 12건 있습니다. 이 12건처럼 일반적인 경우에서 벗어나 판단하기 어려운 입력을 [[엣지 케이스]](edge case)라고 합니다.

빈 문의를 뺀 98건에는 사람이 정한 정답(`문의_예제_정답.csv`)이 있어, 모델의 분류가 맞았는지 확인할 수 있습니다. 사람이 미리 정해 둔 이 정답을 [[정답 라벨]]이라고 합니다. 정답 파일의 `난이도` 열에는 엣지 케이스 12건이 `엣지`, 나머지 86건이 `보통`으로 적혀 있습니다. 문의와 정답은 모두 지어낸 가상 데이터입니다.

이 파트는 다음 순서로 진행합니다.

1. 문의 한 건을 API로 호출하고 응답을 읽습니다. 앞쪽 절은 호출 자체를 설명하므로, 분류 대신 짧은 질문을 예로 쓰기도 합니다.
2. 100건을 보내면 요금이 얼마나 드는지 계산하고, 어느 모델 등급을 쓸지 정답으로 측정해 고릅니다.
3. 호출이 실패하는 경우와, 오류 없이 왔지만 쓸 수 없는 응답을 다룹니다.
4. 1~3에서 만든 코드를 합쳐 배치 처리 코드를 만듭니다. 이 코드는 성공한 분류 결과의 목록, 실패한 건의 목록, 실제 요금을 내놓습니다.

## LLM API란 {원본 p.12, 30}

:::요점
코드에서 모델을 쓰려면 LLM API에 요청을 보내고 응답을 받습니다. 요청을 만들고 응답을 읽는 일은 SDK가 도와줍니다.
:::

[[LLM]]은 주어진 글 다음에 올 내용을 예측하는 방식으로 글을 생성하는 모델입니다. [[API]]는 프로그램이 다른 프로그램의 기능을 정해진 형식으로 요청하고 결과를 받는 인터페이스입니다. 따라서 LLM API는 프로그램이 LLM에 글을 보내고 생성된 글을 돌려받는 인터페이스입니다.

채팅 화면도 내부에서는 같은 방식의 API를 씁니다. 채팅 화면은 여러분이 입력한 글을 [[요청]]으로 만들어 서버에 보내고, 돌아온 [[응답]]을 화면에 표시합니다. 코드로 호출한다는 것은 이 일을 직접 한다는 뜻입니다.

<figure>
<svg viewBox="0 0 680 150" role="img" aria-label="내 코드가 요청을 보내고 API 서버가 응답을 돌려주는 그림">
<rect x="10" y="35" width="170" height="80" rx="8" fill="var(--sheet)" stroke="var(--line)"/>
<text x="95" y="70" text-anchor="middle" fill="var(--ink)" font-weight="700">내 코드</text>
<text x="95" y="93" text-anchor="middle" fill="var(--ink-soft)" font-size="13">SDK가 요청을 조립</text>
<rect x="500" y="35" width="170" height="80" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="585" y="70" text-anchor="middle" fill="var(--ink)" font-weight="700">LLM API 서버</text>
<text x="585" y="93" text-anchor="middle" fill="var(--ink-soft)" font-size="13">모델이 응답을 생성</text>
<line x1="185" y1="58" x2="490" y2="58" stroke="var(--teal)" stroke-width="2"/>
<polygon points="490,58 478,52 478,64" fill="var(--teal)"/>
<text x="338" y="48" text-anchor="middle" fill="var(--ink)" font-size="13">요청: 키, 모델 이름, 최대 출력 토큰, 메시지 목록</text>
<line x1="495" y1="98" x2="190" y2="98" stroke="var(--ink-soft)" stroke-width="2"/>
<polygon points="190,98 202,92 202,104" fill="var(--ink-soft)"/>
<text x="338" y="120" text-anchor="middle" fill="var(--ink)" font-size="13">응답: 응답 텍스트, 토큰 수, 종료 이유</text>
</svg>
<figcaption>요청 하나에 응답 하나가 돌아옵니다. 서버는 응답을 보낸 뒤 그 요청의 내용을 기억하지 않습니다.</figcaption>
</figure>

요청과 응답은 웹 브라우저가 서버와 통신할 때 쓰는 것과 같은 HTTP 형식으로 주고받습니다. 이것을 직접 조립하는 대신 [[SDK]]를 씁니다. SDK는 요청을 조립하고, 응답을 파이썬 객체로 바꾸고, 실패를 파이썬의 예외로 바꿔 주는 라이브러리입니다. 예외는 실행 중에 생긴 오류를 알리는 장치이고 `try`와 `except`로 처리합니다. 이 교재에서는 두 가지 SDK를 다룹니다.

- `anthropic` SDK는 Anthropic API로 Claude 모델을 호출할 때 씁니다.
- `openai` SDK는 OpenAI 형식을 따르는 API를 호출할 때 씁니다. 사내 LLM API가 이 형식(OpenAI 호환)입니다.

두 SDK는 값의 이름과 위치가 조금 다를 뿐 개념은 같습니다. 이 파트에서는 차이가 있는 곳마다 둘을 나란히 보여 줍니다.

## 첫 호출 {원본 p.34-40}

:::요점
요청에는 모델 이름, 최대 출력 토큰, 메시지 목록을 넣습니다. 응답에서는 응답 텍스트, 토큰 수, 종료 이유를 읽습니다.
:::

호출할 때마다 넣는 값은 세 가지입니다. Anthropic API는 세 값이 모두 필수입니다. OpenAI 호환 API에서는 최대 출력 토큰을 생략할 수 있지만, 이 교재에서는 항상 정합니다.

OpenAI 공식 API는 최대 출력 토큰의 이름으로 `max_tokens` 대신 `max_completion_tokens`를 쓰도록 권장하고, reasoning 모델(o 시리즈)은 `max_tokens`를 받지 않습니다(openai SDK 3.16.2의 설명, 2026-11-26 확인). 이 교재의 코드는 `max_tokens`로 보냅니다. 사내 API가 어느 이름을 받는지는 사내 API 문서에서 확인합니다.

| 값 | 뜻 |
| --- | --- |
| 모델 이름 | 어느 모델에 보낼지 |
| [[최대 출력 토큰]] | 모델이 한 번에 생성할 수 있는 토큰 수의 상한 |
| [[메시지]] 목록 | 대화 내용. 각 메시지는 [[역할]](`role`)과 내용(`content`)으로 이루어집니다 |

역할은 말한 쪽을 나타냅니다. 사람이 한 말은 `user`, 모델이 한 말은 `assistant`입니다. 첫 호출에서는 `user` 메시지 하나만 보냅니다.

토큰은 모델이 글을 읽고 쓰는 단위입니다. 다음 절 "토큰과 컨텍스트 윈도우"에서 설명합니다.

Anthropic의 응답(`response.content`)은 블록의 목록입니다. 블록은 응답을 종류별로 나눈 조각이고, 종류는 `type`으로 구분합니다. 응답 텍스트는 `type`이 `text`인 블록에 있습니다. 그래서 아래 예제는 `text` 블록만 골라 이어 붙입니다.

:::예제 1-1 첫 호출과 응답 읽기
:::탭 Anthropic
```python
# 예제 1-1 (Anthropic SDK로 직접 호출)
question = '3호기 로드락 도어 인터록 알람이 세 번 발생했습니다. 이 문의를 한 문장으로 요약해 주세요.'

if llm.provider() == 'anthropic':
    import anthropic

    client = anthropic.Anthropic()            # 환경 변수 ANTHROPIC_API_KEY를 읽습니다
    response = client.messages.create(
        model=llm.model_name('기본'),
        max_tokens=1024,                      # 최대 출력 토큰
        messages=[{'role': 'user', 'content': question}],
    )
    print('블록 종류:', [block.type for block in response.content])
    print('응답:', ''.join(block.text for block in response.content if block.type == 'text'))
    print('입력 토큰:', response.usage.input_tokens)
    print('출력 토큰:', response.usage.output_tokens)
    print('종료 이유:', response.stop_reason)
    print('답한 모델:', response.model)
else:
    print('Anthropic을 쓰지 않으므로 건너뜁니다.')
```
:::
:::탭 OpenAI 호환
```python
# 예제 1-1 (OpenAI 호환 SDK로 직접 호출)
if llm.provider() == 'openai':
    from openai import OpenAI

    client = OpenAI(base_url=os.environ['OPENAI_BASE_URL'], api_key=os.environ['OPENAI_API_KEY'])
    response = client.chat.completions.create(
        model=llm.model_name('기본'),
        max_tokens=1024,                      # 최대 출력 토큰
        messages=[{'role': 'user', 'content': question}],
    )
    choice = response.choices[0]
    print('응답:', choice.message.content)
    print('입력 토큰:', response.usage.prompt_tokens)
    print('출력 토큰:', response.usage.completion_tokens)
    print('종료 이유:', choice.finish_reason)
    print('답한 모델:', response.model)
else:
    print('OpenAI 호환 API를 쓰지 않으므로 건너뜁니다.')
```
:::

`question`이 호출에 쓸 문의입니다. 위의 두 코드 가운데 지금 쓰는 API에 해당하는 쪽만 실행됩니다. `llm.provider()`가 환경 변수를 읽어 어느 API를 쓰는지 알려 주기 때문입니다. `llm.model_name('기본')`은 "기본" 등급에 연결된 실제 모델 이름을 돌려줍니다. 이 교재는 모델을 소형, 기본, 대형 세 등급으로 부릅니다. 등급을 고르는 방법은 "모델 고르기" 절에서 다룹니다.

같은 호출을 `llm.send()`로 하면 다음과 같습니다. `llm.send()`는 두 SDK의 차이를 감춘 함수이고, 이후 예제에서 계속 씁니다. `model` 인자를 주지 않으면 기본 등급 모델로 보냅니다.

```python
# 예제 1-1 (llm.send로 같은 호출)
reply = llm.send([{'role': 'user', 'content': question}])
print('응답:', reply.text)
print(f'입력 토큰: {reply.input_tokens}, 출력 토큰: {reply.output_tokens}')
print(f'종료 이유: {reply.stop_reason}, 모델: {reply.model}, {reply.seconds:.1f}초')
```
:::

응답에는 응답 텍스트만 들어 있지 않습니다. 코드에서 매번 확인할 값은 세 가지입니다.

| 확인할 값 | Anthropic | OpenAI 호환 | 왜 보는가 |
| --- | --- | --- | --- |
| 응답 텍스트 | `response.content` 중 `text` 블록 | `response.choices[0].message.content` | 다음 코드에 넘길 결과입니다 |
| 토큰 수 | `response.usage.input_tokens`, `output_tokens` | `response.usage.prompt_tokens`, `completion_tokens` | 요금과 길이 제한의 기준입니다 |
| [[종료 이유]] | `response.stop_reason` | `response.choices[0].finish_reason` | 응답이 끝까지 쓰였는지 알려 줍니다 |

위 결과의 "블록 종류"를 보면 `thinking` 블록이 `text` 블록 앞에 왔습니다. `thinking` 블록은 모델이 응답을 쓰기 전에 문제를 풀어 본 [[thinking]] 과정이고, 응답 텍스트는 `text` 블록에만 있습니다. 현행 Claude 모델은 필요하다고 판단하면 스스로 thinking을 하고, thinking에 쓴 토큰은 출력 토큰으로 계산됩니다. 자세한 내용은 이 파트 끝의 "Claude의 thinking과 effort"에서 다룹니다.

이 파트에서 다루는 종료 이유는 세 가지입니다.

| 뜻 | Anthropic `stop_reason` | OpenAI 호환 `finish_reason` |
| --- | --- | --- |
| 정상 종료. 모델이 응답을 끝까지 썼다 | `end_turn` | `stop` |
| 잘림. 최대 출력 토큰에 도달해 중간에 끊겼다 | `max_tokens` | `length` |
| 거절. 안전 기준에 따라 응답하지 않았다 | `refusal` | `content_filter` |

코드에서는 정상 종료 값인지를 먼저 확인합니다. 정상 종료가 아니면 응답을 그대로 쓰지 않습니다. 조건은 "잘림이나 거절이면 버린다"가 아니라 "정상 종료일 때만 쓴다"로 작성합니다. 그래야 "종료 이유의 전체 값" 소절에 정리한 다른 값이나 나중에 새로 생기는 값이 와도 잘못된 응답을 저장하지 않습니다.

모델이 "도와드릴 수 없습니다"처럼 문장으로 거절하는 경우에는 종료 이유가 정상 종료(`end_turn`, OpenAI 호환은 `stop`)로 나옵니다. 이런 응답은 종료 이유로는 알 수 없고, 응답의 형식을 검사해야 찾아낼 수 있습니다("조용한 실패" 절).

`llm.send()`는 메시지 목록을 한 번 보내고 응답을 `Reply` 객체로 돌려줍니다. 이 객체에는 응답 텍스트(`text`), 토큰 수(`input_tokens`, `output_tokens`), 종료 이유(`stop_reason`), 모델 이름(`model`), 걸린 시간(`seconds`)이 들어 있습니다. 종료 이유는 두 API의 값을 `end`(정상 종료), `max_tokens`(최대 출력 토큰 도달), `refusal`(거절), `other`(그 밖) 중 하나로 통일해 돌려줍니다. `llm.send()`는 타임아웃을 60초로 정해 보내고, `timeout` 인자로 바꿀 수 있습니다. 타임아웃은 "실패 다루기" 절에서 설명합니다.

### 종료 이유의 전체 값 {추가}

API가 돌려줄 수 있는 종료 이유는 위의 세 가지보다 많습니다. 로그에서 처음 보는 값을 만났을 때 찾아볼 수 있도록 전체 값을 정리합니다. 도구 사용처럼 아직 배우지 않은 기능에서 나오는 값도 있으므로, 지금은 이런 값이 있다는 것만 알아 두면 됩니다.

**Anthropic API의 `stop_reason`**

| 값 | 뜻 | `llm.send()`의 값 |
| --- | --- | --- |
| `end_turn` | 정상 종료. 모델이 응답을 끝까지 썼다 | `end` |
| `stop_sequence` | 중단 문자열 도달. 요청할 때 지정한 문자열(`stop_sequences`)이 나와서 멈췄다 | `end` |
| `max_tokens` | 최대 출력 토큰 도달. 응답이 중간에 끊겼다 | `max_tokens` |
| `model_context_window_exceeded` | 컨텍스트 윈도우 초과. 응답을 쓰는 도중에 컨텍스트 윈도우가 가득 차서 끊겼다 | `max_tokens` |
| `refusal` | 거절. 안전 기준에 따라 응답을 멈췄다 | `refusal` |
| `tool_use` | 도구 호출. 모델이 도구를 써 달라고 요청했다. 도구를 실행해 결과를 보내 주면 이어서 응답한다 | `other` |
| `pause_turn` | 일시 중지. 오래 걸리는 작업을 서버가 잠시 멈췄다. 받은 응답을 그대로 다시 보내면 이어서 진행한다 | `other` |

**OpenAI 호환 API의 `finish_reason`**

| 값 | 뜻 | `llm.send()`의 값 |
| --- | --- | --- |
| `stop` | 정상 종료. 모델이 응답을 끝까지 썼거나, 지정한 중단 문자열이 나와서 멈췄다 | `end` |
| `length` | 최대 출력 토큰 도달. 응답이 중간에 끊겼다 | `max_tokens` |
| `content_filter` | 콘텐츠 필터. 필터에 걸려 응답의 일부나 전부가 빠졌다 | `refusal` |
| `tool_calls` | 도구 호출. 모델이 도구를 써 달라고 요청했다 | `other` |
| `function_call` | 함수 호출. `tool_calls`의 이전 방식이며 더는 권장되지 않는다 | `other` |

:::보충
위 값은 anthropic SDK 2.1.0과 openai SDK 3.16.2에 정의된 것입니다(2026-11-19 확인). 사내 API처럼 OpenAI 형식을 따르는 서버는 이 가운데 일부만 돌려주거나 다른 값을 쓸 수 있습니다. 사내 API 문서에서 확인합니다.
:::

## 토큰과 컨텍스트 윈도우 {추가}

:::요점
길이 제한과 요금은 글자 수가 아니라 토큰 수로 정해집니다. 최대 출력 토큰에 걸려도 오류는 나지 않고 응답만 끊깁니다.
:::

[[토큰]](token)은 모델이 글을 읽고 쓰는 단위입니다. 모델은 글자나 단어가 아니라 토큰 단위로 글을 처리합니다. 토큰 하나는 단어 하나일 수도 있고, 단어의 일부나 글자 하나일 수도 있습니다.

토큰을 알아야 하는 이유는 길이 제한과 요금이 모두 토큰 수로 정해지기 때문입니다. 글자 수로는 토큰 수를 정확히 알 수 없습니다. 예제 1-1의 질문은 50자 남짓이지만 [[입력 토큰]]은 60개였습니다. 같은 글도 모델에 따라 토큰 수가 다릅니다. 모델마다 글을 토큰으로 나누는 방식이 다르기 때문입니다. 한국어는 같은 뜻의 영어 문장보다 토큰이 더 많이 나오는 경우가 많습니다.

토큰 수의 상한은 두 가지입니다.

| 상한 | 뜻 | 누가 정하는가 |
| --- | --- | --- |
| [[컨텍스트 윈도우]](context window) | 한 번의 요청에서 모델이 다룰 수 있는 토큰 수. 입력과 출력을 합쳐 셉니다 | 모델마다 정해져 있습니다. 현행 Claude 모델은 100만 토큰입니다(2026-11-03 확인) |
| 최대 출력 토큰(`max_tokens`) | 이번 응답에서 모델이 생성할 수 있는 토큰 수 | 요청할 때 여러분이 정합니다 |

입력만으로 컨텍스트 윈도우를 넘는 요청은 오류로 거절됩니다. 응답을 쓰는 도중에 컨텍스트 윈도우가 가득 차면 응답이 거기서 끊기고, Anthropic API에서는 종료 이유가 `model_context_window_exceeded`로 나옵니다.

<figure>
<svg viewBox="0 0 680 190" role="img" aria-label="컨텍스트 윈도우 안에 입력과 출력이 함께 들어가고, max_tokens 한도는 출력이 늘어날 수 있는 끝을 정한다는 그림">
<text x="10" y="20" fill="var(--ink)" font-weight="700">컨텍스트 윈도우: 입력과 출력을 합친 상한 (모델이 정함)</text>
<rect x="10" y="34" width="660" height="50" rx="6" fill="none" stroke="var(--line)" stroke-dasharray="5 4"/>
<rect x="16" y="40" width="262" height="38" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="147" y="64" text-anchor="middle" fill="var(--ink)" font-size="14">입력: 시스템 프롬프트 + 메시지</text>
<rect x="284" y="40" width="216" height="38" rx="4" fill="var(--amber-wash)" stroke="var(--amber)"/>
<text x="392" y="64" text-anchor="middle" fill="var(--ink)" font-size="14">출력: thinking + 응답 텍스트</text>
<line x1="560" y1="28" x2="560" y2="112" stroke="var(--amber)" stroke-width="2" stroke-dasharray="6 4"/>
<text x="568" y="64" fill="var(--ink-soft)" font-size="13">남은 공간</text>
<line x1="284" y1="100" x2="560" y2="100" stroke="var(--amber)" stroke-width="2"/>
<line x1="284" y1="94" x2="284" y2="106" stroke="var(--amber)" stroke-width="2"/>
<polygon points="560,100 550,95 550,105" fill="var(--amber)"/>
<text x="16" y="134" fill="var(--ink)" font-size="14">최대 출력 토큰(max_tokens): 출력이 늘어날 수 있는 길이 (요청할 때 정함)</text>
<text x="16" y="156" fill="var(--ink-soft)" font-size="13">출력이 주황색 점선(max_tokens 한도)에 닿으면 응답이 거기서 끊깁니다.</text>
<text x="16" y="176" fill="var(--ink-soft)" font-size="13">이때 종료 이유는 max_tokens(OpenAI 호환은 length)입니다.</text>
</svg>
<figcaption>컨텍스트 윈도우는 입력과 출력을 합친 전체 길이를 제한합니다. 최대 출력 토큰은 그중 출력의 길이만 제한합니다.</figcaption>
</figure>

최대 출력 토큰을 낮게 주면 모델은 응답을 쓰다가 상한에서 멈춥니다. 오류는 나지 않습니다. 종료 이유만 다르게 나옵니다. Anthropic API에서는 `stop_reason`이 `end_turn`이 아니라 `max_tokens`로 나오고, OpenAI 호환 API에서는 `finish_reason`이 `stop`이 아니라 `length`로 나옵니다.

:::예제 1-2 최대 출력 토큰을 낮추면 생기는 일
```python
# 예제 1-2
reply = llm.send([{'role': 'user', 'content': question}], max_tokens=15)
print('종료 이유:', reply.stop_reason)
print('출력 토큰:', reply.output_tokens)
print('응답:', repr(reply.text))
```
:::

종료 이유가 `max_tokens`이고 출력 토큰 15개를 모두 썼는데, 응답은 한 글자도 없습니다. 이 모델이 응답을 쓰기 전에 thinking을 했고, thinking에 쓴 토큰도 [[출력 토큰]]에 들어가기 때문입니다. 최대 출력 토큰 15개가 모두 thinking에 쓰여 응답 텍스트가 나오지 못했습니다. 모델이 thinking 없이 바로 응답을 쓴 경우에는 응답의 앞부분만 나오고 끊깁니다(예제 1-11).

:::주의
종료 이유를 확인하지 않으면 잘린 응답이나 빈 응답을 정상 결과로 저장합니다. 응답을 사용하기 전에 종료 이유를 항상 확인합니다.
:::

## 응답이 매번 다른 이유 {원본 p.41-43, 63}

:::요점
모델은 다음 토큰을 확률에 따라 뽑습니다. 그래서 같은 질문에도 응답이 달라지고, 한 번의 결과로 판단하면 안 됩니다.
:::

같은 모델에 같은 질문을 보내도 응답은 매번 조금씩 다릅니다.

:::예제 1-3 같은 질문을 두 번 보내기
```python
# 예제 1-3
for number in [1, 2]:
    reply = llm.send([{'role': 'user', 'content': question}])
    print(number, reply.text)
```
:::

두 응답은 요약한 뜻은 같지만 표현이 다릅니다. 모델은 토큰을 하나씩 생성하는데, 매번 다음에 올 수 있는 토큰들의 확률을 계산한 뒤 그 확률에 따라 하나를 뽑습니다. 이 과정을 [[샘플링]](sampling)이라고 합니다. 확률이 가장 높은 토큰만 고르는 것이 아니라 확률에 따라 뽑기 때문에, 같은 입력에서도 다른 토큰이 나올 수 있습니다. 한 토큰이 달라지면 그 뒤에 이어지는 문장도 다르게 쓰입니다.

이 성질 때문에 두 가지를 기억해야 합니다.

- 모델의 응답을 그대로 저장하거나 다른 프로그램에 넘기려면 형식을 정해 받아야 합니다. 형식을 강제하는 방법은 파트 2에서 다룹니다.
- 한 번 실행해 본 결과로 "이 프롬프트는 잘 된다"고 결론 내리지 않습니다. 여러 건으로 측정합니다.

[[temperature]]는 샘플링의 무작위성을 조절하는 값입니다. 낮을수록 확률이 높은 토큰을 고르므로 응답의 변동이 줄어듭니다. 다만 0으로 낮춰도 응답이 항상 같다고 보장되지는 않습니다.

:::주의
현행 Claude 모델은 `temperature` 같은 샘플링 값을 받지 않습니다. `anthropic` SDK에서는 `temperature`를 넣으면 `TypeError`가 납니다. OpenAI 호환 API는 대개 `temperature`를 받습니다. 모델마다 다르므로 사내 API 문서를 확인합니다. (anthropic 2.1.0, 2026-11-18 확인)
:::

## 시스템 프롬프트 {원본 p.44-47}

:::요점
모든 요청에 공통인 규칙은 시스템 프롬프트에 두고, 메시지에는 건마다 바뀌는 내용만 넣습니다.
:::

[[시스템 프롬프트]]는 모든 요청에 공통으로 적용할 역할, 규칙, 출력 형식을 적은 글입니다. 문의 100건을 분류한다면 분류 규칙은 100건 모두에 같고 문의 내용만 바뀝니다. 규칙을 시스템 프롬프트에 두고 메시지에는 문의만 넣으면, 규칙은 한 곳에서 관리하고 문의만 바꿔 가며 보낼 수 있습니다.

시스템 프롬프트를 넣는 자리는 두 API가 다릅니다. 아래 두 코드에서 `MODEL`은 모델 이름, `SYSTEM`은 시스템 프롬프트, `inquiry`는 문의 한 건을 담은 문자열입니다. 실행할 수 있는 전체 코드는 예제 1-4에 있습니다.

:::탭 Anthropic
```python
# system 인자로 따로 넣습니다
client.messages.create(
    model=MODEL, max_tokens=1024,
    system=SYSTEM,
    messages=[{'role': 'user', 'content': inquiry}],
)
```
:::
:::탭 OpenAI 호환
```python
# messages의 첫 메시지로, 역할을 system으로 해서 넣습니다
client.chat.completions.create(
    model=MODEL, max_tokens=1024,
    messages=[{'role': 'system', 'content': SYSTEM},
              {'role': 'user', 'content': inquiry}],
)
```
:::

`llm.send()`에는 `system` 인자로 넘기면 API에 맞는 자리에 넣어 줍니다.

이 파트의 과제인 문의 분류에서는 분류 규칙이 시스템 프롬프트입니다. 규칙은 `data/2일차/분류_규칙.txt`에 있습니다.

```
너는 반도체 공장 현장에서 들어오는 문의를 분류하는 도우미다.

문의를 아래 다섯 가지 중 하나로 분류한다.
- 문서안내: 문서, 자료, 양식의 위치나 최신본을 묻는 문의
- 절차안내: 어떻게 하는지(신청, 승인, 작업 순서, 담당, 기준)를 묻는 문의
- 데이터요청: 측정값, 집계, 로그 같은 데이터를 달라는 문의
- 긴급: 지금 일어나고 있는 설비 이상, 알람, 정지를 알리는 문의
- 기타: 위 넷에 해당하지 않는 글

두 가지에 걸치면 긴급, 데이터요청, 절차안내, 문서안내 순으로 앞선 것을 고른다.
urgent 는 즉시 또는 오늘 안에 대응해 달라는 문의면 true, 아니면 false 다. 긴급은 항상 true 다.

출력은 아래 형식의 JSON 한 줄만 쓴다. 설명이나 코드 블록 표시를 붙이지 않는다.
{"id": "문의 id", "category": "분류", "urgent": true 또는 false}
```

규칙의 마지막 두 줄이 출력 형식입니다. 모델은 이 지시에 따라 응답을 JSON 한 줄로 씁니다.

:::예제 1-4 시스템 프롬프트로 분류 규칙 고정하기
```python
# 예제 1-4
print(SYSTEM)
print('-' * 40)

inquiry = 'id: Q900\n문의: 3호기 로드락 도어 인터록 알람이 세 번 연속 발생했습니다'
reply = llm.send([{'role': 'user', 'content': inquiry}], system=SYSTEM)
print(reply.text)
print('입력 토큰:', reply.input_tokens)
```

규칙은 그대로 두고 문의만 바꿔 보냅니다.

```python
# 예제 1-4 (규칙은 그대로 두고 문의만 바꿉니다)
inquiry_2 = 'id: Q901\n문의: PM 체크리스트 최신본 위치를 알고 싶습니다'
print(llm.send([{'role': 'user', 'content': inquiry_2}], system=SYSTEM).text)
```
:::

입력 토큰이 482개입니다. 문의는 한 줄인데 토큰이 많은 것은 시스템 프롬프트도 입력 토큰에 들어가기 때문입니다. 시스템 프롬프트는 요청마다 다시 보내므로, 100건을 보내면 규칙의 토큰도 100번 계산됩니다.

## 대화 이력 {원본 p.48-58}

:::요점
대화를 이으려면 지금까지의 메시지를 요청마다 다시 보내야 합니다. 서버가 앞 대화를 기억해 주지 않기 때문입니다. 대화가 길어질수록 입력 토큰이 늘어납니다.
:::

API 서버는 이전 요청의 내용을 기억하지 않습니다. 요청 하나를 처리하고 응답을 보내면 그것으로 끝이고, 다음 요청은 처음 받는 요청처럼 처리합니다. 이런 성질을 [[무상태]](stateless)라고 합니다.

채팅 화면이 앞 대화를 기억하는 것처럼 보이는 것은 화면 쪽 프로그램이 지금까지의 대화를 매번 다시 보내 주기 때문입니다. 코드로 호출할 때는 이 일을 직접 해야 합니다. 지금까지 주고받은 메시지의 목록을 [[대화 이력]]이라고 하고, 대화를 이어 가려면 요청마다 대화 이력을 함께 보냅니다.

:::예제 1-5 서버는 앞 대화를 기억하지 않는다
```python
# 예제 1-5
first = {'role': 'user', 'content': '우리 팀 설비 점검 요일은 목요일입니다. 기억해 주세요.'}
first_reply = llm.send([first], max_tokens=300)
print('첫 응답:', first_reply.text)

follow_up = {'role': 'user', 'content': '우리 팀 설비 점검 요일이 무슨 요일이라고 했죠? 요일만 답해 주세요.'}

# (가) 새 질문만 보냅니다
alone = llm.send([follow_up], max_tokens=300)
print('\n(가) 새 질문만 보냄 →', alone.text)

# (나) 앞 질문과 응답을 함께 보냅니다
history = [first, {'role': 'assistant', 'content': first_reply.text}, follow_up]
together = llm.send(history, max_tokens=300)
print('(나) 앞 대화를 함께 보냄 →', together.text)
print(f'\n입력 토큰: (가) {alone.input_tokens}, (나) {together.input_tokens}')
```
:::

(가)에서 모델은 요일을 모릅니다. 바로 앞 호출에서 "기억하겠습니다"라고 답했지만, 그 응답은 서버에 남지 않았습니다. (나)처럼 앞 질문과 응답을 함께 보내야 이어서 답합니다.

질문 하나와 그에 대한 응답 하나를 묶어 한 턴이라고 합니다. 대화 이력에는 `user` 메시지와 `assistant` 메시지를 번갈아 넣고, 마지막은 새 질문인 `user` 메시지로 끝냅니다. 모델의 이전 응답은 `assistant` 역할로 넣습니다.

### 이력이 쌓이면 비용도 쌓인다 {원본 p.52-58}

(나)의 입력 토큰은 239개로 (가)의 50개보다 다섯 배 가까이 많습니다. 앞 대화를 함께 보냈기 때문입니다. 대화가 길어질수록 매번 보내는 양이 늘어납니다. 아래 예제는 토큰 수만 비교하므로 `model='소형'`으로 소형 등급 모델에 보냅니다.

:::예제 1-6 대화가 길어지면 입력 토큰이 늘어난다
```python
# 예제 1-6
questions = ['반도체 공정에서 PM 이 무엇의 줄임말인지 한 문장으로 알려 주세요.',
             '그것을 정해진 주기로 하는 이유를 한 문장으로 알려 주세요.',
             '주기를 놓치면 생길 수 있는 문제를 한 가지만 알려 주세요.',
             '지금까지 답한 내용을 한 문장으로 정리해 주세요.']

history = []
for turn, text in enumerate(questions, 1):
    history.append({'role': 'user', 'content': text})
    reply = llm.send(history, model='소형', max_tokens=500)       # 이력 전체를 보냅니다
    history.append({'role': 'assistant', 'content': reply.text})  # 응답도 이력에 넣습니다
    print(f'{turn}번째 호출, 입력 토큰 {reply.input_tokens}')
print('\n마지막 응답:', reply.text)
```

이번에는 최근 한 턴과 마지막 질문만 보냅니다.

```python
# 예제 1-6 (최근 한 턴과 마지막 질문만 보냅니다)
# history는 [질문1, 답1, 질문2, 답2, 질문3, 답3, 질문4, 답4]입니다.
recent = history[-4:-1]          # [질문3, 답3, 질문4]
reply = llm.send(recent, model='소형', max_tokens=500)
print('입력 토큰:', reply.input_tokens)
print('응답:', reply.text)
```
:::

<figure>
<svg viewBox="0 0 680 190" role="img" aria-label="호출할 때마다 앞선 질문과 응답이 모두 다시 전송되어 입력 토큰이 늘어나는 그림">
<text x="92" y="20" fill="var(--ink-soft)" font-size="13">매번 보내는 메시지 (진한 칸이 새 질문)</text>
<text x="10" y="52" fill="var(--ink)" font-size="14">1번째 호출</text>
<rect x="92" y="34" width="64" height="26" rx="4" fill="var(--teal)" stroke="var(--teal)"/>
<text x="124" y="52" text-anchor="middle" font-size="13" fill="var(--sheet)">질문1</text>
<text x="670" y="52" text-anchor="end" fill="var(--ink)" font-size="14">입력 48토큰</text>
<text x="10" y="88" fill="var(--ink)" font-size="14">2번째 호출</text>
<rect x="92" y="70" width="64" height="26" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="124" y="88" text-anchor="middle" font-size="13" fill="var(--ink)">질문1</text>
<rect x="160" y="70" width="64" height="26" rx="4" fill="var(--sheet)" stroke="var(--line)"/>
<text x="192" y="88" text-anchor="middle" font-size="13" fill="var(--ink)">응답1</text>
<rect x="228" y="70" width="64" height="26" rx="4" fill="var(--teal)" stroke="var(--teal)"/>
<text x="260" y="88" text-anchor="middle" font-size="13" fill="var(--sheet)">질문2</text>
<text x="670" y="88" text-anchor="end" fill="var(--ink)" font-size="14">입력 168토큰</text>
<text x="10" y="124" fill="var(--ink)" font-size="14">3번째 호출</text>
<rect x="92" y="106" width="64" height="26" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="124" y="124" text-anchor="middle" font-size="13" fill="var(--ink)">질문1</text>
<rect x="160" y="106" width="64" height="26" rx="4" fill="var(--sheet)" stroke="var(--line)"/>
<text x="192" y="124" text-anchor="middle" font-size="13" fill="var(--ink)">응답1</text>
<rect x="228" y="106" width="64" height="26" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="260" y="124" text-anchor="middle" font-size="13" fill="var(--ink)">질문2</text>
<rect x="296" y="106" width="64" height="26" rx="4" fill="var(--sheet)" stroke="var(--line)"/>
<text x="328" y="124" text-anchor="middle" font-size="13" fill="var(--ink)">응답2</text>
<rect x="364" y="106" width="64" height="26" rx="4" fill="var(--teal)" stroke="var(--teal)"/>
<text x="396" y="124" text-anchor="middle" font-size="13" fill="var(--sheet)">질문3</text>
<text x="670" y="124" text-anchor="end" fill="var(--ink)" font-size="14">입력 322토큰</text>
<text x="10" y="160" fill="var(--ink)" font-size="14">4번째 호출</text>
<rect x="92" y="142" width="64" height="26" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="124" y="160" text-anchor="middle" font-size="13" fill="var(--ink)">질문1</text>
<rect x="160" y="142" width="64" height="26" rx="4" fill="var(--sheet)" stroke="var(--line)"/>
<text x="192" y="160" text-anchor="middle" font-size="13" fill="var(--ink)">응답1</text>
<rect x="228" y="142" width="64" height="26" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="260" y="160" text-anchor="middle" font-size="13" fill="var(--ink)">질문2</text>
<rect x="296" y="142" width="64" height="26" rx="4" fill="var(--sheet)" stroke="var(--line)"/>
<text x="328" y="160" text-anchor="middle" font-size="13" fill="var(--ink)">응답2</text>
<rect x="364" y="142" width="64" height="26" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="396" y="160" text-anchor="middle" font-size="13" fill="var(--ink)">질문3</text>
<rect x="432" y="142" width="64" height="26" rx="4" fill="var(--sheet)" stroke="var(--line)"/>
<text x="464" y="160" text-anchor="middle" font-size="13" fill="var(--ink)">응답3</text>
<rect x="500" y="142" width="64" height="26" rx="4" fill="var(--teal)" stroke="var(--teal)"/>
<text x="532" y="160" text-anchor="middle" font-size="13" fill="var(--sheet)">질문4</text>
<text x="670" y="160" text-anchor="end" fill="var(--ink)" font-size="14">입력 454토큰</text>
</svg>
<figcaption>새 질문은 하나씩이지만, 보내는 양은 호출마다 늘어납니다. 숫자는 예제 1-6의 실행 결과입니다.</figcaption>
</figure>

네 번째 호출은 질문 하나를 보내는 데 454토큰을 썼습니다. 앞의 세 질문과 세 응답이 모두 다시 갔기 때문입니다. 호출 한 번의 입력 토큰은 턴 수에 비례해 늘어납니다. 그런 호출을 턴 수만큼 하므로 입력 토큰의 합계는 턴 수의 제곱에 가깝게 늘어납니다.

최근 한 턴만 남겨 보내자 454토큰이 174토큰으로 줄었습니다. 대신 모델은 잘려 나간 앞 대화를 알 수 없습니다. 네 번째 질문은 "지금까지 답한 내용을 정리해 달라"는 것이었는데, 최근 한 턴만 받은 모델은 세 번째 응답의 내용만 정리했습니다.

이력을 보낼지는 앞 내용을 알아야 답할 수 있는 일인지에 따라 정합니다.

- 문의 분류나 문서 요약처럼 건마다 독립인 일이면 이력 없이 한 건씩 보냅니다.
- 앞 내용을 알아야 하는 대화이면 이력을 보냅니다. 이력이 길어지면 최근 몇 턴만 남기거나 앞부분을 요약해 넣습니다.

## 요금 계산과 사전 추정 {원본 p.67-78}

:::요점
요금은 입력 토큰과 출력 토큰에 각각의 단가를 곱해 더한 값입니다. 건수와 모델 등급에 따라 수십 배까지 벌어지므로 미리 계산합니다.
:::

요금은 토큰 수에 [[단가]]를 곱해 계산합니다. 단가는 토큰 100만 개당 가격이고, 입력과 출력의 단가가 다릅니다.

```
요금 = 입력 토큰 수 × 입력 단가 + 출력 토큰 수 × 출력 단가
```

Claude 모델의 단가는 다음과 같습니다(Anthropic 공개 가격, 2026-11-03 확인).

| 등급 | 모델 | 입력 단가 | 출력 단가 |
| --- | --- | --- | --- |
| 소형 | `claude-haiku-5-5` | $0.10 | $0.50 |
| 기본 | `claude-sonnet-5-5` | $2.00 | $10.00 |
| 대형 | `claude-opus-5-5` | $4.00 | $20.00 |

소형 모델의 단가는 프롬프트가 10만 토큰 이하인 요청의 값입니다. 10만 토큰을 넘는 요청은 입력 $0.50, 출력 $2.50입니다(2026-11-26 확인). 이 파트의 예제는 요청 하나의 입력이 1,000토큰이 안 되므로 표의 단가로 계산합니다.

세 모델 모두 출력 단가가 입력 단가의 5배입니다. thinking에 쓴 토큰도 출력 토큰으로 계산하므로, 응답이 길거나 thinking이 길어지면 요금이 크게 늘어납니다. 사내 API를 쓴다면 사내 과금 기준을 따릅니다.

예제의 `cost_usd()`는 "준비 (2)" 셀에 있는 함수입니다. 등급별 단가로 위 식을 계산하고, 단가가 토큰 100만 개당 가격이므로 100만으로 나눕니다.

:::예제 1-7 요금 계산과 사전 추정
```python
# 예제 1-7
reply = llm.send([{'role': 'user', 'content': inquiry}], system=SYSTEM, model='소형')
print(f'입력 {reply.input_tokens}토큰, 출력 {reply.output_tokens}토큰')
print(f"요금 ${cost_usd(reply.input_tokens, reply.output_tokens, '소형'):.6f}")
```

보내기 전에 입력 토큰을 셉니다.

```python
# 예제 1-7 (보내기 전에 입력 토큰을 셉니다)
counted = llm.count_tokens([{'role': 'user', 'content': inquiry}], system=SYSTEM, model='소형')
print('보내기 전에 센 값:', counted)
print('실제로 보낸 뒤의 값:', reply.input_tokens)
# OpenAI 호환 API는 보내기 전에 세는 표준 방법이 없어 None이 나옵니다.
```

문의 전체를 보낼 때의 요금을 추정합니다.

```python
# 예제 1-7 (문의 전체의 요금을 추정합니다)
inquiries = pd.read_csv(f'{DATA}/문의_예제.csv', dtype=str, keep_default_na=False)
valid = inquiries[inquiries['문의내용'].str.strip() != '']
print(f'전체 {len(inquiries):,}건, 빈 문의 {len(inquiries) - len(valid):,}건')


def prompt_of(row):
    return f"id: {row['id']}\n문의: {row['문의내용']}"


def count_one(row):
    return llm.count_tokens([{'role': 'user', 'content': prompt_of(row)}], system=SYSTEM, model='소형')


rows = [row for _, row in valid.iterrows()]
if llm.provider() == 'anthropic':
    input_counts = [count_one(row) for row in rows]      # 문의마다 한 번씩 토큰 수를 묻습니다
    input_total = sum(input_counts)
    print(f'입력 합계 {input_total:,}토큰, 한 건 평균 {input_total / len(rows):,.0f}토큰, 최대 {max(input_counts):,}토큰')
else:
    # 세어 주는 기능이 없으면 몇 건을 실제로 보내 평균을 내고 건수를 곱합니다
    sample = [llm.send([{'role': 'user', 'content': prompt_of(row)}], system=SYSTEM, model='소형')
              for row in rows[:5]]
    average = sum(reply.input_tokens for reply in sample) / len(sample)
    input_total = round(average * len(rows))
    print(f'표본 5건 평균 {average:,.0f}토큰 → 입력 합계 추정 {input_total:,}토큰')

EXPECTED_OUTPUT = 40     # 응답은 JSON 한 줄이므로 한 건에 40토큰으로 가정합니다
for alias in ['소형', '기본', '대형']:
    estimate = cost_usd(input_total, EXPECTED_OUTPUT * len(rows), alias)
    print(f'{alias} 모델로 {len(rows)}건: 약 ${estimate:.4f}')
```
:::

한 건의 요금은 작지만, 건수가 많아지고 모델 등급이 올라가면 차이가 커집니다. 같은 98건이 소형 모델로는 약 $0.007(0.7센트), 대형 모델로는 약 $0.27(27센트)입니다. 그래서 대량 작업은 보내기 전에 요금을 추정합니다.

추정에 필요한 것은 입력 토큰 합계와 출력 토큰 합계입니다.

- **입력 토큰**은 보내기 전에 알 수 있습니다. Anthropic API에는 토큰을 세어 주는 기능(`count_tokens`)이 있습니다. 이 기능은 요금이 들지 않습니다. 세어 준 값은 추정값이라 실제와 조금 다를 수 있습니다(Anthropic 문서, 2026-11-18 확인). OpenAI 호환 API에는 표준으로 정해진 방법이 없습니다. 이럴 때는 몇 건을 실제로 보내 응답의 입력 토큰 평균을 구하고 건수를 곱합니다.
- **출력 토큰**은 보내기 전에 알 수 없어 가정합니다. 위 예제는 응답이 JSON 한 줄이므로 한 건에 40토큰으로 가정했습니다. 모델이 thinking을 길게 하는 건은 이보다 훨씬 많이 나옵니다. 가정이 맞았는지는 예제 1-12에서 확인합니다.

## 모델 고르기 {원본 p.79-89}

:::요점
모델은 정답을 아는 표본으로 정확도, 시간, 요금을 측정해서 고릅니다. 오답이 나오면 원인이 모델인지 분류 규칙인지부터 가립니다.
:::

API 제공사는 보통 능력과 가격이 다른 여러 [[모델 등급]]을 제공합니다. 등급이 높을수록 어려운 일을 잘하지만 느리고 비쌉니다. 모든 일에 가장 좋은 모델을 쓰면 비용과 시간을 낭비하고, 가장 싼 모델만 쓰면 품질이 모자랄 수 있습니다.

모델은 몇 번 써 본 느낌이 아니라 측정한 결과로 고릅니다. 정답을 아는 표본을 여러 등급으로 처리해 정확도, 시간, 요금을 비교합니다. [[정확도]](accuracy)는 모델의 결과가 정답 라벨과 일치한 건의 비율입니다.

:::예제 1-8 정답이 있는 표본으로 모델 등급 비교하기
```python
# 예제 1-8
answers = pd.read_csv(f'{DATA}/문의_예제_정답.csv', dtype=str).set_index('id')
# 엣지 케이스 12건과 보통 사례 8건을 표본으로 씁니다. 쉬운 문의만 고르면 모델 차이가 드러나지 않습니다.
hard_ids = answers.index[answers['난이도'] == '엣지']
easy_ids = answers.index[answers['난이도'] == '보통'][:8]
sample = valid[valid['id'].isin(hard_ids.union(easy_ids))]
print(f'표본 {len(sample):,}건, 엣지 케이스 {len(hard_ids):,}건')


def classify(row, model):
    """문의 한 건을 분류해 (분류, Reply)를 돌려줍니다. JSON으로 읽지 못하면 분류는 None입니다."""
    reply = llm.send([{'role': 'user', 'content': prompt_of(row)}], system=SYSTEM, model=model)
    try:
        return json.loads(reply.text)['category'], reply
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, reply


MODELS = ['소형', '기본', '대형']      # 대형 모델을 쓰지 않으려면 목록에서 뺍니다
# 여러 등급에 같은 모델 이름을 넣었다면 한 번만 비교합니다
MODELS = [alias for index, alias in enumerate(MODELS)
          if llm.model_name(alias) not in [llm.model_name(earlier) for earlier in MODELS[:index]]]
comparison = {}
for model in MODELS:
    results = [classify(row, model) for _, row in sample.iterrows()]
    correct = sum(category == answers.loc[row_id, 'category']
                  for (category, _), row_id in zip(results, sample['id']))
    seconds = sum(reply.seconds for _, reply in results)
    input_tokens = sum(reply.input_tokens or 0 for _, reply in results)
    output_tokens = sum(reply.output_tokens or 0 for _, reply in results)
    comparison[model] = results
    print(f'{model}: 정답 {correct}/{len(sample)}, {seconds:.1f}초, 입력 {input_tokens:,}토큰, 출력 {output_tokens:,}토큰'
          f', ${cost_usd(input_tokens, output_tokens, model):.4f}')
```

틀린 건을 출력해 직접 읽어 봅니다.

```python
# 예제 1-8 (틀린 건을 직접 읽어 봅니다)
for model in MODELS:
    for (category, _), (_, row) in zip(comparison[model], sample.iterrows()):
        expected = answers.loc[row['id'], 'category']
        if category != expected:
            print(f"[{model}] {row['id']} 정답 {expected}, 모델 {category}, {row['문의내용'][:50]}")
```
:::

같은 코드를 다섯 번 실행한 기록은 다음과 같습니다. 마지막 행이 위 실행 결과입니다.

| 실행 | 소형 | 기본 | 대형 |
| --- | --- | --- | --- |
| 2026-11-18 | 18/20 | 18/20 | 18/20 |
| 2026-11-19 첫 번째 | 18/20 | 20/20 | 18/20 |
| 2026-11-19 두 번째 | 19/20 | 19/20 | 17/20 |
| 2026-11-25 | 19/20 | 18/20 | 18/20 |
| 2026-11-26 | 19/20 | 17/20 | 17/20 |

이 결과에서 읽을 것은 다섯 가지입니다.

- **정확도 차이는 작고, 요금 차이는 수십 배입니다.** 소형은 20건 중 19건, 기본과 대형은 17건을 맞혔습니다. 요금은 소형이 기본의 약 25분의 1, 대형의 약 45분의 1입니다.
- **실행할 때마다 결과가 달라집니다.** 위 표에서 어느 모델이 가장 정확한지가 실행마다 바뀌었습니다. 20건 표본에서 한두 건 차이는 실행할 때마다 생기는 변동과 구별할 수 없으므로, 모델의 실력 차이로 보지 않습니다. 다섯 번 모두에서 변하지 않은 것은 소형 모델이 다른 모델과 2건 이내의 차이로 맞히면서 요금은 20분의 1 이하였다는 점입니다.
- **등급이 높다고 항상 더 정확하지는 않습니다.** 다섯 번 가운데 두 번은 대형 모델이 기본 모델보다 더 많이 틀렸고, 나머지 세 번은 같은 수를 맞혔습니다. 대형 모델이 기본 모델보다 많이 맞힌 실행은 없었습니다.
- **틀린 건은 직접 읽어야 합니다.** Q026은 다섯 번의 실행 모두에서 두 모델 이상이 "긴급"으로 분류했습니다(2026-11-26 실행에서는 세 모델 모두). 문의에 "8호기가 조금 이상하다"는 말이 있어 긴급으로 볼 여지가 있습니다. 여러 모델이 같은 쪽으로 되풀이해 틀린다면 모델이 아니라 정답이나 분류 규칙이 모호한 것일 수 있습니다. 이런 건은 모델 등급을 올려도 해결되지 않습니다. 규칙에 기준을 더하거나 정답을 다시 정해야 합니다.
- **쉬운 문의만 고르면 모델 간 차이가 보이지 않습니다.** 엣지 케이스를 넣기 전에 문의 앞쪽 20건을 표본으로 썼을 때는 세 모델이 모두 20건을 맞혔습니다(2026-11-18 실행). 쉬운 문의만 들어 있어 차이가 드러나지 않았습니다. 사람마다 판단이 다를 수 있는 엣지 케이스를 넣어야 모델과 규칙의 약점이 보입니다.

:::주의
정답 없이 "대형 모델의 응답과 얼마나 같은가"로 비교하는 방법도 있습니다. 그러나 위 결과처럼 대형 모델도 틀립니다. 대형 모델의 응답을 기준으로 삼으면 대형 모델이 틀린 건은 찾을 수 없고, 그 건을 맞힌 모델은 오히려 "대형과 다르다"는 이유로 낮게 평가됩니다. 위 실행에서 대형 모델은 Q060과 Q089를 틀렸지만 소형 모델은 두 건 모두 맞혔습니다. 대형 모델의 응답을 기준으로 삼았다면 소형 모델의 이 두 건은 오답으로 셌을 것입니다. 가능하면 사람이 정한 정답으로 측정합니다.
:::

모델을 고르는 순서를 정리하면 다음과 같습니다.

1. 정답을 아는 표본을 만듭니다. 쉬운 건과 엣지 케이스를 함께 넣습니다.
2. 가장 싼 등급부터 측정합니다. 분류나 추출처럼 응답의 형식이 정해진 일은 소형 모델로 충분한 경우가 많습니다.
3. 틀린 건을 읽습니다. 규칙이 모호해서 틀렸다면 모델 등급을 올리기 전에 규칙을 고칩니다.
4. 그래도 정확도가 모자라면 등급을 올리고 다시 측정합니다.

한 작업을 여러 단계로 나눌 수 있다면 단계마다 다른 등급을 쓸 수 있습니다. 예를 들어 분류는 소형 모델로 하고, 긴급으로 분류된 건의 요약만 기본 모델로 합니다.

20건은 작은 표본입니다. 위 표처럼 한두 건 차이는 다시 실행하면 뒤집히므로, 차이가 작을 때는 표본을 늘리거나 여러 번 실행해 평균을 봅니다.

## 실패 다루기 {원본 p.97-110}

:::요점
실패는 기다리면 풀리는 것과 고쳐야 풀리는 것으로 나눕니다. 기다리면 풀리는 실패만 재시도합니다.
:::

100건을 보내면 몇 건은 실패합니다. 네트워크가 끊기기도 하고, 서버가 바쁘기도 하고, 요청이 잘못되기도 합니다. 한 건의 실패로 전체가 멈추지 않게 하려면, 먼저 실패의 종류를 구분해야 합니다.

서버는 요청의 결과를 [[상태 코드]]로 알려 줍니다. 상태 코드는 세 자리 숫자이고, 첫 자리가 원인을 나타냅니다. 4로 시작하면 요청 쪽 문제, 5로 시작하면 서버 쪽 문제입니다.

`llm.send()`는 호출이 실패하면 `llm.CallError` 예외를 발생시킵니다. 이 예외에는 상태 코드(`status`), 오류 종류(`kind`), 재시도할 만한 오류인지(`retryable`)가 들어 있습니다. 아래 예제는 틀린 모델 이름, 틀린 키(`api_key`), 빈 메시지 목록, 아주 짧은 타임아웃(`timeout`)을 일부러 넣어 이 세 값을 출력합니다. 예제와 그림에 나오는 레이트 리밋과 타임아웃은 이 절의 "레이트 리밋과 타임아웃" 소절에서 설명합니다.

:::예제 1-9 오류를 일부러 일으켜 종류 확인하기
```python
# 예제 1-9
hello = [{'role': 'user', 'content': '안녕하세요'}]
cases = {
    '없는 모델 이름': dict(messages=hello, model='no-such-model-0000'),
    '틀린 키': dict(messages=hello, api_key='wrong-key'),
    '빈 메시지 목록': dict(messages=[]),
    '타임아웃 0.01초': dict(messages=hello, timeout=0.01),
}
for name, options in cases.items():
    try:
        llm.send(max_tokens=50, **options)
        print(f'{name}: 오류 없이 끝남')
    except llm.CallError as error:
        print(f'{name}: 상태 코드 {error.status}, 종류 {error.kind}, 재시도할 만한가 {error.retryable}')
```
:::

오류는 재시도하면 풀릴 수 있는지를 기준으로 둘로 나눕니다.

<figure>
<svg viewBox="0 0 680 190" role="img" aria-label="호출 실패를 재시도할 오류와 바로 멈출 오류로 나누는 그림">
<rect x="10" y="70" width="120" height="50" rx="8" fill="var(--sheet)" stroke="var(--line)"/>
<text x="70" y="100" text-anchor="middle" fill="var(--ink)" font-weight="700">호출 실패</text>
<line x1="130" y1="86" x2="196" y2="46" stroke="var(--teal)" stroke-width="2"/>
<line x1="130" y1="104" x2="196" y2="144" stroke="var(--amber)" stroke-width="2"/>
<rect x="200" y="10" width="292" height="76" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="214" y="32" fill="var(--ink)" font-weight="700">기다리면 풀릴 수 있다</text>
<text x="214" y="54" fill="var(--ink)" font-size="14">429 레이트 리밋 초과, 500번대 서버 오류</text>
<text x="214" y="74" fill="var(--ink)" font-size="14">연결 실패, 타임아웃</text>
<rect x="200" y="104" width="292" height="76" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/>
<text x="214" y="126" fill="var(--ink)" font-weight="700">고쳐야 풀린다</text>
<text x="214" y="148" fill="var(--ink)" font-size="14">400 잘못된 요청, 401 인증 실패</text>
<text x="214" y="168" fill="var(--ink)" font-size="14">403 권한 없음, 404 없는 모델이나 주소</text>
<line x1="492" y1="48" x2="524" y2="48" stroke="var(--teal)" stroke-width="2"/>
<polygon points="524,48 514,43 514,53" fill="var(--teal)"/>
<text x="532" y="44" fill="var(--ink)" font-weight="700">재시도한다</text>
<text x="532" y="64" fill="var(--ink-soft)" font-size="13">대기 시간을 늘리며</text>
<line x1="492" y1="142" x2="524" y2="142" stroke="var(--amber)" stroke-width="2"/>
<polygon points="524,142 514,137 514,147" fill="var(--amber)"/>
<text x="532" y="138" fill="var(--ink)" font-weight="700">바로 멈춘다</text>
<text x="532" y="158" fill="var(--ink-soft)" font-size="13">요청, 키, 이름을 고친다</text>
</svg>
<figcaption>실패를 만나면 먼저 어느 쪽인지 가립니다. 고쳐야 풀리는 오류(주황색 상자)는 재시도해도 똑같이 실패하므로 바로 멈춥니다.</figcaption>
</figure>

상태 코드와 SDK의 예외 이름은 다음과 같습니다.

| 구분 | 오류 | 상태 코드 | SDK 예외 이름 | 처리 |
| --- | --- | --- | --- | --- |
| 재시도한다 | 레이트 리밋 초과 | 429 | `RateLimitError` | 기다렸다가 재시도합니다 |
| | 서버 오류, 서버 과부하 | 500번대 | `InternalServerError` 등 | |
| | 연결 실패 | 없음 | `APIConnectionError` | |
| | 타임아웃 | 없음 | `APITimeoutError` | |
| 바로 멈춘다 | 잘못된 요청 | 400 | `BadRequestError` | 요청 내용을 고칩니다 |
| | 인증 실패 | 401 | `AuthenticationError` | 키를 고칩니다 |
| | 권한 없음 | 403 | `PermissionDeniedError` | 권한을 확인합니다 |
| | 없는 모델이나 주소 | 404 | `NotFoundError` | 이름과 주소를 고칩니다 |

표의 예외 이름은 `anthropic` SDK와 `openai` SDK에 모두 있습니다. 다만 알아 둘 점이 세 가지 있습니다.

- **500번대 오류는 상태 코드로 판단합니다.** `anthropic` SDK는 서버 과부하(529)를 `OverloadedError`라는 별도 예외로 알립니다. 이 예외는 `InternalServerError`로는 잡히지 않고 `openai` SDK에는 없습니다. 그래서 예외 이름이 아니라 상태 코드가 500 이상인지로 판단하는 것이 안전합니다.
- **연결 실패와 타임아웃에는 상태 코드가 없습니다.** 서버의 응답을 받지 못했기 때문입니다. 두 SDK 모두 타임아웃 예외는 연결 실패 예외의 한 종류입니다.
- **`llm.send()`는 어느 SDK의 예외든 `CallError`로 바꿔 줍니다.** 그래서 예제 1-9는 어느 SDK를 쓰든 같은 코드로 상태 코드, 오류 종류, 재시도할 만한 오류인지를 출력합니다.

### 레이트 리밋과 타임아웃 {추가}

[[레이트 리밋]](rate limit)은 일정 시간 동안 보낼 수 있는 요청 수나 토큰 수의 상한입니다. API 제공사는 서버를 여러 사용자가 나눠 쓰도록 계정마다 분당 요청 수와 분당 토큰 수를 제한합니다. 이 한도를 넘으면 429 오류가 납니다. 한꺼번에 많은 요청을 보낼 때 자주 만나는 오류이고, 기다리면 풀립니다. 한도가 분당 값으로 정해지므로, 한도를 크게 넘었다면 몇 초 기다려서는 모자랄 수 있습니다. Anthropic API는 429 응답의 `retry-after` 헤더에 재시도하기 전에 기다릴 시간(초)을 적어 보내기도 합니다. 이 헤더가 있으면 그 시간을 따릅니다(Anthropic 문서, 2026-11-26 확인).

[[타임아웃]](timeout)은 응답 대기 시간의 상한입니다. 두 SDK 모두 기본값이 10분입니다. 한 건이 10분씩 기다리면 배치 처리 전체가 멈춘 것처럼 보이므로, 응답을 받는 데 걸리는 시간에 맞춰 짧게 정합니다. 문의 분류처럼 응답이 짧은 일은 30초에서 60초면 충분합니다. `llm.send()`는 타임아웃을 60초로 정해 보냅니다.

### 재시도와 백오프 {원본 p.103-110}

[[재시도]](retry)는 실패한 요청을 다시 보내는 것입니다. 실패하자마자 바로 재시도하면 서버가 아직 바쁜 상태라 또 실패하기 쉽습니다. 그래서 재시도할 때마다 대기 시간을 늘립니다. 이 방식을 [[백오프]](backoff)라고 합니다. 1초, 2초, 4초처럼 두 배씩 늘리는 방법을 많이 씁니다. 여러 요청을 동시에 보낼 때는 실패한 요청들이 같은 시각에 한꺼번에 다시 몰리지 않도록, 대기 시간에 조금씩 무작위 값을 더하기도 합니다. 이것을 [[지터]](jitter)라고 합니다.

:::예제 1-10 재시도와 백오프를 넣은 ask() 만들기
```python
# 예제 1-10
def ask(prompt, system=None, max_tokens=300, tries=3, send=llm.send, sleep=time.sleep):
    """질문 하나를 보냅니다. 재시도할 만한 오류면 1초, 2초로 기다리며 tries번까지 보냅니다."""
    messages = [{'role': 'user', 'content': prompt}]
    for attempt in range(tries):
        try:
            return send(messages, system=system, max_tokens=max_tokens)
        except llm.CallError as error:
            if not error.retryable or attempt == tries - 1:
                raise                      # 재시도해도 소용없는 오류, 또는 마지막 시도
            wait_seconds = 2 ** attempt    # 1초, 2초, 4초 …
            print(f'  {error.kind} → {wait_seconds}초 뒤 재시도합니다')
            sleep(wait_seconds)
```

mock 호출로 동작을 확인합니다. [[mock]]은 실제 API 대신 미리 정해 둔 응답이나 오류를 돌려주는 테스트용 객체입니다. 여기서는 `checks.FakeSend`가 그 역할을 합니다. 첫 번째는 429(레이트 리밋 초과), 두 번째는 529(서버 과부하)로 실패하고 세 번째에 성공하는 mock 호출을 넣습니다.

```python
# 예제 1-10 (mock 호출로 동작을 확인합니다. API를 부르지 않습니다)
import checks

fake = checks.FakeSend(checks.error('rate_limit', 429), checks.error('server', 529), checks.good_reply())
waits = []
reply = ask('아무 질문', send=fake, sleep=waits.append)     # 실제로 기다리지 않고 기다릴 시간만 기록합니다
print(f'보낸 횟수: {fake.calls}, 대기하려던 시간: {waits}, 결과: {reply.stop_reason}')

fake = checks.FakeSend(checks.error('not_found', 404))
try:
    ask('아무 질문', send=fake, sleep=waits.append)
except llm.CallError as error:
    print(f'404 오류일 때 보낸 횟수: {fake.calls}, 재시도하지 않고 다시 발생시킨 오류: {error.kind}')
```

실제 API로도 한 번 보냅니다.

```python
# 예제 1-10 (실제 API로 한 번 보냅니다)
print(ask(inquiry, system=SYSTEM).text)
```
:::

<figure>
<svg viewBox="0 0 680 120" role="img" aria-label="첫 시도 실패 뒤 1초, 두 번째 실패 뒤 2초를 기다리고 세 번째에 성공하는 시간 흐름 그림">
<line x1="20" y1="60" x2="660" y2="60" stroke="var(--line)" stroke-width="2"/>
<polygon points="660,60 650,55 650,65" fill="var(--line)"/>
<text x="660" y="84" text-anchor="end" fill="var(--ink-soft)" font-size="13">시간</text>
<circle cx="60" cy="60" r="12" fill="var(--amber-wash)" stroke="var(--amber)" stroke-width="2"/>
<text x="60" y="32" text-anchor="middle" fill="var(--ink)" font-size="14">1번째 시도</text>
<text x="60" y="96" text-anchor="middle" fill="var(--ink-soft)" font-size="13">실패 (429)</text>
<rect x="76" y="52" width="120" height="16" fill="var(--teal-wash)"/>
<text x="136" y="46" text-anchor="middle" fill="var(--ink)" font-size="14">1초 대기</text>
<circle cx="212" cy="60" r="12" fill="var(--amber-wash)" stroke="var(--amber)" stroke-width="2"/>
<text x="212" y="32" text-anchor="middle" fill="var(--ink)" font-size="14">2번째 시도</text>
<text x="212" y="96" text-anchor="middle" fill="var(--ink-soft)" font-size="13">실패 (529)</text>
<rect x="228" y="52" width="240" height="16" fill="var(--teal-wash)"/>
<text x="348" y="46" text-anchor="middle" fill="var(--ink)" font-size="14">2초 대기</text>
<circle cx="484" cy="60" r="12" fill="var(--teal)" stroke="var(--teal)" stroke-width="2"/>
<text x="484" y="32" text-anchor="middle" fill="var(--ink)" font-size="14">3번째 시도</text>
<text x="484" y="96" text-anchor="middle" fill="var(--ink-soft)" font-size="13">성공</text>
</svg>
<figcaption>대기 시간을 두 배씩 늘립니다. 세 번째에도 실패하면 더 보내지 않고 예외를 다시 발생시킵니다.</figcaption>
</figure>

`ask()`는 두 가지를 판단합니다. 재시도하면 풀릴 오류인지, 그리고 시도 횟수가 남았는지입니다. 둘 중 하나라도 아니면 `raise`로 예외를 다시 발생시켜, `ask()`를 호출한 코드가 처리하게 합니다.

`send`와 `sleep`을 인자로 받게 만든 데에는 이유가 있습니다. 재시도는 실제 서버에서 일부러 일으키기 어렵습니다. 레이트 리밋 초과나 서버 과부하를 원하는 때에 만들 수 없기 때문입니다. 호출하는 함수를 바꿔 끼울 수 있게 해 두면, 정해 둔 순서대로 실패하는 mock 호출을 넣어 동작을 확인할 수 있습니다. 요금도 들지 않습니다.

`ask()`는 레이트 리밋 초과(429)에도 1초, 2초만 기다리고 `retry-after` 헤더는 읽지 않습니다. SDK의 자동 재시도는 이 헤더를 읽어 그만큼 기다리지만, `llm.send()`는 자동 재시도를 끄므로 이 처리도 하지 않습니다(아래 "재시도 횟수는 한 곳에서만 정합니다"). 그래서 레이트 리밋 초과가 계속되면 세 번째 시도도 실패하고, 예제 1-12에서는 그 건이 실패 목록에 들어갑니다. 실제 배치 처리에서는 레이트 리밋 초과일 때 대기 시간을 더 길게 잡거나, `retry-after` 값을 읽어 그만큼 기다립니다.

재시도에서 주의할 점은 세 가지입니다.

- **재시도 횟수는 한 곳에서만 정합니다.** 두 SDK는 기본으로 2번 재시도합니다(처음 포함 3번). 여기에 직접 만든 3번짜리 재시도를 겹치면 최대 9번을 보냅니다. `llm.send()`는 SDK의 자동 재시도를 끄고, 횟수는 `ask()`에서만 정합니다.
- **몇 번까지 보낼지는 계산해 볼 수 있습니다.** 한 번 보낼 때 실패할 확률이 6%이고 실패가 서로 무관하다면, 세 번 모두 실패할 확률은 0.06 × 0.06 × 0.06 = 0.02%입니다. 다만 실제 실패는 서로 무관하지 않습니다. 서버가 과부하일 때는 재시도한 요청도 실패하기 쉽습니다. 그래서 횟수를 늘리는 것보다 대기 시간을 늘리는 것이 효과적입니다.
- **재시도해도 안전한 일인지 확인합니다.** 분류나 요약은 같은 요청을 두 번 보내도 문제가 없습니다. 하지만 모델의 응답에 따라 메일을 보내거나 데이터를 고치는 일이라면, 첫 요청이 실제로는 처리됐는데 응답만 못 받은 경우 같은 일이 두 번 일어날 수 있습니다.

:::보충
이 절에서 말한 SDK의 동작(예외 이름, 기본 타임아웃 10분, 기본 재시도 2번)은 anthropic 2.1.0과 openai 3.16.2에서 2026-11-18에 확인했습니다. SDK 버전이 바뀌면 달라질 수 있습니다.
:::

## 조용한 실패 {원본 p.111, 134-136}

:::요점
오류 없이 온 응답도 잘렸거나, 거절됐거나, 형식이 틀렸을 수 있습니다. 받은 뒤에 코드로 검사합니다.
:::

오류가 나지 않았다고 해서 성공한 것은 아닙니다. 오류나 예외 없이 끝났지만 결과를 쓸 수 없는 실패를 [[조용한 실패]]라고 합니다. 조용한 실패는 세 가지입니다.

| 경우 | 알아보는 방법 | 예 |
| --- | --- | --- |
| 잘림 | 종료 이유가 `max_tokens`(OpenAI 호환은 `length`) | `{"id": "Q900` |
| 거절 | 종료 이유가 `refusal`(OpenAI 호환은 `content_filter`). 문장으로 거절한 응답은 파싱 오류로 분류됩니다 | 응답이 비어 있거나 거절하는 문장 |
| 파싱 오류 | 응답을 JSON으로 읽을 수 없거나 필요한 값이 없음 | `긴급으로 보입니다.` |

이 세 가지는 `try`로 잡히지 않습니다. 응답을 받은 뒤 코드로 검사해야 합니다. 이것을 [[응답 검사]]라고 합니다.

:::예제 1-11 오류 없이 왔지만 쓸 수 없는 응답 찾아내기
```python
# 예제 1-11
def check_reply(reply):
    """쓸 수 없는 응답이면 사유를, 쓸 수 있으면 None을 돌려줍니다."""
    if reply.stop_reason != 'end':                 # 정상 종료가 아니면 쓰지 않습니다
        return {'max_tokens': '잘림', 'refusal': '거절'}.get(reply.stop_reason, '비정상 종료')
    try:
        parsed = json.loads(reply.text)
    except json.JSONDecodeError:
        return '파싱 오류'
    if not isinstance(parsed, dict) or 'category' not in parsed:
        return '파싱 오류'
    return None


normal = ask(inquiry, system=SYSTEM)
print(f'보통 응답 → {check_reply(normal)}, {normal.text!r}')

cut = ask(inquiry, system=SYSTEM, max_tokens=8)     # 일부러 잘리게 합니다
print(f'max_tokens=8 → {check_reply(cut)}, {cut.text!r}')
```
:::

`check_reply()`는 먼저 종료 이유가 정상 종료(`end`)인지 확인합니다. 정상 종료가 아니면 사유를 돌려주고, 처음 보는 종료 이유도 "비정상 종료"로 처리합니다. 정상 종료인 응답만 JSON으로 읽어 봅니다.

최대 출력 토큰을 8토큰으로 준 호출은 오류 없이 끝났지만 응답이 중간에 끊겼습니다. 이 응답을 그대로 저장하면 결과에 깨진 값이 들어갑니다.

최대 출력 토큰은 실제 출력 토큰을 보고 정합니다. 표본을 보내 출력 토큰의 최댓값을 확인하고 그보다 여유 있게 잡습니다. 너무 낮으면 잘리는 건이 생기고, 높게 잡아도 요금은 실제로 쓴 토큰만큼만 나옵니다.

## 배치 처리로 확장 {원본 p.90-93, 137-141}

:::요점
입력 검사, 호출, 오류 구분, 응답 검사, 실패 기록의 다섯 단계로 만듭니다. 실패한 건은 버리지 않고 목록으로 남깁니다.
:::

지금까지 만든 것을 모으면 배치 처리의 흐름이 됩니다.

| 단계 | 하는 일 | 쓰는 함수 |
| --- | --- | --- |
| 1. 입력 검사 | 보내면 안 되거나 보낼 필요가 없는 건을 필터링합니다 | `is_valid()` |
| 2. 호출 | 타임아웃과 최대 출력 토큰을 정해 보냅니다 | `ask()`(타임아웃은 `llm.send()`의 기본값 60초) |
| 3. 오류 구분 | 재시도할 오류는 재시도하고 나머지는 예외를 다시 발생시킵니다 | `ask()` |
| 4. 응답 검사 | 잘림, 거절, 파싱 오류를 찾습니다 | `check_reply()` |
| 5. 실패 기록 | 실패한 건의 id와 사유를 남깁니다 | 실패 목록 |

앞 단계에서 필터링할수록 요금과 시간이 덜 듭니다.

[[입력 검사]]는 요청을 보내기 전에 하는 검사입니다. 다음과 같은 문의를 보내기 전에 필터링합니다.

- **빈 문의**: 보내 봐야 쓸모 있는 응답이 나오지 않습니다.
- **지나치게 긴 문의**: 요금이 많이 듭니다. 길이는 글자 수로 볼 수도 있고, 입력 토큰을 세어 토큰 수로 볼 수도 있습니다.
- **개인정보가 든 문의**: 이름, 전화번호, 이메일 주소 같은 개인정보는 보내면 안 되는 경우가 있습니다. API로 보낸 내용은 그 API를 운영하는 곳의 서버로 전달되기 때문입니다. 외부 API라면 회사 밖으로 나가는 것이므로, 무엇을 보내도 되는지는 회사의 기준을 따릅니다.

예제 1-12의 `is_valid()`는 이 가운데 빈 문의만 필터링합니다. 긴 문의와 개인정보가 든 문의는 실습 3에서 직접 다룹니다.

[[병렬 처리]]는 여러 요청을 차례로 기다리지 않고 한꺼번에 보내는 것입니다. 호출 한 건의 시간은 대부분 응답 대기 시간이므로, 여러 건을 동시에 보내면 전체 시간이 줄어듭니다. 다만 동시에 보내는 수를 늘리면 레이트 리밋에 걸리기 쉽습니다. 4건에서 8건 정도로 시작해 429 오류가 나는지 보며 조절합니다.

파이썬에서는 표준 라이브러리의 `ThreadPoolExecutor`로 병렬 처리를 합니다. `max_workers`는 동시에 보내는 요청 수입니다. `pool.map(함수, 목록)`은 목록의 항목마다 함수를 실행하고, 결과를 목록과 같은 순서로 돌려줍니다.

[[실패 목록]]은 처리하지 못한 건의 id와 사유를 모은 목록입니다. 실패를 무시하고 넘어가면 결과에서 어떤 건이 빠졌는지 알 수 없습니다. 실패가 한 건도 없더라도 실패 목록은 만들어 둡니다.

예제는 문의 목록의 앞쪽 30건만 보냅니다. 흐름을 확인하는 데는 30건이면 되고, 100건 전체는 파트 2의 예제 2-6에서 처리합니다. 모델은 `ask()`가 보내는 기본 등급입니다. "모델 고르기"의 측정에서는 소형 모델도 비슷하게 맞혔으므로, 실제 작업이라면 `ask()`가 `model` 인자를 받아 `send`에 전달하게 고치고 소형 모델로 보내 요금을 줄입니다.

:::예제 1-12 배치 처리: 입력 검사, 병렬 처리, 실패 목록
```python
# 예제 1-12
def is_valid(text):
    """보낼 만한 문의인지 돌려줍니다. 여기서는 빈 문의만 필터링합니다."""
    return isinstance(text, str) and text.strip() != ''


def process_one(row):
    """문의 한 건을 처리해 ('성공', 결과) 또는 ('실패', (id, 사유))와 로그 한 줄을 돌려줍니다."""
    try:
        reply = ask(prompt_of(row), system=SYSTEM)
    except llm.CallError as error:
        return '실패', (row['id'], error.kind), None
    log = (row['id'], reply.model, reply.input_tokens, reply.output_tokens, reply.stop_reason)
    reason = check_reply(reply)
    if reason:
        return '실패', (row['id'], reason), log
    return '성공', json.loads(reply.text), log


batch = inquiries.head(30)
to_send = [row for _, row in batch.iterrows() if is_valid(row['문의내용'])]
print(f'대상 {len(batch):,}건, 보내기 전에 필터링한 건 {len(batch) - len(to_send):,}건')

started = time.time()
with ThreadPoolExecutor(max_workers=4) as pool:        # 네 건씩 동시에 보냅니다
    outcomes = list(pool.map(process_one, to_send))
elapsed = time.time() - started

success = [result for status, result, _ in outcomes if status == '성공']
failed = [result for status, result, _ in outcomes if status == '실패']
logs = [log for _, _, log in outcomes if log]
print(f'성공 {len(success)}건, 실패 {len(failed)}건 {failed}, {elapsed:.1f}초')
print('결과 첫 줄:', success[0])
print('로그 첫 줄:', logs[0])
```

실패한 건만 다시 처리합니다. 잘린 건은 최대 출력 토큰을 올려 재시도합니다.

```python
# 예제 1-12 (실패한 건만 다시 처리합니다)
# 잘린 건은 최대 출력 토큰을 올려 재시도합니다. 다른 사유는 사람이 확인할 목록으로 남깁니다.
by_id = {row['id']: row for row in to_send}
still_failed = []
for row_id, reason in failed:
    if reason != '잘림':
        still_failed.append((row_id, reason))
        continue
    try:
        reply = ask(prompt_of(by_id[row_id]), system=SYSTEM, max_tokens=1024)
    except llm.CallError as error:
        still_failed.append((row_id, error.kind))     # 재시도에서 호출이 실패해도 사유를 남기고 다음 건을 처리합니다
        continue
    logs.append((row_id, reply.model, reply.input_tokens, reply.output_tokens, reply.stop_reason))
    second_reason = check_reply(reply)
    if second_reason:
        still_failed.append((row_id, second_reason))
    else:
        success.append(json.loads(reply.text))
        print(f'{row_id} 재시도해 성공, 출력 {reply.output_tokens}토큰')
print(f'성공 {len(success):,}건, 남은 실패 {still_failed}')
```

정답과 비교하고 실제 요금을 계산합니다.

```python
# 예제 1-12 (정답과 비교하고 실제 요금을 계산합니다)
correct = sum(result['category'] == answers.loc[result['id'], 'category'] for result in success)
input_tokens = sum(log[2] or 0 for log in logs)
output_tokens = sum(log[3] or 0 for log in logs)
print(f'정답 {correct}/{len(success)}')
print(f"입력 {input_tokens:,}토큰, 출력 {output_tokens:,}토큰, 실제 요금 ${cost_usd(input_tokens, output_tokens, '기본'):.4f}")
```
:::

첫 번째 코드는 세 부분으로 읽습니다.

- `process_one()`은 문의 한 건을 처리해 값 세 개를 돌려줍니다. 첫째는 `'성공'` 또는 `'실패'`입니다. 둘째는 성공이면 분류 결과(dict)이고, 실패면 `(id, 사유)`입니다. 셋째는 로그 한 줄입니다. 호출이 예외로 끝나면 응답이 없으므로 로그는 `None`입니다. 호출이 `CallError`로 실패해도 예외를 다시 발생시키지 않고 `(id, 사유)`를 돌려주므로, 한 건의 실패가 나머지 건의 처리를 멈추지 않습니다.
- `pool.map(process_one, to_send)`는 `process_one()`을 네 건씩 동시에 실행하고, 결과를 `to_send`와 같은 순서로 돌려줍니다.
- 마지막 부분은 돌려받은 `outcomes`를 성공 목록(`success`), 실패 목록(`failed`), 로그(`logs`)로 나눕니다.

<figure>
<svg viewBox="0 0 680 145" role="img" aria-label="문의 30건이 입력 검사, 호출, 오류 구분, 응답 검사를 거쳐 28건이 성공하고 2건이 빠지는 흐름 그림">
<rect x="10" y="14" width="120" height="58" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="70" y="38" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">1. 입력 검사</text>
<text x="70" y="60" text-anchor="middle" fill="var(--ink)" font-size="14">30건</text>
<line x1="130" y1="43" x2="142" y2="43" stroke="var(--teal)" stroke-width="2"/>
<line x1="70" y1="72" x2="70" y2="96" stroke="var(--amber)" stroke-width="2"/>
<polygon points="70,100 65,90 75,90" fill="var(--amber)"/>
<text x="70" y="118" text-anchor="middle" fill="var(--ink)" font-size="14">빈 문의 1건</text>
<text x="70" y="136" text-anchor="middle" fill="var(--ink-soft)" font-size="13">보내지 않음</text>
<rect x="144" y="14" width="120" height="58" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="204" y="38" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">2. 호출</text>
<text x="204" y="60" text-anchor="middle" fill="var(--ink)" font-size="14">29건</text>
<line x1="264" y1="43" x2="276" y2="43" stroke="var(--teal)" stroke-width="2"/>
<rect x="278" y="14" width="120" height="58" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="338" y="38" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">3. 오류 구분</text>
<text x="338" y="60" text-anchor="middle" fill="var(--ink)" font-size="14">29건</text>
<line x1="398" y1="43" x2="410" y2="43" stroke="var(--teal)" stroke-width="2"/>
<line x1="338" y1="72" x2="338" y2="96" stroke="var(--amber)" stroke-width="2"/>
<polygon points="338,100 333,90 343,90" fill="var(--amber)"/>
<text x="338" y="118" text-anchor="middle" fill="var(--ink)" font-size="14">오류 0건</text>
<rect x="412" y="14" width="120" height="58" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="472" y="38" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">4. 응답 검사</text>
<text x="472" y="60" text-anchor="middle" fill="var(--ink)" font-size="14">29건</text>
<line x1="532" y1="43" x2="544" y2="43" stroke="var(--teal)" stroke-width="2"/>
<line x1="472" y1="72" x2="472" y2="96" stroke="var(--amber)" stroke-width="2"/>
<polygon points="472,100 467,90 477,90" fill="var(--amber)"/>
<text x="472" y="118" text-anchor="middle" fill="var(--ink)" font-size="14">잘림 1건</text>
<text x="472" y="136" text-anchor="middle" fill="var(--ink-soft)" font-size="13">실패 목록으로</text>
<rect x="546" y="14" width="120" height="58" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="606" y="38" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">결과</text>
<text x="606" y="60" text-anchor="middle" fill="var(--ink)" font-size="14">성공 28건</text>
</svg>
<figcaption>예제 1-12에서 문의 30건이 단계를 지나며 필터링된 모습입니다. 실패 목록에 들어간 1건은 최대 출력 토큰을 올려 재시도해 성공했습니다.</figcaption>
</figure>

30건 중 빈 문의 1건은 보내기 전에 필터링했고, 29건을 보내 28건이 성공하고 1건이 실패했습니다. 실패한 Q026은 오류가 난 것이 아니라 응답이 잘린 것입니다. `ask()`의 최대 출력 토큰 300개가 이 문의에는 모자랐습니다. Q026은 예제 1-8에서 여러 모델이 틀린 문의이기도 합니다. 이 응답은 출력 토큰 300개를 모두 쓰고 끊겼습니다. 출력에는 thinking과 응답 텍스트에 각각 몇 토큰을 썼는지 나오지 않습니다. 다만 다른 건은 응답 JSON 한 줄을 쓰는 데 출력 토큰을 40개 남짓 썼으므로, 판단하기 애매한 이 문의에서 thinking이 300토큰의 대부분을 썼을 가능성이 큽니다. 최대 출력 토큰을 1,024토큰으로 올려 재시도하자 444토큰을 쓰고 성공했습니다.

로그에는 요청마다 모델 이름, 토큰 수, 종료 이유를 남겨 둡니다. 나중에 요금과 실패 원인을 확인하는 데 씁니다.

이 한 건에서 응답 검사와 실패 목록이 필요한 이유를 확인할 수 있습니다. 응답 검사가 없었다면 잘린 응답이 성공으로 저장됐을 것이고, 실패 목록이 없었다면 어떤 건을 다시 처리해야 하는지 몰랐을 것입니다.

출력 토큰은 모두 1,953개였습니다. 이 가운데 744개는 Q026 한 건이 썼습니다(잘린 첫 호출 300개와 재시도한 호출 444개). 나머지 28건은 합계 1,209개, 한 건 평균 약 43개로 예제 1-7의 가정(40개)과 비슷했습니다. 추정은 대부분의 건에서 맞았지만, thinking이 길어진 한 건이 전체 출력 토큰의 3분의 1 이상을 썼습니다.

배치 처리 코드에 정한 값(모델, 최대 출력 토큰, 타임아웃, 재시도 횟수, 동시 요청 수)에는 그렇게 정한 근거를 주석으로 남겨 둡니다. 나중에 요금이나 실패가 예상과 다를 때 무엇을 바꿔야 할지 판단할 수 있습니다. 추정은 어림값이므로, 큰 작업은 일부를 먼저 보내 실제 토큰 수를 확인한 뒤 전체를 보냅니다.

## AI 코딩 도구에 수정 맡기기 {원본 p.112-127}

:::요점
기준에 번호를 붙여 주고, 고쳤는지는 도구의 설명이 아니라 검사 결과로 판정합니다.
:::

재시도와 응답 검사 같은 코드는 Claude Code나 opencode에 작성을 맡길 수도 있습니다. 두 도구는 작업 폴더에서 파일을 읽고 고치고 명령을 실행하는 [[코딩 에이전트]]입니다. 이 절과 실습 4에서는 AI 코딩 도구라고 부릅니다. 이때 중요한 것은 도구가 낸 결과가 맞는지를 사람이 판정할 수 있어야 한다는 점입니다. 다음 네 단계로 맡깁니다.

1. **설명 듣기**: "코드는 고치지 말고"라는 조건을 붙여, 지금 코드가 실패를 어떻게 다루는지 묻습니다. 고치기 전 상태를 알아야 무엇이 바뀌었는지 판단할 수 있습니다.
2. **기준 주고 고치기**: 지켜야 할 기준에 번호를 붙여 줍니다. 그러면 도구의 응답과 바뀐 줄을 번호별로 맞춰 볼 수 있습니다.
3. **검사로 확인**: 검사 스크립트를 고치기 전과 후에 실행해 결과를 비교합니다. 도구가 고쳤다고 답해도, 실제로 고쳐졌는지는 검사 스크립트의 출력을 보고 판단합니다.
4. **빈틈 묻기**: 검사가 확인하지 못하는 위험이 남아 있는지 묻습니다. 검사를 통과했다는 것은 검사한 항목이 맞다는 뜻일 뿐입니다.

실습 4의 재료(`코딩도구_실습` 폴더)에 맞춰 보면 다음과 같습니다.

- `send_batch.py`가 고칠 대상입니다. 재시도도 응답 검사도 없는 배치 처리 코드입니다.
- `check.py`가 검사 스크립트입니다. mock 호출로 열 가지 상황(429 뒤 성공, 404, 타임아웃, 잘린 응답 등)을 만들어 `send_batch.py`가 기준대로 동작하는지 확인하고 "결과 N/10 통과"를 출력합니다. API를 부르지 않으므로 요금이 들지 않습니다.
- `보낼_글` 폴더에는 1, 2, 4단계에서 도구에 보낼 글이 있습니다. 2단계의 글에 아래 다섯 기준이 번호와 함께 들어 있습니다.

기준은 이 파트에서 배운 내용 그대로입니다.

1. 재시도할 만한 오류는 대기 시간을 늘리며 정해진 횟수까지 재시도한다.
2. 그 밖의 오류는 재시도하지 않고 예외를 바로 다시 발생시킨다.
3. 재시도 횟수는 한 곳에서만 정한다.
4. 한 건이 실패해도 멈추지 않고, 실패한 건의 id와 사유를 남긴다.
5. 잘린 응답, 거절된 응답, 형식이 틀린 응답은 성공으로 세지 않는다.

검사를 모두 통과해도 남는 위험이 있습니다. `check.py`의 열 가지 검사는 성공한 응답의 분류가 허용된 다섯 가지 중 하나인지, 응답의 id가 보낸 문의의 id와 같은지, 실패 목록이 파일로 저장되는지, 타임아웃이 걸려 있는지를 확인하지 않습니다. 4단계에서 이런 빈틈을 찾아 필요한 것만 기준에 더합니다.

기준을 스스로 설명할 수 있어야 도구에 맡길 수 있습니다. "잘 고쳐 줘"라고만 하면 도구가 무엇을 고쳤는지, 빠뜨린 것은 없는지 확인할 방법이 없습니다. 실습 4에서 직접 해 봅니다.

## Claude의 thinking과 effort {원본 p.38-40, 59-62}

:::요점
thinking에 쓴 토큰은 출력 토큰으로 계산됩니다. `effort`를 낮추면 thinking과 응답 텍스트에 쓰는 토큰이 함께 줄어듭니다.
:::

이 절은 Anthropic API로 Claude 모델을 쓸 때 해당하는 내용입니다.

[[thinking]]은 모델이 응답을 쓰기 전에 문제를 풀어 보는 과정입니다. 현행 Claude 모델은 필요하다고 판단하면 스스로 thinking을 합니다. 쉬운 질문에는 thinking 없이 바로 답하고, 어려운 질문에는 thinking을 길게 합니다. 응답에서는 `thinking` 블록으로 나타나고, thinking에 쓴 토큰은 출력 토큰으로 계산됩니다.

Claude 5 이후 모델은 `thinking` 블록의 `thinking` 필드를 기본으로 빈 문자열로 돌려줍니다. thinking 내용의 요약을 받으려면 요청에 `thinking={'type': 'adaptive', 'display': 'summarized'}`를 넣습니다. 내용을 받든 받지 않든 thinking에 쓴 토큰은 모두 출력 토큰으로 요금이 계산됩니다(Anthropic 문서, 2026-11-26 확인).

[[effort]]는 모델이 응답 하나에 쓰는 출력 토큰의 양을 조절하는 설정입니다. thinking뿐 아니라 응답 텍스트와 도구 호출에도 적용됩니다. 값은 `low`, `medium`, `high` 등이 있고, 모델에 따라 `xhigh`와 `max`도 받습니다. 낮을수록 thinking을 덜 하고 전체 토큰 사용량이 줄어듭니다. 요청의 `output_config` 안에 넣습니다. 넣지 않으면 기본 등급(`claude-sonnet-5-5`)은 `high`, 소형(`claude-haiku-5-5`)과 대형(`claude-opus-5-5`)은 `medium`으로 동작합니다(Anthropic 문서, 2026-11-26 확인). 이 파트의 다른 예제는 `effort`를 넣지 않았으므로 이 기본값으로 실행했습니다.

:::예제 보충A effort에 따른 차이
```python
# 예제 보충A
if llm.provider() == 'anthropic':
    import anthropic

    client = anthropic.Anthropic()
    puzzle = ('한 로트는 웨이퍼 25장입니다. 장비 한 대는 한 번에 6장까지 처리하고 한 번에 40분이 걸립니다. '
              '장비 두 대로 3로트를 처리하는데, 서로 다른 로트의 웨이퍼를 한 번에 섞어 넣을 수 없습니다. '
              '모두 처리하는 데 걸리는 최소 시간은 몇 분입니까? 답과 근거를 두 문장으로 알려 주세요.')
    for effort in ['low', 'high']:
        started = time.time()
        response = client.messages.create(
            model=llm.model_name('기본'),
            max_tokens=4000,
            output_config={'effort': effort},
            messages=[{'role': 'user', 'content': puzzle}],
        )
        answer = ''.join(block.text for block in response.content if block.type == 'text')
        print(f"effort={effort}: {time.time() - started:.1f}초, 출력 {response.usage.output_tokens}토큰"
              f", 블록 {[block.type for block in response.content]}, 응답 {answer!r}")
else:
    print('Anthropic을 쓰지 않으므로 건너뜁니다.')
```
:::

두 설정 모두 응답은 320분으로 같았습니다. `high`에서는 `thinking` 블록이 생겼고 출력 토큰이 222개에서 398개로 늘었습니다. 한 번 실행한 결과이므로 차이의 크기는 실행마다 달라집니다. 분류처럼 쉬운 일을 대량으로 처리할 때는 `effort`를 낮추면 시간과 요금을 줄일 수 있습니다. 판단이 어려운 일에서는 낮춘 만큼 정확도가 떨어질 수 있으므로, 모델 등급을 고를 때와 같이 표본으로 측정해 정합니다.

thinking이 있는 모델에서는 최대 출력 토큰을 넉넉히 줍니다. thinking이 최대 출력 토큰을 다 쓰면 응답이 비거나 잘립니다(예제 1-2, 1-12).

## 실습

실습은 `2일차_실습.ipynb`에서 합니다. 실습 1과 3에는 테스트 셀이 있어, mock 호출로 여러분의 함수가 맞게 동작하는지 알려 줍니다. 실습 4는 `코딩도구_실습/check.py`로 판정합니다. 풀이와 해설은 `2일차_실습_풀이.ipynb`에 있습니다.

:::실습 1 대화 이력을 관리하는 함수
대화 이력에 질문을 넣어 보내고 응답도 이력에 넣는 `chat()` 함수를 작성합니다. 최근 몇 턴만 보내는 옵션을 더한 뒤, 5턴 대화에서 전체를 보낼 때와 최근 2턴만 보낼 때의 입력 토큰을 비교합니다. 풀이와 숫자를 비교할 수 있도록 소형 모델에 최대 출력 토큰 500으로 보냅니다.

완료 기준: 테스트 셀이 "실습 1 통과"를 출력하고, 두 경우의 입력 토큰 합계를 적습니다.
:::

:::실습 2 비용을 추정하고 모델 고르기
새 문의 60건을 보내기 전에 요금을 추정합니다. 그다음 정답이 있는 20건을 소형 모델과 기본 모델로 분류해 정확도, 시간, 요금을 비교하고 모델을 고릅니다.

완료 기준: 추정 요금, 모델별 정확도와 시간과 요금, 선택 근거 한 문장이 있습니다.
:::

:::실습 3 끝까지 처리하는 배치 처리 코드
`ask()`, `check_reply()`, `is_valid()`, `process_all()`을 직접 작성합니다. 재료에는 빈 문의 2건과 연락처가 든 문의 2건이 섞여 있어 보내기 전에 필터링해야 합니다. 긴 문의도 2건 있지만 1,000자를 넘지 않으므로 그대로 보냅니다.

완료 기준: 테스트 셀이 "결과 10/10 통과"와 "입력 검사 통과"를 출력하고, 60건을 처리한 성공 건수와 실패 건수, 실제 요금을 확인합니다.
:::

:::실습 4 AI 코딩 도구에 수정 맡기고 검사로 확인하기
재시도도 응답 검사도 없는 `코딩도구_실습/send_batch.py`를 Claude Code나 opencode에 맡겨 고칩니다. 실습 3과 같은 열 가지 검사로 결과를 판정합니다.

완료 기준: `python check.py`가 "결과 10/10 통과"를 출력하고, 도구가 바꾼 줄을 기준 1~5와 짝지어 설명할 수 있습니다.
:::

풀이를 실행한 결과는 다음과 같습니다. 여러분의 숫자와 비교해 봅니다.

| 실습 | 풀이 실행 결과 (2026-11-19, Claude 모델) |
| --- | --- |
| 실습 1 | 전체 전송: 호출별 입력 토큰 41, 187, 525, 821, 1,156(합계 2,730). 최근 2턴 전송: 41, 167, 436, 554, 519(합계 1,717) |
| 실습 2 | 추정 요금: 소형 $0.0040, 기본 $0.0797. 표본 20건: 소형은 20건 정답, 20.8초, $0.0015. 기본은 19건 정답, 32.2초, $0.0292 |
| 실습 3 | 60건 중 4건을 보내기 전에 필터링. 56건 성공, 실패 0건. 입력 27,251토큰, 출력 3,426토큰, 요금 $0.0044. 정답 55건 |
| 실습 4 | 고치기 전 4/10 통과. 풀이 파일은 10/10 통과 |

## 핵심 정리

- LLM API 호출은 요청 하나에 응답 하나입니다. 요청에는 모델 이름, 최대 출력 토큰, 메시지 목록을 넣고, 응답에서는 응답 텍스트, 토큰 수, 종료 이유를 읽습니다.
- 길이 제한과 요금은 토큰으로 계산합니다. 출력 토큰이 입력 토큰보다 비싸고, thinking에 쓴 토큰도 출력 토큰입니다.
- 서버는 앞 대화를 기억하지 않습니다. 대화를 이으려면 이력을 다시 보내야 하고, 이력이 길수록 입력 토큰이 늘어납니다.
- 같은 질문에도 응답은 매번 다릅니다. 한 번의 결과로 판단하지 않고 여러 건으로 측정합니다.
- 모델은 정답이 있는 표본으로 측정해 고릅니다. 틀린 건은 직접 읽고, 규칙이 모호한지 먼저 확인합니다.
- 실패는 세 가지입니다. 재시도할 오류는 백오프를 두고 재시도하고, 고쳐야 풀리는 오류는 재시도하지 않고 바로 멈추며, 오류 없이 왔지만 쓸 수 없는 응답은 응답 검사로 찾아냅니다.
- 배치 처리는 입력 검사, 호출, 오류 구분, 응답 검사, 실패 기록의 순서로 만듭니다.

## 자가점검

**1.** 두 번째 호출에서 모델이 첫 번째 호출의 내용을 참고해 답하게 하려면 무엇을 해야 합니까?

- A. 같은 `client` 객체로 한 번 더 호출한다
- B. 앞의 질문과 응답을 메시지 목록에 넣어 함께 보낸다
- C. 시스템 프롬프트에 "앞 대화를 기억해"라고 적는다

:::정답
**B.** 서버는 이전 요청을 기억하지 않습니다. 같은 `client`를 쓰는 것은 관계가 없고, 기억하라고 지시해도 서버에 남는 것이 없습니다. "대화 이력" 절을 다시 봅니다.
:::

**2.** 출력을 한 건에 40토큰으로 가정해 요금을 추정했는데 실제 출력 토큰이 더 많이 나왔습니다. 가장 가능성이 큰 이유는 무엇입니까?

- A. 입력 단가가 출력 단가보다 비싸서
- B. 토큰을 세어 주는 기능이 틀린 값을 줘서
- C. thinking에 쓴 토큰도 출력 토큰에 들어가서

:::정답
**C.** thinking을 하는 모델은 응답 텍스트 외에 thinking에 쓴 토큰도 출력 토큰으로 계산합니다. 토큰 세기 기능은 입력 토큰을 세는 것이라 출력과 관계가 없습니다.
:::

**3.** 분류 규칙(역할, 분류의 종류, 출력 형식)은 요청의 어디에 넣습니까? Anthropic API와 OpenAI 호환 API 각각에 대해 답해 보세요.

:::정답
둘 다 시스템 프롬프트로 넣습니다. Anthropic API는 `system` 인자로 따로 넣고, OpenAI 호환 API는 메시지 목록의 첫 메시지에 역할을 `system`으로 해서 넣습니다.
:::

**4.** 오류 없이 응답이 왔는데 종료 이유가 `max_tokens`(OpenAI 호환은 `length`)입니다. 이 응답을 어떻게 다룹니까?

- A. 응답이 잘린 것이므로 실패로 처리하고, 최대 출력 토큰을 올려 재시도한다
- B. 오류가 없었으므로 그대로 저장한다
- C. 키가 잘못된 것이므로 키를 바꾼다

:::정답
**A.** 예제 1-12의 Q026이 이 경우였습니다. 응답 검사로 찾아 실패 목록에 넣고, 최대 출력 토큰을 올려 재시도했습니다.
:::

**5.** 휴대폰 번호가 적힌 문의를 보내기 전에 필터링했습니다. 가장 큰 이유는 무엇입니까?

- A. 보낸 내용은 API를 운영하는 곳의 서버로 전달되므로 개인정보를 보내지 않으려고
- B. 번호가 길어 입력 토큰이 많이 늘기 때문에
- C. 모델이 숫자를 읽지 못해 오류가 나기 때문에

:::정답
**A.** 토큰 수는 거의 늘지 않고, 모델은 숫자를 읽을 수 있습니다. 무엇을 보내도 되는지는 회사의 기준을 따릅니다.
:::

**6.** "재시도할 오류"와 "바로 멈출 오류"를 하나씩 들고, 왜 그렇게 나누는지 한 문장으로 써 보세요.

:::정답
예: 재시도할 오류는 429(레이트 리밋 초과), 바로 멈출 오류는 401(인증 실패). 429는 기다리면 풀리지만 401은 키를 고치기 전에는 몇 번을 보내도 똑같이 실패하기 때문입니다.
:::

**7.** 대화가 10턴째입니다. 이력 전체를 보내는 방식에서 10번째 호출의 입력 토큰이 1번째 호출보다 훨씬 많은 이유를 설명해 보세요. 이를 줄이는 방법 하나와 그 방법의 단점도 함께 써 보세요.

:::정답
10번째 호출에는 앞선 아홉 번의 질문과 응답이 모두 다시 들어가기 때문입니다. 최근 몇 턴만 남겨 보내면 입력 토큰이 줄지만, 잘려 나간 앞 대화의 내용은 모델이 알 수 없습니다.
:::

**8.** 재시도를 SDK의 자동 재시도와 직접 만든 재시도 두 곳에 모두 두면 어떤 문제가 생깁니까?

:::정답
전체 시도 횟수가 두 횟수의 곱이 됩니다. SDK가 3번, 직접 만든 코드가 3번이면 최대 9번을 보내므로, 실패한 건에서 대기 시간과 요금이 예상보다 크게 늘어납니다. 재시도 횟수는 한 곳에서만 정합니다.
:::

**9.** 세 등급의 모델이 같은 문의를 모두 같은 분류로 틀렸습니다. 모델 등급을 올리기 전에 무엇을 확인해야 합니까?

:::정답
정답 라벨과 분류 규칙을 확인합니다. 모든 모델이 같은 분류를 냈다면 규칙이 모호하거나 정답이 잘못 정해졌을 가능성이 큽니다. 이런 건은 모델 등급을 올려도 해결되지 않습니다.
:::

## 원본과 달라진 점

이 파트는 원본 강의안 2일차 p.25–175를 토대로 다시 구성했습니다. 문장을 다듬은 것은 적지 않고, 내용이 달라진 것만 적습니다.

### 예제, 실습, 재료 대응

| 원본 | 교재 | 달라진 점 |
| --- | --- | --- |
| 예제 1-1 (1)(2) | 예제 1-1 | Anthropic과 OpenAI 호환 호출을 나란히 실음 |
| 예제 1-1 (8) 앞부분 | 예제 1-2 | |
| 예제 1-1 (3) | 예제 1-3 | 응답이 달라지는 이유(샘플링) 설명을 추가 |
| 예제 1-1 (4) | 예제 1-4 | 분류 규칙에 라벨의 정의와 우선순위를 넣음. "기타" 라벨 추가 |
| 예제 1-1 (5) | 예제 1-5 | 새로 구성. 원본은 서로 무관한 분류 문의를 이력으로 쌓아 이력이 왜 필요한지 드러나지 않았음. 앞 응답을 알아야 답할 수 있는 질문으로 바꿈 |
| 예제 1-1 (6)(7) | 예제 1-6 | 대화형 질문으로 바꿈 |
| 예제 1-2 (1)(2)(3) | 예제 1-7 | 토큰을 세어 주지 않는 API에서 추정하는 방법을 추가 |
| 예제 1-2 (4)(5) | 예제 1-8 | 새로 구성. 원본은 대형 모델의 답을 기준으로 "같은 답 수"를 셌음. 정답 라벨로 정확도를 측정하도록 바꿈 |
| 예제 1-2 (6) | 예제 1-12에 통합 | |
| 예제 1-3 (1)(2) | 예제 1-9 | |
| 예제 1-3 (3)(9)(10) | 예제 1-10 | mock 호출을 노트북 안에서 넣어 재시도 동작을 확인 |
| 예제 1-3 (4)~(8) | "AI 코딩 도구에 수정 맡기기" 절, 실습 4 | Claude Code와 opencode 어느 쪽으로도 할 수 있게 바꿈. 특정 도구의 화면 설명은 뺌 |
| 예제 1-3 (11) | 예제 1-11 | JSON으로 실제로 읽어 보는 검사로 강화 |
| 예제 1-3 (12) | 예제 1-12 | 실패한 건을 다시 처리하는 단계를 추가 |
| 예제 1-1 (8) 뒷부분 | 보충A | 차이가 드러나는 문제로 교체 |
| 실습 미션 1 | 실습 1, 2, 3 | 준비된 셀을 실행하는 방식에서, 함수를 직접 작성하고 테스트 셀로 검증하는 방식으로 바꿈 |
| 확장 미션 1 | 뺌 | 실습 3과 4가 같은 내용을 다룸 |
| `inquiries_120.csv`, `2일차_미션1_재료.csv` | `문의_예제.csv`(100건), `문의_실습.csv`(60건)와 정답 파일 | 새로 작성. 정답 라벨과 엣지 케이스 표시를 추가. 원본 문의의 주제와 문체를 따른 가상 데이터 |
| `day02-cc/` | `코딩도구_실습/` | 새로 작성. Anthropic과 사내 API 어느 설정에서도 동작. 검사 열 가지는 유지하되 7번을 "SDK 자동 재시도 끔"에서 "400 오류는 다시 보내지 않음"으로 바꿈 |

### 추가한 내용

- 파트의 과제와 재료를 먼저 소개하는 절(문의 목록의 예, 응답의 예, 진행 순서)
- LLM API와 채팅 화면의 관계, SDK가 하는 일
- 토큰이 무엇이고 글자 수와 왜 다른지, 컨텍스트 윈도우와 최대 출력 토큰의 차이
- 응답이 매번 달라지는 이유(샘플링)와 temperature
- OpenAI 호환 API에서의 호출 방법, 시스템 프롬프트의 위치, 종료 이유의 값
- 레이트 리밋이 무엇인지, 병렬 처리와의 관계
- 모델 비교에서 표본 고르기와 틀린 건 읽기, 대형 모델을 기준으로 삼을 때의 한계
- 재시도 횟수 계산의 전제(실패가 서로 무관하지 않음), 재시도해도 안전한 일인지 확인하기, 서버가 알려 주는 대기 시간, 대기 시간에 무작위 값을 더하는 방법
- 문장으로 거절한 응답은 종료 이유로 알 수 없다는 점
- 종료 이유의 전체 값 표(Anthropic 7가지, OpenAI 호환 5가지)와 "정상 종료일 때만 쓴다"는 작성 원칙
- 입력 검사에서 개인정보를 필터링하는 이유
- Claude 5 이후 모델이 thinking 블록의 내용을 기본으로 비워 돌려준다는 점, effort의 모델별 기본값
- 소형 모델의 긴 입력(10만 토큰 초과) 단가, OpenAI 공식 API의 `max_completion_tokens`
- `llm.send()`의 타임아웃(60초), 직접 만든 재시도가 `retry-after`를 읽지 않을 때의 한계
- 자가점검 3, 7, 8, 9번과 모든 문항의 정답과 해설(원본 퀴즈에는 정답이 없음)

### 고친 내용

| 원본 | 교재 | 이유 |
| --- | --- | --- |
| temperature 설명 "최신 SDK에 없음", "넣으면 TypeError" (p.63) | 현행 Claude 모델이 샘플링 값을 받지 않는다는 이유와, OpenAI 호환 API는 다를 수 있다는 점을 함께 설명 | 원본의 설명은 사실이지만 이유가 없음 |
| 경량 모델 `claude-haiku-4-5`, 단가 $1 / $5 (p.21, 67) | 소형 모델 `claude-haiku-5-5`, 단가 $0.10 / $0.50 | 현행 모델로 바꿈(2026-11-03 확인) |
| "출력 115에는 생각 토큰 62도 들어 있습니다" (p.40), 실행 결과는 출력 112 (p.39) | 한 번의 실행 결과로 통일 | 원본의 두 쪽이 서로 다른 실행의 값 |
| "세 번까지 보내면 남는 실패가 0.022%" (p.108–110) | 같은 계산을 싣되 실패가 서로 무관하다는 전제를 밝힘 | 서버 과부하 때는 실패가 연달아 일어남 |
| 분류 라벨 4종 (p.45) | 5종("기타" 추가) | 원본 재료에 네 라벨 어디에도 맞지 않는 글이 있음 |
| 재시도할 예외 목록에 `OverloadedError`(529)를 넣음 (p.128) | 500번대는 예외 이름이 아니라 상태 코드로 판단 | `OverloadedError`는 `anthropic` SDK에만 있어 사내 API에서는 쓸 수 없음 |

### 삭제한 내용

- 오리엔테이션과 로드맵 (p.2–10, 26–29): 학습 목표로 대체
- "예제에서 하는 일과 배우는 이유" 슬라이드 (p.33, 66, 96): 각 절의 도입 문장으로 대체
- Colab 사본 저장, 보안 비밀 등록 순서 (p.13–20): 환경 준비 장에서 환경 변수 설명으로 대체
- 키 한도와 회수, 제출 방법 (p.12, 153): 강의 운영 안내
- 코드마다 붙은 "Claude Code에 물어보기" 주석
- Claude Code 권한 카드 화면 설명 (p.116): 특정 도구의 화면
- 한 건씩 보낼 때와 동시에 보낼 때의 시간을 측정한 비교 (p.90–93): 병렬 처리의 원리와 주의점은 설명했지만 비교 측정은 싣지 않았습니다
- 재시도를 네 번째까지 늘렸을 때의 계산 (p.110), `client.max_retries`와 `client.timeout`으로 기본값을 확인하는 코드 (p.103–106): 기본값과 결론만 본문에 적었습니다
- 입력 길이 기준과 최대 출력 토큰을 바꿔 가며 결과를 비교하는 미션 과제 (p.149, 170–172): 최대 출력 토큰을 정하는 방법은 본문에 설명으로 넣었습니다
