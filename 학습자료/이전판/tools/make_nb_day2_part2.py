"""2일차 파트 2의 실습 노트북과 풀이 노트북을 만든다.

사용법: python make_nb_day2_part2.py
출력: 노트북/2일차_02_실습.ipynb, 노트북/2일차_02_실습_풀이.ipynb

노트북은 노트북/ 폴더에서 실행한다(llm.py, checks2.py, data/가 같은 폴더에 있다).
"""
from make_nb_day2 import SETUP_AFTER, SETUP_COMMON, SETUP_KEYS, SETUP_MD, TODO, code, md, save

PRACTICE_INTRO = '''
# 2일차 파트 2 실습: 구조화 출력과 시스템 연동

실습은 세 개입니다(실습 5, 6, 7). 접수 요청 80건을 담당팀, 위치, 긴급 여부로 정리해 DB에 저장하고, 결과를 얼마나 믿을 수 있는지 숫자로 확인합니다.
`NotImplementedError`가 있는 곳을 직접 채웁니다. 막히면 힌트를 펼쳐 보고, 다 한 뒤에 `2일차_02_실습_풀이.ipynb`와 비교합니다.
테스트 셀은 mock 호출을 써서 여러분의 코드가 맞게 동작하는지 알려 줍니다. API를 부르지 않으므로 요금이 들지 않습니다.
'''

SOLUTION_INTRO = '''
# 2일차 파트 2 실습 풀이

`2일차_02_실습.ipynb`의 풀이와 해설입니다. 풀이는 하나의 예시이며, 테스트 셀을 통과한다면 다르게 작성해도 됩니다.
'''

COMMON_MD = '''
## 실습 준비

아래 셀은 세 실습이 함께 쓰는 재료와 함수입니다. 그대로 실행합니다.

| 이름 | 내용 |
| --- | --- |
| `tickets` | 접수 80건. 열은 `id`, `접수시각`, `본문`입니다 |
| `ticket_answers` | 정답 라벨. 열은 `team`, `location`, `urgent`, `난이도`입니다. `난이도`에는 판단하기 어려운 엣지 케이스 15건이 `엣지`, 나머지 65건이 `보통`으로 적혀 있습니다. 위치가 없는 접수의 `location`은 `None`입니다 |
| `TICKET_RULES` | 담당팀 기준(`접수_규칙.txt`). 시스템 프롬프트로 씁니다 |
| `prompt_of(row)` | 접수 한 건을 모델에 보낼 글로 만듭니다 |
| `parse_reply(reply, model_class)` | 응답을 검증해 `(객체, None)` 또는 `(None, 사유)`를 돌려줍니다. 교재의 예제 2-5와 같습니다 |
| `open_db(path)` | `requests` 테이블이 있는 SQLite DB를 엽니다. `id`가 기본 키입니다 |
'''

COMMON_CELL = '''
# 실습 준비
import sqlite3
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

import checks2

tickets = pd.read_csv(f'{DATA}/접수_실습.csv').fillna('')
ticket_answers = pd.read_csv(f'{DATA}/접수_실습_정답.csv', dtype=str, keep_default_na=False).set_index('id')
ticket_answers['urgent'] = ticket_answers['urgent'] == 'true'
ticket_answers['location'] = ticket_answers['location'].map(lambda value: value or None)
TICKET_RULES = open(f'{DATA}/접수_규칙.txt', encoding='utf-8').read().strip()
print(TICKET_RULES)
print('----')
print(tickets.head(8).to_string(index=False))


def prompt_of(row):
    """접수 한 건을 모델에 보낼 글로 만듭니다."""
    return f"id: {row['id']}\\n본문: {row['본문']}"


def parse_reply(reply, model_class):
    """응답을 검증해 (객체, None) 또는 (None, 사유)를 돌려줍니다."""
    if reply.stop_reason != 'end':
        return None, {'max_tokens': '잘림', 'refusal': '거절'}.get(reply.stop_reason, '비정상 종료')
    text = reply.text[reply.text.find('{'):reply.text.rfind('}') + 1]
    try:
        return model_class.model_validate_json(text), None
    except ValidationError as error:
        first = error.errors()[0]
        field = '.'.join(str(part) for part in first['loc']) or '전체'
        return None, f"스키마 불일치({field}: {first['type']})"


def open_db(path=':memory:'):
    """requests 테이블이 있는 DB를 엽니다. 경로를 주지 않으면 메모리에만 있는 DB입니다."""
    db = sqlite3.connect(path)
    db.execute(\'\'\'CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY, team TEXT, location TEXT, urgent INTEGER,
        model TEXT, run_at TEXT, reviewed TEXT)\'\'\')
    return db
'''

