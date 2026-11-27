# 1장 LLM은 어떻게 글을 만드는가

강의 1일차 파트 1, 2일차 파트 1, 6일차의 토큰 내용에 해당합니다.

LLM(large language model)의 응답은 어딘가에서 찾아 온 답이 아니라, 모델이 토큰을 하나씩 골라 이어 붙인 글입니다. 이 장은 글이 토큰으로 나뉘고, 다음 토큰의 확률이 계산되고, 그중 하나가 뽑히는 과정을 차례로 설명합니다.

## 학습 목표

1. LLM이 응답을 만드는 과정을 "토큰으로 나누기, 다음 토큰의 확률 계산, 하나 뽑기, 이어 붙이기"의 반복으로 설명할 수 있습니다. 이 과정에 사실을 찾아보는 단계가 없다는 것도 설명할 수 있습니다.
2. 토크나이저가 BPE(byte pair encoding)로 어휘를 만드는 방법을 설명하고, 같은 뜻의 한국어 문장이 영어 문장보다 토큰이 많은 이유를 설명할 수 있습니다.
3. 모델이 어휘 전체에 대한 logit을 내고 softmax로 확률 분포를 만드는 과정을 설명할 수 있습니다.
4. 같은 질문에 응답이 매번 다른 이유를 샘플링으로 설명하고, temperature와 top-p가 확률 분포를 어떻게 바꾸는지 계산으로 보일 수 있습니다.

예제 1-1~1-3은 PC에서 공개 소형 LLM인 Qwen2.5-0.5B-Instruct(파라미터 약 5억 개)를 실행합니다. 서비스 모델은 토큰마다의 확률을 돌려주지 않으므로, 확률을 직접 보려면 PC에서 실행하는 모델이 필요합니다. 예제 1-4만 API(application programming interface)로 서비스 모델을 호출합니다. 생성한 문장과 소수점 아래 숫자는 PC, 라이브러리 버전, 실행할 때마다 교재와 다를 수 있습니다.

## LLM이 응답을 만드는 과정

:::요점
LLM은 입력 끝에 올 토큰 하나를 확률로 고르고, 그 토큰을 붙여 다시 다음 토큰을 고르는 일을 되풀이해 응답을 만듭니다. 이 반복 어디에도 사실을 찾아보는 단계는 없습니다.
:::

[[LLM]](large language model)은 대량의 글로 학습해, 주어진 글 다음에 올 내용을 예측하는 방식으로 글을 생성하는 모델입니다. 모델은 글을 글자 단위로 다루지 않고 [[토큰]](token)이라는 조각으로 나눠 다룹니다. 토큰은 단어 하나일 때도 있고, 단어의 일부나 글자 하나의 일부일 때도 있습니다(다음 절 "토큰과 토크나이저"에서 설명합니다).

모델이 한 번에 하는 일은 지금까지의 토큰을 보고 다음에 올 수 있는 토큰마다 확률을 계산하는 것 하나뿐입니다. 이것을 [[다음 토큰 예측]](next-token prediction)이라고 하고, 확률에 따라 토큰 하나를 뽑는 것을 [[샘플링]](sampling)이라고 합니다. 응답이 300토큰이면 아래 그림의 2~4를 300번 되풀이합니다.

<figure>
<svg viewBox="0 0 680 220" role="img" aria-label="입력한 글을 토큰 ID로 바꾸고, 어휘의 토큰마다 확률을 계산하고, 확률에 따라 토큰 하나를 뽑아 입력 끝에 붙인 뒤, 끝 토큰이 나오거나 최대 출력 토큰에 닿을 때까지 확률 계산부터 되풀이하는 그림">
<rect x="10" y="14" width="150" height="84" rx="8" fill="var(--sheet)" stroke="var(--line)"/>
<text x="85" y="40" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">1. 토큰으로 나눔</text>
<text x="85" y="63" text-anchor="middle" fill="var(--ink-soft)" font-size="13">입력한 글을</text>
<text x="85" y="81" text-anchor="middle" fill="var(--ink-soft)" font-size="13">토큰 ID로 바꿉니다</text>
<rect x="180" y="14" width="150" height="84" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="255" y="40" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">2. 확률 계산</text>
<text x="255" y="63" text-anchor="middle" fill="var(--ink-soft)" font-size="13">어휘의 토큰마다</text>
<text x="255" y="81" text-anchor="middle" fill="var(--ink-soft)" font-size="13">확률을 계산합니다</text>
<rect x="350" y="14" width="150" height="84" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="425" y="40" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">3. 하나를 뽑음</text>
<text x="425" y="63" text-anchor="middle" fill="var(--ink-soft)" font-size="13">확률에 따라</text>
<text x="425" y="81" text-anchor="middle" fill="var(--ink-soft)" font-size="13">토큰 하나를 뽑습니다</text>
<rect x="520" y="14" width="150" height="84" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/>
<text x="595" y="40" text-anchor="middle" fill="var(--ink)" font-weight="700" font-size="14">4. 이어 붙임</text>
<text x="595" y="63" text-anchor="middle" fill="var(--ink-soft)" font-size="13">뽑은 토큰을</text>
<text x="595" y="81" text-anchor="middle" fill="var(--ink-soft)" font-size="13">입력 끝에 붙입니다</text>
<line x1="160" y1="56" x2="172" y2="56" stroke="var(--teal)" stroke-width="2"/>
<polygon points="172,51 180,56 172,61" fill="var(--teal)"/>
<line x1="330" y1="56" x2="342" y2="56" stroke="var(--teal)" stroke-width="2"/>
<polygon points="342,51 350,56 342,61" fill="var(--teal)"/>
<line x1="500" y1="56" x2="512" y2="56" stroke="var(--teal)" stroke-width="2"/>
<polygon points="512,51 520,56 512,61" fill="var(--teal)"/>
<polyline points="595,98 595,124 255,124 255,106" fill="none" stroke="var(--teal)" stroke-width="2" stroke-dasharray="6 4"/>
<polygon points="250,106 255,98 260,106" fill="var(--teal)"/>
<text x="425" y="144" text-anchor="middle" fill="var(--ink-soft)" font-size="13">끝 토큰이 나오거나 최대 출력 토큰에 닿을 때까지 2~4를 되풀이합니다</text>
<text x="20" y="182" fill="var(--ink)" font-size="13">예(예제 1-2): "웨이퍼를 개별 칩으로 자르는 공정을" 다음에 올 토큰의 확률</text>
<text x="20" y="204" fill="var(--ink-soft)" font-size="13">" 위해" 7.4%, " 위한" 3.5%, " 보" 2.9%, " �" 2.5%, … 어휘의 모든 토큰에 확률이 붙습니다</text>
</svg>
<figcaption>LLM이 응답을 만드는 과정. 2~4는 토큰 하나를 만들 때마다 되풀이합니다.</figcaption>
</figure>

반복은 모델이 "글이 끝났다"는 뜻의 끝 토큰을 뽑거나, 생성한 토큰 수가 요청에서 정한 상한인 [[최대 출력 토큰]](max tokens)에 닿으면 멈춥니다. 상한에 닿은 응답은 문장 중간에서 끊깁니다.

네 단계 어디에도 데이터베이스나 문서를 찾아보는 일은 없습니다. 모델이 "다이싱은 웨이퍼를 개별 칩으로 자르는 공정입니다"라고 쓸 때도, 학습한 글에서 이런 토큰 다음에 이런 토큰이 자주 왔다는 패턴을 따라 토큰을 고른 결과입니다. 그래서 학습한 글에 자주 나온 내용은 대체로 맞게 쓰지만, 드물거나 학습하지 않은 내용도 같은 말투로 그럴듯하게 써 냅니다.

## 토큰과 토크나이저

:::요점
토크나이저에는 어휘를 만들 때 쓴 글에서 자주 붙어 나온 조각을 하나의 토큰으로 묶어 둔 어휘가 있습니다. 영어가 많은 글로 만든 어휘에는 한국어 조각이 적게 묶여 있어서, 같은 뜻이라도 한국어 문장이 더 많은 토큰으로 나뉩니다.
:::

API 요금과 모델이 한 번에 다룰 수 있는 길이는 글자 수가 아니라 토큰 수로 정해집니다. 그래서 같은 내용이 토큰 몇 개가 되는지에 따라 비용과 넣을 수 있는 분량이 바뀝니다.

[[토크나이저]](tokenizer)는 글을 토큰으로 나누고 토큰마다 번호를 붙이는 프로그램입니다. 토크나이저가 아는 토큰 전체의 목록을 [[어휘]](vocabulary)라고 하고, 어휘에서 토큰에 붙은 번호를 [[토큰 ID]](token ID)라고 합니다. 모델이 실제로 입력받는 것은 글자가 아니라 토큰 ID의 나열입니다. 예제 1-1의 토크나이저의 어휘에는 토큰이 151,665개 있습니다.

### BPE가 어휘를 만드는 방법

토크나이저의 어휘는 대량의 글에서 자동으로 만듭니다. 지금의 LLM이 대부분 쓰는 방법은 [[BPE]](byte pair encoding)입니다. BPE는 글자 하나하나에서 시작해, 가장 자주 붙어 나오는 두 조각을 하나로 합치는 일을 되풀이합니다(Sennrich 외, 2016). 아래 그림은 "다이싱" 5번, "다이본딩" 4번, "와이어본딩" 3번이 나오는 글로 세 번 합쳐 본 것입니다.

