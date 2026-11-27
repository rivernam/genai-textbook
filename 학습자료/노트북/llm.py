"""교재 공통 호출 함수.

Anthropic API와 OpenAI 호환 API(사내 LLM API 등)를 같은 함수로 부른다.
어느 쪽을 쓸지는 환경 변수로 정한다. 키와 주소는 이 파일에 적지 않는다.

    LLM_PROVIDER       anthropic(기본값) 또는 openai
    ANTHROPIC_API_KEY  Anthropic을 쓸 때
    OPENAI_BASE_URL    OpenAI 호환 API 주소 (예: https://.../v1)
    OPENAI_API_KEY     OpenAI 호환 API 키
    LLM_MODEL_SMALL    '소형' 별칭이 가리킬 모델 이름
    LLM_MODEL_DEFAULT  '기본' 별칭이 가리킬 모델 이름
    LLM_MODEL_LARGE    '대형' 별칭이 가리킬 모델 이름

    LLM_STRUCTURED     OpenAI 호환 API에서 구조화 출력을 요청하는 방식
                       json_schema(기본값), json_object, prompt

OpenAI 호환 API에는 모델 기본값이 없으므로 쓰는 별칭의 환경 변수를 꼭 정한다.

함수
    send(messages, ...)   한 번 보낸다. 실패하면 CallError를 낸다. 재시도하지 않는다.
                          schema에 JSON 스키마를 주면 구조화 출력으로 요청한다.
    ask(prompt, ...)      send()에 재시도와 백오프를 더한 것.
    ask_messages(...)     메시지 목록을 그대로 보낸다. 재시도는 ask()와 같다. 도구 호출이 든 대화를 이어 갈 때 쓴다.
    count_tokens(...)     보내기 전에 입력 토큰 수를 센다. 지원하지 않는 API면 None.
    Chat(...)             채팅 화면처럼 쓰는 대화 하나. say()로 보내면 응답을 출력하고 대화를 잇는다.
"""
import json
import os
import time
from dataclasses import dataclass, field

_ALIAS_ENV = {'소형': 'LLM_MODEL_SMALL', '기본': 'LLM_MODEL_DEFAULT', '대형': 'LLM_MODEL_LARGE'}

# Anthropic 모델 기본값 (2026-11 기준). 모델이 바뀌면 환경 변수로 덮어쓴다.
_ANTHROPIC_DEFAULTS = {'소형': 'claude-haiku-5-5', '기본': 'claude-sonnet-5-5',
                       '대형': 'claude-opus-5-5'}

# 컨텍스트 윈도우가 가득 차서 끊긴 응답도 잘린 응답이므로 'max_tokens' 로 돌려준다
_ANTHROPIC_STOP = {'end_turn': 'end', 'stop_sequence': 'end',
                   'max_tokens': 'max_tokens', 'model_context_window_exceeded': 'max_tokens',
                   'refusal': 'refusal', 'tool_use': 'tool_use'}
_OPENAI_STOP = {'stop': 'end', 'length': 'max_tokens', 'content_filter': 'refusal',
                'tool_calls': 'tool_use'}
_STATUS_KIND = {400: 'bad_request', 401: 'auth', 403: 'permission', 404: 'not_found',
                429: 'rate_limit'}

_sleep = time.sleep  # 테스트에서 바꿔 끼운다


@dataclass
class ToolCall:
    """모델이 요청한 도구 호출 하나. 도구를 실행하는 것은 모델이 아니라 이 요청을 받은 코드다."""
    id: str                    # 호출 번호. 결과를 돌려줄 때 같은 번호를 붙인다
    name: str                  # 도구 이름
    arguments: dict            # 인자. 모델이 생성한 JSON을 파싱한 것


