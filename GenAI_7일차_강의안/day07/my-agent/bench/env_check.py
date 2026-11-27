# 실습 환경 점검 (7일차 Claude Code CLI, 첫 메시지) · 사용: python bench/env_check.py
#   모두가 같은 환경에서 시작하도록 Python, 연 폴더, 설정 파일, 도구, DB, 문서, 한글 출력을 한 번에 확인합니다
#   이 스크립트가 권한 카드 없이 실행됐다면 실습 폴더 설정(.claude/settings.json의 허용 목록)이 적용된 것입니다
import json, os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 실습 폴더(my-agent)
try:
    sys.stdout.reconfigure(encoding='utf-8')   # Windows에서도 한글이 깨지지 않게 UTF-8로 출력합니다
except Exception:
    pass

checks = []   # (항목, 통과 여부, 확인한 값)

# 1. Python 3.8 이상 · 도구 스크립트가 표준 라이브러리만 쓰므로 버전만 맞으면 됩니다
version = sys.version.split()[0]
checks.append(('Python', sys.version_info >= (3, 8), version))

# 2. 연 폴더 · Claude Code는 claude를 실행한 폴더에서 명령을 실행하므로 지금 위치가 my-agent여야 합니다
folder = os.path.basename(os.getcwd())
checks.append(('연 폴더', folder == 'my-agent', folder))

# 3. 지시 파일과 설정 파일 · CLAUDE.md는 세션마다 읽히고, settings.json이 권한 「수동」과 허용 목록, 차단 목록을 정합니다
settings_file = os.path.join(ROOT, '.claude', 'settings.json')
mode = ''
if os.path.exists(settings_file):
    mode = json.load(open(settings_file, encoding='utf-8')).get('permissions', {}).get('defaultMode', '')
checks.append(('CLAUDE.md', os.path.exists(os.path.join(ROOT, 'CLAUDE.md')), '있음'))
checks.append(('설정 파일 권한 모드', mode == 'default', mode or '없음'))

# 4. 도구 스크립트 · CLAUDE.md 「도구」 절에 적힌 셋이 있어야 합니다
tool_names = ['query_db', 'search_rag', 'calc']
missing = [name for name in tool_names if not os.path.exists(os.path.join(ROOT, 'tools', name + '.py'))]
checks.append(('도구 스크립트', not missing, '없음 ' + ', '.join(missing) if missing else ' · '.join(tool_names)))

# 5. 생산 DB · 읽기 전용으로 열어 스트립 수를 셉니다
try:
    connection = sqlite3.connect(f"file:{os.path.join(ROOT, 'data', 'pkg.db')}?mode=ro", uri=True)
    strip_count = connection.execute('select count(*) from strips').fetchone()[0]
    connection.close()
    checks.append(('생산 DB', strip_count > 0, f'스트립 {strip_count}개'))
except Exception as error:
    checks.append(('생산 DB', False, str(error)[:40]))

# 6. 설비 문서 · 검색 도구가 읽는 문서 23건
docs_dir = os.path.join(ROOT, 'data', 'docs')
doc_count = len([name for name in os.listdir(docs_dir) if name.endswith('.md')]) if os.path.isdir(docs_dir) else 0
checks.append(('설비 문서', doc_count == 23, f'{doc_count}건'))

# 7. 한글 출력 · 이 줄이 깨지지 않고 보이면 통과입니다
checks.append(('한글 출력', True, '가나다 정비 문의 답변서'))

for name, passed, value in checks:
    print(f"{'통과' if passed else '확인 필요'}  {name} · {value}")
passed_count = sum(passed for _, passed, _ in checks)
print(f'환경 점검 {passed_count}/{len(checks)}' + (' · 모두 통과' if passed_count == len(checks) else ' · 확인 필요 항목을 강사에게 알려 주세요'))
