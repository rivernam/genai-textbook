# 5장 LLM API

강의 2일차 파트 1에 해당합니다.

채팅 화면에서는 질문을 한 건씩 붙여 넣고 응답을 눈으로 읽습니다. 같은 일을 문의 1만 건에 하려면 프로그램이 LLM(large language model)에 요청을 보내고 응답을 받아야 합니다. 이 장은 요청과 응답에 무엇이 들어 있는지, 요금이 어떻게 계산되는지, 어떤 모델 등급을 고를지, 요청이 어떻게 실패하는지를 설명합니다.

## 학습 목표

1. API(application programming interface) 요청에 넣는 값과 응답으로 돌아오는 값(응답 텍스트, 토큰 사용량, 종료 이유)을 설명하고, Anthropic SDK(software development kit)와 OpenAI 호환 SDK로 같은 요청을 보낼 수 있습니다.
2. 요금이 입력 토큰과 출력 토큰으로 계산되고 thinking 토큰도 출력 토큰에 들어간다는 것을 설명하고, 대량 작업의 요금을 보내기 전에 어림할 수 있습니다.
3. 같은 문의를 모델 등급별로 보내 정확도, 시간, 요금을 측정하고 그 결과로 등급을 고를 수 있습니다.
4. 실패를 기다리면 풀리는 오류, 요청을 고쳐야 풀리는 오류, 예외 없이 끝난 실패로 나누고, 각각을 어떻게 처리할지 설명할 수 있습니다.
5. effort와 프롬프트 캐싱이 각각 어떤 토큰을 줄여 요금을 낮추는지 설명할 수 있습니다.

예제 5-1~5-3은 API로 서비스 모델을 호출합니다. 예제 5-1의 effort 비교는 Anthropic API에서만 실행됩니다. 모델의 응답, 토큰 수, 걸린 시간은 실행할 때마다 교재와 다를 수 있습니다.

## 요청과 응답

:::요점
프로그램은 모델 이름, 최대 출력 토큰, 메시지 목록을 담은 요청을 보내고, 응답 텍스트, 토큰 사용량, 종료 이유를 담은 응답을 받습니다. 응답 텍스트만 읽지 않고 종료 이유를 먼저 확인합니다.
:::

[[API]](application programming interface)는 프로그램이 다른 프로그램의 기능을 정해진 형식으로 요청하고 결과를 받는 인터페이스입니다. LLM API에서 프로그램이 보내는 한 번의 [[요청]](request)에는 어느 모델에 보낼지, 출력을 최대 몇 토큰까지 허용할지, 무엇을 물을지가 들어 있습니다. 서버는 모델이 생성한 글과 그 과정의 기록을 [[응답]](response)으로 돌려줍니다. 요청과 응답은 HTTP로 주고받지만, 이를 직접 조립하지 않고 [[SDK]](software development kit)를 씁니다. SDK는 요청을 조립하고, 응답을 파이썬 객체로 바꾸고, 실패를 파이썬 예외로 바꿔 주는 라이브러리입니다.

<figure>
<svg viewBox="0 0 680 236" role="img" aria-label="요청과 응답의 구성. 요청에는 model(모델 이름), max_tokens(최대 출력 토큰), system(시스템 프롬프트), messages(메시지 목록), output_config(effort와 출력 형식, Anthropic만)가 들어갑니다. API 서버에서 모델이 토큰을 생성한 뒤, 응답에는 content(thinking 블록과 text 블록), usage(입력 토큰, 출력 토큰, 그중 thinking 토큰), stop_reason(종료 이유)이 들어 있습니다.">
<rect x="10" y="30" width="250" height="196" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="135" y="20" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">요청</text><text x="24" y="58" fill="var(--teal)" font-size="12" font-weight="700">model</text><text x="120" y="58" fill="var(--ink)" font-size="12">모델 이름</text><text x="24" y="92" fill="var(--teal)" font-size="12" font-weight="700">max_tokens</text><text x="120" y="92" fill="var(--ink)" font-size="12">최대 출력 토큰</text><text x="24" y="126" fill="var(--teal)" font-size="12" font-weight="700">system</text><text x="120" y="126" fill="var(--ink)" font-size="12">시스템 프롬프트</text><text x="24" y="160" fill="var(--teal)" font-size="12" font-weight="700">messages</text><text x="120" y="160" fill="var(--ink)" font-size="12">메시지 목록</text><text x="24" y="194" fill="var(--teal)" font-size="12" font-weight="700">output_config</text><text x="120" y="194" fill="var(--ink)" font-size="12">effort, 출력 형식</text><text x="120" y="212" fill="var(--ink-soft)" font-size="11">(Anthropic만)</text>
<line x1="266" y1="128" x2="300" y2="128" stroke="var(--teal)" stroke-width="2"/><polygon points="300,123 308,128 300,133" fill="var(--teal)"/><rect x="312" y="96" width="96" height="64" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="360" y="122" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">API 서버</text><text x="360" y="142" text-anchor="middle" fill="var(--ink-soft)" font-size="11">토큰을 생성</text><line x1="412" y1="128" x2="414" y2="128" stroke="var(--teal)" stroke-width="2"/><polygon points="414,123 422,128 414,133" fill="var(--teal)"/>
<rect x="426" y="30" width="244" height="196" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="548" y="20" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">응답</text><text x="440" y="58" fill="var(--teal)" font-size="12" font-weight="700">content</text><rect x="440" y="68" width="100" height="24" rx="4" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="490" y="84" text-anchor="middle" fill="var(--ink)" font-size="11">thinking 블록</text><rect x="548" y="68" width="108" height="24" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="602" y="84" text-anchor="middle" fill="var(--ink)" font-size="11">text 블록(응답)</text><text x="440" y="122" fill="var(--teal)" font-size="12" font-weight="700">usage</text><text x="440" y="142" fill="var(--ink)" font-size="12">입력 토큰, 출력 토큰</text><text x="440" y="160" fill="var(--ink-soft)" font-size="11">(출력 토큰에 thinking 토큰 포함)</text><text x="440" y="192" fill="var(--teal)" font-size="12" font-weight="700">stop_reason</text><text x="530" y="192" fill="var(--ink)" font-size="12">종료 이유</text>
</svg>
<figcaption>요청 하나에 응답 하나가 돌아오며, 응답에는 생성한 글과 함께 토큰 사용량과 종료 이유가 들어 있습니다.</figcaption>
</figure>

요청에 꼭 넣는 값은 세 가지입니다. `model`은 모델 이름, `max_tokens`는 [[최대 출력 토큰]], `messages`는 대화의 [[메시지]] 목록입니다. 시스템 프롬프트(3장)는 Anthropic API에서는 `system` 파라미터로, OpenAI 호환 API에서는 `messages` 맨 앞의 system 메시지로 보냅니다.