@dataclass
class Reply:
    """모델 응답에서 교재가 쓰는 값만 모은 것."""
    text: str                  # 응답 텍스트
    input_tokens: int | None   # 입력 토큰 수 (서버가 알려 주지 않으면 None)
    output_tokens: int | None  # 출력 토큰 수 (서버가 알려 주지 않으면 None)
    stop_reason: str           # 'end' 정상 종료, 'max_tokens' 잘림, 'refusal' 거절, 'tool_use' 도구 호출, 'other'
    model: str                 # 실제로 답한 모델 이름
    seconds: float             # 걸린 시간(초)
    tool_calls: list[ToolCall] = field(default_factory=list)   # 모델이 요청한 도구 호출 (tools를 줬을 때)


class CallError(Exception):
    """API 호출 실패. 어느 SDK에서 났든 같은 형식의 예외로 바꿔 발생시킨다.

    status     HTTP 상태 코드. 서버 응답을 받지 못했으면(연결 실패, 타임아웃) None
    kind       'bad_request' 'auth' 'permission' 'not_found' 'rate_limit' 'server'
               'timeout' 'connection' 'other'
    retryable  기다렸다 재시도하면 풀릴 수 있는 오류인지
    """

    def __init__(self, kind: str, status: int | None, detail: str):
        self.kind, self.status, self.detail = kind, status, detail
        self.retryable = kind in ('rate_limit', 'server', 'timeout', 'connection')
        label = f'{status} {kind}' if status else kind
        super().__init__(f'{label}: {detail}')


def provider() -> str:
    """환경 변수 LLM_PROVIDER 값을 돌려준다."""
    name = os.environ.get('LLM_PROVIDER', 'anthropic').strip().lower()
    if name not in ('anthropic', 'openai'):
        raise ValueError(f"LLM_PROVIDER는 'anthropic' 또는 'openai' 여야 합니다. 지금 값: {name!r}")
    return name


def model_name(alias: str) -> str:
    """'소형', '기본', '대형' 별칭을 실제 모델 이름으로 바꾼다."""
    if alias not in _ALIAS_ENV:
        raise ValueError(f"모델 별칭은 '소형', '기본', '대형' 중 하나여야 합니다. 받은 값: {alias!r}")
    name = os.environ.get(_ALIAS_ENV[alias], '').strip()
    if name:
        return name
    if provider() == 'anthropic':
        return _ANTHROPIC_DEFAULTS[alias]
    raise RuntimeError(f"환경 변수 {_ALIAS_ENV[alias]}에 '{alias}' 모델 이름을 넣어 주세요.")


def structured_mode() -> str:
    """구조화 출력을 요청하는 방식을 돌려준다.

    json_schema  서버가 스키마에 맞는 JSON만 생성한다. Anthropic은 항상 이 방식이다.
    json_object  서버가 JSON 형식만 보장한다. 스키마는 프롬프트에 적어 보낸다.
    prompt       서버가 아무것도 보장하지 않는다. 스키마를 프롬프트에 적어 보내기만 한다.
    """
    if provider() == 'anthropic':
        return 'json_schema'
    mode = os.environ.get('LLM_STRUCTURED', 'json_schema').strip().lower()
    if mode not in ('json_schema', 'json_object', 'prompt'):
        raise ValueError("LLM_STRUCTURED는 'json_schema', 'json_object', 'prompt' 중 하나여야 합니다. "
                         f'지금 값: {mode!r}')
    return mode


def schema_instruction(schema: dict) -> str:
    """서버가 스키마를 강제하지 않을 때 시스템 프롬프트 끝에 붙이는 글."""
    return ('아래 JSON 스키마에 맞는 JSON 객체 하나만 출력한다. 설명이나 코드 블록 표시를 붙이지 않는다.\n'
            + json.dumps(schema, ensure_ascii=False))


def _resolve_model(model: str) -> str:
    """별칭이면 실제 이름으로 바꾸고, 아니면 받은 이름을 그대로 쓴다."""
    return model_name(model) if model in _ALIAS_ENV else model


def _require(name: str) -> str:
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(f'환경 변수 {name}의 값이 비어 있습니다. 값을 넣은 뒤 다시 실행해 주세요.')
    return value


def _sdk():
    if provider() == 'anthropic':
        import anthropic
        return anthropic
    import openai
    return openai


