"""2일차 파트 2 실습(실습 5, 6, 7)의 테스트.

실제 API를 부르지 않는다. 정해 둔 응답을 돌려주는 mock 호출을 넣어 본다.
그래서 키가 없어도 되고 요금도 들지 않는다.

검사하는 것의 약속

    Ticket (실습 5)
        pydantic 클래스. 필드는 id(str), team(설비, 시설, IT, 안전, 기타 중 하나),
        location(str 또는 None), urgent(bool)이고 넷 다 필수다.
        정하지 않은 필드는 거부하고, "yes" 같은 문자열을 불리언 값으로 바꿔 받지 않는다.

    classify(row, ask=llm.ask, model_class=Ticket, rules=TICKET_RULES)  (실습 6)
        row는 {'id': ..., '본문': ...}다. 예외를 발생시키지 않고 아래 키를 가진 dict를 돌려준다.
        id, answer_id, team, location, urgent, error, input_tokens, output_tokens
        성공하면 error는 None, 실패하면 error에 사유를 적고 team은 None이다.

    save(db, records, model, run_at)  (실습 6)
        error가 없는 결과만 requests 테이블에 넣는다. 같은 id가 있으면 결과 열만 고친다.
        넣은 건수를 돌려준다.

    run(db, rows, ask=llm.ask)  (실습 6)
        requests 테이블에 없는 id만 보내고, 성공한 결과를 저장한다.
        (보낸 건수, 실패 목록)을 돌려준다. 실패 목록은 [(id, 사유), ...]다.

    validate(record, text)  (실습 7)
        걸린 사유를, 통과하면 None을 돌려준다. text는 그 접수의 본문이다.

    status_of(record, text)  (실습 7)
        'auto', 'review', 'manual' 가운데 하나를 돌려준다.
"""
import json

from llm import CallError, Reply

ROWS = [{'id': f'T{number:02d}', '본문': f'3호기 옆 검사용 접수 {number}'} for number in range(1, 6)]


def reply_for(row_id, team='설비', location='3호기', urgent=False, stop_reason='end'):
    text = json.dumps({'id': row_id, 'team': team, 'location': location, 'urgent': urgent},
                      ensure_ascii=False)
    return Reply(text, 300, 30, stop_reason, 'fake-model', 0.1)


def id_in(prompt):
    return next(row['id'] for row in ROWS if row['id'] in prompt)


class FakeAsk:
    """mock ask(). fail에 든 id는 CallError를 발생시키고, 나머지는 정상 응답을 돌려준다."""

    def __init__(self, fail=(), reply=None):
        self.fail, self.reply, self.sent = set(fail), reply, []

    def __call__(self, prompt, **options):
        row_id = id_in(prompt)
        self.sent.append(row_id)
        if row_id in self.fail:
            raise CallError('timeout', None, '검사용 mock 오류')
        return self.reply(row_id) if self.reply else reply_for(row_id)


def _report(name, results):
    for number, (ok, title, note) in enumerate(results, 1):
        print(f'{number}. {"통과" if ok else "실패"} {title}' + (f' ({note})' if note else ''))
    passed = sum(ok for ok, _, _ in results)
    if passed == len(results):
        print(f'{name} 통과')
    else:
        print(f'{name}: {passed}/{len(results)} 통과')
    return passed == len(results)


def _try(function):
    """검사받는 코드가 어떤 예외를 발생시켜도 검사는 끝까지 진행한다."""
    try:
        return function()
    except Exception as crashed:
        return False, f'{type(crashed).__name__}: {crashed}'


# ---- 실습 5 ----

def check_schema(model_class):
    def accepts(text):
        try:
            model_class.model_validate_json(text)
            return True
        except Exception:
            return False

    good = '{"id": "T01", "team": "설비", "location": "3호기", "urgent": true}'
    schema = model_class.model_json_schema()
    results = [
        (accepts(good), '올바른 응답을 받아들인다', ''),
        (accepts(good.replace('"3호기"', 'null')), 'location이 null인 응답을 받아들인다', ''),
        (not accepts(good.replace('설비', '총무')), '목록에 없는 team을 거부한다', ''),
        (not accepts('{"id": "T01", "team": "설비", "urgent": true}'), 'location이 빠진 응답을 거부한다',
         'location은 없을 수 있지만 필드는 있어야 합니다. 기본값을 주지 않습니다'),
        (not accepts(good.replace('true', '"yes"')), '불리언 값 자리의 문자열을 거부한다', 'strict=True'),
        (not accepts(good[:-1] + ', "note": "메모"}'), '정하지 않은 필드를 거부한다', "extra='forbid'"),
        (schema.get('additionalProperties') is False
         and sorted(schema.get('required', [])) == ['id', 'location', 'team', 'urgent'],
         '스키마가 구조화 출력의 두 조건을 지킨다', 'additionalProperties: false, 모든 필드가 required'),
    ]
    return _report('실습 5', [(ok, title, '' if ok else note) for ok, title, note in results])


# ---- 실습 6 ----