응답에서는 세 가지를 읽습니다. 응답 텍스트는 Anthropic API에서는 `content` 목록의 `text` 블록에 있고, 그 앞에 thinking 블록이 올 수 있습니다(2장). `usage`는 이 요청에 쓴 토큰 수이고, 요금은 이 값으로 계산합니다. [[종료 이유]](stop reason)는 모델이 생성을 멈춘 이유입니다. 종료 이유가 정상 종료가 아니면 응답 텍스트가 있어도 그대로 쓰지 않습니다. 조건은 "정상 종료일 때만 쓴다"로 작성합니다. "잘림이면 버린다"로 작성하면 새로 생긴 종료 이유가 왔을 때 잘못된 응답을 저장합니다.

| 뜻 | Anthropic `stop_reason` | OpenAI 호환 `finish_reason` | `llm.py`의 `Reply.stop_reason` |
| --- | --- | --- | --- |
| 정상 종료 | `end_turn` | `stop` | `end` |
| 최대 출력 토큰이나 컨텍스트 윈도우에 닿아 잘림 | `max_tokens`, `model_context_window_exceeded` | `length` | `max_tokens` |
| 안전 기준에 따른 거절 | `refusal` | `content_filter` | `refusal` |

이 교재의 예제는 공통 호출 함수 `llm.py`로 요청을 보냅니다. `llm.send()`는 요청을 한 번 보내고, `llm.ask()`는 여기에 재시도("실패 유형" 절)를 더합니다. 두 함수 모두 어느 SDK를 쓰든 같은 `Reply`(응답 텍스트 `text`, `input_tokens`, `output_tokens`, `stop_reason`, `seconds`)를 돌려줍니다. 두 SDK를 직접 부르는 코드는 예제 5-1에서 한 번만 나란히 보여 줍니다.

## 토큰과 요금

:::요점
요금은 입력 토큰 수와 출력 토큰 수에 각각의 단가를 곱해 더한 값이고, 출력 단가가 입력의 5배입니다. thinking 토큰은 응답에 보이지 않아도 출력 토큰으로 계산되므로, 요금을 어림할 때 출력을 응답 텍스트 길이만으로 잡으면 적게 나옵니다.
:::

LLM API의 요금은 토큰 수로 계산합니다. [[단가]](price)는 토큰 100만 개당 요금이고, 입력 토큰과 출력 토큰의 단가가 다릅니다. Anthropic API의 현행 모델은 세 등급 모두 출력 단가가 입력 단가의 5배입니다(아래 표, 2026-11 확인). 출력이 더 비싼 이유는 생성 방식에 있습니다. 모델은 입력 전체를 한 번의 계산으로 읽지만, 출력은 1장의 반복대로 토큰 하나마다 계산을 한 번씩 합니다.

| 교재의 등급 | Anthropic 기본 모델 | 입력 단가 | 출력 단가 | 캐시 읽기 단가 |
| --- | --- | --- | --- | --- |
| 소형 | Claude Haiku 5.5 | 0.10달러 | 0.50달러 | 0.01달러 |
| 기본 | Claude Sonnet 5.5 | 2달러 | 10달러 | 0.10달러 |
| 대형 | Claude Opus 5.5 | 4달러 | 20달러 | 0.20달러 |

Haiku 5.5의 단가는 프롬프트가 10만 토큰 이하일 때의 값이고, 넘으면 입력 0.50달러, 출력 2.50달러입니다. 캐시 읽기 단가는 "프롬프트 캐싱" 절에서 설명합니다. 사내 API의 단가는 사내 안내를 따릅니다.

출력 토큰에는 응답 텍스트뿐 아니라 thinking 토큰도 들어갑니다(2장). 현행 Claude 모델은 thinking 내용을 기본으로 보여 주지 않지만, 생성한 thinking 토큰은 모두 출력 토큰으로 요금이 붙습니다. 그래서 짧게 답한 응답도 출력 토큰이 수백 개일 수 있습니다.

<figure>
<svg viewBox="0 0 680 150" role="img" aria-label="입력 1,000토큰, thinking 200토큰, 응답 텍스트 100토큰인 요청을 기본 등급 단가로 계산한 그림. 토큰 수로는 입력이 1,300토큰 가운데 77%이지만, 요금 0.005달러 가운데 입력은 0.002달러(40%), thinking이 0.002달러(40%), 응답 텍스트가 0.001달러(20%)입니다.">
<text x="10" y="44" fill="var(--ink)" font-size="12" font-weight="700">토큰 수</text><rect x="100" y="26" width="385" height="28" fill="var(--sheet)" stroke="var(--line)"/><text x="292" y="45" text-anchor="middle" fill="var(--ink)" font-size="12">입력 1,000</text><rect x="485" y="26" width="77" height="28" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="523" y="45" text-anchor="middle" fill="var(--ink)" font-size="11">thinking 200</text><rect x="562" y="26" width="38" height="28" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="581" y="45" text-anchor="middle" fill="var(--ink)" font-size="11">100</text><text x="610" y="45" fill="var(--ink-soft)" font-size="12">1,300</text>
<text x="10" y="98" fill="var(--ink)" font-size="12" font-weight="700">요금</text><rect x="100" y="80" width="200" height="28" fill="var(--sheet)" stroke="var(--line)"/><text x="200" y="99" text-anchor="middle" fill="var(--ink)" font-size="12">입력 0.002달러</text><rect x="300" y="80" width="200" height="28" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="400" y="99" text-anchor="middle" fill="var(--ink)" font-size="12">thinking 0.002달러</text><rect x="500" y="80" width="100" height="28" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="550" y="99" text-anchor="middle" fill="var(--ink)" font-size="11">응답 0.001달러</text><text x="610" y="99" fill="var(--ink-soft)" font-size="12">0.005달러</text>
<text x="340" y="138" text-anchor="middle" fill="var(--ink-soft)" font-size="12">기본 등급 단가(입력 2달러, 출력 10달러)로 계산한 예. 주황색은 응답에 보이지 않는 thinking 토큰입니다</text>
</svg>
<figcaption>출력 단가가 입력의 5배이므로 토큰 수의 23%인 출력(thinking 포함)이 요금의 60%를 차지합니다.</figcaption>
</figure>

thinking에 쓴 토큰 수는 응답에서 따로 확인할 수 있습니다. Anthropic API는 `usage.output_tokens_details.thinking_tokens`에 출력 토큰 가운데 thinking에 쓴 수를 적어 줍니다. 이 값은 요약해서 돌려준 thinking 글이 아니라 모델이 실제로 생성한 thinking 토큰의 수이고, `output_tokens`에 이미 포함되어 있습니다(2026-11 확인). OpenAI 호환 API는 `usage.completion_tokens_details.reasoning_tokens`라는 같은 뜻의 필드가 있지만, 서버가 이 값을 채우지 않으면 비어 있습니다.

### 보내기 전에 토큰 세기

요금을 미리 어림하려면 입력 토큰 수를 알아야 합니다. Claude의 토크나이저는 공개되어 있지 않으므로, Anthropic API가 제공하는 [[토큰 세기]](token counting) 기능으로 셉니다. 요청과 같은 모델, 시스템 프롬프트, 메시지를 보내면 생성 없이 입력 토큰 수만 돌려줍니다. 요금은 들지 않고, 분당 요청 수의 상한만 따로 있습니다. 돌려주는 값은 추정값이라 실제 요청의 입력 토큰과 조금 다를 수 있습니다(2026-11 확인). `llm.count_tokens()`가 이 기능을 부르고, OpenAI 호환 API에는 표준 기능이 없어 `None`을 돌려줍니다. 그때는 몇 건을 실제로 보내 `Reply.input_tokens`로 어림합니다.