# ---- 실습 5 ----

P5_MD = '''
## 실습 5 스키마 설계

**목적** 결과 테이블의 열에서 출발해 스키마를 정합니다. 허용값과, 값이 없을 때의 처리를 직접 정해 봅니다.

**할 일** pydantic 클래스 `Ticket`을 작성합니다. 결과 테이블에 필요한 열은 네 개입니다.

| 필드 | 내용 |
| --- | --- |
| `id` | 접수 id |
| `team` | 담당팀. 설비, 시설, IT, 안전, 기타 가운데 하나 |
| `location` | 본문에 나온 장비 이름이나 장소. 본문에 없으면 값이 없습니다 |
| `urgent` | 긴급 여부 |

**완료 기준** 테스트 셀이 "실습 5 통과"를 출력합니다. 그다음 3건을 실제로 보내, 위치가 없는 접수의 `location`이 `None`으로 오는지 확인합니다.

<details><summary>힌트 1</summary>

허용값은 `Literal['설비', '시설', ...]`로, 없을 수 있는 값은 `str | None`으로 적습니다.
</details>

<details><summary>힌트 2</summary>

`location: str | None = None`처럼 기본값을 주면 그 필드는 필수 필드에서 빠집니다. 구조화 출력의 스키마는 모든 필드가 필수여야 하므로 기본값을 주지 않습니다. 값이 없다는 것은 필드를 빼는 것이 아니라 `null`을 넣는 것으로 표현합니다.
</details>

<details><summary>힌트 3</summary>

정하지 않은 필드를 거부하고 문자열을 불리언 값으로 바꿔 받지 않게 하려면 `model_config = ConfigDict(extra='forbid', strict=True)`를 클래스 안에 적습니다.
</details>
'''

P5_SKELETON = f'''
# 실습 5
class Ticket(BaseModel):
    """접수 한 건의 결과. 필드는 id, team, location, urgent입니다."""
    {TODO}
'''

P5_SOLUTION = '''
# 실습 5
class Ticket(BaseModel):
    """접수 한 건의 결과. 필드는 id, team, location, urgent입니다."""
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    team: Literal['설비', '시설', 'IT', '안전', '기타']
    location: str | None          # 기본값을 주지 않습니다. 없으면 null이 와야 합니다
    urgent: bool
'''

P5_CHECK = '''
# 실습 5 확인 (API를 부르지 않습니다)
checks2.check_schema(Ticket)
'''

P5_RUN = '''
# 실습 5 실행 (실제 API를 부릅니다. 3건)
for _, row in tickets.iloc[[3, 5, 7]].iterrows():
    reply = llm.ask(prompt_of(row), system=TICKET_RULES, model='소형', schema=Ticket.model_json_schema())
    parsed, reason = parse_reply(reply, Ticket)
    print(row['본문'][:40])
    print(f'  → {parsed}, 사유: {reason}')
'''

P5_ANSWER_MD = '''
**적어 보기** 3건의 결과에서 고칠 점이 보였다면 무엇을 고쳤는지 적습니다.

- (여기에 적습니다)
'''

P5_EXPLAIN = '''
**해설**

- `location`을 `str`로만 두면 위치가 없는 접수에서도 모델이 문자열을 채워야 합니다. `str | None`으로 두면 "없음"을 `None` 한 가지로 받을 수 있고, 실습 7에서 "본문에 없는 위치를 적었는가"를 검사하기도 쉬워집니다.
- 기본값(`= None`)을 주면 pydantic은 그 필드를 스키마의 `required`에서 뺍니다. 그러면 모델이 필드를 아예 빼고 응답해도 검증을 통과합니다. "값이 없다"와 "응답에서 빠졌다"를 구분하려면 필드는 필수로 두고 `null`을 허용합니다.
- `team`의 목록에 "기타"가 있어야 네 팀의 일이 아닌 접수를 받을 곳이 생깁니다. 실습 7의 실험에서 목록을 줄이면 어떤 일이 생기는지 확인합니다.
'''