<figure>
<svg viewBox="0 0 680 274" role="img" aria-label="BPE가 다이싱 5번, 다이본딩 4번, 와이어본딩 3번이 나오는 글에서 가장 자주 붙어 나온 쌍을 차례로 합치는 그림. 1단계에서 다와 이를 9번 나와 다이로, 2단계에서 본과 딩을 7번 나와 본딩으로, 3단계에서 다이와 싱을 5번 나와 다이싱으로 합칩니다. 이 어휘로 다이아몬드를 나누면 다이는 토큰 하나가 되고 아, 몬, 드는 어휘에 없어 나눌 수 없습니다.">
<text x="10" y="22" fill="var(--ink-soft)" font-size="13">단계</text><text x="80" y="22" fill="var(--ink-soft)" font-size="13">다이싱 (5번)</text><text x="210" y="22" fill="var(--ink-soft)" font-size="13">다이본딩 (4번)</text><text x="370" y="22" fill="var(--ink-soft)" font-size="13">와이어본딩 (3번)</text><text x="540" y="22" fill="var(--ink-soft)" font-size="13">합친 쌍 (나온 횟수)</text><text x="22" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">시작</text><rect x="80" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="93" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">다</text><rect x="110" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="123" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">이</text><rect x="140" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="153" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">싱</text><rect x="210" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="223" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">다</text><rect x="240" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="253" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">이</text><rect x="270" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="283" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">본</text><rect x="300" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="313" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">딩</text><rect x="370" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="383" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">와</text><rect x="400" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="413" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">이</text><rect x="430" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="443" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">어</text><rect x="460" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="473" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">본</text><rect x="490" y="34" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="503" y="54" text-anchor="middle" fill="var(--ink)" font-size="13">딩</text><text x="22" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">1</text><rect x="80" y="78" width="56" height="30" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="108" y="98" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">다이</text><rect x="140" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="153" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">싱</text><rect x="210" y="78" width="56" height="30" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="238" y="98" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">다이</text><rect x="270" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="283" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">본</text><rect x="300" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="313" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">딩</text><rect x="370" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="383" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">와</text><rect x="400" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="413" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">이</text><rect x="430" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="443" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">어</text><rect x="460" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="473" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">본</text><rect x="490" y="78" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="503" y="98" text-anchor="middle" fill="var(--ink)" font-size="13">딩</text><text x="540" y="98" fill="var(--teal)" font-size="13" font-weight="700">다 + 이 (9번)</text><text x="22" y="142" text-anchor="middle" fill="var(--ink)" font-size="13">2</text><rect x="80" y="122" width="56" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="108" y="142" text-anchor="middle" fill="var(--ink)" font-size="13">다이</text><rect x="140" y="122" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="153" y="142" text-anchor="middle" fill="var(--ink)" font-size="13">싱</text><rect x="210" y="122" width="56" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="238" y="142" text-anchor="middle" fill="var(--ink)" font-size="13">다이</text><rect x="270" y="122" width="56" height="30" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="298" y="142" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">본딩</text><rect x="370" y="122" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="383" y="142" text-anchor="middle" fill="var(--ink)" font-size="13">와</text><rect x="400" y="122" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="413" y="142" text-anchor="middle" fill="var(--ink)" font-size="13">이</text><rect x="430" y="122" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="443" y="142" text-anchor="middle" fill="var(--ink)" font-size="13">어</text><rect x="460" y="122" width="56" height="30" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="488" y="142" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">본딩</text><text x="540" y="142" fill="var(--teal)" font-size="13" font-weight="700">본 + 딩 (7번)</text><text x="22" y="186" text-anchor="middle" fill="var(--ink)" font-size="13">3</text><rect x="80" y="166" width="86" height="30" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="123" y="186" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">다이싱</text><rect x="210" y="166" width="56" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="238" y="186" text-anchor="middle" fill="var(--ink)" font-size="13">다이</text><rect x="270" y="166" width="56" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="298" y="186" text-anchor="middle" fill="var(--ink)" font-size="13">본딩</text><rect x="370" y="166" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="383" y="186" text-anchor="middle" fill="var(--ink)" font-size="13">와</text><rect x="400" y="166" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="413" y="186" text-anchor="middle" fill="var(--ink)" font-size="13">이</text><rect x="430" y="166" width="26" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="443" y="186" text-anchor="middle" fill="var(--ink)" font-size="13">어</text><rect x="460" y="166" width="56" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="488" y="186" text-anchor="middle" fill="var(--ink)" font-size="13">본딩</text><text x="540" y="186" fill="var(--teal)" font-size="13" font-weight="700">다이 + 싱 (5번)</text><line x1="10" y1="218" x2="670" y2="218" stroke="var(--line)"/><text x="10" y="246" fill="var(--ink-soft)" font-size="13">새 낱말</text><rect x="80" y="226" width="56" height="30" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="108" y="246" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">다이</text><rect x="140" y="226" width="26" height="30" rx="4" fill="var(--amber-wash)" stroke="var(--amber)" stroke-dasharray="4 3"/><text x="153" y="246" text-anchor="middle" fill="var(--amber)" font-size="13">아</text><rect x="170" y="226" width="26" height="30" rx="4" fill="var(--amber-wash)" stroke="var(--amber)" stroke-dasharray="4 3"/><text x="183" y="246" text-anchor="middle" fill="var(--amber)" font-size="13">몬</text><rect x="200" y="226" width="26" height="30" rx="4" fill="var(--amber-wash)" stroke="var(--amber)" stroke-dasharray="4 3"/><text x="213" y="246" text-anchor="middle" fill="var(--amber)" font-size="13">드</text><text x="240" y="240" fill="var(--ink-soft)" font-size="13">"다이"는 어휘에 있는 조각이라 토큰 하나가 됩니다</text><text x="240" y="258" fill="var(--amber)" font-size="13">"아", "몬", "드"는 어휘에 없는 글자라 나눌 수 없습니다</text>
</svg>
<figcaption>BPE의 합치기. 단계마다 가장 자주 붙어 나온 쌍(청록색 칸)을 하나의 조각으로 합칩니다. 괄호 안은 학습할 글에 나온 횟수입니다.</figcaption>
</figure>

자주 나온 낱말일수록 적은 토큰으로 나뉩니다. 어휘에 없는 글자("아", "몬", "드")를 나눌 수 없는 문제는 다음 소절의 바이트 단위 BPE가 해결합니다. 실제 토크나이저는 합치기를 십수만 번 되풀이합니다(예제 1-1의 토크나이저는 151,387번).

같은 뜻의 한국어 문장에 토큰이 많은 이유도 여기에 있습니다. 어휘를 만들 때 쓴 글에 한국어가 영어보다 훨씬 적어서, 한국어 조각은 덜 합쳐진 채 남습니다.

### 바이트 단위 BPE와 한글

글자에서 시작하면 어휘에 없는 글자를 나눌 수 없습니다. 그래서 GPT 계열, Llama 3, Qwen 같은 많은 LLM은 글자 대신 바이트에서 시작합니다. 이것을 [[바이트 단위 BPE]](byte-level BPE)라고 합니다(Radford 외, 2019). 컴퓨터는 글을 UTF-8 규칙으로 바이트에 저장하는데, 바이트는 256가지뿐이므로 모두 어휘에 넣고 시작하면 어떤 글이든 나눌 수 있습니다.

UTF-8에서 영어 글자는 1바이트, 한글 한 글자는 3바이트입니다. 세 바이트가 학습 중에 합쳐졌으면 토큰 1개가 되고, 합쳐지지 않았으면 바이트 조각 2~3개가 됩니다. 토큰에는 앞의 공백이 포함되기도 해서, 아래 그림처럼 "칩"은 토큰 1개이지만 " 칩"은 2개로 나뉩니다.

<figure>
<svg viewBox="0 0 680 186" role="img" aria-label="칩 한 글자는 UTF-8 3바이트 EC B9 A9이고, 이 세 바이트가 합쳐진 토큰 하나(ID 144660)입니다. 앞에 공백이 붙은 칩은 4바이트 20 EC B9 A9인데, 공백과 앞 두 바이트가 토큰 하나(ID 90711), 마지막 바이트 A9가 토큰 하나(ID 102)로 나뉩니다.">
<text x="10" y="18" fill="var(--ink-soft)" font-size="13">글</text><text x="120" y="18" fill="var(--ink-soft)" font-size="13">토큰(위)과 UTF-8 바이트(아래)</text><text x="10" y="74" fill="var(--ink)" font-size="15" font-weight="700">"칩"</text><rect x="120" y="56" width="62" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="151" y="76" text-anchor="middle" fill="var(--ink)" font-size="13">EC</text><rect x="190" y="56" width="62" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="221" y="76" text-anchor="middle" fill="var(--ink)" font-size="13">B9</text><rect x="260" y="56" width="62" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="291" y="76" text-anchor="middle" fill="var(--ink)" font-size="13">A9</text><rect x="120" y="30" width="202" height="22" rx="4" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="221" y="46" text-anchor="middle" fill="var(--teal)" font-size="12">토큰 1개 (ID 144660)</text><text x="350" y="76" fill="var(--ink-soft)" font-size="12">한글 한 글자 = 3바이트. 세 바이트가 학습 중에 합쳐져 있습니다</text><text x="10" y="154" fill="var(--ink)" font-size="15" font-weight="700">" 칩"</text><rect x="120" y="136" width="62" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="151" y="156" text-anchor="middle" fill="var(--ink)" font-size="13">20 (공백)</text><rect x="190" y="136" width="62" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="221" y="156" text-anchor="middle" fill="var(--ink)" font-size="13">EC</text><rect x="260" y="136" width="62" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="291" y="156" text-anchor="middle" fill="var(--ink)" font-size="13">B9</text><rect x="330" y="136" width="62" height="30" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="361" y="156" text-anchor="middle" fill="var(--ink)" font-size="13">A9</text><rect x="120" y="110" width="202" height="22" rx="4" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="221" y="126" text-anchor="middle" fill="var(--amber)" font-size="12">토큰 (ID 90711)</text><rect x="330" y="110" width="62" height="22" rx="4" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="361" y="126" text-anchor="middle" fill="var(--amber)" font-size="12">ID 102</text><text x="420" y="156" fill="var(--amber)" font-size="12">" 칩"은 합쳐진 적이 없어 바이트 조각 2개로</text><text x="420" y="174" fill="var(--amber)" font-size="12">나뉩니다. 조각을 글로 되돌리면 �로 보입니다</text>
</svg>
<figcaption>예제 1-1의 토크나이저에서 "칩"과 " 칩"이 토큰으로 나뉘는 방법. 위의 띠가 토큰, 아래 칸이 바이트입니다.</figcaption>
</figure>

