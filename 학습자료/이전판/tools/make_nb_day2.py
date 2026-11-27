"""2일차 실습 노트북과 풀이 노트북을 만든다. (예제는 build.py가 원고에서 학습 노트북으로 만든다)

사용법: python make_nb_day2.py
출력: 노트북/2일차_실습.ipynb, 노트북/2일차_실습_풀이.ipynb

노트북은 노트북/ 폴더에서 실행한다(llm.py, checks.py, data/가 같은 폴더에 있다).
"""
import re
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = Path(__file__).resolve().parents[1] / '노트북'


def md(text):
    return new_markdown_cell(text.strip('\n'))


def code(text, tag=None):
    cell = new_code_cell(text.strip('\n'))
    if tag:
        cell.metadata['tags'] = [tag]
    return cell


def save(name, cells):
    notebook = new_notebook(cells=cells)
    notebook.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    notebook.metadata['language_info'] = {'name': 'python'}
    nbformat.validate(notebook)
    nbformat.write(notebook, OUT / name)
    print(f'{name} {len(cells)}셀')


import learn_nb  # noqa: E402  (같은 tools 폴더)

SETUP_TEXT = learn_nb.setup_text(Path(__file__).resolve().parents[1] / '교재_템플릿', '2일차')
SETUP_MD, SETUP_KEYS, SETUP_COMMON, SETUP_AFTER = [      # 안내, 준비 (1), 준비 (2), 오류 표
    part.strip('\n') for part in re.split(r'```python\n(.*?)\n```', SETUP_TEXT, flags=re.S)
    if part.strip()]

TODO = "raise NotImplementedError('이 부분을 채웁니다')"

PRACTICE_INTRO = '''
# 2일차 파트 1 실습: LLM API 기초

실습은 네 개입니다. 각 실습에는 목적, 재료, 완료 기준이 적혀 있습니다.
`{todo}`가 있는 곳을 직접 채웁니다. 막히면 힌트를 펼쳐 보고, 다 한 뒤에 `2일차_실습_풀이.ipynb`와 비교합니다.
실습 1과 3의 테스트 셀은 mock 호출을 써서 여러분의 함수가 맞게 동작하는지 알려 줍니다. API를 부르지 않으므로 요금이 들지 않습니다. 실습 4는 `코딩도구_실습/check.py`로 판정합니다.
'''.replace('{todo}', 'NotImplementedError')

SOLUTION_INTRO = '''
# 2일차 파트 1 실습 풀이

`2일차_실습.ipynb`의 풀이와 해설입니다. 풀이는 하나의 예시이며, 테스트 셀을 통과한다면 다르게 작성해도 됩니다.
'''

P1_MD = '''
## 실습 1 대화 이력을 관리하는 함수

**목적** API 서버는 앞 대화를 기억하지 않습니다. 대화를 이어 가는 일을 코드로 직접 해 봅니다.

**할 일** `chat(history, user_message, keep_turns=None, send=llm.send)`을 완성합니다.

1. `history`(메시지 목록)에 새 질문을 넣습니다.
2. `send`로 보냅니다. `keep_turns`가 `None`이면 `history` 전체를 보냅니다. 숫자면 최근 `keep_turns`턴(질문과 응답 한 쌍이 한 턴)과 새 질문만 보냅니다. `send`에는 `model='소형', max_tokens=500`을 함께 넘깁니다. 풀이와 같은 조건이어야 측정한 입력 토큰을 풀이의 숫자와 비교할 수 있습니다.
3. 받은 응답을 `history`에 넣고, `send`가 돌려준 `Reply` 객체를 그대로 돌려줍니다.

**완료 기준** 테스트 셀이 "실습 1 통과"를 출력합니다. 그다음 측정 셀을 실행해 전체를 보낼 때와 최근 2턴만 보낼 때의 입력 토큰을 비교해 적습니다.

<details><summary>힌트 1</summary>

보낼 목록은 `history`를 잘라서 만듭니다. 한 턴은 메시지 두 개이고 새 질문이 하나 더 있으므로, 최근 k턴과 새 질문은 뒤에서 `2 * k + 1`개입니다.
</details>

<details><summary>힌트 2</summary>

`history`에는 잘라 낸 목록이 아니라 전체 대화를 계속 쌓습니다. 자르는 것은 보낼 때뿐입니다.
</details>
'''