# ---- 실습 6 ----

P6_MD = '''
## 실습 6 배치 처리와 멱등한 저장

**목적** 한 건의 실패가 배치를 멈추지 않게 하고, 다시 실행해도 행이 중복되지 않으며 이미 처리한 건을 다시 보내지 않게 합니다.

**할 일** 함수 세 개를 작성합니다.

1. `classify(row, ask=llm.ask, model_class=None, rules=None)`: 접수 한 건을 보내고 dict를 돌려줍니다. 어떤 경우에도 예외를 발생시키지 않습니다.
    - `ask(prompt_of(row), system=규칙, model='소형', max_tokens=1024, schema=스키마)`로 보냅니다. `model_class`가 `None`이면 `Ticket`을, `rules`가 `None`이면 `TICKET_RULES`를 씁니다(실습 7의 실험에서 다른 값을 넘깁니다).
    - 돌려주는 dict의 키는 `id`, `answer_id`, `team`, `location`, `urgent`, `error`, `input_tokens`, `output_tokens`입니다. `id`는 보낸 id, `answer_id`는 모델이 돌려준 id입니다.
    - 성공하면 `error`는 `None`입니다. 호출 실패(`llm.CallError`)나 `parse_reply()`가 돌려준 사유가 있으면 `error`에 적고 `team`, `location`, `urgent`, `answer_id`는 `None`으로 둡니다.
2. `save(db, records, model, run_at)`: `error`가 없는 결과만 `requests` 테이블에 넣고 넣은 건수를 돌려줍니다. 같은 `id`가 있으면 `team`, `location`, `urgent`, `model`, `run_at`만 고칩니다. `reviewed` 열은 건드리지 않습니다.
3. `run(db, rows, ask=llm.ask)`: `requests` 테이블에 없는 `id`의 행만 `classify()`로 보내고 `save()`로 저장합니다. `(보낸 건수, 실패 목록)`을 돌려줍니다. 실패 목록은 `[(id, 사유), ...]`입니다.

**완료 기준** 테스트 셀이 "실습 6 통과"를 출력합니다. 그다음 80건을 실제로 처리해 저장한 행 수를 확인하고, 한 번 더 실행했을 때 보내는 건이 0건인지 확인합니다.

<details><summary>힌트 1</summary>

`classify()`는 결과 dict를 먼저 만들어 두고(`error`와 결과 필드는 `None`), 단계마다 채워 나가면 어느 경로에서든 같은 키를 가진 dict를 돌려줄 수 있습니다. `except`에는 `llm.CallError`만 적습니다.
</details>

<details><summary>힌트 2</summary>

`save()`의 SQL은 `INSERT INTO requests (id, team, location, urgent, model, run_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET team = excluded.team, ...`처럼 작성합니다. `INSERT OR REPLACE`는 기존 행을 지우고 새 행을 넣으므로 `reviewed` 열의 값이 남지 않아 마지막 테스트를 통과하지 못합니다.
</details>

<details><summary>힌트 3</summary>

`run()`은 먼저 `SELECT id FROM requests`로 저장된 id의 집합을 만들고, 거기에 없는 행만 골라 보냅니다. 여러 건은 `ThreadPoolExecutor`로 병렬 처리하되, DB에 쓰는 일은 병렬 처리가 끝난 뒤 한 번에 합니다.
</details>
'''

P6_SKELETON = f'''
# 실습 6
def classify(row, ask=llm.ask, model_class=None, rules=None):
    """접수 한 건을 보내 결과 dict를 돌려줍니다. 실패해도 예외를 발생시키지 않습니다."""
    {TODO}


def save(db, records, model, run_at):
    """error가 없는 결과를 requests 테이블에 넣고 넣은 건수를 돌려줍니다. 같은 id는 결과 열만 고칩니다."""
    {TODO}


def run(db, rows, ask=llm.ask):
    """requests 테이블에 없는 id만 보내고 저장합니다. (보낸 건수, 실패 목록)을 돌려줍니다."""
    {TODO}
'''

