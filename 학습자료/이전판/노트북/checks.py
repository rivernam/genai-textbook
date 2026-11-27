"""재시도와 실패 처리를 제대로 했는지 확인하는 열 가지 검사.

실제 API를 부르지 않는다. 미리 정한 대로 성공하거나 실패하는 mock 호출을 넣어 본다.
그래서 키가 없어도 되고 요금도 들지 않는다.

검사하는 함수의 약속

    ask(prompt, system=None, max_tokens=300, tries=3, send=llm.send, sleep=time.sleep)
        send(messages, system=..., max_tokens=...)로 한 번 보낸다.
        재시도할 만한 오류(CallError.retryable)면 sleep(1), sleep(2) …로 기다리며
        tries번까지 보낸다. 그 밖의 오류와 마지막 실패는 예외를 그대로 다시 발생시킨다.
        성공하면 Reply를 돌려준다.

    process_all(rows, ask=ask)
        rows는 [{'id': ..., '문의내용': ...}, ...]다.
        (성공 목록, 실패 목록)을 돌려준다.
        성공 목록은 [{'id': ..., 'category': ..., 'urgent': ...}, ...]
        실패 목록은 [(id, 사유), ...]다.
        한 건이 실패해도 멈추지 않는다. 잘린 응답, 거절된 응답, JSON으로 읽을 수 없는
        응답은 성공으로 세지 않고 실패 목록에 넣는다.
"""
from llm import CallError, Reply

TITLES = {
    1: '정상 응답은 한 번만 보낸다',
    2: '429 오류는 재시도해 성공한다',
    3: '5xx 오류는 재시도해 성공한다',
    4: '타임아웃은 세 번까지만 보내고 예외를 다시 발생시킨다',
    5: '404 오류는 재시도하지 않는다',
    6: '401 오류는 재시도하지 않는다',
    7: '400 오류는 재시도하지 않는다',
    8: '대기 시간이 1초, 2초로 늘어난다',
    9: '한 건이 실패해도 끝까지 처리한다',
    10: '잘림, 거절, 파싱 오류는 실패 목록에 넣는다',
}


def good_reply(text='{"id": "Q", "category": "문서안내", "urgent": false}', stop_reason='end'):
    return Reply(text, 100, 20, stop_reason, 'fake-model', 0.1)


def error(kind, status=None):
    return CallError(kind, status, '검사용 mock 오류')


class FakeSend:
    """정해 둔 순서대로 응답하거나 오류를 발생시키는 mock send(). 마지막 항목은 계속 되풀이한다."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = 0

    def __call__(self, messages, **options):
        self.calls += 1
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        return item


def _ask_with(ask, fake, waits):
    return ask('검사용 문의', system='검사용 규칙', send=fake, sleep=waits.append)


def _check_ask(ask, number):
    waits = []
    if number == 1:
        fake = FakeSend(good_reply())
        _ask_with(ask, fake, waits)
        return fake.calls == 1, f'보낸 횟수 {fake.calls}'
    if number in (2, 3):
        script = ([error('rate_limit', 429), error('rate_limit', 429), good_reply()] if number == 2
                  else [error('server', 529), good_reply()])
        fake = FakeSend(*script)
        try:
            _ask_with(ask, fake, waits)
        except CallError as failed:
            return False, f'보낸 횟수 {fake.calls}, {failed.status} 오류로 끝남'
        return fake.calls == len(script), f'보낸 횟수 {fake.calls}, 성공'
    if number == 4:
        fake = FakeSend(error('timeout'))
        try:
            _ask_with(ask, fake, waits)
        except CallError:
            return fake.calls == 3, f'보낸 횟수 {fake.calls}, 예외를 다시 발생시킴'
        return False, f'보낸 횟수 {fake.calls}, 예외를 다시 발생시키지 않음'
    if number in (5, 6, 7):
        kind, status = {5: ('not_found', 404), 6: ('auth', 401), 7: ('bad_request', 400)}[number]
        fake = FakeSend(error(kind, status))
        try:
            _ask_with(ask, fake, waits)
        except CallError:
            return fake.calls == 1 and not waits, f'보낸 횟수 {fake.calls}'
        return False, '예외를 다시 발생시키지 않음'
    if number == 8:
        fake = FakeSend(error('server', 500), error('server', 500), good_reply())
        try:
            _ask_with(ask, fake, waits)
        except CallError:
            pass
        return waits == [1, 2], f'대기 시간 {waits or "없음"}'
    raise ValueError(number)


ROWS = [{'id': f'T{number:02d}', '문의내용': f'검사용 문의 {number}'} for number in range(1, 6)]

# 검사 9, 10의 mock ask는 프롬프트에 든 id로 건을 구별한다. 실패한 건이 하나도 없으면 id를 빠뜨렸을 가능성이 크다
_ID_HINT = '. ask에 넘기는 프롬프트에 문의 id가 들어 있는지 확인합니다'


def _check_process_all(process_all, number):
    if number == 9:
        def fake_ask(prompt, **options):
            if 'T03' in prompt:
                raise error('timeout')
            return good_reply()
        success, failed = process_all(ROWS, ask=fake_ask)
        ok = len(success) == 4 and [row_id for row_id, _ in failed] == ['T03']
        return ok, f'성공 {len(success)}건, 실패 {[row_id for row_id, _ in failed]}' + _ID_HINT * (not failed)
    if number == 10:
        def fake_ask(prompt, **options):
            if 'T02' in prompt:
                return good_reply('{"id": "T02", "categ', stop_reason='max_tokens')
            if 'T04' in prompt:
                return good_reply('', stop_reason='refusal')
            if 'T05' in prompt:
                return good_reply('긴급으로 보입니다.')
            return good_reply()
        success, failed = process_all(ROWS, ask=fake_ask)
        failed_ids = sorted(row_id for row_id, _ in failed)
        ok = len(success) == 2 and failed_ids == ['T02', 'T04', 'T05']
        return ok, f'성공 {len(success)}건, 실패 {failed_ids}' + _ID_HINT * (not failed)
    raise ValueError(number)


def run(ask, process_all):
    """열 가지 검사를 돌려 결과를 출력한다. [(번호, 통과 여부, 설명), ...]을 돌려준다."""
    results = []
    for number, title in TITLES.items():
        try:
            if number <= 8:
                ok, note = _check_ask(ask, number)
            else:
                ok, note = _check_process_all(process_all, number)
        except Exception as crashed:  # 검사받는 코드가 어떤 예외를 발생시켜도 검사는 끝까지 진행한다
            ok, note = False, f'{type(crashed).__name__}: {crashed}'
        results.append((number, ok, note))
        print(f'{number}. {"통과" if ok else "실패"} {title} ({note})')
    passed = sum(ok for _, ok, _ in results)
    print(f'결과 {passed}/10 통과')
    return results