P1_SKELETON = f'''
# 실습 1
def chat(history, user_message, keep_turns=None, send=llm.send):
    """history에 질문을 더해 보내고, 받은 응답도 history에 넣은 뒤 Reply를 돌려줍니다."""
    {TODO}
'''

P1_SOLUTION = '''
# 실습 1
def chat(history, user_message, keep_turns=None, send=llm.send):
    """history에 질문을 더해 보내고, 받은 응답도 history에 넣은 뒤 Reply를 돌려줍니다."""
    history.append({'role': 'user', 'content': user_message})
    if keep_turns is None:
        to_send = history
    else:
        to_send = history[-(2 * keep_turns + 1):]     # 최근 k턴(메시지 2k개)과 새 질문
    reply = send(to_send, model='소형', max_tokens=500)
    history.append({'role': 'assistant', 'content': reply.text})
    return reply
'''

P1_CHECK = '''
# 실습 1 확인 (mock 호출을 씁니다)
import checks


class Recorder:
    """보낸 메시지 목록을 기록하고 정해 둔 응답을 돌려주는 mock send()."""

    def __init__(self):
        self.sent = []

    def __call__(self, messages, **options):
        self.sent.append([dict(message) for message in messages])
        return checks.good_reply(f'응답 {len(self.sent)}')


recorder, history = Recorder(), []
for number in [1, 2, 3]:
    reply = chat(history, f'질문 {number}', send=recorder)
assert reply.text == '응답 3', 'Reply를 돌려주어야 합니다'
assert [m['content'] for m in history] == ['질문 1', '응답 1', '질문 2', '응답 2', '질문 3', '응답 3'], \\
    'history에 질문과 응답이 차례로 쌓여야 합니다'
assert len(recorder.sent[2]) == 5, 'keep_turns가 None이면 이력 전체를 보냅니다'

chat(history, '질문 4', keep_turns=1, send=recorder)
assert [m['content'] for m in recorder.sent[3]] == ['질문 3', '응답 3', '질문 4'], \\
    'keep_turns=1이면 최근 한 턴과 새 질문만 보냅니다'
assert len(history) == 8, '보낼 때만 자르고 history에는 전체를 남깁니다'

chat(history, '질문 5', keep_turns=0, send=recorder)
assert [m['content'] for m in recorder.sent[4]] == ['질문 5'], 'keep_turns=0이면 새 질문만 보냅니다'
print('실습 1 통과')
'''

P1_MEASURE = '''
# 실습 1 측정 (실제 API를 부릅니다)
questions = ['클린룸에서 방진복을 입는 이유를 한 문장으로 알려 주세요.',
             '방진복을 입는 순서를 세 단계로 알려 주세요.',
             '그중 가장 자주 빠뜨리는 단계는 무엇일까요?',
             '그 단계를 빠뜨리지 않는 방법을 한 가지 알려 주세요.',
             '지금까지의 내용을 두 문장으로 정리해 주세요.']

for keep_turns in [None, 2]:
    history = []
    tokens = [chat(history, text, keep_turns=keep_turns).input_tokens for text in questions]
    print(f'keep_turns={keep_turns}, 호출별 입력 토큰 {tokens}, 합계 {sum(tokens):,}토큰')
'''

P1_ANSWER_MD = '''
**비교해 적기** 전체를 보낼 때와 최근 2턴만 보낼 때 입력 토큰 합계가 얼마였나요? 최근 2턴만 보냈을 때 마지막 답(정리)에 빠진 내용이 있었나요?

(여기에 적습니다)
'''

P1_EXPLAIN = '''
**해설**

- 전체를 보내면 호출마다 입력 토큰이 늘어납니다. 턴이 n개면 입력 토큰 합계는 대략 n의 제곱에 비례합니다.
- 최근 몇 턴만 보내면 입력 토큰이 일정한 수준에서 멈춥니다. 대신 잘려 나간 앞 대화의 내용은 모델이 알 수 없습니다. 마지막 질문처럼 "지금까지의 내용"을 묻는 경우에는 앞부분이 빠진 응답이 나옵니다.
- 그래서 이력을 줄일 때는 무엇을 잃어도 되는지를 먼저 정합니다. 문의 분류처럼 건마다 독립인 일은 이력 없이 한 건씩 보내는 것이 맞습니다.
'''