P6_SOLUTION = '''
# 실습 6
def classify(row, ask=llm.ask, model_class=None, rules=None):
    """접수 한 건을 보내 결과 dict를 돌려줍니다. 실패해도 예외를 발생시키지 않습니다."""
    model_class = model_class or Ticket
    record = {'id': row['id'], 'answer_id': None, 'team': None, 'location': None, 'urgent': None,
              'error': None, 'input_tokens': 0, 'output_tokens': 0}
    try:
        reply = ask(prompt_of(row), system=rules or TICKET_RULES, model='소형', max_tokens=1024,
                    schema=model_class.model_json_schema())
    except llm.CallError as error:            # API 호출의 실패만 잡습니다
        record['error'] = f'호출 실패({error.kind})'
        return record
    record.update(input_tokens=reply.input_tokens or 0, output_tokens=reply.output_tokens or 0)
    parsed, reason = parse_reply(reply, model_class)
    if reason:
        record['error'] = reason
    else:
        record.update(answer_id=parsed.id, team=parsed.team, location=parsed.location, urgent=parsed.urgent)
    return record


UPSERT = \'\'\'INSERT INTO requests (id, team, location, urgent, model, run_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                team = excluded.team, location = excluded.location, urgent = excluded.urgent,
                model = excluded.model, run_at = excluded.run_at\'\'\'


def save(db, records, model, run_at):
    """error가 없는 결과를 requests 테이블에 넣고 넣은 건수를 돌려줍니다. 같은 id는 결과 열만 고칩니다."""
    db_rows = [(record['id'], record['team'], record['location'], int(record['urgent']), model, run_at)
               for record in records if not record['error']]
    db.executemany(UPSERT, db_rows)
    db.commit()
    return len(db_rows)


def run(db, rows, ask=llm.ask):
    """requests 테이블에 없는 id만 보내고 저장합니다. (보낸 건수, 실패 목록)을 돌려줍니다."""
    done_ids = {row_id for (row_id,) in db.execute('SELECT id FROM requests')}
    to_send = [row for row in rows if row['id'] not in done_ids]
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(lambda row: classify(row, ask=ask), to_send))
    save(db, records, llm.model_name('소형'), pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'))
    return len(to_send), [(record['id'], record['error']) for record in records if record['error']]
'''

P6_CHECK = '''
# 실습 6 확인 (mock 호출을 씁니다)
checks2.check_batch(classify, save, run, open_db)
'''

P6_RUN = '''
# 실습 6 실행 (실제 API를 부릅니다. 80건)
os.makedirs('out', exist_ok=True)
if os.path.exists('out/requests.db'):
    os.remove('out/requests.db')              # 처음부터 다시 해 볼 수 있게 지웁니다
db = open_db('out/requests.db')
rows = [row for _, row in tickets.iterrows()]

sent, failed = run(db, rows)
print(f'첫 실행: 보낸 건 {sent}, 실패 {failed}')
print('저장한 행', db.execute('SELECT COUNT(*) FROM requests').fetchone()[0])
sent, failed = run(db, rows)
print(f'다시 실행: 보낸 건 {sent}, 실패 {failed}')
print('저장한 행', db.execute('SELECT COUNT(*) FROM requests').fetchone()[0])
print(db.execute('SELECT team, COUNT(*) FROM requests GROUP BY team ORDER BY team').fetchall())
db.close()
'''