문장 안의 글자는 대개 앞에 공백이 있으므로 " 칩"처럼 조각으로 나뉘기 쉽습니다. 숫자는 토크나이저마다 규칙을 따로 둡니다. 예제 1-1의 토크나이저는 BPE 전에 숫자를 한 자리씩 떼어 놓아서, "175"는 토큰 3개가 됩니다.

:::예제 1-1 토큰으로 나눠 보기
같은 뜻의 한국어 문장과 영어 문장, 숫자가 든 문장을 토크나이저로 나눠 토큰 수를 비교합니다. 토큰을 하나씩 글로 되돌려 출력하므로 어디서 나뉘었는지 볼 수 있습니다. 깨진 글자(�)로 보이는 토큰은 한글 한 글자의 바이트 조각입니다.

```python
sentences = [
    '웨이퍼를 개별 칩으로 자르는 공정을 다이싱이라고 합니다.',
    'Dicing is the process of cutting a wafer into individual chips.',
    '와이어 본딩 온도 기준은 175°C입니다.',
]
print(f'어휘 크기: {len(tokenizer):,}개')
for sentence in sentences:
    token_ids = tokenizer.encode(sentence)
    pieces = [tokenizer.decode([token_id]) for token_id in token_ids]  # 토큰을 하나씩 글로 되돌립니다
    print(f'\n{len(sentence)}자, {len(token_ids)}토큰')
    print(' | '.join(pieces))

# 앞에 공백이 있는지에 따라 같은 글자도 토큰 수가 다릅니다
print('\n"칩"의 토큰 ID:', tokenizer.encode('칩'), '  " 칩"의 토큰 ID:', tokenizer.encode(' 칩'))
```
:::

한국어 문장은 영어 문장의 절반 길이인데 토큰은 더 많습니다. 손으로 따라간 예와 달리 실제 토크나이저에서 "다이싱"은 토큰 3개인데, 이 어휘를 만든 글에 "다이싱"이 합쳐질 만큼 자주 나오지 않았다는 뜻입니다.

토크나이저는 모델마다 따로 있어서 같은 글도 모델에 따라 토큰 수가 다릅니다. Anthropic은 Claude Opus 4.7부터 새 토크나이저를 쓰는데, 같은 글이 이전 모델보다 토큰으로 1~1.35배가 된다고 안내합니다(2026-11 확인). Claude의 토크나이저는 공개되어 있지 않아서, 토큰 수는 API의 토큰 세기 기능으로 셉니다(5장 "LLM API"에서 다룹니다).

:::주의
"한글 1글자는 약 1토큰"처럼 글자 수로 토큰 수를 어림하는 규칙은 특정 토크나이저에서 나온 값입니다. 쓰는 모델이 바뀌면 맞지 않습니다. 비용이나 길이를 계산할 때는 그 모델의 토크나이저나 토큰 세기 기능으로 직접 셉니다.
:::

## 다음 토큰의 확률 분포

:::요점
모델은 토큰 ID를 벡터로 바꾸고 여러 층의 계산을 거쳐, 어휘의 모든 토큰에 점수(logit)를 하나씩 매깁니다. softmax가 이 점수들을 합이 1인 확률로 바꿉니다.
:::

### 토큰에서 점수까지

<figure>
<svg viewBox="0 0 680 208" role="img" aria-label="입력 토큰 ID 15개가 각각 숫자 896개짜리 벡터가 되고, 트랜스포머 층 24개를 차례로 통과합니다. 맨 끝 위치의 벡터(숫자 896개)에서 logit 151,936개를 계산하고, softmax가 이를 합이 1인 확률 분포 151,936개로 바꿉니다.">
<rect x="10" y="10" width="148" height="58" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="84" y="34" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">입력 토큰 ID</text><text x="84" y="54" text-anchor="middle" fill="var(--ink-soft)" font-size="13">15개</text><line x1="158" y1="39" x2="170" y2="39" stroke="var(--teal)" stroke-width="2"/><polygon points="170,34 178,39 170,44" fill="var(--teal)"/><rect x="178" y="10" width="148" height="58" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="252" y="34" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">벡터 15개</text><text x="252" y="54" text-anchor="middle" fill="var(--ink-soft)" font-size="13">각각 숫자 896개</text><line x1="326" y1="39" x2="338" y2="39" stroke="var(--teal)" stroke-width="2"/><polygon points="338,34 346,39 338,44" fill="var(--teal)"/><rect x="346" y="10" width="148" height="58" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="420" y="34" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">트랜스포머 층</text><text x="420" y="54" text-anchor="middle" fill="var(--ink-soft)" font-size="13">24개를 차례로 통과</text><line x1="494" y1="39" x2="506" y2="39" stroke="var(--teal)" stroke-width="2"/><polygon points="506,34 514,39 506,44" fill="var(--teal)"/><rect x="514" y="10" width="148" height="58" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="588" y="34" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">맨 끝 위치의 벡터</text><text x="588" y="54" text-anchor="middle" fill="var(--ink-soft)" font-size="13">숫자 896개</text><polyline points="588,68 588,90 94,90 94,104" fill="none" stroke="var(--teal)" stroke-width="2"/><polygon points="89,104 94,112 99,104" fill="var(--teal)"/><rect x="20" y="112" width="148" height="58" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="94" y="136" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">logit</text><text x="94" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">151,936개</text><line x1="168" y1="141" x2="242" y2="141" stroke="var(--teal)" stroke-width="2"/><polygon points="242,136 250,141 242,146" fill="var(--teal)"/><rect x="250" y="112" width="148" height="58" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="324" y="136" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">softmax</text><text x="324" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">합이 1이 되게 바꿈</text><line x1="398" y1="141" x2="472" y2="141" stroke="var(--teal)" stroke-width="2"/><polygon points="472,136 480,141 472,146" fill="var(--teal)"/><rect x="480" y="112" width="148" height="58" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="554" y="136" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">확률 분포</text><text x="554" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">151,936개, 합 1</text><text x="340" y="196" text-anchor="middle" fill="var(--ink-soft)" font-size="12">예제 1-2: "웨이퍼를 개별 칩으로 자르는 공정을"(15토큰)을 넣었을 때의 크기</text>
</svg>
<figcaption>모델 안에서 다음 토큰의 확률이 계산되는 순서. 숫자는 예제의 모델과 예제 1-2의 입력 기준입니다.</figcaption>
</figure>

그림에 나오는 용어는 다음과 같습니다.

- [[벡터]]: 숫자를 순서대로 나열한 것입니다.
- [[트랜스포머]](transformer): 지금의 LLM 대부분이 쓰는 신경망 구조입니다. 층 하나는 앞 토큰들의 정보를 섞는 어텐션(아래 소절)과 위치마다 벡터를 변환하는 계산으로 이루어집니다.
- [[logit]]: 맨 끝 위치의 벡터에 토큰마다 한 행씩 있는 행렬을 곱해 얻은, 토큰마다의 점수입니다.
- [[softmax]]: logit을 합이 1인 확률로 바꾸는 계산입니다(아래 소절). 그 결과를 [[확률 분포]](probability distribution)라고 합니다.

모델은 언제나 어휘 전체에 대한 확률 분포를 내놓고, 토큰 하나를 정하는 일은 샘플링이 합니다.

벡터와 층의 계산에 쓰는 숫자는 학습으로 정해집니다. 이런 숫자를 [[파라미터]](parameter)라고 합니다. 예제의 모델은 약 4.9억 개이고, 파일이 공개된 큰 모델인 Llama 3.1 405B는 약 4,050억 개입니다. Anthropic과 OpenAI는 자사 모델의 파라미터 수를 공개하지 않습니다.

### 어텐션: 앞 내용을 섞는 방법

"공정을" 다음 토큰을 정하려면 앞의 "웨이퍼"와 "칩"을 함께 봐야 합니다. 트랜스포머는 이 일을 [[어텐션]](attention)으로 합니다(Vaswani 외, 2017). 각 위치가 앞 토큰들의 벡터를 얼마씩 섞을지 가중치로 정하고, 가중 평균을 구합니다.