def _client(timeout: float, api_key: str | None):
    sdk = _sdk()
    # SDK의 자동 재시도는 끈다. 재시도 횟수는 ask() 한 곳에서만 정한다.
    if provider() == 'anthropic':
        return sdk.Anthropic(api_key=api_key or _require('ANTHROPIC_API_KEY'),
                             max_retries=0, timeout=timeout)
    return sdk.OpenAI(base_url=_require('OPENAI_BASE_URL'),
                      api_key=api_key or _require('OPENAI_API_KEY'),
                      max_retries=0, timeout=timeout)


def _to_call_error(error: Exception, sdk) -> CallError:
    if isinstance(error, sdk.APITimeoutError):
        return CallError('timeout', None, '정해 둔 시간 안에 응답이 오지 않았습니다')
    if isinstance(error, sdk.APIConnectionError):
        return CallError('connection', None, '서버에 연결하지 못했습니다')
    if isinstance(error, sdk.APIStatusError):
        status = error.status_code
        kind = _STATUS_KIND.get(status, 'server' if status >= 500 else 'other')
        return CallError(kind, status, str(getattr(error, 'message', error)))
    return CallError('other', None, str(error))


def assistant_turn(reply: Reply) -> dict:
    """도구 호출이 든 응답을 대화 이력에 넣을 메시지로 바꾼다."""
    return {'role': 'assistant', 'content': reply.text, 'tool_calls': list(reply.tool_calls)}


def tool_result(call: ToolCall, content: str, is_error: bool = False) -> dict:
    """도구를 실행한 결과를 대화 이력에 넣을 메시지로 만든다. call은 Reply.tool_calls의 항목이다."""
    return {'role': 'tool', 'tool_call_id': call.id, 'content': content, 'is_error': is_error}


def _anthropic_messages(messages: list[dict]) -> list[dict]:
    """교재 형식의 도구 메시지를 Anthropic 형식(tool_use, tool_result 블록)으로 바꾼다."""
    out = []
    for message in messages:
        if message['role'] == 'tool':
            block = {'type': 'tool_result', 'tool_use_id': message['tool_call_id'],
                     'content': message['content'], 'is_error': message.get('is_error', False)}
            if out and out[-1]['role'] == 'user' and isinstance(out[-1]['content'], list):
                out[-1]['content'].append(block)      # 연달아 온 결과는 user 메시지 하나에 모은다
            else:
                out.append({'role': 'user', 'content': [block]})
        elif message.get('tool_calls'):
            blocks = [{'type': 'text', 'text': message['content']}] if message['content'] else []
            blocks += [{'type': 'tool_use', 'id': call.id, 'name': call.name, 'input': call.arguments}
                       for call in message['tool_calls']]
            out.append({'role': 'assistant', 'content': blocks})
        else:
            out.append({key: value for key, value in message.items() if key != 'tool_calls'})
    return out


def _openai_messages(messages: list[dict]) -> list[dict]:
    """교재 형식의 도구 메시지를 OpenAI 호환 형식(tool_calls, role tool)으로 바꾼다."""
    out = []
    for message in messages:
        if message['role'] == 'tool':
            out.append({'role': 'tool', 'tool_call_id': message['tool_call_id'],
                        'content': message['content']})
        elif message.get('tool_calls'):
            out.append({'role': 'assistant', 'content': message['content'] or None, 'tool_calls': [
                {'id': call.id, 'type': 'function',
                 'function': {'name': call.name, 'arguments': json.dumps(call.arguments, ensure_ascii=False)}}
                for call in message['tool_calls']]})
        else:
            out.append({key: value for key, value in message.items() if key != 'tool_calls'})
    return out


def _openai_arguments(text: str) -> dict:
    """OpenAI 호환 API는 인자를 JSON 문자열로 준다. 파싱하지 못하면 원문을 그대로 담아 돌려준다."""
    try:
        value = json.loads(text or '{}')
    except json.JSONDecodeError:
        return {'_파싱_오류': text}
    return value if isinstance(value, dict) else {'_파싱_오류': text}