P2_MD = '''
## 실습 2 비용을 추정하고 모델 고르기

**목적** 대량 작업을 보내기 전에 비용을 추정하고, 측정한 숫자를 근거로 모델 등급을 고릅니다.

**재료** `data/2일차/문의_실습.csv`(60건), `data/2일차/문의_실습_정답.csv`

**할 일**

1. 빈 문의를 뺀 나머지를 소형 모델과 기본 모델로 보낼 때의 요금을 각각 추정합니다. 출력은 한 건에 40토큰으로 가정합니다.
2. 정답이 있는 문의 20건을 두 모델로 분류해 정확도, 걸린 시간, 실제 요금을 구합니다.
3. 어느 모델을 쓸지 정하고 근거를 한 문장으로 적습니다.

**완료 기준** 추정 요금 두 개, 모델별 정확도와 시간과 요금, 선택 근거 한 문장이 있습니다.

<details><summary>힌트 1</summary>

입력 토큰은 `llm.count_tokens()`로 셉니다. `None`이 나오는 API에서는 5건쯤 실제로 보내 `Reply.input_tokens`의 평균을 구한 뒤 건수를 곱합니다.
</details>

<details><summary>힌트 2</summary>

정확도는 모델이 낸 `category`와 정답 파일의 `category`가 같은 건수를 세면 됩니다. 응답이 JSON이 아닐 수 있으니 `json.loads`를 `try`로 감쌉니다.
</details>
'''

P2_LOAD = '''
# 실습 2 (재료 읽기)
practice = pd.read_csv(f'{DATA}/문의_실습.csv', dtype=str, keep_default_na=False)
practice_answers = pd.read_csv(f'{DATA}/문의_실습_정답.csv', dtype=str).set_index('id')


def prompt_of(row):
    return f"id: {row['id']}\\n문의: {row['문의내용']}"


print(f'{len(practice):,}건')
'''

P2_SKELETON_1 = f'''
# 실습 2 (1) 요금 추정
def estimate_input_tokens(rows):
    """문의 목록을 소형 모델로 보낼 때의 입력 토큰 합계를 추정해 돌려줍니다."""
    {TODO}


nonblank = [row for _, row in practice.iterrows() if row['문의내용'].strip()]
input_total = estimate_input_tokens(nonblank)
for alias in ['소형', '기본']:
    print(alias, f'${{cost_usd(input_total, 40 * len(nonblank), alias):.4f}}')
'''.replace('{{', '{').replace('}}', '}')

P2_SOLUTION_1 = '''
# 실습 2 (1) 요금 추정
def estimate_input_tokens(rows):
    """문의 목록을 소형 모델로 보낼 때의 입력 토큰 합계를 추정해 돌려줍니다."""
    def count(row):
        return llm.count_tokens([{'role': 'user', 'content': prompt_of(row)}], system=SYSTEM, model='소형')

    if count(rows[0]) is not None:                       # 세어 주는 API
        with ThreadPoolExecutor(max_workers=4) as pool:
            return sum(pool.map(count, rows))
    # 세어 주지 않는 API: 5건을 실제로 보내 평균을 내고 건수를 곱합니다
    sample = [llm.send([{'role': 'user', 'content': prompt_of(row)}], system=SYSTEM, model='소형')
              for row in rows[:5]]
    return round(sum(reply.input_tokens for reply in sample) / len(sample) * len(rows))


nonblank = [row for _, row in practice.iterrows() if row['문의내용'].strip()]
input_total = estimate_input_tokens(nonblank)
print(f'입력 토큰 합계(추정): {input_total:,}토큰')
for alias in ['소형', '기본']:
    print(alias, f'${cost_usd(input_total, 40 * len(nonblank), alias):.4f}')
'''