<figure>
<svg viewBox="0 0 680 232" role="img" aria-label="공정을 위치가 앞 낱말들의 벡터를 섞는 비율을 화살표 굵기로 나타낸 그림. 웨이퍼를 0.40, 개별 0.05, 칩으로 0.30, 자르는 0.15, 공정을 자신 0.10이고 합은 1입니다. 공정을 위치의 새 벡터는 이 가중치로 계산한 가중 평균입니다. 가중치는 가정한 값입니다.">
<rect x="470" y="14" width="180" height="40" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="560" y="31" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">"공정을" 위치에서</text><text x="560" y="48" text-anchor="middle" fill="var(--ink-soft)" font-size="12">앞 낱말을 섞는 비율</text><line x1="560" y1="54" x2="70" y2="140" stroke="var(--teal)" stroke-width="9" stroke-linecap="round" opacity="0.8"/><rect x="235.2" y="95.32" width="42" height="20" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="256.2" y="110.32" text-anchor="middle" fill="var(--teal)" font-size="12" font-weight="700">0.40</text><line x1="560" y1="54" x2="190" y2="140" stroke="var(--teal)" stroke-width="2" stroke-linecap="round" opacity="0.8"/><rect x="309.6" y="95.32" width="42" height="20" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="330.6" y="110.32" text-anchor="middle" fill="var(--teal)" font-size="12" font-weight="700">0.05</text><line x1="560" y1="54" x2="300" y2="140" stroke="var(--teal)" stroke-width="7" stroke-linecap="round" opacity="0.8"/><rect x="377.8" y="95.32" width="42" height="20" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="398.8" y="110.32" text-anchor="middle" fill="var(--teal)" font-size="12" font-weight="700">0.30</text><line x1="560" y1="54" x2="420" y2="140" stroke="var(--teal)" stroke-width="4" stroke-linecap="round" opacity="0.8"/><rect x="452.2" y="95.32" width="42" height="20" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="473.2" y="110.32" text-anchor="middle" fill="var(--teal)" font-size="12" font-weight="700">0.15</text><line x1="560" y1="54" x2="560" y2="140" stroke="var(--teal)" stroke-width="3" stroke-linecap="round" opacity="0.8"/><rect x="539" y="95.32" width="42" height="20" rx="4" fill="var(--sheet)" stroke="var(--line)"/><text x="560" y="110.32" text-anchor="middle" fill="var(--teal)" font-size="12" font-weight="700">0.10</text><rect x="20" y="140" width="100" height="34" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="70" y="162" text-anchor="middle" fill="var(--ink)" font-size="13">웨이퍼를</text><rect x="140" y="140" width="100" height="34" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="190" y="162" text-anchor="middle" fill="var(--ink)" font-size="13">개별</text><rect x="250" y="140" width="100" height="34" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="300" y="162" text-anchor="middle" fill="var(--ink)" font-size="13">칩으로</text><rect x="370" y="140" width="100" height="34" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="420" y="162" text-anchor="middle" fill="var(--ink)" font-size="13">자르는</text><rect x="510" y="140" width="100" height="34" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="560" y="162" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">공정을</text><text x="340" y="200" text-anchor="middle" fill="var(--ink)" font-size="12">"공정을" 위치의 새 벡터 = 0.40 × "웨이퍼를" + 0.05 × "개별" + 0.30 × "칩으로" + 0.15 × "자르는" + 0.10 × "공정을"</text><text x="340" y="220" text-anchor="middle" fill="var(--ink-soft)" font-size="12">가중치의 합은 1입니다. 그림의 가중치는 설명을 위해 가정한 값입니다</text>
</svg>
<figcaption>어텐션의 가중 평균. 선이 굵을수록 그 낱말의 정보를 많이 섞습니다. 실제 모델은 낱말이 아니라 토큰 단위로 계산합니다.</figcaption>
</figure>

가중치는 입력의 내용에 따라 매번 계산되므로, 같은 "공정을"이라도 앞에 무엇이 있었는지에 따라 다음 토큰의 확률 분포가 바뀝니다. 각 위치는 자기와 그 앞의 토큰만 봅니다. 학습할 때 정답인 뒤 토큰을 미리 보지 못하게 하려는 것입니다.

:::보충
**관심이 있으면 더 공부해 볼 내용: Q, K, V.** 어텐션의 가중치는 query(Q), key(K), value(V)라는 세 벡터로 계산합니다. 각 위치의 벡터에서 Q, K, V를 만들고, 지금 위치의 Q와 앞 위치들의 K가 얼마나 비슷한지로 가중치를 정한 뒤, 그 가중치로 앞 위치들의 V를 가중 평균합니다. 어텐션 여러 개를 동시에 계산하는 것을 multi-head attention이라고 합니다. LLM을 쓰는 데는 "앞 내용 전체를 보고 다음 토큰을 정한다"는 이해로 충분합니다. 모델의 구조에 관심이 있으면 Vaswani 외(2017) "Attention Is All You Need"를 읽어 보기 바랍니다.
:::

### logit과 softmax

logit은 확률이 아니라 점수여서 음수일 수도 있고 합이 1이 되지도 않습니다. softmax는 점수마다 e(약 2.718)를 그 점수만큼 거듭제곱하고, 그 값들의 합으로 나눠 확률로 바꿉니다.

```text
토큰 i의 확률 = exp(logit_i) / (모든 토큰의 exp(logit)을 더한 값)
```

<figure>
<svg viewBox="0 0 680 194" role="img" aria-label="softmax 계산. logit A 2.0, B 1.0, C 0.1에서 e의 거듭제곱 7.39, 2.72, 1.11을 구하고, 합 11.21로 나누어 확률 65.9%, 24.2%, 9.9%를 얻습니다. logit 차이 1.0이 확률에서는 약 2.7배 차이가 됩니다.">
<text x="90" y="18" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">logit</text><line x1="10" y1="140" x2="170" y2="140" stroke="var(--line)"/><rect x="22" y="40" width="36" height="100" rx="2" fill="var(--teal)" stroke="var(--teal)"/><text x="40" y="34" text-anchor="middle" fill="var(--ink)" font-size="12">2.0</text><text x="40" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">A</text><rect x="72" y="90" width="36" height="50" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="90" y="84" text-anchor="middle" fill="var(--ink)" font-size="12">1.0</text><text x="90" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">B</text><rect x="122" y="135" width="36" height="5" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="140" y="129" text-anchor="middle" fill="var(--ink)" font-size="12">0.1</text><text x="140" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">C</text><line x1="178" y1="90" x2="230" y2="90" stroke="var(--teal)" stroke-width="2"/><polygon points="230,85 238,90 230,95" fill="var(--teal)"/><text x="208" y="80" text-anchor="middle" fill="var(--ink-soft)" font-size="11">e^logit</text><text x="330" y="18" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">e^logit</text><line x1="250" y1="140" x2="410" y2="140" stroke="var(--line)"/><rect x="262" y="40" width="36" height="100" rx="2" fill="var(--teal)" stroke="var(--teal)"/><text x="280" y="34" text-anchor="middle" fill="var(--ink)" font-size="12">7.39</text><text x="280" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">A</text><rect x="312" y="103.19350473612991" width="36" height="36.8064952638701" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="330" y="97.19350473612991" text-anchor="middle" fill="var(--ink)" font-size="12">2.72</text><text x="330" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">B</text><rect x="362" y="124.97970230040595" width="36" height="15.020297699594048" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="380" y="118.97970230040595" text-anchor="middle" fill="var(--ink)" font-size="12">1.11</text><text x="380" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">C</text><line x1="418" y1="90" x2="470" y2="90" stroke="var(--teal)" stroke-width="2"/><polygon points="470,85 478,90 470,95" fill="var(--teal)"/><text x="448" y="80" text-anchor="middle" fill="var(--ink-soft)" font-size="11">÷ 합 11.21</text><text x="570" y="18" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">확률</text><line x1="490" y1="140" x2="650" y2="140" stroke="var(--line)"/><rect x="502" y="40" width="36" height="100" rx="2" fill="var(--teal)" stroke="var(--teal)"/><text x="520" y="34" text-anchor="middle" fill="var(--ink)" font-size="12">65.9%</text><text x="520" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">A</text><rect x="552" y="103.27769347496206" width="36" height="36.722306525037936" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="570" y="97.27769347496206" text-anchor="middle" fill="var(--ink)" font-size="12">24.2%</text><text x="570" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">B</text><rect x="602" y="124.97723823975721" width="36" height="15.022761760242792" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="620" y="118.97723823975721" text-anchor="middle" fill="var(--ink)" font-size="12">9.9%</text><text x="620" y="156" text-anchor="middle" fill="var(--ink-soft)" font-size="13">C</text><text x="340" y="182" text-anchor="middle" fill="var(--ink-soft)" font-size="12">logit 차이 1.0(A와 B)이 확률에서는 약 2.7배 차이가 됩니다</text>
</svg>
<figcaption>softmax. 점수를 e의 거듭제곱으로 바꾼 뒤 합으로 나누어 확률을 만듭니다.</figcaption>
</figure>

두 후보의 확률 비는 logit의 차이만으로 정해집니다. logit이 1 높으면 확률은 약 2.7배(e¹), 2 높으면 약 7.4배(e²)입니다.

:::예제 1-2 다음 토큰의 확률 보기
"웨이퍼를 개별 칩으로 자르는 공정을" 다음에 올 토큰의 확률 분포를 계산하고 상위 10개를 출력합니다. logit의 개수, 확률의 합, 1위 토큰의 확률을 봅니다.

