"""llm.py 테스트. 로컬 가짜 HTTP 서버에 실제 SDK로 호출한다(네트워크·요금 없음)."""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '노트북'))
import llm  # noqa: E402

ENV_NAMES = ['LLM_PROVIDER', 'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_AUTH_TOKEN',
             'ANTHROPIC_PROFILE', 'OPENAI_BASE_URL', 'OPENAI_API_KEY',
             'LLM_MODEL_SMALL', 'LLM_MODEL_DEFAULT', 'LLM_MODEL_LARGE', 'LLM_STRUCTURED']


def anthropic_body(text='안녕하세요', stop_reason='end_turn', model='claude-test'):
    return {'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'model': model,
            'content': [{'type': 'thinking', 'thinking': '', 'signature': 's'},
                        {'type': 'text', 'text': text}],
            'stop_reason': stop_reason, 'stop_sequence': None,
            'usage': {'input_tokens': 12, 'output_tokens': 7}}


def openai_body(text='안녕하세요', finish_reason='stop', usage=True, model='inhouse-test'):
    body = {'id': 'c1', 'object': 'chat.completion', 'created': 0, 'model': model,
            'choices': [{'index': 0, 'finish_reason': finish_reason,
                         'message': {'role': 'assistant', 'content': text}}]}
    if usage:
        body['usage'] = {'prompt_tokens': 12, 'completion_tokens': 7, 'total_tokens': 19}
    return body


ERROR = {'type': 'error', 'error': {'type': 'x', 'message': '가짜 오류'}}