출력 토큰은 보내기 전에 셀 수 없습니다. 몇 건을 실제로 보내 출력 토큰의 평균을 측정하고, 그 값으로 전체를 어림합니다. 이때 출력에 thinking 토큰이 들어 있다는 점을 빼놓지 않습니다.

## thinking의 양을 정하는 effort

:::요점
effort는 모델이 응답 하나에 토큰을 얼마나 쓸지 정하는 Anthropic API의 설정입니다. 낮추면 thinking과 응답 텍스트 모두 짧아져 출력 토큰과 시간이 줄고, 어려운 문제에서는 정확도도 함께 낮아질 수 있습니다.
:::

[[effort]]는 `output_config`의 `effort` 값으로, `low`, `medium`, `high`, `xhigh`, `max` 가운데 하나를 넣습니다. 값을 넣지 않으면 모델마다 정해진 기본값을 씁니다. Claude Haiku 5.5와 Claude Opus 5.5는 `medium`, Claude Sonnet 5.5는 `high`가 기본값입니다(2026-11 확인). effort는 thinking뿐 아니라 응답 텍스트와 도구 호출을 포함한 모든 출력 토큰에 작용합니다.

effort는 정해진 토큰 수의 상한이 아닙니다. 낮은 effort에서도 어려운 문제에는 thinking을 하고, 같은 문제에서 높은 effort일 때보다 적게 할 뿐입니다. 최대 출력 토큰은 thinking과 응답 텍스트를 합친 길이를 자르는 상한이므로, effort를 높일 때는 `max_tokens`도 넉넉하게 둡니다. 분류처럼 답이 정해진 일은 낮은 effort부터 시험하고, 정확도가 떨어지는지 표본으로 확인한 뒤 정합니다.

OpenAI 호환 API에는 effort에 해당하는 표준 파라미터가 없고, `llm.py`의 함수도 effort를 받지 않습니다. 아래 예제는 Anthropic SDK를 직접 불러 effort를 바꿔 봅니다.

:::예제 5-1 SDK로 직접 보내기
같은 계산 문제를 SDK로 직접 보내고, 응답의 블록 종류, 종료 이유, 입력 토큰, 출력 토큰과 그중 thinking 토큰을 봅니다. Anthropic 쪽은 effort를 `low`와 `high`로 바꿔 두 번 보내고 출력 토큰이 어떻게 다른지 봅니다. 두 코드 가운데 지금 쓰는 API에 해당하는 쪽만 실행되고, 이 셀은 API를 2번(OpenAI 호환은 1번) 호출합니다.

:::탭 Anthropic
```python
question = 'UPH 1,200인 와이어 본더 3대가 하루 22시간, 가동률 87%로 돌면 하루 생산량은 몇 개입니까? 숫자만 답하세요.'
if llm.provider() == 'anthropic':
    import anthropic
    client = anthropic.Anthropic()                    # 환경 변수 ANTHROPIC_API_KEY를 읽습니다
    for effort in ['low', 'high']:
        response = client.messages.create(
            model=llm.model_name('소형'), max_tokens=4000,   # max_tokens에는 thinking 토큰도 들어갑니다
            system='너는 후공정 라인의 생산 계산을 돕는 도우미다.',
            messages=[{'role': 'user', 'content': question}],
            output_config={'effort': effort})        # Anthropic API에만 있는 설정입니다
        usage, text = response.usage, ''.join(block.text for block in response.content if block.type == 'text')
        thinking = usage.output_tokens_details.thinking_tokens if usage.output_tokens_details else '알 수 없음'
        print(f'effort={effort}: 블록 {[block.type for block in response.content]}, 종료 이유 {response.stop_reason}')
        print(f'  입력 {usage.input_tokens}토큰, 출력 {usage.output_tokens}토큰(그중 thinking {thinking}) → {text.strip()}')
else:
    print('Anthropic을 쓰지 않으므로 건너뜁니다.')
```
:::
:::탭 OpenAI 호환
```python
question = 'UPH 1,200인 와이어 본더 3대가 하루 22시간, 가동률 87%로 돌면 하루 생산량은 몇 개입니까? 숫자만 답하세요.'
if llm.provider() == 'openai':
    from openai import OpenAI
    client = OpenAI(base_url=os.environ['OPENAI_BASE_URL'], api_key=os.environ['OPENAI_API_KEY'])
    response = client.chat.completions.create(
        model=llm.model_name('소형'), max_tokens=4000,
        messages=[{'role': 'system', 'content': '너는 후공정 라인의 생산 계산을 돕는 도우미다.'},
                  {'role': 'user', 'content': question}])      # 시스템 프롬프트는 맨 앞의 system 메시지입니다
    choice, usage = response.choices[0], response.usage
    details = usage.completion_tokens_details
    thinking = details.reasoning_tokens if details and details.reasoning_tokens is not None else '알 수 없음'
    print(f'종료 이유 {choice.finish_reason}, 입력 {usage.prompt_tokens}토큰, '
          f'출력 {usage.completion_tokens}토큰(그중 thinking {thinking}) → {choice.message.content.strip()}')
else:
    print('OpenAI 호환 API를 쓰지 않으므로 건너뜁니다.')
```
:::
:::

교재의 실행에서 effort가 `low`일 때 출력 70토큰 가운데 thinking이 66토큰, `high`일 때 163토큰 가운데 159토큰이었고, 두 번 모두 답은 68,904로 맞았습니다. 응답 텍스트는 숫자 하나뿐이어서 출력 토큰의 대부분이 응답에 보이지 않는 thinking이었습니다. 이 정도의 계산에서는 effort를 낮춰도 답이 같았고, 출력 토큰만 절반 아래로 줄었습니다. 두 SDK 코드의 차이는 시스템 프롬프트를 넣는 곳과, 응답 텍스트, 토큰 수, 종료 이유를 읽는 이름입니다.

## 모델 등급 고르기

:::요점
등급이 높은 모델은 단가가 높고 thinking도 길어 요금과 시간이 함께 늘어납니다. 등급은 정답 라벨이 있는 표본으로 정확도, 시간, 요금을 측정해, 필요한 정확도를 내는 가장 낮은 등급으로 고릅니다.
:::

같은 제공사의 모델은 능력과 가격에 따라 여러 등급으로 나뉩니다. 이 교재는 이를 [[모델 등급]](model tier)이라 하고 소형, 기본, 대형으로 부릅니다. 큰 모델은 파라미터가 많아 토큰 하나를 생성하는 계산이 크므로 단가가 높고 응답이 느립니다. 그 대신 판단이 까다로운 입력에서 더 정확할 수 있습니다.