P2_SKELETON_2 = f'''
# 실습 2 (2) 표본 20건으로 두 모델 비교
sample = [row for row in nonblank if row['id'] in practice_answers.index][:20]


def compare(model):
    """표본을 model로 분류해 (정답 수, 걸린 시간 합계, 요금)을 돌려줍니다."""
    {TODO}


for model in ['소형', '기본']:
    correct, seconds, usd = compare(model)
    print(f'{{model}}: 정답 {{correct}}/{{len(sample)}}, {{seconds:.1f}}초, ${{usd:.4f}}')
'''.replace('{{', '{').replace('}}', '}')

P2_SOLUTION_2 = '''
# 실습 2 (2) 표본 20건으로 두 모델 비교
sample = [row for row in nonblank if row['id'] in practice_answers.index][:20]


def compare(model):
    """표본을 model로 분류해 (정답 수, 걸린 시간 합계, 요금)을 돌려줍니다."""
    correct, seconds, input_tokens, output_tokens = 0, 0.0, 0, 0
    for row in sample:
        reply = llm.send([{'role': 'user', 'content': prompt_of(row)}], system=SYSTEM, model=model)
        seconds += reply.seconds
        input_tokens += reply.input_tokens or 0
        output_tokens += reply.output_tokens or 0
        try:
            category = json.loads(reply.text)['category']
        except (json.JSONDecodeError, KeyError, TypeError):
            category = None                              # 읽지 못한 응답은 오답으로 셉니다
        correct += category == practice_answers.loc[row['id'], 'category']
    return correct, seconds, cost_usd(input_tokens, output_tokens, model)


for model in ['소형', '기본']:
    correct, seconds, usd = compare(model)
    print(f'{model}: 정답 {correct}/{len(sample)}, {seconds:.1f}초, ${usd:.4f}')
'''

P2_ANSWER_MD = '''
**선택과 근거** 어느 모델을 쓰겠습니까? 위 숫자를 근거로 한 문장으로 적습니다.

(여기에 적습니다)
'''

P2_EXPLAIN = '''
**해설**

- 실습 3에서 60건을 실제로 처리하면 실제 요금이 나옵니다. 그 값을 여기서 구한 소형 모델의 추정 요금과 비교해 봅니다. 다르다면 대개 출력 토큰 때문입니다. 추정은 한 건에 40토큰으로 가정했지만, 모델이 thinking에 쓴 토큰도 출력 토큰에 들어갑니다.
- 정확도가 같다면 더 싸고 빠른 등급을 고릅니다. 차이가 난다면 틀린 건을 직접 읽어 봅니다. 엣지 케이스에서만 결과가 달랐다면 모델 등급을 올리기 전에 분류 규칙을 더 분명히 쓰는 쪽을 먼저 검토합니다.
- 20건은 작은 표본입니다. 한두 건 차이로 결론을 내리지 말고, 차이가 작으면 표본을 늘려 다시 측정합니다.
'''

