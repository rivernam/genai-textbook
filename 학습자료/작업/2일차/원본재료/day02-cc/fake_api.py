# 검사용 가짜 Claude 응답기입니다. 실제 서버에 보내지 않고, 정해 둔 순서대로 성공 · 오류 · 잘린 응답을 돌려줍니다.
# API 키가 없어도 돌고 요금이 들지 않습니다. 이 파일은 고치지 않습니다.
import types
import anthropic
import httpx

URL = 'https://api.anthropic.com/v1/messages'


def _err(kind):
    req = httpx.Request('POST', URL)
    if kind == 'timeout':
        return anthropic.APITimeoutError(request=req)
    code, cls = {429: (429, anthropic.RateLimitError), 529: (529, anthropic.OverloadedError),
                 500: (500, anthropic.InternalServerError), 404: (404, anthropic.NotFoundError),
                 401: (401, anthropic.AuthenticationError), 400: (400, anthropic.BadRequestError)}[kind]
    return cls(f'가짜 오류 {code}', response=httpx.Response(code, request=req), body=None)


def _resp(user, stop='end_turn'):
    rid = user.split('\n')[0].replace('id:', '').strip() or 'Q00'
    text = '{"id": "%s", "category": "문서안내", "urgent": false}' % rid
    if stop == 'max_tokens':
        text = text[:12]
    if stop == 'refusal':
        text = ''
    block = types.SimpleNamespace(type='text', text=text)
    usage = types.SimpleNamespace(input_tokens=80, output_tokens=len(text) // 2)
    return types.SimpleNamespace(content=[block], stop_reason=stop, usage=usage, model='fake-model')


class FakeClient:
    """script: 호출 순서대로 쓸 동작 목록. by_id: 문의 id 마다 늘 같은 동작.
    동작은 'ok' · 'max_tokens' · 'refusal' · 'timeout' · 429 · 529 · 500 · 404 · 401 · 400 입니다."""

    def __init__(self, script=None, by_id=None, log=None):
        self.script = list(script or [])
        self.by_id = by_id or {}
        self.log = log if log is not None else {'calls': 0, 'options': []}
        self.messages = self

    def with_options(self, **kw):
        self.log['options'].append(kw)
        c = FakeClient(self.script, self.by_id, self.log)
        c.script = self.script            # 같은 목록을 함께 씁니다
        return c

    def create(self, **kw):
        self.log['calls'] += 1
        user = kw['messages'][-1]['content']
        rid = user.split('\n')[0].replace('id:', '').strip()
        act = self.by_id.get(rid) if rid in self.by_id else (self.script.pop(0) if self.script else 'ok')
        if act in ('ok', 'max_tokens', 'refusal'):
            return _resp(user, 'end_turn' if act == 'ok' else act)
        raise _err(act)
