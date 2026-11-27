# 생산 DB 조회 도구 (7일차 query_db와 같음, 읽기 전용)
# 사용: python tools/query_db.py "SELECT ..."                      (예제, SL-FAB 전공정 DB)
import sqlite3, sys
from _common import show, path

MAX_ROWS = 50   # 한 번에 보여 주는 행 수
db_name = 'slfab.db'

# 1. 명령줄 인자를 SQL 한 문장으로 모으고, SELECT 계열만 허용합니다
sql = ' '.join(sys.argv[1:]).strip().rstrip(';')
if not sql.lower().startswith(('select', 'with')):
    show({'error': 'SELECT 문만 실행할 수 있습니다'})
    sys.exit(0)

# 2. DB를 읽기 전용으로 열어 조회하고, 결과를 JSON 한 줄로 냅니다
db = sqlite3.connect(f'file:{path("data", db_name)}?mode=ro', uri=True)
try:
    cursor = db.execute(sql)
    rows = cursor.fetchmany(MAX_ROWS + 1)   # 한 행을 더 받아 50행이 넘는지 확인합니다
    columns = [name for name, *_ in cursor.description]
    out = {'db': db_name, 'columns': columns, 'rows': [list(row) for row in rows[:MAX_ROWS]]}
    if len(rows) > MAX_ROWS:
        out['note'] = '50행까지만 보여 줍니다. 집계(COUNT · SUM)나 WHERE 로 줄여 주세요'
    show(out)
except Exception as error:
    show({'error': str(error)})
finally:
    db.close()