def check_batch(classify, save, run, open_db):
    def count(db):
        return db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]

    def success():
        record = classify(ROWS[0], ask=FakeAsk())
        ok = (record['error'] is None and record['id'] == 'T01' and record['answer_id'] == 'T01'
              and record['team'] == '설비' and record['location'] == '3호기' and record['urgent'] is False
              and record['input_tokens'] == 300)
        return ok, f'받은 값 {record}'

    def call_error():
        record = classify(ROWS[0], ask=FakeAsk(fail=['T01']))
        return bool(record['error']) and record['team'] is None, f"error={record['error']!r}"

    def truncated():
        record = classify(ROWS[0], ask=FakeAsk(reply=lambda row_id: reply_for(row_id, stop_reason='max_tokens')))
        return bool(record['error']) and record['team'] is None, f"error={record['error']!r}"

    def off_schema():
        record = classify(ROWS[0], ask=FakeAsk(reply=lambda row_id: reply_for(row_id, team='총무')))
        return bool(record['error']) and record['team'] is None, f"error={record['error']!r}"

    db = open_db()
    state = {}

    def first_run():
        fake = FakeAsk(fail=['T03'])
        sent, failed = run(db, ROWS, ask=fake)
        state['first'] = True
        ok = sent == 5 and count(db) == 4 and [row_id for row_id, _ in failed] == ['T03']
        return ok, f'보낸 건 {sent}, 저장한 행 {count(db)}, 실패 {[row_id for row_id, _ in failed]}'

    def second_run():
        fake = FakeAsk()
        sent, failed = run(db, ROWS, ask=fake)
        ok = sent == 1 and fake.sent == ['T03'] and count(db) == 5 and not failed
        return ok, f'보낸 건 {sent} {fake.sent}, 저장한 행 {count(db)}'

    def third_run():
        fake = FakeAsk()
        sent, _ = run(db, ROWS, ask=fake)
        return sent == 0 and not fake.sent and count(db) == 5, f'보낸 건 {sent}, 저장한 행 {count(db)}'

    def keeps_review():
        other = open_db()
        records = [classify(row, ask=FakeAsk()) for row in ROWS]
        inserted = save(other, records, 'fake-model', '2026-01-01 00:00')
        other.execute("UPDATE requests SET reviewed = '확인함' WHERE id = 'T01'")
        records[0]['team'] = '시설'
        save(other, records, 'fake-model', '2026-01-02 00:00')
        team, reviewed = other.execute("SELECT team, reviewed FROM requests WHERE id = 'T01'").fetchone()
        ok = inserted == 5 and count(other) == 5 and team == '시설' and reviewed == '확인함'
        return ok, f'넣은 건수 {inserted!r}, 행 {count(other)}, team={team!r}, reviewed={reviewed!r}'

    checks = [
        (success, '성공한 건은 결과를 채우고 error는 None이다'),
        (call_error, '호출 실패는 예외를 발생시키지 않고 error에 사유를 적는다'),
        (truncated, '잘린 응답은 error에 사유를 적는다'),
        (off_schema, '스키마에 어긋난 응답은 error에 사유를 적는다'),
        (first_run, '한 건이 실패해도 끝까지 처리하고 성공한 건만 저장한다'),
        (second_run, '다시 실행하면 저장하지 않은 건만 보낸다'),
        (third_run, '모두 저장한 뒤에는 보내는 건이 없다'),
        (keeps_review, '넣은 건수를 돌려주고, 다시 저장해도 행이 늘지 않으며 사람이 적은 값이 남는다'),
    ]
    results = []
    for function, title in checks:
        ok, note = _try(function)
        results.append((ok, title, '' if ok else note))
    return _report('실습 6', results)


# ---- 실습 7 ----

def _record(**changes):
    record = {'id': 'T01', 'answer_id': 'T01', 'team': '설비', 'location': '3호기', 'urgent': False,
              'error': None, 'input_tokens': 300, 'output_tokens': 30}
    record.update(changes)
    return record


def check_validate(validate, status_of):
    text = '3호기 옆 바닥에 물이 고여 있습니다'
    failed = _record(team=None, location=None, urgent=None, answer_id=None, error='호출 실패(timeout)')
    cases = [
        ('문제가 없는 결과는 통과한다', _record(), None, 'auto'),
        ('위치가 None인 결과는 통과한다', _record(location=None), None, 'auto'),
        ('error가 있으면 그 사유를 돌려준다', failed, '호출 실패(timeout)', 'manual'),
        ('보낸 id와 받은 id가 다르면 걸린다', _record(answer_id='T99'), True, 'review'),
        ('기타인데 urgent가 true면 걸린다', _record(team='기타', urgent=True), True, 'review'),
        ('본문에 없는 위치는 걸린다', _record(location='5호기 챔버'), True, 'review'),
    ]
    results = []
    for title, record, expected, expected_status in cases:
        def run_case():
            why, status = validate(record, text), status_of(record, text)
            if expected is None:
                ok = why is None
            elif expected is True:
                ok = isinstance(why, str) and bool(why)
            else:
                ok = why == expected
            return ok and status == expected_status, f'사유 {why!r}, 상태 {status!r}'
        ok, note = _try(run_case)
        results.append((ok, title, '' if ok else note))
    return _report('실습 7', results)