```python
prompt = '웨이퍼를 개별 칩으로 자르는 공정을'
input_ids = tokenizer(prompt, return_tensors='pt').input_ids  # 토큰 ID의 나열. 'pt'는 PyTorch 배열로 받는다는 뜻
with torch.no_grad():                                          # 확률만 계산하고 학습에 쓰는 값은 저장하지 않습니다
    logits = model(input_ids).logits[0, -1]                    # [0, -1]: 첫 번째(유일한) 입력의 맨 끝 위치
probabilities = torch.softmax(logits, dim=-1)
print(f'logit 개수: {len(logits):,}개, 확률의 합: {probabilities.sum():.3f}')

top = torch.topk(probabilities, 10)                            # 확률이 큰 순서로 10개
for probability, token_id in zip(top.values, top.indices):
    print(f'{tokenizer.decode([token_id])!r:10} logit {logits[token_id]:6.2f}  확률 {probability:6.1%}')
```
:::

logit 151,936개는 어휘(151,665개)보다 조금 많은데, 모델의 출력 개수를 넉넉하게 만들어 두었기 때문입니다. 1위 " 위해"도 7.4%뿐이고 상위 10개를 합쳐도 30%가 안 됩니다. 나머지 확률은 수많은 토큰에 조금씩 나뉘어 있습니다. 깨진 글자(' �') 후보는 한글 한 글자의 첫 바이트 조각입니다.

## 샘플링과 temperature

:::요점
확률 분포에서 토큰을 고르는 방법은 매번 1위를 고르는 방법과 확률대로 뽑는 방법이 있습니다. temperature는 뽑기 전에 분포를 1위 쪽으로 모으거나 고르게 펴고, top-p는 확률이 낮은 후보를 잘라 냅니다.
:::

### 1위만 고를 것인가, 확률대로 뽑을 것인가

확률 분포에서 토큰을 하나 고르는 가장 단순한 방법은 언제나 확률이 가장 높은 토큰을 고르는 것입니다. 이것을 [[greedy decoding]]이라고 합니다. 이론상 같은 입력에는 언제나 같은 응답이 나옵니다(서버의 예외는 이 장 끝에서 설명합니다). Holtzman 외(2020)는 이 방법으로 긴 글을 만들면 같은 구절을 되풀이하거나 단조로운 글이 되기 쉽다고 보고했습니다.

그래서 대부분의 서비스는 확률에 따라 무작위로 뽑는 샘플링을 씁니다. 예제 1-2의 분포라면 " 위해"는 100번 중 7번쯤, " 위한"은 3~4번쯤 뽑힙니다.

### temperature

[[temperature]]는 샘플링하기 전에 분포의 형태를 바꾸는 값입니다. logit을 temperature(T)로 나눈 뒤 softmax를 계산합니다.

```text
토큰 i의 확률 = exp(logit_i / T) / (모든 토큰의 exp(logit / T)를 더한 값)
```

앞의 세 후보에 T를 바꿔 적용하면 다음과 같습니다.

<figure>
<svg viewBox="0 0 680 222" role="img" aria-label="logit이 A 2.0, B 1.0, C 0.1인 세 후보에 temperature를 적용한 확률 막대그래프. T=0.5에서 A 86.4%, B 11.7%, C 1.9%. T=1.0에서 A 65.9%, B 24.2%, C 9.9%. T=2.0에서 A 50.2%, B 30.4%, C 19.4%. T가 낮을수록 A에 확률이 집중되고 높을수록 고르게 퍼집니다.">
<text x="115" y="20" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">T = 0.5</text><line x1="20" y1="170" x2="210" y2="170" stroke="var(--line)"/><rect x="35" y="57.67999999999999" width="44" height="112.32000000000001" rx="2" fill="var(--teal)" stroke="var(--teal)"/><text x="57" y="51.67999999999999" text-anchor="middle" fill="var(--ink)" font-size="12">86.4%</text><text x="57" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">A</text><rect x="95" y="154.79" width="44" height="15.209999999999999" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="117" y="148.79" text-anchor="middle" fill="var(--ink)" font-size="12">11.7%</text><text x="117" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">B</text><rect x="155" y="167.53" width="44" height="2.4699999999999998" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="177" y="161.53" text-anchor="middle" fill="var(--ink)" font-size="12">1.9%</text><text x="177" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">C</text><text x="340" y="20" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">T = 1.0</text><line x1="245" y1="170" x2="435" y2="170" stroke="var(--line)"/><rect x="260" y="84.32999999999998" width="44" height="85.67000000000002" rx="2" fill="var(--teal)" stroke="var(--teal)"/><text x="282" y="78.32999999999998" text-anchor="middle" fill="var(--ink)" font-size="12">65.9%</text><text x="282" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">A</text><rect x="320" y="138.54" width="44" height="31.46" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="342" y="132.54" text-anchor="middle" fill="var(--ink)" font-size="12">24.2%</text><text x="342" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">B</text><rect x="380" y="157.13" width="44" height="12.870000000000001" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="402" y="151.13" text-anchor="middle" fill="var(--ink)" font-size="12">9.9%</text><text x="402" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">C</text><text x="565" y="20" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">T = 2.0</text><line x1="470" y1="170" x2="660" y2="170" stroke="var(--line)"/><rect x="485" y="104.74" width="44" height="65.26" rx="2" fill="var(--teal)" stroke="var(--teal)"/><text x="507" y="98.74" text-anchor="middle" fill="var(--ink)" font-size="12">50.2%</text><text x="507" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">A</text><rect x="545" y="130.48000000000002" width="44" height="39.519999999999996" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="567" y="124.48000000000002" text-anchor="middle" fill="var(--ink)" font-size="12">30.4%</text><text x="567" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">B</text><rect x="605" y="144.78" width="44" height="25.22" rx="2" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="627" y="138.78" text-anchor="middle" fill="var(--ink)" font-size="12">19.4%</text><text x="627" y="188" text-anchor="middle" fill="var(--ink-soft)" font-size="13">C</text><text x="340" y="212" text-anchor="middle" fill="var(--ink-soft)" font-size="12">logit은 세 그림 모두 A 2.0, B 1.0, C 0.1로 같습니다. 바뀐 것은 T뿐입니다</text>
</svg>
<figcaption>temperature에 따른 확률 분포. T가 낮으면 1위(A)로 모이고, 높으면 고르게 퍼집니다.</figcaption>
</figure>

T가 1보다 작으면 logit의 차이가 커진 것과 같아서 1위에 확률이 모이고, 0에 가까우면 greedy decoding과 같아집니다. T가 1보다 크면 차이가 줄어 확률이 고르게 퍼집니다.

:::예제 1-3 temperature가 분포를 바꾸는 모습
예제 1-2의 logit에 T=0.3, 1.0, 2.0을 적용해 상위 3개 토큰의 확률을 비교합니다. 이어서 같은 T로 문장을 두 번씩 생성합니다. T가 커질수록 1위의 확률과 생성한 문장이 어떻게 바뀌는지 봅니다. [[시드]](seed)는 난수를 만드는 시작값입니다. `top_k`, `top_p`는 이 절 뒤의 "top-k와 top-p"에서 설명합니다.

```python
for temperature in [0.3, 1.0, 2.0]:
    scaled = torch.softmax(logits / temperature, dim=-1)         # logit을 T로 나눈 뒤 softmax
    top = torch.topk(scaled, 3)
    summary = ', '.join(f'{tokenizer.decode([token_id])!r} {probability:.1%}'
                        for probability, token_id in zip(top.values, top.indices))
    print(f'T={temperature}  상위 3개: {summary}')

torch.manual_seed(0)                                              # 시드를 고정해 같은 PC에서는 같은 문장이 나오게 합니다
for temperature in [0.3, 1.0, 2.0]:
    for attempt in range(2):
        # generate()는 네 단계를 max_new_tokens번 되풀이합니다. do_sample=True는 샘플링한다는 뜻이고,
        # top_k=0, top_p=1.0, repetition_penalty=1.0은 이 모델의 기본 조정을 꺼서 temperature만의 효과를 봅니다
        output = model.generate(input_ids, do_sample=True, temperature=temperature, top_k=0, top_p=1.0,
                                repetition_penalty=1.0, max_new_tokens=20, pad_token_id=tokenizer.eos_token_id)
        continuation = tokenizer.decode(output[0, input_ids.shape[1]:], skip_special_tokens=True)
        print(f'\nT={temperature}: {prompt}{continuation}'.replace('\n', ' ').strip())
```
:::


T=0.3에서는 1위가 75%로 올라가 " 위해"가 자주 뽑히고, "위해, 공정의 개선을 위해, 공정의 보호를 위해"처럼 같은 구절이 되풀이되기도 합니다. T=2.0에서는 1위도 1%가 안 되어, 다른 언어의 토큰과 기호가 섞인 문장이 나옵니다. T=1.0의 문장도 주제와 관계없는 글로 흘렀습니다.

### top-k와 top-p

T=1.0과 T=2.0에서 생성한 문장의 뜻이 통하지 않는 이유는, 하나하나는 확률이 낮지만 개수가 많은 후보들이 합쳐서 큰 확률을 차지하기 때문입니다. 이런 후보를 분포의 꼬리라고 부릅니다. 꼬리를 잘라 내는 방법이 두 가지 있습니다.