P3_MD = '''
## 실습 3 끝까지 처리하는 배치 처리 코드

**목적** 한 건을 처리하는 코드를, 실패가 섞여도 끝까지 처리하고 실패를 기록하는 코드로 확장합니다.

**할 일** 아래 네 함수를 완성합니다.

| 함수 | 하는 일 |
| --- | --- |
| `ask(prompt, system=None, max_tokens=300, tries=3, send=llm.send, sleep=time.sleep)` | `send`로 보냅니다. `CallError.retryable`이 참인 오류면 `sleep(1)`, `sleep(2)`처럼 대기 시간을 두 배씩 늘리며 `tries`번까지 보냅니다. 그 밖의 오류와 마지막 실패는 예외를 그대로 다시 발생시킵니다 |
| `check_reply(reply)` | 잘린 응답이면 `'잘림'`, 거절된 응답이면 `'거절'`, JSON으로 읽을 수 없거나 `category`가 없으면 `'파싱 오류'`, 쓸 수 있으면 `None`을 돌려줍니다 |
| `is_valid(text)` | 보내도 되는 문의면 `True`를 돌려줍니다. 빈 문의, 1,000자를 넘는 문의, 이메일 주소나 휴대폰 번호가 든 문의는 `False`입니다 |
| `process_all(rows, ask=ask)` | 문의를 차례로 처리해 `(성공 목록, 실패 목록)`을 돌려줍니다. 문의마다 `prompt_of(row)`로 만든 프롬프트(id와 문의내용)를 `system=SYSTEM`과 함께 `ask`에 넘깁니다. 한 건이 실패해도 멈추지 않습니다. 실패 목록에는 `(id, 사유)`를 넣습니다 |

**완료 기준** 테스트 셀이 "결과 10/10 통과"와 "입력 검사 통과"를 출력합니다. 그다음 실행 셀로 60건을 처리해 성공 건수와 실패 건수, 실패 사유, 실제 요금을 확인합니다.

<details><summary>힌트 1: ask()</summary>

`for attempt in range(tries)` 안에서 `try`로 `send`를 부르고 성공하면 바로 `return`합니다. `except llm.CallError`에서 재시도할지 판단합니다. 기다릴 시간은 `2 ** attempt`입니다.
</details>

<details><summary>힌트 2: process_all()</summary>

한 건마다 `try`로 `ask`를 부릅니다. `CallError`가 나면 실패 목록에 넣고 `continue`합니다. 오류 없이 응답을 받았더라도 `check_reply`가 사유를 돌려주면 실패 목록에 넣습니다.
</details>

<details><summary>힌트 3: is_valid()</summary>

이메일 주소는 `re.search(r'[\\w.]+@[\\w.]+', text)`, 휴대폰 번호는 `re.search(r'01\\d-\\d{3,4}-\\d{4}', text)`로 찾을 수 있습니다.
</details>
'''

P3_SKELETON = f'''
# 실습 3
import re


def ask(prompt, system=None, max_tokens=300, tries=3, send=llm.send, sleep=time.sleep):
    """질문 하나를 보냅니다. 재시도할 만한 오류면 기다리며 tries번까지 보냅니다."""
    {TODO}


def check_reply(reply):
    """쓸 수 없는 응답이면 사유를, 쓸 수 있으면 None을 돌려줍니다."""
    {TODO}


def is_valid(text):
    """보내도 되는 문의인지 돌려줍니다."""
    {TODO}


def process_all(rows, ask=ask):
    """문의 목록을 차례로 처리해 (성공 목록, 실패 목록)을 돌려줍니다."""
    {TODO}
'''

P3_SOLUTION = '''
# 실습 3
import re

MAX_CHARS = 1000


def ask(prompt, system=None, max_tokens=300, tries=3, send=llm.send, sleep=time.sleep):
    """질문 하나를 보냅니다. 재시도할 만한 오류면 기다리며 tries번까지 보냅니다."""
    messages = [{'role': 'user', 'content': prompt}]
    for attempt in range(tries):
        try:
            return send(messages, system=system, max_tokens=max_tokens)
        except llm.CallError as error:
            if not error.retryable or attempt == tries - 1:
                raise
            sleep(2 ** attempt)


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


def is_valid(text):
    """보내도 되는 문의인지 돌려줍니다."""
    if not isinstance(text, str) or not text.strip():
        return False                                   # 빈 문의
    if len(text) > MAX_CHARS:
        return False                                   # 지나치게 긴 문의
    if re.search(r'[\\w.]+@[\\w.]+', text) or re.search(r'01\\d-\\d{3,4}-\\d{4}', text):
        return False                                   # 이메일 주소나 휴대폰 번호
    return True


def process_all(rows, ask=ask):
    """문의 목록을 차례로 처리해 (성공 목록, 실패 목록)을 돌려줍니다."""
    success, failed = [], []
    for row in rows:
        try:
            reply = ask(f"id: {row['id']}\\n문의: {row['문의내용']}", system=SYSTEM)
        except llm.CallError as error:
            failed.append((row['id'], error.kind))
            continue
        reason = check_reply(reply)
        if reason:
            failed.append((row['id'], reason))
        else:
            success.append(json.loads(reply.text))
    return success, failed
'''

