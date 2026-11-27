# 실습 환경 점검 (8일차 환경 준비, day08-cc 첫 메시지, 7일차 my-agent의 env_check.py와 같은 방식). 사용: python bench/env_check.py
#   모두가 같은 환경에서 시작하도록 Python, 연 폴더, 설정 파일, 도구, DB, 문서, 옆 폴더, 한글 출력을 한 번에 확인합니다
#   이 스크립트가 권한 프롬프트 없이 실행됐다면 실습 폴더 설정(.claude/settings.json의 허용 목록)이 적용된 것입니다
import json, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 실습 폴더(day08-cc)
try:
    sys.stdout.reconfigure(encoding='utf-8')   # Windows에서도 한글이 깨지지 않게 UTF-8로 출력합니다
except Exception:
    pass

checks = []   # (항목, 통과 여부, 확인한 값)

# 1. Python 3.8 이상: 도구 스크립트가 표준 라이브러리만 쓰므로 버전만 맞으면 됩니다
version = sys.version.split()[0]
checks.append(('Python', sys.version_info >= (3, 8), version))

# 2. 연 폴더: Claude Code는 claude를 실행한 폴더에서 명령을 실행하므로 지금 위치가 day08-cc 여야 합니다
folder = os.path.basename(os.getcwd())
checks.append(('연 폴더', folder == 'day08-cc', folder))

# 3. 지시 파일과 설정 파일: CLAUDE.md는 세션마다 읽히고, settings.json이 권한 「수동」과 허용, 차단 목록을 정합니다
settings_file = os.path.join(ROOT, '.claude', 'settings.json')
mode = ''
if os.path.exists(settings_file):
    settings = json.load(open(settings_file, encoding='utf-8'))
    mode = settings.get('permissions', {}).get('defaultMode', '')
claude_md_exists = os.path.exists(os.path.join(ROOT, 'CLAUDE.md'))
checks.append(('CLAUDE.md', claude_md_exists, '있음'))
checks.append(('설정 파일 권한 모드', mode == 'default', mode or '없음'))

# 4. 도구 스크립트: CLAUDE.md 「도구」 절에 적힌 넷이 있어야 합니다
tool_names = ['query_db', 'search_docs', 'calc', 'grade_tilt']
missing_tools = [name for name in tool_names
                 if not os.path.exists(os.path.join(ROOT, 'tools', name + '.py'))]
if missing_tools:
    tools_value = '없음 ' + ', '.join(missing_tools)
else:
    tools_value = ' · '.join(tool_names)
checks.append(('도구 스크립트', not missing_tools, tools_value))

# 5. 생산 DB: 읽기 전용으로 열어 런 수를 셉니다
db_file = os.path.join(ROOT, 'data', 'slfab.db')
try:
    db = sqlite3.connect(f'file:{db_file}?mode=ro', uri=True)
    run_count = db.execute('select count(*) from runs').fetchone()[0]
    db.close()
    checks.append(('생산 DB', run_count > 0, f'런 {run_count}개'))
except Exception as error:
    checks.append(('생산 DB', False, str(error)[:40]))   # 오류 문구는 앞 40자만 보여 줍니다

# 6. 옆 폴더: 예제에서 Skill 원본을 복사해 올 day08-pack과 미션 폴더 my-agent가 같은 day08 폴더 안에 있어야 합니다
side_names = ('day08-pack', 'my-agent')
missing_side = [name for name in side_names
                if not os.path.isdir(os.path.join(ROOT, '..', name))]
if missing_side:
    side_value = '없음 ' + ', '.join(missing_side)
else:
    side_value = 'day08-pack · my-agent'
checks.append(('옆 폴더', not missing_side, side_value))

# 7. 한글 출력: 이 줄이 깨지지 않고 보이면 통과입니다
checks.append(('한글 출력', True, '가나다 챔버 월간 상태 보고서'))

# 8. 항목별 결과와 요약을 출력합니다
for name, passed, value in checks:
    status = '통과' if passed else '확인 필요'
    print(f'{status}  {name} · {value}')
passed_count = sum(passed for _, passed, _ in checks)
summary = f'환경 점검 {passed_count}/{len(checks)}'
if passed_count == len(checks):
    summary += ' · 모두 통과'
else:
    summary += ' · 확인 필요 항목을 강사에게 알려 주세요'
print(summary)