어느 등급이 충분한지는 일마다 다르고, 모델 설명만 읽어서는 알 수 없습니다. 정답 라벨이 있는 표본 10~20건을 등급마다 보내 정확도, 시간, 요금을 나란히 놓고 봅니다. 쉬운 입력만 고르면 등급 사이의 차이가 드러나지 않으므로, 표본에는 판단이 어려운 입력을 넣습니다. 등급을 올려도 정확도가 그대로라면 남은 오류는 모델의 능력보다 분류 기준이 모호한 데서 오는 경우가 많으므로, 기준을 먼저 고칩니다(4장 "프롬프트 설계").

:::예제 5-2 등급별 정확도, 시간, 요금
4장의 문의 데이터에서 두 라벨에 걸쳐 판단하기 어려운 문의 15건(Q41~Q55)을 한 요청에 담아 소형, 기본, 대형 모델에 보냅니다. 보내기 전에 센 입력 토큰과 실제 입력 토큰, 정확도, 출력 토큰, 걸린 시간, 요금을 비교합니다. 이 셀은 API를 3번 호출하고, 토큰 세기를 3번 부릅니다(요금 없음).

```python
hard = inquiries[40:55]                                # Q41~Q55, 두 라벨에 걸쳐 헷갈리는 문의
system = ('문의를 다음 판정 기준을 위에서부터 차례로 적용해 하나의 라벨로 분류한다. '
          '1. 사람이 다치거나 다칠 위험이 있으면 안전 2. 원하는 것이 문서나 기록의 전달이면 문서와 데이터 요청 '
          '3. 원인 설비가 특정되고 조치 대상이 설비이면 설비 이상 4. 제품 결과에 이상이 있고 원인 설비가 특정되지 않으면 품질. '
          '답은 "번호: 라벨" 형식으로 한 줄에 한 건씩만 쓴다.')
messages = [{'role': 'user', 'content': numbered(hard)}]
for tier in ['소형', '기본', '대형']:
    counted = llm.count_tokens(messages, system=system, model=tier)       # 보내기 전에 셉니다. OpenAI 호환이면 None
    reply = llm.send(messages, system=system, model=tier, max_tokens=16000, timeout=300)
    print(f'{tier}: 정확도 {accuracy(parse_labels(reply.text), hard):.0%}, 입력 {counted}→{reply.input_tokens}토큰, '
          f'출력 {reply.output_tokens:,}토큰, {reply.seconds:.1f}초, {cost(reply, tier):.4f}달러')
```
:::

교재의 실행에서 세 등급 모두 15건 가운데 14건(93%)을 맞혔습니다. 요금은 대형이 0.0210달러로 소형(0.0008달러)의 약 26배였고, 시간은 소형이 6.7초로 가장 짧았습니다. 응답은 15줄인데 출력은 870~1,475토큰으로, 대부분이 thinking이었습니다. 토큰 세기로 미리 센 입력 912토큰은 실제 입력 토큰과 같았습니다. 판정 기준을 프롬프트에 적어 준 이 일에서는 소형으로 충분했습니다. 15건은 작은 표본이므로, 실제로 등급을 정할 때는 표본을 늘리고 여러 번 실행해 정확도의 변동도 확인합니다.

## 실패 유형

:::요점
API 요청의 실패는 세 가지입니다. 기다렸다 다시 보내면 풀리는 오류는 재시도하고, 요청을 고쳐야 풀리는 오류는 바로 멈추고, 예외 없이 끝났지만 쓸 수 없는 응답은 응답 검사로 찾아냅니다.
:::

서버는 요청이 실패하면 [[상태 코드]](status code)로 이유를 알립니다. 4xx는 요청 쪽의 문제, 5xx는 서버 쪽의 문제입니다. SDK는 이 상태 코드를 예외로 바꿔 발생시키고, `llm.py`는 다시 `llm.CallError` 하나로 바꿉니다. `CallError`의 `kind`는 오류의 종류이고, `retryable`은 기다렸다 다시 보내면 풀릴 수 있는 오류인지를 알려 줍니다.

<figure>
<svg viewBox="0 0 680 214" role="img" aria-label="실패의 세 가지. 첫째, 예외가 나고 기다리면 풀리는 오류: 429 레이트 리밋, 500과 529 서버 과부하, 타임아웃, 연결 실패. 백오프하며 재시도합니다. 둘째, 예외가 나고 요청을 고쳐야 풀리는 오류: 400 잘못된 요청, 401 키 오류, 403 권한 없음, 404 없는 모델. 재시도하지 않고 멈춥니다. 셋째, 예외 없이 끝난 실패: 종료 이유가 max_tokens나 refusal인 응답, 요구한 형식이 아닌 응답. 응답 검사로 찾아 실패 목록에 남깁니다.">
<rect x="10" y="10" width="210" height="194" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="115" y="32" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">기다리면 풀리는 오류</text><text x="115" y="50" text-anchor="middle" fill="var(--ink-soft)" font-size="11">예외 발생, retryable=True</text><text x="26" y="80" fill="var(--ink)" font-size="12">429 레이트 리밋</text><text x="26" y="102" fill="var(--ink)" font-size="12">500, 529 서버 오류, 과부하</text><text x="26" y="124" fill="var(--ink)" font-size="12">타임아웃</text><text x="26" y="146" fill="var(--ink)" font-size="12">연결 실패</text><line x1="26" y1="164" x2="204" y2="164" stroke="var(--line)"/><text x="115" y="188" text-anchor="middle" fill="var(--teal)" font-size="12" font-weight="700">백오프하며 재시도</text>
<rect x="235" y="10" width="210" height="194" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="340" y="32" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">요청을 고쳐야 풀리는 오류</text><text x="340" y="50" text-anchor="middle" fill="var(--ink-soft)" font-size="11">예외 발생, retryable=False</text><text x="251" y="80" fill="var(--ink)" font-size="12">400 잘못된 요청</text><text x="251" y="102" fill="var(--ink)" font-size="12">401 키 오류</text><text x="251" y="124" fill="var(--ink)" font-size="12">403 권한 없음</text><text x="251" y="146" fill="var(--ink)" font-size="12">404 없는 모델이나 주소</text><line x1="251" y1="164" x2="429" y2="164" stroke="var(--line)"/><text x="340" y="188" text-anchor="middle" fill="var(--amber)" font-size="12" font-weight="700">재시도하지 않고 멈춤</text>
<rect x="460" y="10" width="210" height="194" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="565" y="32" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">예외 없이 끝난 실패</text><text x="565" y="50" text-anchor="middle" fill="var(--ink-soft)" font-size="11">응답은 받았지만 쓸 수 없음</text><text x="476" y="80" fill="var(--ink)" font-size="12">종료 이유 max_tokens(잘림)</text><text x="476" y="102" fill="var(--ink)" font-size="12">종료 이유 refusal(거절)</text><text x="476" y="124" fill="var(--ink)" font-size="12">요구한 형식이 아닌 응답</text><text x="476" y="146" fill="var(--ink)" font-size="12">빈 응답 텍스트</text><line x1="476" y1="164" x2="654" y2="164" stroke="var(--line)"/><text x="565" y="188" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700">응답 검사, 실패 목록</text>
</svg>
<figcaption>실패는 처리 방법에 따라 세 가지로 나뉩니다.</figcaption>
</figure>

### 기다리면 풀리는 오류