P6_EXPLAIN = '''
**해설**

- `classify()`가 잡는 예외는 `llm.CallError`뿐입니다. `except Exception`으로 넓히면 함수 안의 오타나 잘못된 키 이름으로 생긴 오류도 "호출 실패"로 기록되고, 80건이 모두 같은 버그로 실패해도 배치는 정상적으로 끝난 것처럼 보입니다.
- `run()`은 DB에 저장된 id를 "처리가 끝난 건"의 기준으로 씁니다. 실패한 건은 저장하지 않으므로 다음 실행에서 자동으로 다시 보냅니다. 따로 실패 목록 파일을 관리하지 않아도 이어서 실행할 수 있습니다.
- 병렬 처리는 API 호출까지만 하고, DB에는 호출이 모두 끝난 뒤 한 번에 씁니다. SQLite의 연결은 만든 스레드에서만 쓸 수 있고, 한 번에 쓰는 편이 빠릅니다. 다만 이 방식은 배치가 중간에 중단되면 그때까지의 결과를 잃습니다. 건수가 많다면 수십 건 단위로 끊어 저장합니다.
- `ON CONFLICT(id) DO UPDATE SET`은 적어 준 열만 고칩니다. 담당자가 `reviewed` 열에 적은 내용은 배치를 다시 실행해도 남습니다.
'''

# ---- 실습 7 ----

P7_MD = '''
## 실습 7 검증, 상태, 정확도

**목적** 스키마 검증을 통과한 결과를 얼마나 믿을 수 있는지 숫자로 확인합니다. 그리고 허용값과 기준 문장이 결과를 어떻게 바꾸는지 실험합니다.

**할 일 1** 함수 두 개를 작성합니다. `record`는 `classify()`가 돌려준 dict이고 `text`는 그 접수의 본문입니다.

1. `validate(record, text)`: 걸린 사유(문자열)를, 통과하면 `None`을 돌려줍니다. 아래 순서로 검사합니다.
    - `error`가 있으면 그 값을 그대로 돌려줍니다.
    - 보낸 `id`와 모델이 돌려준 `answer_id`가 다르면 걸립니다.
    - `team`이 "기타"인데 `urgent`가 `True`이면 걸립니다. 네 팀의 일이 아닌 글이 긴급일 수는 없습니다.
    - `location`이 `None`이 아닌데 본문에 그 글자가 없으면 걸립니다. 규칙은 위치를 "본문의 글자 그대로" 옮기라고 했습니다.
2. `status_of(record, text)`: `error`가 있으면 `'manual'`, 그 밖의 사유로 걸리면 `'review'`, 통과하면 `'auto'`를 돌려줍니다.

**할 일 2** 측정 셀을 실행해 실험 전 실행의 숫자를 확인합니다.

**할 일 3** 실험 A와 실험 B의 셀을 실행하고, 바뀐 숫자와 그 이유를 적습니다.

**완료 기준** 테스트 셀이 "실습 7 통과"를 출력합니다. 스키마 검증 통과율, 업무 규칙에 걸린 건수, 담당팀 정확도, `auto` 가운데 틀린 건수를 적습니다. 두 실험에서 바뀐 숫자와 이유를 한 문장씩 적습니다.

<details><summary>힌트 1</summary>

본문에 그 글자가 있는지는 `record['location'] in text`로 확인합니다. `None`에는 `in`을 쓸 수 없으므로 `None`인지를 먼저 확인합니다.
</details>

<details><summary>힌트 2</summary>

`status_of()`는 `validate()`를 불러 쓰면 됩니다. `error`가 있는 경우만 먼저 가려 `'manual'`로 돌려줍니다.
</details>
'''

P7_SKELETON = f'''
# 실습 7
def validate(record, text):
    """결과 한 건을 검사해 걸린 사유를, 통과하면 None을 돌려줍니다."""
    {TODO}


def status_of(record, text):
    """'auto', 'review', 'manual' 가운데 하나를 돌려줍니다."""
    {TODO}
'''

P7_SOLUTION = '''
# 실습 7
def validate(record, text):
    """결과 한 건을 검사해 걸린 사유를, 통과하면 None을 돌려줍니다."""
    if record['error']:
        return record['error']
    if record['answer_id'] != record['id']:
        return 'id 불일치'
    if record['team'] == '기타' and record['urgent']:
        return '기타인데 urgent가 true'
    if record['location'] is not None and record['location'] not in text:
        return '본문에 없는 위치'
    return None


def status_of(record, text):
    """'auto', 'review', 'manual' 가운데 하나를 돌려줍니다."""
    if record['error']:
        return 'manual'                    # 모델의 결과가 없습니다
    return 'review' if validate(record, text) else 'auto'
'''

