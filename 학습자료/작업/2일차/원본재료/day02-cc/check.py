# send_batch.py 가 오류를 제대로 다루는지 가짜 응답기로 검사합니다.
# 실행: python check.py            (같은 폴더의 send_batch.py 를 검사)
#       python check.py 다른파일.py  (다른 파일을 검사)
# 실제 API 를 부르지 않으니 키가 없어도 되고 요금이 들지 않습니다. 이 파일은 고치지 않습니다.
import importlib.util, os, sys, time
import anthropic
from fake_api import FakeClient

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'send_batch.py')
spec = importlib.util.spec_from_file_location('target', path)
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)

WAITS = []
time.sleep = lambda s: WAITS.append(s)          # 기다리는 시간은 재기만 하고 실제로 기다리지 않습니다
ROWS = [{'id': f'Q{i:02d}', '문의내용': f'시험 문의 {i}'} for i in range(1, 21)]


def call(script):
    log = {'calls': 0, 'options': []}
    WAITS.clear()
    try:
        sb.ask(FakeClient(script, log=log), sb.SYS_CLS, 'id: Q01\n문의: 시험')
        err = None
    except Exception as e:
        err = e
    return log['calls'], err, list(WAITS)


def ids(xs):
    return sorted(x['id'] if isinstance(x, dict) else str(x) for x in xs)


def t1():
    n, e, _ = call(['ok'])
    return n == 1 and e is None, f'보냄 {n}'

def t2():
    n, e, _ = call([429, 429, 'ok'])
    return n == 3 and e is None, f'보냄 {n} · ' + ('성공' if e is None else type(e).__name__)

def t3():
    n, e, _ = call([529, 'ok'])
    return n == 2 and e is None, f'보냄 {n} · ' + ('성공' if e is None else type(e).__name__)

def t4():
    n, e, _ = call(['timeout'] * 10)
    return n == 3 and isinstance(e, anthropic.APIConnectionError), f'보냄 {n} · ' + ('예외 없음' if e is None else type(e).__name__)

def t5():
    n, e, _ = call([404, 'ok'])
    return n == 1 and isinstance(e, anthropic.NotFoundError), f'보냄 {n} · ' + ('예외 없음' if e is None else type(e).__name__)

def t6():
    n, e, _ = call([401, 'ok'])
    return n == 1 and isinstance(e, anthropic.AuthenticationError), f'보냄 {n} · ' + ('예외 없음' if e is None else type(e).__name__)

def t7():
    seen = []
    real = anthropic.Anthropic
    class Rec:
        def __init__(self, *a, **kw): seen.append(kw)
    sb.anthropic.Anthropic = Rec
    try:
        sb.make_client()
    except Exception:
        pass
    finally:
        sb.anthropic.Anthropic = real
    log = {'calls': 0, 'options': []}
    try:
        sb.ask(FakeClient(['ok'], log=log), sb.SYS_CLS, 'id: Q01\n문의: 시험')
    except Exception:
        pass
    vals = [kw.get('max_retries') for kw in seen + log['options'] if 'max_retries' in kw]
    return 0 in vals, f'max_retries {vals or "없음"}'

def t8():
    log = {'calls': 0, 'options': []}
    try:
        ok, failed = sb.run(FakeClient(by_id={'Q03': 'timeout'}, log=log), ROWS)
    except Exception as e:
        return False, f'중간에 멈춤 · {type(e).__name__}'
    return len(ok) == 19 and ids(failed) == ['Q03'], f'성공 {len(ok)} · 실패 {ids(failed)}'

def t9():
    try:
        ok, failed = sb.run(FakeClient(by_id={'Q05': 'max_tokens', 'Q07': 'refusal'}), ROWS)
    except Exception as e:
        return False, f'중간에 멈춤 · {type(e).__name__}'
    return ids(failed) == ['Q05', 'Q07'] and len(ok) == 18, f'성공 {len(ok)} · 실패 {ids(failed)}'

def t10():
    _, _, w = call([429, 429, 'ok'])
    good = len(w) == 2 and w[1] > w[0] > 0
    return good, '기다림 ' + (' · '.join(f'{x:g}초' for x in w) if w else '없음')


TESTS = [('정상 응답은 한 번만 보냄', t1),
         ('429 는 다시 보내 성공', t2),
         ('529 는 다시 보내 성공', t3),
         ('시간 초과는 세 번까지만', t4),
         ('404 는 다시 보내지 않음', t5),
         ('401 은 다시 보내지 않음', t6),
         ('SDK 자동 재시도를 끔', t7),
         ('한 건이 실패해도 20건 끝까지', t8),
         ('잘림 · 거절은 실패 목록으로', t9),
         ('기다리는 시간이 늘어남', t10)]

passed = 0
for i, (name, fn) in enumerate(TESTS, 1):
    try:
        good, info = fn()
    except Exception as e:
        good, info = False, f'검사 중 오류 · {type(e).__name__}: {e}'[:80]
    passed += good
    print(f'{i:2d}. {"통과" if good else "실패"} {name} ({info})')
print(f'결과 {passed}/{len(TESTS)} 통과 · 검사한 파일 {os.path.basename(path)}')