[[레이트 리밋]](rate limit)은 일정 시간에 보낼 수 있는 요청 수와 토큰 수의 상한입니다. Anthropic API는 모델마다 분당 요청 수, 분당 입력 토큰 수, 분당 출력 토큰 수의 상한을 두고, 어느 하나라도 넘으면 429 오류가 납니다. 상한은 한 번에 초기화되지 않고 시간이 지나는 만큼 조금씩 채워지므로, 잠시 기다리면 다시 보낼 수 있습니다. 응답에 `retry-after` 헤더가 있으면 그 초만큼 기다립니다. 같은 429라도 월 사용 한도에 닿은 경우에는 다음 달까지 풀리지 않고 `retry-after` 헤더도 없습니다(2026-11 확인).

[[타임아웃]](timeout)은 응답 대기 시간의 상한입니다. 상한 안에 응답이 오지 않으면 SDK가 요청을 포기하고 예외를 발생시킵니다. 출력이 길거나 thinking이 길면 응답이 늦으므로, 타임아웃은 측정한 응답 시간보다 넉넉하게 둡니다. 타임아웃으로 포기한 요청도 서버에서는 이미 처리되어 요금이 붙었을 수 있습니다.

이런 오류는 같은 요청을 다시 보내는 [[재시도]](retry)로 풀립니다. 재시도할 때는 대기 시간을 1초, 2초, 4초처럼 늘려 가는 [[백오프]](backoff)를 씁니다. 레이트 리밋에 걸린 요청 여러 개가 같은 간격으로 다시 보내면 같은 순간에 다시 몰리므로, 대기 시간에 작은 무작위 값인 [[지터]](jitter)를 더합니다.

<figure>
<svg viewBox="0 0 680 128" role="img" aria-label="재시도 시간 순서. 1번째 시도가 429로 실패하면 1초와 지터만큼 기다리고, 2번째 시도가 다시 429로 실패하면 2초와 지터만큼 기다린 뒤, 3번째 시도에서 응답을 받습니다. 3번째도 실패하면 실패 목록에 남깁니다.">
<line x1="20" y1="60" x2="660" y2="60" stroke="var(--line)" stroke-width="2"/><rect x="20" y="40" width="80" height="40" rx="4" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="60" y="58" text-anchor="middle" fill="var(--ink)" font-size="12">1번째</text><text x="60" y="73" text-anchor="middle" fill="var(--amber)" font-size="11">429</text><text x="160" y="52" text-anchor="middle" fill="var(--ink-soft)" font-size="12">1초 + 지터</text><rect x="220" y="40" width="80" height="40" rx="4" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="260" y="58" text-anchor="middle" fill="var(--ink)" font-size="12">2번째</text><text x="260" y="73" text-anchor="middle" fill="var(--amber)" font-size="11">429</text><text x="410" y="52" text-anchor="middle" fill="var(--ink-soft)" font-size="12">2초 + 지터</text><rect x="520" y="40" width="80" height="40" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="560" y="58" text-anchor="middle" fill="var(--ink)" font-size="12">3번째</text><text x="560" y="73" text-anchor="middle" fill="var(--teal)" font-size="11">응답</text><text x="340" y="112" text-anchor="middle" fill="var(--ink-soft)" font-size="12">3번째도 실패하면 더 보내지 않고 실패 목록에 남깁니다</text>
</svg>
<figcaption>재시도할 때마다 대기 시간을 두 배로 늘리고 지터를 더합니다.</figcaption>
</figure>

SDK에도 자동 재시도가 있습니다. Anthropic SDK는 연결 실패, 타임아웃, 408, 409, 429, 500 이상을 기본 2번 재시도하고, 기본 타임아웃은 10분입니다(2026-11 확인). SDK의 재시도와 직접 작성한 재시도를 함께 쓰면 전체 시도 횟수는 두 횟수의 곱이 됩니다. SDK가 3번, 직접 작성한 재시도가 3번이면 최대 9번 보냅니다. 그래서 `llm.py`는 SDK의 재시도를 끄고(`max_retries=0`) `llm.ask()` 한 곳에서만 재시도합니다.

### 요청을 고쳐야 풀리는 오류

400(요청 형식이 잘못됨), 401(키가 틀림), 403(권한 없음), 404(없는 모델이나 주소)는 같은 요청을 몇 번 다시 보내도 똑같이 실패합니다. 재시도하면 시간만 쓰므로, 바로 멈추고 요청이나 설정을 고칩니다. 400은 입력이 컨텍스트 윈도우를 넘을 때(3장)도 납니다.

### 예외 없이 끝난 실패

예외 없이 응답을 받았어도 쓸 수 없는 응답이 있습니다. 종료 이유가 `max_tokens`이면 응답이 중간에 끊겼고, `refusal`이면 모델이 답하지 않았습니다. 정상 종료했더라도 요구한 형식이 아니거나 응답 텍스트가 비어 있을 수 있습니다. 이처럼 오류나 예외 없이 끝났지만 결과를 쓸 수 없는 실패를 [[조용한 실패]](silent failure)라고 합니다. 이런 실패는 `try`와 `except`로 잡히지 않으므로, 받은 응답을 코드로 확인하는 [[응답 검사]](response validation)로 찾아냅니다.

:::예제 5-3 세 가지 실패
없는 모델 이름, 0.5초 타임아웃, 20토큰의 최대 출력 토큰으로 같은 요청을 보냅니다. 앞의 두 요청이 어떤 예외로 바뀌는지, 셋째 요청은 예외 없이 무엇을 돌려주는지 봅니다. 이 셀은 API를 최대 3번 호출합니다. 재시도가 섞이지 않도록 `llm.send()`로 한 번씩만 보냅니다.

```python
messages = [{'role': 'user', 'content': '와이어 본딩 공정을 세 문장으로 설명해 주세요.'}]
cases = {'없는 모델 이름': dict(model='claude-no-such-model'),
         '타임아웃 0.5초': dict(model='소형', timeout=0.5),        # 0.5초 안에 응답이 오지 않으면 포기합니다
         '최대 출력 토큰 20': dict(model='소형', max_tokens=20)}    # thinking 토큰도 이 20토큰 안에 들어갑니다
for name, options in cases.items():
    try:
        reply = llm.send(messages, **options)
        print(f'{name}: 예외 없음, 종료 이유 {reply.stop_reason}, 출력 {reply.output_tokens}토큰, 응답 텍스트 {reply.text!r}')
    except llm.CallError as error:
        print(f'{name}: 예외 {error.kind}, 상태 코드 {error.status}, 재시도할 오류인지 {error.retryable}')
```
:::

없는 모델 이름은 404로 실패했고 재시도할 오류가 아니었습니다. 0.5초 타임아웃은 서버 응답을 받기 전에 포기했으므로 상태 코드 없이 `timeout`이 되었고, 재시도할 오류였습니다. 최대 출력 토큰 20은 예외 없이 끝났지만 종료 이유가 `max_tokens`이고, 응답 텍스트는 문장 중간에서 끊겼습니다. 이 응답은 `try`와 `except`로는 찾을 수 없고, 종료 이유를 확인해야 찾을 수 있습니다.