P7_CHECK = '''
# 실습 7 확인 (API를 부르지 않습니다)
checks2.check_validate(validate, status_of)
'''

P7_MEASURE = '''
# 실습 7 측정 (실제 API를 부릅니다. 80건)
rows = [row for _, row in tickets.iterrows()]
text_of = dict(zip(tickets['id'], tickets['본문']))


def run_all(model_class=None, rules=None):
    """80건을 모두 분류해 결과 dict의 목록을 돌려줍니다. DB에는 저장하지 않습니다."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda row: classify(row, model_class=model_class, rules=rules), rows))


def report(records, label):
    """검증 결과와 정답 라벨 비교를 출력합니다."""
    done = [record for record in records if not record['error']]
    team_ok = sum(record['team'] == ticket_answers.loc[record['id'], 'team'] for record in done)
    urgent_ok = sum(record['urgent'] == ticket_answers.loc[record['id'], 'urgent'] for record in done)
    statuses = [status_of(record, text_of[record['id']]) for record in records]
    reasons = pd.Series([validate(record, text_of[record['id']]) for record in records]).dropna()
    auto_wrong = [record['id'] for record, status in zip(records, statuses)
                  if status == 'auto' and record['team'] != ticket_answers.loc[record['id'], 'team']]
    print(f'[{label}] 스키마 검증 통과 {len(done)}/{len(records)}'
          f', 담당팀 정확도 {team_ok}/{len(done)}, 긴급 여부 정확도 {urgent_ok}/{len(done)}')
    print(f'  상태: {pd.Series(statuses).value_counts().to_dict()}, 걸린 사유: {reasons.value_counts().to_dict()}')
    print(f'  auto {statuses.count("auto")}건 가운데 담당팀이 틀린 건 {len(auto_wrong)}건', auto_wrong)
    urgent_count = sum(bool(record['urgent']) for record in done)
    print(f"  urgent가 true인 건 {urgent_count}건(정답은 {int(ticket_answers['urgent'].sum())}건)")


base = run_all()
report(base, '실험 전')
for record in base:
    answer = ticket_answers.loc[record['id']]
    why = validate(record, text_of[record['id']])
    if why or record['team'] != answer['team']:
        print(f"  {record['id']} 모델 {record['team']} / {record['location']!r}, 정답 {answer['team']}"
              f", 사유 {why}, {text_of[record['id']][:30]}")
'''

P7_A = '''
# 실습 7 실험 A (담당팀 허용값에서 IT를 뺍니다. 80건을 다시 보냅니다)
class TicketNoIT(Ticket):
    team: Literal['설비', '시설', '안전', '기타']


no_it = run_all(model_class=TicketNoIT)
report(no_it, 'IT 제외')
it_ids = set(ticket_answers.index[ticket_answers['team'] == 'IT'])
moved = pd.Series([record['team'] for record in no_it if record['id'] in it_ids])
print(f'  정답이 IT인 {len(it_ids)}건의 분류:', moved.value_counts(dropna=False).to_dict())
'''

P7_B = '''
# 실습 7 실험 B (규칙에서 긴급 기준 문장을 뺍니다. 80건을 다시 보냅니다)
URGENT_LINE = next(line for line in TICKET_RULES.splitlines() if line.startswith('urgent'))
print('뺀 문장:', URGENT_LINE)
no_rule = run_all(rules=TICKET_RULES.replace(URGENT_LINE, '').strip())
report(no_rule, '긴급 기준 제외')
flipped = [(new, old) for new, old in zip(no_rule, base) if new['urgent'] != old['urgent']]
print('  긴급 판단이 바뀐 건', len(flipped))
for new, old in flipped[:10]:
    print(f"  {new['id']} 실험 전 {old['urgent']} → {new['urgent']}"
          f", 정답 {ticket_answers.loc[new['id'], 'urgent']}, {text_of[new['id']][:34]}")
'''