- [[top-k 샘플링]]은 확률이 높은 토큰 k개만 남기고 그 안에서 뽑습니다. k가 고정이라, 분포가 1위에 집중된 자리에서도 고르게 퍼진 자리에서도 같은 개수를 남깁니다.
- [[top-p]](nucleus sampling)는 확률이 높은 토큰부터 차례로 더해, 누적 확률이 p에 이르는 데까지만 남기고 그 안에서 뽑습니다(Holtzman 외, 2020). 분포가 1위에 집중된 자리에서는 몇 개만 남고, 고르게 퍼진 자리에서는 많이 남습니다.

남은 후보는 합이 1이 되도록 다시 나눈 뒤 그 안에서 뽑습니다.

<figure>
<svg viewBox="0 0 680 276" role="img" aria-label="top-p(p=0.9)가 후보를 남기는 방법을 누적 확률 막대로 나타낸 그림. 65.9%, 24.2%, 9.9%인 세 후보는 B까지 누적 90.1%로 A와 B가 남습니다. 1위가 95%인 분포는 A 하나만 남고, 30%, 25%, 20%, 15%, 10%로 고르게 퍼진 분포는 D까지 4개가 남습니다.">
<text x="100" y="16" fill="var(--ink-soft)" font-size="12">누적 확률 0%</text><text x="660" y="16" text-anchor="end" fill="var(--ink-soft)" font-size="12">100%</text><text x="598" y="16" text-anchor="end" fill="var(--amber)" font-size="12" font-weight="700">p = 0.9</text><text x="10" y="47" fill="var(--ink)" font-size="13" font-weight="700">세 후보</text><rect x="100" y="26" width="369.04" height="32" rx="0" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="284.52" y="47" text-anchor="middle" fill="var(--ink)" font-size="12">A 65.9%</text><rect x="469.04" y="26" width="135.51999999999998" height="32" rx="0" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="536.8" y="47" text-anchor="middle" fill="var(--ink)" font-size="12">B 24.2%</text><rect x="604.56" y="26" width="55.440000000000005" height="32" rx="0" fill="var(--amber-wash)" stroke="var(--amber)" stroke-dasharray="4 3"/><text x="632.28" y="47" text-anchor="middle" fill="var(--amber)" font-size="12">C</text><line x1="604" y1="18" x2="604" y2="66" stroke="var(--amber)" stroke-width="2"/><text x="100" y="80" fill="var(--ink-soft)" font-size="12">B까지 쌓으면 90.1%로 0.9에 이릅니다. A와 B를 남기고 다시 나누면 A 73.1%, B 26.9%</text><text x="10" y="137" fill="var(--ink)" font-size="13" font-weight="700">1위에 집중</text><rect x="100" y="116" width="532" height="32" rx="0" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="366" y="137" text-anchor="middle" fill="var(--ink)" font-size="12">A 95%</text><rect x="632" y="116" width="16.8" height="32" rx="0" fill="var(--amber-wash)" stroke="var(--amber)" stroke-dasharray="4 3"/><rect x="648.8" y="116" width="11.200000000000001" height="32" rx="0" fill="var(--amber-wash)" stroke="var(--amber)" stroke-dasharray="4 3"/><line x1="604" y1="108" x2="604" y2="156" stroke="var(--amber)" stroke-width="2"/><text x="100" y="170" fill="var(--ink-soft)" font-size="12">A 하나로 0.9를 넘으므로 후보 1개만 남습니다</text><text x="10" y="227" fill="var(--ink)" font-size="13" font-weight="700">고르게 퍼짐</text><rect x="100" y="206" width="168" height="32" rx="0" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="184" y="227" text-anchor="middle" fill="var(--ink)" font-size="12">A 30%</text><rect x="268" y="206" width="140" height="32" rx="0" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="338" y="227" text-anchor="middle" fill="var(--ink)" font-size="12">B 25%</text><rect x="408" y="206" width="112" height="32" rx="0" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="464" y="227" text-anchor="middle" fill="var(--ink)" font-size="12">C 20%</text><rect x="520" y="206" width="84" height="32" rx="0" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="562" y="227" text-anchor="middle" fill="var(--ink)" font-size="12">D 15%</text><rect x="604" y="206" width="56" height="32" rx="0" fill="var(--amber-wash)" stroke="var(--amber)" stroke-dasharray="4 3"/><text x="632" y="227" text-anchor="middle" fill="var(--amber)" font-size="12">E</text><line x1="604" y1="198" x2="604" y2="246" stroke="var(--amber)" stroke-width="2"/><text x="100" y="260" fill="var(--ink-soft)" font-size="12">D까지 쌓아야 90%에 이르므로 후보 4개가 남습니다</text>
</svg>
<figcaption>top-p(p=0.9). 확률이 큰 후보부터 쌓아 0.9(주황색 선)에 이르는 데까지 남기고, 나머지(주황색 점선 칸)는 잘라 냅니다. 남는 후보 수는 분포의 형태에 따라 바뀝니다.</figcaption>
</figure>

temperature로 분포를 조정한 뒤 top-p로 꼬리를 자르는 식으로 함께 쓸 수 있습니다. 실습 1-2에서 top-p를 직접 작성합니다.

## 같은 질문에 응답이 매번 다른 이유

:::요점
서비스 모델도 샘플링으로 토큰을 고르므로, 같은 질문에 표현이 다른 응답이 돌아옵니다. 앞에서 뽑힌 토큰 하나가 달라지면 그 토큰이 다음 입력이 되므로 그 뒤의 글 전체가 달라질 수 있습니다.
:::

LLM 서비스도 토큰마다 샘플링하므로 같은 질문에 다른 토큰이 뽑힐 수 있습니다. 뽑힌 토큰은 다음 계산의 입력이 되므로, 토큰 하나가 달라지면 그 뒤의 확률 분포가 모두 바뀝니다. 예제 1-3에서는 확률 0.65%인 " 제공"이 뽑히자 문장이 전혀 다른 내용으로 이어졌습니다.

<figure>
<svg viewBox="0 0 680 210" role="img" aria-label="같은 입력 웨이퍼를 개별 칩으로 자르는 공정을 에서 T=0.3으로 두 번 생성한 결과. 한 번은 확률 75.4%인 1위 토큰 위해가 뽑혀 위해, 공정의 개선을 위해, 공정의 보호를 위해로 이어졌고, 다른 한 번은 확률 0.65%인 10위 토큰 제공이 뽑혀 제공하는 기술은 2017년에 발달한 것으로 알려져 있습니다로 이어졌습니다.">
<rect x="10" y="62" width="200" height="60" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="110" y="87" text-anchor="middle" fill="var(--ink)" font-size="13">웨이퍼를 개별 칩으로</text><text x="110" y="107" text-anchor="middle" fill="var(--ink)" font-size="13">자르는 공정을</text><path d="M 210 92 C 230 92, 225 40, 250 40" fill="none" stroke="var(--teal)" stroke-width="5"/><path d="M 210 92 C 230 92, 225 146, 250 146" fill="none" stroke="var(--amber)" stroke-width="1.5" stroke-dasharray="5 4"/><rect x="250" y="14" width="150" height="52" rx="8" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="325" y="36" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">" 위해" 75.4%</text><text x="325" y="56" text-anchor="middle" fill="var(--ink-soft)" font-size="12">1위</text><rect x="250" y="120" width="150" height="52" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="325" y="142" text-anchor="middle" fill="var(--amber)" font-size="13" font-weight="700">" 제공" 0.65%</text><text x="325" y="162" text-anchor="middle" fill="var(--ink-soft)" font-size="12">10위</text><line x1="400" y1="40" x2="412" y2="40" stroke="var(--teal)" stroke-width="2"/><polygon points="412,35 420,40 412,45" fill="var(--teal)"/><line x1="400" y1="146" x2="412" y2="146" stroke="var(--amber)" stroke-width="2"/><polygon points="412,141 420,146 412,151" fill="var(--amber)"/><rect x="420" y="14" width="250" height="52" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="434" y="36" fill="var(--ink)" font-size="13">위해, 공정의 개선을 위해,</text><text x="434" y="56" fill="var(--ink)" font-size="13">공정의 보호를 위해, 공정</text><rect x="420" y="120" width="250" height="52" rx="8" fill="var(--sheet)" stroke="var(--line)"/><text x="434" y="142" fill="var(--ink)" font-size="13">제공하는 기술은 2017년에</text><text x="434" y="162" fill="var(--ink)" font-size="13">발달한 것으로 알려져 있습니다.</text><text x="340" y="198" text-anchor="middle" fill="var(--ink-soft)" font-size="12">같은 입력, 같은 T=0.3에서 첫 토큰 하나가 다르게 뽑힌 두 문장(예제 1-3의 실행 결과)</text>
</svg>
<figcaption>예제 1-3에서 T=0.3으로 생성한 두 문장. 첫 토큰 하나가 다르면 뒤의 글 전체가 달라집니다.</figcaption>
</figure>

:::예제 1-4 같은 질문 세 번
같은 질문을 서비스 모델에 세 번 보내 표현, 문장 순서, 덧붙인 내용이 어떻게 다른지 봅니다. `llm.ask()`는 공통 호출 함수 `llm.py`의 함수로, 질문을 API로 보내고 응답(`reply.text`)을 돌려줍니다. `model='소형'`은 [[모델 등급]] 가운데 가장 작은 모델입니다(5장 "LLM API"에서 자세히 다룹니다). 이 셀은 API를 3번 호출합니다.

```python
question = '반도체 후공정의 다이싱 공정을 두 문장으로 설명해 주세요.'
for attempt in range(1, 4):
    reply = llm.ask(question, model='소형', max_tokens=1000)
    print(f'[{attempt}회] {reply.text}\n')
```
:::