이 세 가지 처리를 문의 여러 건에 적용하면 [[배치 처리]](batch processing) 코드가 됩니다. 재시도를 끝까지 실패한 건과 응답 검사에 걸린 건은 버리지 않고, 식별자와 사유를 [[실패 목록]](failure list)에 남겨 사람이 다시 처리하게 합니다. 이 구현은 관통 프로젝트 1단계(실습 P1)에서 작성합니다.

## 프롬프트 캐싱

:::요점
요청마다 같은 앞부분(시스템 프롬프트, 긴 문서, 대화 이력)을 보내면, 프롬프트 캐싱으로 그 앞부분을 서버에 저장해 두고 다음 요청에서 입력 단가의 0.1배 이하로 다시 읽을 수 있습니다. 앞부분이 한 글자라도 다르면 캐시를 읽지 못합니다.
:::

3장의 대화 이력, 4장의 긴 시스템 프롬프트와 few-shot 예시처럼 요청마다 같은 앞부분을 다시 보내는 경우가 많습니다. 모델은 요청마다 입력 전체를 처음부터 계산하므로, 같은 앞부분이라도 매번 입력 단가를 냅니다. [[프롬프트 캐싱]](prompt caching)은 서버가 앞부분의 계산 결과를 저장해 두었다가, 다음 요청의 앞부분이 똑같으면 그 결과를 다시 읽는 기능입니다. 다시 계산하지 않으므로 단가가 낮고 응답도 빨라집니다.

<figure>
<svg viewBox="0 0 680 160" role="img" aria-label="프롬프트 캐싱. 1번째 요청은 시스템 프롬프트 800토큰을 캐시에 쓰며 입력 단가의 1.25배를 내고, 문의 60토큰은 입력 단가를 냅니다. 5분 안에 보낸 2번째 요청은 같은 시스템 프롬프트 800토큰을 캐시에서 읽어 입력 단가의 0.1배를 내고, 다른 문의 60토큰은 입력 단가를 냅니다. 시스템 프롬프트가 한 글자라도 바뀐 3번째 요청은 캐시를 읽지 못합니다.">
<text x="10" y="36" fill="var(--ink)" font-size="12" font-weight="700">1번째 요청</text><rect x="100" y="16" width="400" height="30" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="300" y="36" text-anchor="middle" fill="var(--ink)" font-size="12">시스템 프롬프트 800토큰: 캐시 쓰기(입력 단가 × 1.25)</text><rect x="500" y="16" width="60" height="30" fill="var(--sheet)" stroke="var(--line)"/><text x="530" y="36" text-anchor="middle" fill="var(--ink)" font-size="11">문의 A</text>
<text x="10" y="86" fill="var(--ink)" font-size="12" font-weight="700">2번째 요청</text><rect x="100" y="66" width="400" height="30" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="300" y="86" text-anchor="middle" fill="var(--ink)" font-size="12">같은 시스템 프롬프트: 캐시 읽기(입력 단가 × 0.1)</text><rect x="500" y="66" width="60" height="30" fill="var(--sheet)" stroke="var(--line)"/><text x="530" y="86" text-anchor="middle" fill="var(--ink)" font-size="11">문의 B</text><text x="570" y="86" fill="var(--ink-soft)" font-size="11">5분 안</text>
<text x="10" y="136" fill="var(--ink)" font-size="12" font-weight="700">3번째 요청</text><rect x="100" y="116" width="400" height="30" fill="var(--sheet)" stroke="var(--line)" stroke-dasharray="5 3"/><text x="300" y="136" text-anchor="middle" fill="var(--ink)" font-size="12">한 글자 바뀐 시스템 프롬프트: 캐시를 읽지 못함</text><rect x="500" y="116" width="60" height="30" fill="var(--sheet)" stroke="var(--line)"/><text x="530" y="136" text-anchor="middle" fill="var(--ink)" font-size="11">문의 C</text>
</svg>
<figcaption>앞부분이 똑같은 요청만 캐시를 읽습니다.</figcaption>
</figure>

캐시는 요청의 맨 앞부터 같은 부분까지만 적용됩니다. 그래서 바뀌지 않는 내용(시스템 프롬프트, 고정된 문서)을 앞에 두고, 요청마다 바뀌는 내용(질문, 현재 시각)을 뒤에 둡니다. 시스템 프롬프트 맨 앞에 현재 시각을 넣으면 요청마다 앞부분이 달라져 캐시를 한 번도 읽지 못합니다.

Anthropic API의 수치는 다음과 같습니다(2026-11 확인).

- 요청에 `cache_control`을 넣어야 캐싱합니다. 캐시를 처음 쓸 때는 입력 단가의 1.25배를 내고, 캐시를 읽을 때는 0.1배(Sonnet 5.5와 Opus 5.5는 0.05배)를 냅니다. 그래서 같은 앞부분을 두 번만 보내도 캐싱하지 않을 때보다 저렴합니다.
- 캐시는 기본으로 5분 동안 유지되고, 읽을 때마다 5분이 다시 시작됩니다. 1시간 동안 유지하는 설정은 캐시 쓰기 단가가 입력 단가의 2배입니다.
- 앞부분이 512토큰(현행 모델 기준)보다 짧으면 표시를 해도 캐싱하지 않습니다.
- 응답의 `usage.cache_creation_input_tokens`는 캐시에 쓴 토큰 수, `usage.cache_read_input_tokens`는 캐시에서 읽은 토큰 수입니다. 이 둘은 `input_tokens`와 따로 집계됩니다.

`llm.py`는 캐싱을 요청하지 않으므로 이 교재의 예제에서는 캐시를 쓰지 않습니다. OpenAI 호환 서버의 캐싱 지원과 단가는 서버마다 다르므로 사내 안내를 확인합니다.

## 개념 확인 실습

실습은 장 노트북의 빈칸을 채워 실행합니다. 코드를 실행하기 전에 결과를 먼저 예측해 적고, 실행한 뒤 예측과 다른 부분을 이 장의 원리로 설명해 봅니다.

:::실습 5-1 한 달 요금 어림하기
문의를 한 건에 한 요청씩 한 달에 1만 건 분류합니다. 요청마다 시스템 프롬프트 800토큰과 문의 60토큰을 보내고, 출력은 thinking을 포함해 평균 40토큰이라고 가정합니다. 등급마다 한 달 요금을 계산하는 `monthly_cost()`를 작성하고, 시스템 프롬프트를 캐싱할 때의 요금도 계산합니다. 캐싱은 첫 요청에서 캐시에 쓰고 나머지 요청은 모두 캐시에서 읽는다고 가정합니다. 먼저 `my_guess`에 대형 모델의 두 요금을 어림해 적습니다. API를 호출하지 않습니다.

```python
def monthly_cost(tier, requests=10_000, system_tokens=800, inquiry_tokens=60, output_tokens=40, cached=False):
    """한 달 요금(달러). PRICES의 단가를 씁니다. cached=True면 시스템 프롬프트를 캐싱합니다"""
    return 0.0  # TODO


my_guess = {'대형, 캐싱 없음': None, '대형, 캐싱': None}  # TODO: 달러로 어림해 적습니다
for tier in PRICES:
    print(f'{tier}: 캐싱 없음 {monthly_cost(tier):,.2f}달러, 캐싱 {monthly_cost(tier, cached=True):,.2f}달러')
print('예측:', my_guess)
```