P7_ANSWER_MD = '''
**적어 보기**

| 항목 | 실험 전 | 실험 A (IT 제외) | 실험 B (긴급 기준 제외) |
| --- | --- | --- | --- |
| 스키마 검증 통과 | | | |
| 업무 규칙에 걸린 건 | | | |
| 담당팀 정확도 | | | |
| 긴급 여부 정확도 | | | |
| `auto` 가운데 담당팀이 틀린 건 | | | |

- 실험 A에서 바뀐 숫자와 이유:
- 실험 B에서 바뀐 숫자와 이유:
- 이 결과 테이블을 담당자에게 넘긴다면 함께 알려 줄 숫자:
'''

P7_EXPLAIN = '''
**해설**

아래 숫자는 2026-11-23에 Claude 모델로 실행한 결과입니다. 여러분의 숫자는 조금 다를 수 있습니다.

{RESULT_TABLE}

- **스키마 검증 통과율은 세 경우 모두 같습니다.** 허용값에서 "IT"를 빼도, 긴급 기준을 빼도 응답의 형식은 스키마에 맞습니다. 통과율만 보면 세 실행을 구분할 수 없습니다. 차이는 정답 라벨과 비교해야 드러납니다.
- **실험 A: 허용값이 답의 범위를 정합니다.** {NOTE_A}
- **실험 B: 스키마는 값의 기준을 정하지 않습니다.** {NOTE_B}
- **본문에 없는 위치.** {NOTE_LOCATION}
- **넘길 때 함께 알려 줄 숫자.** 사람이 확인할 건수(`review`와 `manual`), 그리고 `auto` 가운데 틀린 비율입니다. `auto` 가운데 틀린 비율은 정답 라벨이 있어야 계산할 수 있습니다. 실제 업무에서는 80건 모두에 정답을 붙일 수 없으므로 `auto`에서 표본을 뽑아 확인합니다. 이 실습에서는 재실행 비교를 하지 않았습니다. 교재의 예제 2-8처럼 한 번 더 실행해 담당팀이 달라진 건을 `review`에 더하면 `auto`에 남는 오류를 더 줄일 수 있습니다.
'''

MORE_MD = '''
## 더 해 보기

- `validate()`에 업무 규칙을 하나 더 넣어 봅니다. 예: 본문에 "멈췄", "대피" 같은 말이 있는데 `urgent`가 `False`인 건을 `review`로 보냅니다. 걸리는 건수와, 그 가운데 실제로 틀린 건수를 비교합니다.
- 담당팀이 틀린 건의 본문을 읽고 `접수_규칙.txt`에 문장을 더해 정확도가 오르는지 확인합니다. 규칙 파일은 사본을 만들어 고칩니다.
- AI 코딩 도구(Claude Code나 opencode)에 "접수 CSV를 읽어 담당팀별로 엑셀 시트를 나누고 DB에 쌓는 프로그램"을 맡겨 봅니다. 실습 6의 테스트(`checks2.check_batch`)가 요구하는 조건을 기준으로 적어 주고, 테스트로 결과를 판정합니다.
'''