class FakeServer:
    """미리 정한 (상태 코드, 본문) 목록을 차례로 돌려주고 받은 요청을 기록한다."""

    def __init__(self):
        self.script = []
        self.requests = []
        self.delay = 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('content-length', 0))
                outer.requests.append((self.path, json.loads(self.rfile.read(length))))
                status, body = outer.script.pop(0) if len(outer.script) > 1 else outer.script[0]
                if outer.delay:
                    time.sleep(outer.delay)
                data = json.dumps(body).encode('utf-8')
                self.send_response(status)
                self.send_header('content-type', 'application/json')
                self.send_header('content-length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.httpd.server_port}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def server(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    waits = []
    monkeypatch.setattr(llm, '_sleep', waits.append)
    fake = FakeServer()
    fake.waits = waits
    yield fake
    fake.close()


@pytest.fixture
def anthropic_env(server, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
    monkeypatch.setenv('ANTHROPIC_BASE_URL', server.url)
    return server


@pytest.fixture
def openai_env(server, monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_BASE_URL', server.url + '/v1')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('LLM_MODEL_DEFAULT', 'inhouse-default')
    monkeypatch.setenv('LLM_MODEL_SMALL', 'inhouse-small')
    return server


def test_anthropic_request_and_reply(anthropic_env):
    anthropic_env.script = [(200, anthropic_body())]
    history = [{'role': 'user', 'content': '앞 질문'}, {'role': 'assistant', 'content': '앞 답'}]
    reply = llm.ask('새 질문', system='규칙', history=history, max_tokens=50)

    path, sent = anthropic_env.requests[0]
    assert path == '/v1/messages'
    assert sent['system'] == '규칙'
    assert sent['messages'] == history + [{'role': 'user', 'content': '새 질문'}]
    assert sent['max_tokens'] == 50
    assert sent['model'] == llm.model_name('기본')
    assert reply.text == '안녕하세요'            # thinking 블록은 빼고 text 블록만
    assert (reply.input_tokens, reply.output_tokens) == (12, 7)
    assert reply.stop_reason == 'end'
    assert reply.model == 'claude-test'
    assert reply.seconds >= 0


def test_anthropic_omits_system_when_none(anthropic_env):
    anthropic_env.script = [(200, anthropic_body())]
    llm.ask('질문')
    assert 'system' not in anthropic_env.requests[0][1]


@pytest.mark.parametrize('raw, expected', [('end_turn', 'end'), ('stop_sequence', 'end'),
                                           ('max_tokens', 'max_tokens'),
                                           ('model_context_window_exceeded', 'max_tokens'),
                                           ('refusal', 'refusal'), ('tool_use', 'other'),
                                           ('pause_turn', 'other')])
def test_anthropic_stop_reason(anthropic_env, raw, expected):
    anthropic_env.script = [(200, anthropic_body(stop_reason=raw))]
    assert llm.ask('질문').stop_reason == expected


def test_openai_request_and_reply(openai_env):
    openai_env.script = [(200, openai_body())]
    history = [{'role': 'user', 'content': '앞 질문'}, {'role': 'assistant', 'content': '앞 답'}]
    reply = llm.ask('새 질문', system='규칙', history=history, model='소형', max_tokens=50)

    path, sent = openai_env.requests[0]
    assert path == '/v1/chat/completions'
    assert sent['messages'] == ([{'role': 'system', 'content': '규칙'}] + history
                                + [{'role': 'user', 'content': '새 질문'}])
    assert sent['model'] == 'inhouse-small'
    assert sent['max_tokens'] == 50
    assert reply.text == '안녕하세요'
    assert (reply.input_tokens, reply.output_tokens) == (12, 7)
    assert reply.stop_reason == 'end'
    assert reply.model == 'inhouse-test'


@pytest.mark.parametrize('raw, expected', [('stop', 'end'), ('length', 'max_tokens'),
                                           ('content_filter', 'refusal'), ('tool_calls', 'other'),
                                           ('function_call', 'other')])
def test_openai_stop_reason(openai_env, raw, expected):
    openai_env.script = [(200, openai_body(finish_reason=raw))]
    assert llm.ask('질문').stop_reason == expected


def test_openai_without_usage_gives_none(openai_env):
    openai_env.script = [(200, openai_body(usage=False))]
    reply = llm.ask('질문')
    assert reply.input_tokens is None and reply.output_tokens is None


def test_openai_null_content_gives_empty_text(openai_env):
    body = openai_body()
    body['choices'][0]['message']['content'] = None
    openai_env.script = [(200, body)]
    assert llm.ask('질문').text == ''


@pytest.mark.parametrize('env', ['anthropic_env', 'openai_env'])
def test_retries_429_then_succeeds(env, request):
    server = request.getfixturevalue(env)
    ok = anthropic_body() if env == 'anthropic_env' else openai_body()
    server.script = [(429, ERROR), (529, ERROR), (200, ok)]
    reply = llm.ask('질문')
    assert reply.text == '안녕하세요'
    assert len(server.requests) == 3          # SDK 자동 재시도가 꺼져 있어 정확히 세 번
    assert server.waits == [1, 2]             # 1초, 2초로 늘어나는 대기


@pytest.mark.parametrize('env', ['anthropic_env', 'openai_env'])
@pytest.mark.parametrize('status', [400, 401, 404])
def test_does_not_retry_client_errors(env, status, request):
    server = request.getfixturevalue(env)
    server.script = [(status, ERROR)]
    with pytest.raises(llm.CallError) as caught:
        llm.ask('질문')
    assert caught.value.status == status
    assert len(server.requests) == 1
    assert server.waits == []


def test_gives_up_after_tries(anthropic_env):
    anthropic_env.script = [(500, ERROR)]
    with pytest.raises(llm.CallError) as caught:
        llm.ask('질문', tries=3)
    assert caught.value.status == 500
    assert len(anthropic_env.requests) == 3
    assert anthropic_env.waits == [1, 2]


def test_missing_openai_base_url(server, monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.setenv('OPENAI_API_KEY', 'k')
    monkeypatch.setenv('LLM_MODEL_DEFAULT', 'm')
    with pytest.raises(RuntimeError, match='OPENAI_BASE_URL'):
        llm.ask('질문')


def test_missing_openai_model(server, monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    with pytest.raises(RuntimeError, match='LLM_MODEL_DEFAULT'):
        llm.model_name('기본')


def test_missing_anthropic_key(server):
    with pytest.raises(RuntimeError, match='ANTHROPIC_API_KEY'):
        llm.ask('질문')


def test_unknown_provider(server, monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'gemini')
    with pytest.raises(ValueError, match='LLM_PROVIDER'):
        llm.ask('질문')


def test_unknown_alias(server):
    with pytest.raises(ValueError, match='없는별칭'):
        llm.model_name('없는별칭')


def test_model_name_passes_through_env_override(server, monkeypatch):
    monkeypatch.setenv('LLM_MODEL_LARGE', 'my-large')
    assert llm.model_name('대형') == 'my-large'


# ---- send(): 재시도 없는 한 번 호출 ----

def test_send_takes_messages_and_never_retries(anthropic_env):
    anthropic_env.script = [(429, ERROR), (200, anthropic_body())]
    with pytest.raises(llm.CallError) as caught:
        llm.send([{'role': 'user', 'content': '질문'}])
    assert caught.value.status == 429 and caught.value.kind == 'rate_limit'
    assert caught.value.retryable is True
    assert len(anthropic_env.requests) == 1


@pytest.mark.parametrize('env', ['anthropic_env', 'openai_env'])
@pytest.mark.parametrize('status, kind, retryable', [
    (400, 'bad_request', False), (401, 'auth', False), (403, 'permission', False),
    (404, 'not_found', False), (429, 'rate_limit', True), (500, 'server', True), (529, 'server', True)])
def test_call_error_kinds(env, status, kind, retryable, request):
    server = request.getfixturevalue(env)
    server.script = [(status, ERROR)]
    with pytest.raises(llm.CallError) as caught:
        llm.send([{'role': 'user', 'content': '질문'}])
    assert (caught.value.status, caught.value.kind, caught.value.retryable) == (status, kind, retryable)
    assert str(status) in str(caught.value)


@pytest.mark.parametrize('env', ['anthropic_env', 'openai_env'])
def test_timeout_is_retryable_call_error(env, request):
    server = request.getfixturevalue(env)
    server.script = [(200, anthropic_body() if env == 'anthropic_env' else openai_body())]
    server.delay = 1.0
    with pytest.raises(llm.CallError) as caught:
        llm.send([{'role': 'user', 'content': '질문'}], timeout=0.2)
    assert caught.value.kind == 'timeout' and caught.value.status is None
    assert caught.value.retryable is True


def test_connection_error_kind(server, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'k')
    monkeypatch.setenv('ANTHROPIC_BASE_URL', 'http://127.0.0.1:9')   # 아무도 듣지 않는 포트
    with pytest.raises(llm.CallError) as caught:
        llm.send([{'role': 'user', 'content': '질문'}], timeout=2)
    assert caught.value.kind in ('connection', 'timeout') and caught.value.retryable is True


def test_send_api_key_override(anthropic_env):
    anthropic_env.script = [(200, anthropic_body())]
    seen = {}
    original = anthropic_env.httpd.RequestHandlerClass.do_POST

    def spy(handler):
        seen['headers'] = dict(handler.headers)
        original(handler)
    anthropic_env.httpd.RequestHandlerClass.do_POST = spy
    llm.send([{'role': 'user', 'content': '질문'}], api_key='other-key')
    assert any('other-key' in value for value in seen['headers'].values()), seen['headers']
    assert not any('test-key' in value for value in seen['headers'].values())


def test_send_accepts_raw_model_name(anthropic_env):
    anthropic_env.script = [(200, anthropic_body())]
    llm.send([{'role': 'user', 'content': '질문'}], model='claude-nonexistent')
    assert anthropic_env.requests[0][1]['model'] == 'claude-nonexistent'


def test_count_tokens_anthropic(anthropic_env):
    anthropic_env.script = [(200, {'input_tokens': 33})]
    count = llm.count_tokens([{'role': 'user', 'content': '질문'}], system='규칙', model='소형')
    path, sent = anthropic_env.requests[0]
    assert path == '/v1/messages/count_tokens'
    assert sent['system'] == '규칙' and sent['model'] == llm.model_name('소형')
    assert count == 33


def test_count_tokens_openai_returns_none(openai_env):
    assert llm.count_tokens([{'role': 'user', 'content': '질문'}]) is None
    assert openai_env.requests == []


# ---- 구조화 출력 ----

SCHEMA = {'type': 'object', 'properties': {'category': {'type': 'string', 'enum': ['긴급', '기타']}},
          'required': ['category'], 'additionalProperties': False}


def test_anthropic_schema_goes_to_output_config(anthropic_env):
    anthropic_env.script = [(200, anthropic_body('{"category": "긴급"}'))]
    reply = llm.ask('질문', system='규칙', schema=SCHEMA)
    sent = anthropic_env.requests[0][1]
    assert sent['output_config'] == {'format': {'type': 'json_schema', 'schema': SCHEMA}}
    assert sent['system'] == '규칙'                       # 프롬프트는 바뀌지 않는다
    assert json.loads(reply.text) == {'category': '긴급'}
    assert llm.structured_mode() == 'json_schema'


def test_no_schema_sends_no_format(anthropic_env):
    anthropic_env.script = [(200, anthropic_body())]
    llm.ask('질문')
    assert 'output_config' not in anthropic_env.requests[0][1]


def test_openai_schema_default_is_strict_json_schema(openai_env):
    openai_env.script = [(200, openai_body('{"category": "긴급"}'))]
    llm.ask('질문', system='규칙', schema=SCHEMA)
    sent = openai_env.requests[0][1]
    assert sent['response_format'] == {'type': 'json_schema', 'json_schema': {
        'name': 'result', 'schema': SCHEMA, 'strict': True}}
    assert sent['messages'][0] == {'role': 'system', 'content': '규칙'}


@pytest.mark.parametrize('mode, expected_format', [('json_object', {'type': 'json_object'}),
                                                   ('prompt', None)])
def test_openai_fallback_modes_put_schema_in_prompt(openai_env, monkeypatch, mode, expected_format):
    monkeypatch.setenv('LLM_STRUCTURED', mode)
    openai_env.script = [(200, openai_body('{"category": "긴급"}'))]
    llm.ask('질문', system='규칙', schema=SCHEMA)
    sent = openai_env.requests[0][1]
    assert sent.get('response_format') == expected_format
    system = sent['messages'][0]['content']
    assert system.startswith('규칙\n\n') and 'JSON' in system
    assert json.dumps(SCHEMA, ensure_ascii=False) in system


def test_openai_fallback_without_system_still_sends_schema(openai_env, monkeypatch):
    monkeypatch.setenv('LLM_STRUCTURED', 'prompt')
    openai_env.script = [(200, openai_body('{}'))]
    llm.ask('질문', schema=SCHEMA)
    first = openai_env.requests[0][1]['messages'][0]
    assert first['role'] == 'system' and first['content'] == llm.schema_instruction(SCHEMA)


def test_unknown_structured_mode_is_rejected(openai_env, monkeypatch):
    monkeypatch.setenv('LLM_STRUCTURED', 'xml')
    with pytest.raises(ValueError):
        llm.structured_mode()


def test_chat_keeps_history_and_prints_reply(anthropic_env, capsys):
    anthropic_env.script = [(200, anthropic_body('첫 답')), (200, anthropic_body('둘째 답'))]
    chat = llm.Chat(system='규칙', model='소형')
    assert chat.say('첫 질문') is None                      # 노트북 셀 끝에서 응답 객체가 되풀이 출력되지 않게 한다
    chat.say('둘째 질문')

    first, second = [sent for _, sent in anthropic_env.requests]
    assert first['system'] == '규칙' and first['model'] == 'claude-haiku-5-5'
    assert first['messages'] == [{'role': 'user', 'content': '첫 질문'}]
    assert second['messages'] == [{'role': 'user', 'content': '첫 질문'}, {'role': 'assistant', 'content': '첫 답'},
                                  {'role': 'user', 'content': '둘째 질문'}]
    assert capsys.readouterr().out == '첫 답\n둘째 답\n'
    assert chat.last.text == '둘째 답' and len(chat.history) == 4


def test_new_chat_starts_without_history(anthropic_env):
    anthropic_env.script = [(200, anthropic_body())]
    llm.Chat().say('앞 대화', show=False)
    llm.Chat().say('새 대화', show=False)
    assert anthropic_env.requests[1][1]['messages'] == [{'role': 'user', 'content': '새 대화'}]


def test_chat_reports_cut_reply_and_skips_empty_history(anthropic_env, capsys):
    anthropic_env.script = [(200, anthropic_body('', stop_reason='max_tokens'))]
    chat = llm.Chat()
    chat.say('긴 계산')
    printed = capsys.readouterr().out
    assert '응답 텍스트가 없습니다' in printed and 'max_tokens' in printed
    assert chat.history == [] and chat.last.stop_reason == 'max_tokens'