:::풀이
입력 요금은 시스템 프롬프트와 문의로 나눠 계산합니다. 캐싱하면 시스템 프롬프트는 첫 요청만 캐시 쓰기 단가, 나머지는 캐시 읽기 단가를 냅니다.

```python
def monthly_cost(tier, requests=10_000, system_tokens=800, inquiry_tokens=60, output_tokens=40, cached=False):
    """한 달 요금(달러). PRICES의 단가를 씁니다. cached=True면 시스템 프롬프트를 캐싱합니다"""
    price = PRICES[tier]
    if cached:
        system_cost = system_tokens * (price['cache_write'] + (requests - 1) * price['cache_read'])
    else:
        system_cost = requests * system_tokens * price['input']
    rest = requests * (inquiry_tokens * price['input'] + output_tokens * price['output'])
    return (system_cost + rest) / 1_000_000


my_guess = {'대형, 캐싱 없음': 50, '대형, 캐싱': 20}
for tier in PRICES:
    print(f'{tier}: 캐싱 없음 {monthly_cost(tier):,.2f}달러, 캐싱 {monthly_cost(tier, cached=True):,.2f}달러')
print('예측:', my_guess)
```

대형 모델은 캐싱 없이 한 달 42.40달러, 캐싱하면 12.00달러이고, 소형은 1.06달러와 0.34달러입니다. 같은 등급에서는 캐싱으로 요금이 약 70% 줄고, 등급 사이에는 40배 차이가 납니다. 캐싱해도 출력 요금(대형 8달러)은 그대로이므로 캐싱한 뒤에는 출력이 요금의 대부분을 차지합니다. 출력 40토큰은 thinking을 포함한 가정이므로, 예제 5-2처럼 thinking이 길면 출력 요금이 이보다 커집니다.
:::
:::

## 관통 프로젝트 1단계

이 교재는 여러 장에 걸쳐 "사내 문서 질의응답 도우미"를 한 단계씩 만듭니다. 1단계는 질문을 API로 보내 답을 받되, 실패가 섞여도 멈추지 않고 요금과 실패를 기록하는 함수를 만듭니다. 6장에서는 답을 구조화된 데이터로 받고(2단계), 8장에서 사내 문서를 검색해 근거를 붙입니다(3단계).

:::실습 P1 질문에 답하는 함수
질문 하나를 보내고 결과를 dict로 돌려주는 `answer()`를 작성합니다. 재시도할 오류(`error.retryable`)는 백오프와 지터를 넣어 `tries`번까지 보내고, 고쳐야 풀리는 오류는 바로 멈춥니다. 정상 종료가 아닌 응답은 "확인 필요"로 표시합니다. `send`와 `sleep`을 인자로 받게 하면, 아래 테스트처럼 실제 API 대신 mock을 넣어 재시도 동작을 요금 없이 확인할 수 있습니다. 테스트 네 줄이 "완료, 실패, 실패, 확인 필요"로 나오고, 문의 5건의 답과 요금 합계가 출력되면 끝납니다. 이 셀은 API를 5번 호출합니다.

완료 기준

- 429를 두 번 받은 뒤 성공하면 "완료", 세 번 모두 429면 "실패", 404는 한 번만 보내고 "실패"입니다.
- 종료 이유가 `end`가 아니면 응답 텍스트가 있어도 "확인 필요"입니다.
- 결과에 입력 토큰, 출력 토큰, 요금(`cost()`), 실패 사유가 들어 있습니다.

:::정답
힌트 1. `for attempt in range(tries):` 안에서 `send()`를 부르고, `except llm.CallError as error:`에서 `error.retryable`이 거짓이면 바로 결과를 돌려줍니다.

힌트 2. 대기 시간은 `2 ** attempt + random.random()`처럼 백오프에 지터를 더합니다. 마지막 시도 뒤에는 기다리지 않습니다.
:::

```python
SYSTEM = '너는 반도체 후공정 라인의 문의에 답하는 도우미다. 사내 정보를 모르면 지어내지 말고 모른다고 답한다.'


def answer(question, tier='소형', tries=3, send=llm.send, sleep=time.sleep):
    """질문 하나에 답합니다. 돌려주는 dict의 키: question, status('완료', '확인 필요', '실패'),
    answer, input_tokens, output_tokens, cost, reason"""
    return {'question': question, 'status': '실패', 'answer': '', 'input_tokens': 0,
            'output_tokens': 0, 'cost': 0.0, 'reason': '작성하지 않음'}  # TODO


def mock_send(results):
    """미리 정해 둔 결과를 차례로 돌려주는 mock. 결과가 예외이면 발생시킵니다"""
    queue = list(results)

    def send(messages, **options):
        result = queue.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
    return send


done = llm.Reply('완료된 답', 50, 20, 'end', 'mock', 0.1)
cut = llm.Reply('잘린 답', 50, 2000, 'max_tokens', 'mock', 0.1)
busy, missing = llm.CallError('rate_limit', 429, '요청이 많음'), llm.CallError('not_found', 404, '없는 모델')
no_wait = lambda seconds: None                       # 테스트에서는 기다리지 않습니다
print('429 두 번 뒤 성공:', answer('질문', send=mock_send([busy, busy, done]), sleep=no_wait)['status'])
print('429 세 번:', answer('질문', send=mock_send([busy, busy, busy]), sleep=no_wait)['status'])
print('404 뒤 성공:', answer('질문', send=mock_send([missing, done]), sleep=no_wait)['status'])
print('잘린 응답:', answer('질문', send=mock_send([cut]), sleep=no_wait)['status'])

results = [answer(item['문의']) for item in inquiries if item['번호'] in ('Q31', 'Q33', 'Q35', 'Q36', 'Q38')]
for result in results:
    print(f"\n[{result['status']}] {result['question']}\n  → {result['answer'].strip()[:100]}")
print(f"\n요금 합계 {sum(result['cost'] for result in results):.5f}달러, "
      f"실패 목록 {[(result['question'], result['reason']) for result in results if result['status'] == '실패']}")
```

:::풀이
`except`에서 오류를 두 가지로 나누고, 응답을 받으면 종료 이유로 상태를 정합니다.