def send(messages: list[dict], *, system: str | None = None, model: str = '기본',
         max_tokens: int = 1024, timeout: float = 60.0, api_key: str | None = None,
         schema: dict | None = None, tools: list[dict] | None = None) -> Reply:
    """메시지 목록을 한 번 보내고 Reply를 돌려준다. 실패하면 CallError를 낸다.

    messages는 [{'role': 'user'|'assistant', 'content': str}, ...]이고 user로 끝나야 한다.
    도구를 쓰는 대화에서는 assistant_turn(), tool_result()가 만든 메시지도 넣을 수 있다.
    model은 별칭('소형', '기본', '대형')이나 실제 모델 이름이다.
    schema는 JSON 스키마(dict)다. 주면 구조화 출력으로 요청한다(structured_mode() 참고).
    tools는 [{'name': ..., 'description': ..., 'input_schema': JSON 스키마}, ...]다(Anthropic 형식).
    모델이 도구를 요청하면 stop_reason이 'tool_use'이고 Reply.tool_calls에 요청이 들어 있다.
    """
    sdk = _sdk()
    real_model = _resolve_model(model)
    client = _client(timeout, api_key)
    started = time.time()
    try:
        if provider() == 'anthropic':
            request = dict(model=real_model, max_tokens=max_tokens, messages=_anthropic_messages(messages))
            if system:
                request['system'] = system
            if schema:
                request['output_config'] = {'format': {'type': 'json_schema', 'schema': schema}}
            if tools:
                request['tools'] = tools
            response = client.messages.create(**request)
            text = ''.join(block.text for block in response.content if block.type == 'text')
            calls = [ToolCall(block.id, block.name, dict(block.input))
                     for block in response.content if block.type == 'tool_use']
            result = (text, response.usage.input_tokens, response.usage.output_tokens,
                      _ANTHROPIC_STOP.get(response.stop_reason, 'other'), response.model)
        else:
            options = {}
            if schema and structured_mode() == 'json_schema':
                options['response_format'] = {'type': 'json_schema', 'json_schema': {
                    'name': 'result', 'schema': schema, 'strict': True}}
            elif schema:
                # 서버가 스키마를 강제하지 않으므로 스키마를 시스템 프롬프트에 적어 보낸다
                system = (system + '\n\n' if system else '') + schema_instruction(schema)
                if structured_mode() == 'json_object':
                    options['response_format'] = {'type': 'json_object'}
            if tools:
                options['tools'] = [{'type': 'function', 'function': {
                    'name': tool['name'], 'description': tool.get('description', ''),
                    'parameters': tool['input_schema']}} for tool in tools]
            messages = _openai_messages(messages)
            if system:
                messages = [{'role': 'system', 'content': system}] + messages
            response = client.chat.completions.create(
                model=real_model, max_tokens=max_tokens, messages=messages, **options)
            choice, usage = response.choices[0], response.usage
            calls = [ToolCall(call.id, call.function.name, _openai_arguments(call.function.arguments))
                     for call in (choice.message.tool_calls or [])]
            result = (choice.message.content or '',
                      usage.prompt_tokens if usage else None,
                      usage.completion_tokens if usage else None,
                      # 구조화 출력의 거절은 종료 이유가 아니라 message.refusal 필드로 온다
                      'refusal' if getattr(choice.message, 'refusal', None)
                      else _OPENAI_STOP.get(choice.finish_reason, 'other'), response.model)
    except sdk.APIError as error:
        raise _to_call_error(error, sdk) from error
    return Reply(*result, time.time() - started, calls)