# 풀이 노트북의 해설에 넣을 실행 결과. 풀이를 실행한 뒤 실제 값으로 채운다.
RESULTS = {
    'RESULT_TABLE': (
        '| 항목 | 실험 전 | 실험 A (IT 제외) | 실험 B (긴급 기준 제외) |\n'
        '| --- | --- | --- | --- |\n'
        '| 스키마 검증 통과 | 80/80 | 80/80 | 80/80 |\n'
        '| 업무 규칙에 걸린 건 | 0 | 1 | 0 |\n'
        '| 담당팀 정확도 | 76/80 | 64/80 | 77/80 |\n'
        '| 긴급 여부 정확도 | 79/80 | 80/80 | 74/80 |\n'
        '| `auto` 가운데 담당팀이 틀린 건 | 80건 중 4건 | 79건 중 15건 | 80건 중 3건 |\n\n'
        '실험 전 실행에서는 80건이 모두 `auto`였고 그 가운데 4건의 담당팀이 틀렸습니다. 클린룸 차압 경보와 정전으로 꺼진 장비는 '
        '정답이 시설인데 설비로, 화면이 꺼진 키오스크는 정답이 IT인데 시설로, 약액이 빠지는 세정 장비는 정답이 설비인데 안전으로 '
        '분류됐습니다. 네 건 모두 두 팀의 일로 읽을 수 있는 접수입니다. 업무 규칙은 이 4건을 하나도 찾아내지 못했습니다.'),
    'NOTE_A': ('정답이 IT인 16건 가운데 12건이 기타로, 4건이 시설로 분류됐습니다. 오류는 한 건도 나지 않았고 담당팀 정확도는 '
               '76건에서 64건으로 내려갔습니다. 모델은 목록 안에서 반드시 하나를 골라야 하므로, 맞는 값이 목록에 없으면 '
               '가장 가까운 값을 고릅니다. 업무 규칙("기타인데 urgent가 true")에는 1건만 걸렸고, 틀린 16건 가운데 15건은 '
               '`auto`로 분류됐습니다. 새 종류의 접수가 들어올 수 있는 업무라면 "기타"로 분류된 건을 정기적으로 읽어 보고 '
               '허용값을 고쳐야 합니다.'),
    'NOTE_B': ('`urgent`가 `true`인 건이 22건에서 27건으로 늘었고(정답은 21건) 긴급 여부 정확도는 79건에서 74건으로 내려갔습니다. '
               '판단이 바뀐 건은 5건입니다. 출입 카드 분실, 열려 있던 후문 출입 통제기, 중간에서 멈춘 창고 셔터, 올라가지 않는 '
               '주차장 차단기, 오작동으로 울리는 화재 감지기입니다. 다섯 건 모두 `false`에서 `true`로 바뀌었고 정답은 `false`입니다. '
               '생산이 멈추거나 사람이 다칠 상황은 아니지만 급해 보이는 접수입니다. 기준 문장이 없으면 모델은 "긴급"을 '
               '자기 상식으로 판단하고, 급해 보이는 접수를 긴급으로 분류하는 경우가 늘어납니다. '
               '스키마는 `urgent`가 불리언이라는 것만 정합니다. 어떤 경우에 `true`인지는 프롬프트의 기준 문장이 정합니다. '
               '담당팀 정확도가 76건에서 77건으로 바뀐 것은 실행할 때마다 한두 건 바뀌는 범위 안이라 이 실험의 효과로 보기 어렵습니다.'),
    'NOTE_LOCATION': ('세 실행 모두 "본문에 없는 위치"에 걸린 건은 없었습니다. 이 실습에서는 `null`을 허용하고 규칙에 '
                      '"본문의 글자 그대로"라고 적은 조건만 실행했으므로, 이 두 가지가 없을 때와는 비교하지 않았습니다. 걸린 건이 없더라도 이 검사는 남겨 둡니다. 요금 없이 모든 건에 적용할 수 있고, '
                      '모델이나 규칙이 바뀌었을 때 지어낸 위치가 생기면 바로 드러납니다.'),
}


def practice_cells(solution):
    cells = [md(SOLUTION_INTRO if solution else PRACTICE_INTRO),
             md(SETUP_MD), code(SETUP_KEYS), code(SETUP_COMMON), md(SETUP_AFTER),
             md(COMMON_MD), code(COMMON_CELL, '실습준비')]
    cells += [md(P5_MD), code(P5_SOLUTION if solution else P5_SKELETON, '실습5'), code(P5_CHECK), code(P5_RUN),
              md(P5_EXPLAIN if solution else P5_ANSWER_MD)]
    cells += [md(P6_MD), code(P6_SOLUTION if solution else P6_SKELETON, '실습6'), code(P6_CHECK), code(P6_RUN)]
    if solution:
        cells.append(md(P6_EXPLAIN))
    cells += [md(P7_MD), code(P7_SOLUTION if solution else P7_SKELETON, '실습7'), code(P7_CHECK),
              code(P7_MEASURE), code(P7_A), code(P7_B)]
    explain = P7_EXPLAIN
    for key, value in RESULTS.items():
        explain = explain.replace('{' + key + '}', value)
    cells.append(md(explain if solution else P7_ANSWER_MD))
    if not solution:
        cells.append(md(MORE_MD))
    return cells


if __name__ == '__main__':
    save('2일차_02_실습.ipynb', practice_cells(solution=False))
    save('2일차_02_실습_풀이.ipynb', practice_cells(solution=True))