P3_CHECK = '''
# 실습 3 확인 (mock 호출을 씁니다)
import checks

results = checks.run(ask, process_all)

assert is_valid('3호기 PM 주기 문서는 어디에서 볼 수 있나요')
assert not is_valid('') and not is_valid('   '), '빈 문의는 필터링합니다'
assert not is_valid('가' * 1001), '1,000자를 넘는 문의는 필터링합니다'
assert not is_valid('결과를 hong@example.com 으로 보내 주세요'), '이메일 주소가 든 문의는 필터링합니다'
assert not is_valid('담당자 010-1234-5678 로 연락 주세요'), '휴대폰 번호가 든 문의는 필터링합니다'
assert check_reply(checks.good_reply()) is None
assert check_reply(checks.good_reply('{"id": "Q1"}')) == '파싱 오류', 'category가 없으면 파싱 오류입니다'
print('입력 검사 통과')
'''

P3_RUN = '''
# 실습 3 실행 (실제 API를 부릅니다)
practice = pd.read_csv(f'{DATA}/문의_실습.csv', dtype=str, keep_default_na=False)
rows = [row for _, row in practice.iterrows()]
to_send = [row for row in rows if is_valid(row['문의내용'])]
print(f'전체 {len(rows):,}건, 보내기 전에 필터링한 건 {len(rows) - len(to_send):,}건')
print('필터링한 id:', [row['id'] for row in rows if not is_valid(row['문의내용'])])

usage = []


def counting_send(messages, **options):
    """llm.send를 부르면서 토큰 수를 따로 모읍니다."""
    reply = llm.send(messages, model='소형', **options)
    usage.append((reply.input_tokens or 0, reply.output_tokens or 0))
    return reply


success, failed = process_all(to_send, ask=lambda prompt, **options: ask(prompt, send=counting_send, **options))
input_tokens, output_tokens = sum(u[0] for u in usage), sum(u[1] for u in usage)
print(f'성공 {len(success)}건, 실패 {len(failed)}건 {failed}')
print(f"입력 {input_tokens:,}토큰, 출력 {output_tokens:,}토큰, 실제 요금 ${cost_usd(input_tokens, output_tokens, '소형'):.4f}")

practice_answers = pd.read_csv(f'{DATA}/문의_실습_정답.csv', dtype=str).set_index('id')
correct = sum(result.get('category') == practice_answers.loc[result['id'], 'category']
              for result in success if result.get('id') in practice_answers.index)
print(f'정답 {correct}/{len(success)}')
'''

P3_EXPLAIN = '''
**해설**

- `ask()`는 두 가지를 판단합니다. 재시도하면 풀릴 오류인지, 그리고 아직 시도 횟수가 남았는지입니다. 둘 중 하나라도 아니면 `raise`로 예외를 다시 발생시킵니다.
- `process_all()`은 실패를 무시하지 않습니다. 실패한 건의 id와 사유를 남겨, 나중에 사람이 확인하거나 그 건만 다시 처리할 수 있게 합니다.
- 입력 검사는 요금과 시간을 아끼고, 보내면 안 되는 내용이 밖으로 나가는 것을 막습니다. 여기서 쓴 이메일 주소와 휴대폰 번호 검사는 가장 흔한 형태만 찾아내는 예시입니다. 실제 업무에서는 회사의 개인정보 기준에 맞는 검사를 써야 합니다.
- 긴 문의의 기준(1,000자)은 정답이 있는 값이 아닙니다. 긴 문의를 필터링할지, 그대로 보낼지, 요약해서 보낼지는 그 문의를 놓쳤을 때의 비용과 추가 요금을 비교해 정합니다.
'''