세 응답 모두 다이싱을 "스크라이브 레인을 따라 잘라 개별 칩으로 분리하는 공정"으로 설명했지만, 문장 구성과 둘째 문장에 덧붙인 내용(다이싱 테이프, 다음 공정)은 응답마다 달랐습니다. 핵심 내용은 확률이 높은 토큰으로 비슷하게 이어지고, 확률이 비슷한 후보가 여럿인 자리에서 어떤 토큰이 뽑히느냐에 따라 표현이 바뀝니다.

### temperature를 설정할 수 있는가

- Anthropic의 최신 Claude 모델은 temperature를 바꿀 수 없습니다. Claude Opus 4.7 이후의 모델은 temperature, top_p, top_k를 기본값에서 바꾸면 오류(400)를 돌려주고, API 버전 2026-10-21부터는 넣기만 해도 오류가 납니다. 현재 Python SDK(software development kit) 2.x에는 이 인자가 없습니다(2026-11 확인).
- OpenAI 호환 API는 대개 `temperature`와 `top_p`를 받지만, 범위와 기본값은 서버마다 다릅니다.

그래서 이 교재의 `llm.py`는 temperature를 인자로 받지 않습니다.

### temperature를 0으로 해도 같지 않은 이유

temperature를 0으로 설정하면 이론상 언제나 1위 토큰만 고르지만, 실제로는 응답이 완전히 같지 않을 때가 있습니다(Anthropic 문서도 같은 출력을 보장하지 않는다고 적고 있습니다). He(2025)는 원인을 서버가 여러 요청을 묶어(배치) 계산하는 방식으로 설명합니다.

<figure>
<svg viewBox="0 0 680 158" role="img" aria-label="같은 입력이라도 요청을 혼자 계산할 때와 8개를 묶어 계산할 때 계산 순서가 달라져 logit의 끝자리가 바뀌는 그림. 혼자 계산하면 위해가 11.5003, 위한이 11.5001이라 위해를 고르고, 묶어 계산하면 위해 11.5001, 위한 11.5002라 위한을 골라 뒤의 글이 달라집니다. 숫자는 가정한 값입니다.">
<text x="10" y="34" fill="var(--ink)" font-size="13" font-weight="700">요청을 혼자 계산</text><text x="10" y="52" fill="var(--ink-soft)" font-size="11">묶음 크기 1</text><rect x="170" y="14" width="200" height="44" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="270" y="33" text-anchor="middle" fill="var(--ink)" font-size="12">" 위해" logit 11.5003</text><text x="270" y="50" text-anchor="middle" fill="var(--ink)" font-size="12">" 위한" logit 11.5001</text><line x1="370" y1="36" x2="384" y2="36" stroke="var(--teal)" stroke-width="2"/><polygon points="384,31 392,36 384,41" fill="var(--teal)"/><rect x="392" y="14" width="100" height="44" rx="6" fill="var(--teal-wash)" stroke="var(--teal)"/><text x="442" y="41" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="700">" 위해"</text><line x1="492" y1="36" x2="504" y2="36" stroke="var(--teal)" stroke-width="2"/><polygon points="504,31 512,36 504,41" fill="var(--teal)"/><rect x="512" y="14" width="158" height="44" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="591" y="41" text-anchor="middle" fill="var(--ink)" font-size="12">…위해 …로 이어짐</text><text x="10" y="96" fill="var(--ink)" font-size="13" font-weight="700">요청 8개를 묶어 계산</text><text x="10" y="114" fill="var(--ink-soft)" font-size="11">계산 순서가 달라짐</text><rect x="170" y="76" width="200" height="44" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="270" y="95" text-anchor="middle" fill="var(--ink)" font-size="12">" 위해" logit 11.5001</text><text x="270" y="112" text-anchor="middle" fill="var(--ink)" font-size="12">" 위한" logit 11.5002</text><line x1="370" y1="98" x2="384" y2="98" stroke="var(--teal)" stroke-width="2"/><polygon points="384,93 392,98 384,103" fill="var(--teal)"/><rect x="392" y="76" width="100" height="44" rx="6" fill="var(--amber-wash)" stroke="var(--amber)"/><text x="442" y="103" text-anchor="middle" fill="var(--amber)" font-size="13" font-weight="700">" 위한"</text><line x1="492" y1="98" x2="504" y2="98" stroke="var(--teal)" stroke-width="2"/><polygon points="504,93 512,98 504,103" fill="var(--teal)"/><rect x="512" y="76" width="158" height="44" rx="6" fill="var(--sheet)" stroke="var(--line)"/><text x="591" y="103" text-anchor="middle" fill="var(--ink)" font-size="12">…위한 …로 이어짐</text><text x="340" y="146" text-anchor="middle" fill="var(--ink-soft)" font-size="12">temperature 0이라도 1위가 바뀌면 그 뒤의 글이 달라집니다. 숫자는 설명을 위해 가정한 값입니다</text>
</svg>
<figcaption>서버가 요청을 묶어 계산할 때 생기는 차이(He, 2025). 1위와 2위의 logit이 거의 같은 자리에서만 결과가 바뀝니다.</figcaption>
</figure>

따라서 응답이 매번 다를 수 있다는 전제로 설계합니다. 응답을 프로그램이 처리한다면 출력 형식을 정하고(4장, 6장) 받은 응답을 검사합니다.

## 이 원리에서 나오는 것

:::요점
사실을 찾아보지 않고, 토큰 단위로 다루고, 확률로 뽑는다는 세 가지 성질이 LLM을 쓸 때의 주의점이 됩니다.
:::

- **근거 없는 내용이 생성됩니다**([[환각]], 2장).
- **비용과 길이가 토큰으로 정해집니다**(3장, 5장).
- **응답이 매번 다릅니다.** 프로그램에서 처리하려면 형식을 정하고 검사합니다(4장, 6장).

## 개념 확인 실습

실습은 장 노트북의 빈칸을 채워 실행합니다. 코드를 실행하기 전에 결과를 먼저 예측해 적고, 실행한 뒤 예측과 다른 부분을 이 장의 원리로 설명해 봅니다.

:::실습 1-1 토큰 수를 먼저 예측하기
후공정 문장 다섯 개의 토큰 수를 셉니다. 실행하기 전에 `my_ranking`에 토큰이 많을 것 같은 순서로 이름을 적습니다. `token_count()`는 예제 1-1의 `tokenizer`로 토큰 수를 세어 돌려주도록 작성합니다. 예측과 다른 문장의 이유를 BPE로 한 문장씩 설명하면 끝납니다. 힌트: `tokenizer.encode()`가 돌려주는 목록의 길이가 토큰 수입니다.

```python
sentences = {
    '한국어': '패키지 테스트에서 불량으로 판정된 칩은 별도 트레이로 옮깁니다.',
    '영어': 'Chips that fail the package test are moved to a separate tray.',
    '숫자와 단위': '리플로 최고 온도 260°C, 유지 시간 10초, 승온 속도 3°C/s',
    '제품 코드': 'QFN-48, BGA-256, SOP-8',
    '파이썬 코드': 'for chip in wafer.chips: print(chip.id)',
}
my_ranking = []  # TODO: 토큰이 많을 것 같은 순서로 이름을 적습니다. 예: ['한국어', '영어', ...]


def token_count(text):
    return None  # TODO: tokenizer로 text의 토큰 수를 세어 돌려줍니다


counts = {name: token_count(sentence) for name, sentence in sentences.items()}
for name, sentence in sentences.items():
    print(f'{name}: {len(sentence)}자, {counts[name]}토큰')
print('\n예측한 순서:', my_ranking)
print('실제 순서:  ', sorted(counts, key=counts.get, reverse=True))
```

:::풀이
`tokenizer.encode()`가 돌려주는 토큰 ID 목록의 길이가 토큰 수입니다. 실제 순위를 구해 예측과 나란히 출력합니다.

```python
sentences = {
    '한국어': '패키지 테스트에서 불량으로 판정된 칩은 별도 트레이로 옮깁니다.',
    '영어': 'Chips that fail the package test are moved to a separate tray.',
    '숫자와 단위': '리플로 최고 온도 260°C, 유지 시간 10초, 승온 속도 3°C/s',
    '제품 코드': 'QFN-48, BGA-256, SOP-8',
    '파이썬 코드': 'for chip in wafer.chips: print(chip.id)',
}
my_ranking = ['숫자와 단위', '한국어', '제품 코드', '영어', '파이썬 코드']


def token_count(text):
    return len(tokenizer.encode(text))


counts = {name: token_count(sentence) for name, sentence in sentences.items()}
for name, sentence in sentences.items():
    print(f'{name}: {len(sentence)}자, {counts[name]}토큰')
print('\n예측한 순서:', my_ranking)
print('실제 순서:  ', sorted(counts, key=counts.get, reverse=True))
print('\n숫자와 단위:', ' | '.join(tokenizer.decode([token_id]) for token_id in tokenizer.encode(sentences['숫자와 단위'])))
```

숫자와 단위가 많은 문장은 숫자가 한 자리씩 나뉘고, " 온", " 승"처럼 앞에 공백이 붙은 한글 글자가 바이트 조각 2개로 나뉘어 글자 수보다 토큰이 조금 적은 정도입니다. 한국어 문장은 글자 수가 영어 문장의 절반 남짓인데 토큰은 두 배입니다. 파이썬 코드는 영어 낱말과 자주 쓰는 기호 조합(".id", "(chip")이 토큰 하나로 묶여 있어 글자 수에 비해 토큰이 가장 적습니다.
:::
:::

