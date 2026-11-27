# 차단 훅 (예제 2-3 단계 4, 5, settings.json의 PreToolUse 훅이 도구를 실행하기 직전에 호출합니다)
#   rules/, data/를 고치거나 지우려는 실행을 권한 프롬프트보다 먼저 막습니다
#   deny 규칙은 Claude의 파일 도구와 Claude Code가 알아보는 셸 파일 명령까지만 막고,
#   python -c처럼 스크립트가 직접 파일을 여는 실행은 막지 못합니다. 이 훅은 명령 글자를 직접 읽어 그 빈틈을 막습니다
#   종료 코드 2 = 실행 차단, 표준 오류의 글이 Claude에게 이유로 전달됩니다
import json, re, sys

# 경로 조각 rules 또는 data가 단어로 들어 있는지 봅니다(앞뒤가 경로 구분자, 공백, 따옴표, 괄호)
GUARD = re.compile(r'(^|[\\/\s"\'(])(rules|data)([\\/\s"\')]|$)', re.I)
# 허용 목록의 도구 스크립트(python tools/…, python bench/…)로 시작하는 명령
TOOL_CALL = re.compile(r'\s*(python|py|python3)\s+(tools|bench)[\\/]')
FILE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
SHELL_TOOLS = ('Bash', 'PowerShell')


def block(message):
    """이유를 표준 오류에 적고 종료 코드 2로 실행을 막습니다."""
    sys.stderr.write(message + '\n')
    sys.exit(2)


# 1. Claude Code가 표준 입력으로 넘겨 준 도구 실행 정보를 읽습니다(Windows 기본 cp949 대신 UTF-8)
#    읽다가 오류가 나면 종료 코드 1로 끝나 막지 못하고 지나가므로, 읽지 못한 실행도 막습니다
try:
    event = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace'))
    tool = event.get('tool_name') or ''
    tool_input = event.get('tool_input') or {}
except Exception as error:
    block(f'차단 훅: 도구 실행 정보를 읽지 못해 이번 실행을 막습니다({type(error).__name__}).')

# 2. 파일 도구: 고칠 파일 경로가 rules/, data/ 안이면 막습니다
if tool in FILE_TOOLS:
    target = str(tool_input.get('file_path') or tool_input.get('notebook_path') or '')
    if GUARD.search(target.replace('\\', '/')):
        block(f'차단 훅: {target} 는 읽기 전용 폴더(rules/ · data/)의 파일이라 고칠 수 없습니다. '
              '기준표를 바꿔야 하면 담당자에게 요청하세요.')

# 3. 셸 도구: 명령 글자에 rules, data가 있으면 막되, 허용 목록의 도구 스크립트 실행은 그대로 둡니다
if tool in SHELL_TOOLS:
    command = str(tool_input.get('command') or '')
    if GUARD.search(command) and not TOOL_CALL.match(command):
        block('차단 훅: rules/ · data/ 를 건드리는 셸 명령은 실행하지 않습니다. 조회는 tools/ 의 도구로만 합니다.')

sys.exit(0)