```python
SYSTEM = '너는 반도체 후공정 라인의 문의에 답하는 도우미다. 사내 정보를 모르면 지어내지 말고 모른다고 답한다.'


def answer(question, tier='소형', tries=3, send=llm.send, sleep=time.sleep):
    """질문 하나에 답합니다. 돌려주는 dict의 키: question, status('완료', '확인 필요', '실패'),
    answer, input_tokens, output_tokens, cost, reason"""
    result = {'question': question, 'status': '실패', 'answer': '', 'input_tokens': 0,
              'output_tokens': 0, 'cost': 0.0, 'reason': ''}
    for attempt in range(tries):
        try:
            reply = send([{'role': 'user', 'content': question}], system=SYSTEM, model=tier, max_tokens=2000)
        except llm.CallError as error:
            result['reason'] = str(error)
            if not error.retryable:
                return result                         # 요청을 고쳐야 풀리는 오류는 다시 보내지 않습니다
            if attempt < tries - 1:
                sleep(2 ** attempt + random.random())  # 1초, 2초 … 백오프에 지터를 더합니다
            continue
        result.update(answer=reply.text, input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
                      cost=cost(reply, tier), reason=reply.stop_reason,
                      status='완료' if reply.stop_reason == 'end' else '확인 필요')
        return result
    return result


def mock_send(results):
    """미리 정해 둔 결과를 차례로 돌려주는 mock. 결과가 예외이면 발생시킵니다"""
    queue = list(results)

    def send(messages, **options):
        result = queue.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
    return send


done = llm.Reply('완료된 답', 50, 20, 'end', 'mock', 0.1)
cut = llm.Reply('잘린 답', 50, 2000, 'max_tokens', 'mock', 0.1)
busy, missing = llm.CallError('rate_limit', 429, '요청이 많음'), llm.CallError('not_found', 404, '없는 모델')
no_wait = lambda seconds: None                       # 테스트에서는 기다리지 않습니다
print('429 두 번 뒤 성공:', answer('질문', send=mock_send([busy, busy, done]), sleep=no_wait)['status'])
print('429 세 번:', answer('질문', send=mock_send([busy, busy, busy]), sleep=no_wait)['status'])
print('404 뒤 성공:', answer('질문', send=mock_send([missing, done]), sleep=no_wait)['status'])
print('잘린 응답:', answer('질문', send=mock_send([cut]), sleep=no_wait)['status'])

results = [answer(item['문의']) for item in inquiries if item['번호'] in ('Q31', 'Q33', 'Q35', 'Q36', 'Q38')]
for result in results:
    print(f"\n[{result['status']}] {result['question']}\n  → {result['answer'].strip()[:100]}")
print(f"\n요금 합계 {sum(result['cost'] for result in results):.5f}달러, "
      f"실패 목록 {[(result['question'], result['reason']) for result in results if result['status'] == '실패']}")
```

테스트 네 줄은 "완료, 실패, 실패, 확인 필요"로 나왔습니다. 문의 5건은 모두 정상 종료했고, 모델은 사내 문서의 위치를 알 수 없다고 답했습니다. 모델은 사내 문서를 본 적이 없고, 시스템 프롬프트가 모르는 사내 정보를 지어내지 말라고 했기 때문입니다. 이 질문에 답하려면 사내 문서를 검색해 입력에 넣어야 하고, 이것이 3단계(8장)입니다. 5건의 요금은 소형 모델로 약 0.0015달러였습니다.
:::
:::

## 자가점검

**1.** 응답 텍스트가 들어 있는데도 그대로 저장하면 안 되는 응답은 어떤 경우입니까? 코드에서 무엇을 확인해야 합니까?

:::정답
종료 이유가 정상 종료가 아닌 경우입니다. `max_tokens`이면 응답이 중간에 끊겼고, `refusal`이면 모델이 답하지 않았습니다. 코드는 종료 이유가 정상 종료(`end_turn`, OpenAI 호환은 `stop`)일 때만 응답을 쓰고, 그 밖의 값은 모두 실패 목록에 남깁니다.
:::

**2.** 응답 텍스트는 숫자 하나뿐인데 출력 토큰이 300개로 나왔습니다. 어디에 토큰이 쓰였고, 요금은 무엇을 기준으로 계산됩니까? 확인하려면 어느 값을 봅니까?

:::정답
모델이 응답 전에 thinking을 했고, thinking 토큰이 출력 토큰에 들어갔습니다. 요금은 응답 텍스트 길이가 아니라 thinking을 포함한 출력 토큰 수로 계산됩니다. Anthropic API는 `usage.output_tokens_details.thinking_tokens`에 그중 thinking에 쓴 토큰 수를 적어 줍니다.
:::

**3.** 문의 1만 건을 분류할 모델 등급을 정하려 합니다. 무엇을 준비해 어떤 순서로 정합니까?

:::정답
정답 라벨이 있는 표본 10~20건을 준비합니다. 판단이 어려운 문의를 섞어야 등급 사이의 차이가 드러납니다. 등급마다 이 표본을 보내 정확도, 시간, 요금을 측정하고, 필요한 정확도를 내는 가장 낮은 등급을 고릅니다. 높은 등급에서도 틀리는 문의가 남으면 등급보다 분류 기준을 먼저 고칩니다.
:::

**4.** 다음 실패를 재시도할 것, 바로 멈출 것, 응답 검사로 찾아낼 것으로 나눠 보세요. (가) 429 (나) 404 (다) 종료 이유 `max_tokens` (라) 타임아웃 (마) 401

:::정답
재시도할 것은 (가)와 (라)입니다. 기다리면 풀릴 수 있으므로 백오프와 지터를 넣어 다시 보냅니다. 바로 멈출 것은 (나)와 (마)입니다. 모델 이름이나 키를 고쳐야 하므로 같은 요청을 다시 보내도 실패합니다. (다)는 예외 없이 응답을 받았으므로 응답 검사로 찾아내 실패 목록에 남깁니다.
:::

**5.** SDK의 기본 재시도(2번)를 켜 둔 채 직접 작성한 재시도로 3번까지 보내면, 실패가 계속될 때 요청은 최대 몇 번 나갑니까? 어떻게 고칩니까?

:::정답
SDK는 요청 하나를 처음 1번과 재시도 2번으로 최대 3번 보내고, 직접 작성한 재시도가 이것을 3번 부르므로 최대 9번입니다. 대기 시간도 함께 늘어납니다. 재시도 횟수는 한 곳에서만 정하도록 SDK의 재시도를 끕니다(`max_retries=0`).
:::

**6.** 요청마다 같은 3,000토큰짜리 시스템 프롬프트를 보내고 있습니다. effort를 낮추는 것과 프롬프트 캐싱을 쓰는 것은 각각 어떤 토큰의 요금을 줄입니까? 캐싱이 효과를 내려면 시스템 프롬프트를 어떻게 작성해야 합니까?

:::정답
effort는 출력 토큰(thinking과 응답 텍스트)을 줄이고, 프롬프트 캐싱은 반복해서 보내는 입력 토큰의 단가를 낮춥니다. 캐싱은 요청의 앞부분이 똑같을 때만 적용되므로, 시스템 프롬프트에 요청마다 바뀌는 내용(현재 시각, 질문)을 넣지 않고 바뀌는 내용은 뒤에 둡니다.
:::

## 참고 문헌

- Anthropic. Claude API 문서: Messages API의 `usage` 필드(`output_tokens_details.thinking_tokens`), 종료 이유(2026-11 확인).
- Anthropic. Claude API 문서: Pricing, Token counting, Effort, Rate limits, Errors, Prompt caching(2026-11 확인).
- OpenAI Python SDK 3.16.2: `CompletionUsage`의 `completion_tokens_details.reasoning_tokens`(2026-11 확인).