:::실습 1-2 top-p 함수 작성하기
`top_p_filter(probabilities, p)`를 작성합니다. 확률이 높은 토큰부터 차례로 더해 누적 확률이 처음으로 p 이상이 되는 토큰까지 남기고, 남은 토큰 ID 목록을 돌려줍니다. 실행하기 전에 `my_guess`에 세 경우의 남는 후보 수를 예측해 적습니다. 셋째 경우는 temperature 0.3의 분포입니다. 예제 1-2를 먼저 실행해야 합니다. 예측과 다른 경우의 이유를 분포의 형태로 설명하면 끝납니다.

```python
def top_p_filter(probabilities, p):
    """누적 확률이 처음으로 p 이상이 되는 토큰까지, 확률이 높은 순서로 토큰 ID 목록을 돌려줍니다."""
    return []  # TODO


my_guess = {'T=1.0, p=0.5': None, 'T=1.0, p=0.9': None, 'T=0.3, p=0.9': None}  # TODO: 남는 후보 수를 예측해 적습니다

for temperature, p in [(1.0, 0.5), (1.0, 0.9), (0.3, 0.9)]:
    kept = top_p_filter(torch.softmax(logits / temperature, dim=-1), p)
    guess = my_guess[f'T={temperature}, p={p}']
    print(f'T={temperature}, p={p}: 후보 {len(kept):,}개 (예측 {guess})', [tokenizer.decode([token_id]) for token_id in kept[:5]])
```

:::풀이
확률을 큰 순서로 정렬하고 누적합을 구합니다. 누적합이 p보다 작은 토큰의 개수에 1을 더하면, 누적 확률이 처음으로 p 이상이 되는 토큰까지의 개수입니다.

```python
def top_p_filter(probabilities, p):
    """누적 확률이 처음으로 p 이상이 되는 토큰까지, 확률이 높은 순서로 토큰 ID 목록을 돌려줍니다."""
    sorted_probabilities, sorted_ids = torch.sort(probabilities, descending=True)
    cumulative = torch.cumsum(sorted_probabilities, dim=0)
    keep = int((cumulative < p).sum()) + 1
    return sorted_ids[:keep].tolist()


my_guess = {'T=1.0, p=0.5': 10, 'T=1.0, p=0.9': 50, 'T=0.3, p=0.9': 3}

for temperature, p in [(1.0, 0.5), (1.0, 0.9), (0.3, 0.9)]:
    kept = top_p_filter(torch.softmax(logits / temperature, dim=-1), p)
    guess = my_guess[f'T={temperature}, p={p}']
    print(f'T={temperature}, p={p}: 후보 {len(kept):,}개 (예측 {guess})', [tokenizer.decode([token_id]) for token_id in kept[:5]])
```

T=1.0에서는 1위의 확률이 7.4%밖에 되지 않아, 누적 확률 0.5를 채우는 데도 수십 개, 0.9를 채우는 데는 백 개가 넘는 후보가 필요합니다. temperature를 0.3으로 낮추면 1위에 확률이 집중되어 같은 p=0.9로도 후보가 몇 개만 남습니다. top-p가 남기는 후보 수는 고정되어 있지 않고 분포의 형태에 따라 바뀝니다.
:::
:::

## 자가점검

**1.** LLM에 사내 규정의 숫자를 물었더니 그럴듯한 숫자를 답했습니다. 응답을 만드는 과정의 네 단계에 비추어, 이 숫자를 그대로 믿으면 안 되는 이유를 설명해 보세요.

:::정답
네 단계(토큰으로 나누기, 확률 계산, 하나 뽑기, 이어 붙이기) 어디에도 규정을 찾아보는 단계가 없습니다. 모델은 학습한 글의 패턴에 따라 그럴듯한 숫자 토큰을 뽑았을 뿐입니다. 사내 규정은 학습한 글에 없으므로, 숫자가 맞는지는 규정 문서와 대조해야 알 수 있습니다.
:::

**2.** 다음 중 BPE 토크나이저에서 같은 뜻의 한국어 문장이 영어 문장보다 토큰이 많은 이유로 가장 알맞은 것은 무엇입니까?

- A. 한국어는 문법이 복잡해서 모델이 더 많이 계산해야 한다
- B. 학습 데이터에 한국어가 적게 나와 한국어 조각이 덜 합쳐졌다
- C. 토크나이저가 한국어를 영어로 번역한 뒤 나눈다

:::정답
**B.** BPE는 학습 데이터에서 자주 붙어 나온 조각을 합쳐 어휘를 만듭니다. 영어 낱말은 자주 나와 통째로 토큰이 되고, 한국어는 적게 나와 여러 조각으로 남습니다. 바이트 단위 BPE에서는 한글 한 글자가 바이트 조각 여러 개가 되기도 합니다.
:::

**3.** 예제 1-1에서 "칩"은 토큰 하나였지만 " 칩"(앞에 공백)은 토큰 2개였습니다. 왜 이런 차이가 생깁니까?

:::정답
토큰에는 앞의 공백이 포함되기도 합니다. 어휘에는 "칩"이 토큰으로 있지만 " 칩"은 없습니다. " 칩"은 공백과 "칩"의 UTF-8 3바이트가 한 토큰으로 합쳐진 적이 없어서 바이트 조각으로 나뉩니다.
:::

**4.** 예제 1-2에서 logit이 151,936개 나왔습니다. 이 개수는 무엇에 맞춰 정해지고, logit은 입력의 어느 위치의 벡터에서 계산합니까?

:::정답
모델의 출력 개수이고, 어휘의 토큰마다 하나씩 대응합니다(어휘 151,665개보다 조금 넉넉하게 만들어져 있습니다). logit은 마지막 층을 지난 뒤 입력의 맨 끝 위치에 있는 벡터에 토큰마다 한 행씩 있는 행렬을 곱해 계산합니다. 그 벡터에는 어텐션으로 앞 토큰들의 정보가 섞여 있습니다.
:::

**5.** 어떤 자리에서 후보 세 개의 logit이 3.0, 1.0, 1.0입니다. softmax로 계산한 1위의 확률은 대략 얼마입니까? temperature를 2로 하면 1위의 확률은 커집니까, 작아집니까?

:::정답
e^3 ≈ 20.1, e^1 ≈ 2.72이므로 1위의 확률은 20.1 ÷ (20.1 + 2.72 + 2.72) ≈ 78.7%입니다. temperature를 2로 하면 logit이 1.5, 0.5, 0.5가 되어 차이가 줄어듭니다. 1위의 확률은 e^1.5 ≈ 4.48을 (4.48 + 1.65 + 1.65)로 나눈 약 57.6%로 작아집니다.
:::

**6.** top-k 샘플링(k=10)과 top-p 샘플링(p=0.9)의 차이를, 분포가 1위에 집중된 자리와 고르게 퍼진 자리를 예로 들어 설명해 보세요.

:::정답
top-k는 어느 자리에서나 후보 10개를 남깁니다. 1위의 확률이 95%인 자리에서도 확률이 아주 낮은 후보 9개가 함께 남고, 확률이 고르게 퍼진 자리에서는 적당한 후보가 10개보다 많아도 10개만 남습니다. top-p는 누적 확률이 0.9에 이를 때까지만 남기므로 1위가 95%인 자리에서는 후보 1개, 고르게 퍼진 자리에서는 후보 수십에서 수백 개가 남습니다(실습 1-2에서는 194개).
:::

**7.** 후보 네 개의 확률이 50%, 25%, 15%, 10%입니다. top-p(p=0.8)를 적용하면 후보가 몇 개 남고, 남은 후보를 합이 1이 되도록 다시 나눈 확률은 각각 얼마입니까?

:::정답
3개가 남습니다. 50%와 25%를 더하면 75%로 0.8에 못 미치고, 15%를 더하면 90%로 0.8에 이릅니다. 남은 세 후보의 합 90%로 다시 나누면 55.6%, 27.8%, 16.7%입니다.
:::

**8.** 응답을 프로그램에서 처리하려고 temperature를 0으로 설정했는데도 가끔 응답이 달랐습니다. 가능한 원인은 무엇이고, 어떻게 대비해야 합니까?

:::정답
서버는 여러 요청을 묶어 계산하는데, 묶인 요청의 수에 따라 계산 순서가 바뀌어 logit의 끝자리가 조금씩 바뀝니다. 1위와 2위가 비슷한 자리에서 고른 토큰이 바뀌면 그 뒤의 글이 달라집니다. 응답이 매번 같다고 가정하지 않고, 출력 형식을 정해 두고 받은 응답이 형식과 조건에 맞는지 검사합니다. 최신 Claude 모델은 temperature를 설정할 수도 없습니다.
:::

## 참고 문헌

- Sennrich, R., Haddow, B., Birch, A. (2016). Neural Machine Translation of Rare Words with Subword Units. ACL 2016.
- Radford, A. 외 (2019). Language Models are Unsupervised Multitask Learners. OpenAI.
- Vaswani, A. 외 (2017). Attention Is All You Need. NeurIPS 2017.
- Holtzman, A. 외 (2020). The Curious Case of Neural Text Degeneration. ICLR 2020.
- He, H. (2025). Defeating Nondeterminism in LLM Inference. Thinking Machines Lab.
- Anthropic. Claude API 문서: 모델 이전 안내, API 버전 2026-10-21 이전 안내(2026-11 확인).