def ask_messages(messages: list[dict], *, system: str | None = None, model: str = '기본',
                 max_tokens: int = 1024, timeout: float = 60.0, tries: int = 3,
                 schema: dict | None = None, tools: list[dict] | None = None) -> Reply:
    """메시지 목록을 보내고 Reply를 돌려준다. 재시도할 만한 오류는 ask()처럼 재시도한다.

    도구 호출과 결과가 든 대화를 이어 갈 때 쓴다. 메시지 형식은 send()와 같다.
    """
    for attempt in range(tries):
        try:
            return send(messages, system=system, model=model, max_tokens=max_tokens,
                        timeout=timeout, schema=schema, tools=tools)
        except CallError as error:
            if not error.retryable or attempt == tries - 1:
                raise
            _sleep(2 ** attempt)  # 1초, 2초, 4초 …


def ask(prompt: str, *, system: str | None = None, history: list[dict] | None = None,
        model: str = '기본', max_tokens: int = 1024, timeout: float = 60.0,
        tries: int = 3, schema: dict | None = None) -> Reply:
    """질문 하나를 보내고 Reply를 돌려준다. 재시도할 만한 오류는 재시도한다.

    history는 앞선 대화다. [{'role': 'user'|'assistant', 'content': str}, ...]
    CallError.retryable 인 오류(429, 5xx, 연결 실패, 타임아웃)는 1초, 2초로 기다리는
    시간을 늘려 가며 tries 번까지 보낸다. 그 밖의 오류와 마지막 실패는 예외를 그대로 다시 발생시킨다.
    """
    messages = list(history or []) + [{'role': 'user', 'content': prompt}]
    return ask_messages(messages, system=system, model=model, max_tokens=max_tokens,
                        timeout=timeout, tries=tries, schema=schema)


def count_tokens(messages: list[dict], *, system: str | None = None,
                 model: str = '기본') -> int | None:
    """보내기 전에 입력 토큰 수를 센다.

    Anthropic API는 요금 없이 세어 준다. OpenAI 호환 API에는 표준 방법이 없어 None을
    돌려준다. 그럴 때는 몇 건을 실제로 보내 Reply.input_tokens로 어림한다.
    """
    if provider() != 'anthropic':
        return None
    sdk = _sdk()
    request = dict(model=_resolve_model(model), messages=messages)
    if system:
        request['system'] = system
    try:
        return _client(60.0, None).messages.count_tokens(**request).input_tokens
    except sdk.APIError as error:
        raise _to_call_error(error, sdk) from error


class Chat:
    """채팅 화면의 대화 하나. 1일차 예제가 프롬프트를 보내고 응답을 읽는 데 쓴다.

    Chat()이 새 채팅이다. say()는 프롬프트를 보내고 응답을 출력한다. 같은 Chat에 이어서
    say() 하면 앞의 질문과 응답을 함께 보내므로 같은 대화가 이어진다. 마지막 응답은 last에,
    지금까지의 대화는 history에 남는다.

    system      시스템 프롬프트. 이 대화의 모든 요청에 함께 보낸다
    model       '소형', '기본', '대형' 또는 실제 모델 이름
    max_tokens  최대 출력 토큰. thinking에 쓰는 토큰도 여기에 들어가므로 넉넉히 둔다
    """

    def __init__(self, *, system: str | None = None, model: str = '기본', max_tokens: int = 4000):
        self.system, self.model, self.max_tokens = system, model, max_tokens
        self.history: list[dict] = []
        self.last: Reply | None = None

    def say(self, prompt: str, *, show: bool = True) -> None:
        """프롬프트를 보내고 응답을 출력한다. 응답 객체가 필요하면 last를 읽는다."""
        reply = ask(prompt, system=self.system, history=self.history, model=self.model,
                    max_tokens=self.max_tokens, timeout=300.0)
        self.last = reply
        if reply.text:
            # 응답이 비어 있으면 이력에 넣지 않는다. 빈 메시지가 든 이력은 다음 요청에서 거부된다
            self.history += [{'role': 'user', 'content': prompt},
                             {'role': 'assistant', 'content': reply.text}]
        if show:
            print(reply.text or '(응답 텍스트가 없습니다)')
            if reply.stop_reason != 'end':
                print(f'[종료 이유: {reply.stop_reason}. 응답이 끝까지 쓰이지 않았습니다]')
