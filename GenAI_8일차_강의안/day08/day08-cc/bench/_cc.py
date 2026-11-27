# 측정 스크립트 공용. claude를 헤드리스로 한 번 실행하고(stream-json) 도구 줄, 토큰, 끝난 이유를 돌려줍니다
import json, os, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from _common import path, utf8_out

utf8_out()
CLAUDE = shutil.which('claude') or sys.exit(
    'claude 명령을 찾지 못했습니다. 새 PowerShell 창에서 claude --version 을 먼저 확인해 주세요')
TOOLS = ['PowerShell(python tools/*)', 'Bash(python tools/*)',
         'Read', 'Grep', 'Glob', 'Write', 'Edit', 'Skill', 'Agent']
TOKEN_KEYS = ('input_tokens', 'cache_read_input_tokens',   # 토큰 수, 네 가지를 모두 더합니다
              'cache_creation_input_tokens', 'output_tokens')


def clean_copy(no_skills=False):
    # 측정용 임시 사본, 미션 문서, 카드, 결과, 제출물처럼 답의 단서가 든 폴더를 빼고 복사합니다
    copy_dir = os.path.join(tempfile.mkdtemp(prefix='day08-bench-'), 'day08-cc')
    excluded = ('missions', 'results', 'out', 'bench', 'logs', 'share_*.zip', '__pycache__')
    shutil.copytree(path(), copy_dir, ignore=shutil.ignore_patterns(*excluded))
    if no_skills:   # 장착 전, Skill 폴더를 통째로 뺍니다(파일을 직접 읽어 가지 못하게)
        skills_dir = os.path.join(copy_dir, '.claude', 'skills')
        shutil.rmtree(skills_dir, ignore_errors=True)
        os.makedirs(skills_dir)
    return copy_dir


def _tool_calls(events):
    """assistant 이벤트에서 도구 호출(tool_use)만 골라 도구, 대상, 서브에이전트 여부 줄로 돌려줍니다."""
    calls = []
    for event in events:
        if event.get('type') != 'assistant':
            continue
        is_subagent = event.get('parent_tool_use_id') is not None   # Agent 안에서 부른 호출이면 True
        for block in event['message']['content']:
            if block.get('type') != 'tool_use':
                continue
            tool_input = block['input']
            what = (tool_input.get('skill') or tool_input.get('subagent_type')
                    or tool_input.get('command') or tool_input.get('file_path') or '')
            calls.append({'tool': block['name'], 'what': str(what)[:80], 'sub': is_subagent})   # 80자까지
    return calls


def run(prompt, extra=(), max_turns=None, cwd=None):
    # 1. 헤드리스(-p) 실행 명령줄: 허용 도구는 TOOLS에 extra를 더합니다
    command = [CLAUDE, '-p', prompt, '--setting-sources', 'project', '--model', 'sonnet',
               '--output-format', 'stream-json', '--verbose', '--allowedTools', *TOOLS, *extra]
    if max_turns:
        command += ['--max-turns', str(max_turns)]
    # 2. 실행하고(최대 1800초 = 30분) stream-json 출력을 한 줄에 이벤트 하나씩 읽습니다
    started = time.time()
    proc = subprocess.run(command, cwd=cwd or path(), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL, timeout=1800)
    events = []
    for line in proc.stdout.splitlines():
        if line.strip().startswith('{'):
            events.append(json.loads(line))
    # 3. 마지막 result 이벤트에 답, 턴 수, 토큰, 끝난 이유가 있습니다
    result = next((event for event in reversed(events) if event.get('type') == 'result'), {})
    usage = result.get('usage', {})
    tokens = sum(usage.get(key, 0) for key in TOKEN_KEYS)
    return {'reply': result.get('result') or '', 'calls': _tool_calls(events),
            'turns': result.get('num_turns'), 'tokens': tokens, 'stop': result.get('subtype'),
            'sec': round(time.time() - started, 1), 'cost_usd': result.get('total_cost_usd')}


def save(name, obj):
    os.makedirs(path('results'), exist_ok=True)
    result_file = path('results', name)
    with open(result_file, 'w', encoding='utf-8') as out:
        json.dump(obj, out, ensure_ascii=False, indent=1)
    return os.path.relpath(result_file, path()).replace('\\', '/')