P4_MD = '''
## 실습 4 AI 코딩 도구에 수정 맡기고 검사로 확인하기

**목적** 실습 3에서 직접 작성한 것과 같은 수정을 AI 코딩 도구(Claude Code나 opencode 같은 코딩 에이전트)에 맡기고, 도구가 낸 결과가 맞는지 검사로 판정합니다.

**재료** `코딩도구_실습` 폴더

| 파일 | 내용 |
| --- | --- |
| `send_batch.py` | 고칠 파일. 재시도도, 응답 검사도, 실패 기록도 없습니다 |
| `check.py` | mock 호출로 열 가지를 검사합니다. 키도 요금도 필요 없습니다 |
| `보낼_글/1_설명.txt`, `2_수정.txt`, `3_빈틈.txt` | 도구에 보낼 글 |
| `풀이/send_batch_풀이.py` | 고친 예시 |

**할 일**

1. 터미널에서 `코딩도구_실습` 폴더로 가서 `python check.py`를 실행합니다. 고치기 전 결과를 적어 둡니다.
2. 같은 폴더에서 AI 코딩 도구를 열고 `보낼_글/1_설명.txt`의 내용을 보냅니다. 응답을 읽고 1번의 실패 항목과 맞춰 봅니다.
3. `보낼_글/2_수정.txt`의 내용을 보냅니다. 도구가 파일을 고치려 할 때 바뀌는 줄을 읽고 허용합니다.
4. `python check.py`를 다시 실행합니다. 통과하지 못한 항목이 있으면 그 줄을 도구에 그대로 알려 주고 다시 고치게 합니다.
5. `보낼_글/3_빈틈.txt`의 내용을 보냅니다. 검사가 보지 못하는 위험 중 하나를 골라 기준으로 적어 주고 고치게 한 뒤 다시 검사합니다.

**완료 기준** `python check.py`가 "결과 10/10 통과"를 출력합니다. 도구가 바꾼 줄을 `보낼_글/2_수정.txt`에 적힌 기준 1~5와 하나씩 짝지어 설명할 수 있습니다.

아래 셀은 노트북에서 검사를 실행하는 방법입니다.
'''

P4_CELL = '''
# 실습 4 (검사 실행. 고치기 전에는 4/10이 나옵니다)
import subprocess
import sys

done = subprocess.run([sys.executable, '-X', 'utf8', '코딩도구_실습/check.py'],
                      capture_output=True, text=True, encoding='utf-8')
print(done.stdout or done.stderr)
'''

P4_EXPLAIN = '''
**해설**

- 도구가 "고쳤습니다"라고 답한 것은 근거가 아닙니다. 고쳤는지는 검사 출력으로 판정합니다.
- 기준을 번호로 주면, 도구의 응답과 바뀐 줄을 번호별로 맞춰 볼 수 있습니다. "잘 고쳐 줘"처럼 기준 없이 맡기면 무엇을 확인해야 할지도 정할 수 없습니다.
- 검사 10/10은 "검사한 열 가지가 맞다"는 뜻입니다. 검사가 보지 않는 것은 여전히 모릅니다. 예를 들어 이 검사는 성공한 응답의 분류가 정답인지, 타임아웃이 걸려 있는지, 실패 목록이 파일로 남는지는 보지 않습니다.
- `풀이/send_batch_풀이.py`와 도구가 고친 파일을 비교해 봅니다. 구조가 달라도 기준 다섯 가지를 지키면 됩니다.
'''


def practice_cells(solution):
    intro = SOLUTION_INTRO if solution else PRACTICE_INTRO
    cells = [md(intro), md(SETUP_MD), code(SETUP_KEYS), code(SETUP_COMMON), md(SETUP_AFTER)]
    cells += [md(P1_MD), code(P1_SOLUTION if solution else P1_SKELETON, '실습1'),
              code(P1_CHECK), code(P1_MEASURE)]
    cells += [md(P1_EXPLAIN if solution else P1_ANSWER_MD)]
    cells += [md(P2_MD), code(P2_LOAD),
              code(P2_SOLUTION_1 if solution else P2_SKELETON_1),
              code(P2_SOLUTION_2 if solution else P2_SKELETON_2),
              md(P2_EXPLAIN if solution else P2_ANSWER_MD)]
    cells += [md(P3_MD), code(P3_SOLUTION if solution else P3_SKELETON, '실습3'),
              code(P3_CHECK), code(P3_RUN)]
    if solution:
        cells.append(md(P3_EXPLAIN))
    cells += [md(P4_MD), code(P4_CELL)]
    if solution:
        cells.append(md(P4_EXPLAIN))
    return cells


if __name__ == '__main__':
    save('2일차_실습.ipynb', practice_cells(solution=False))
    save('2일차_실습_풀이.ipynb', practice_cells(solution=True))
