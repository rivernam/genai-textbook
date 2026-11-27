# 생산 DB 조회 도구 (읽기 전용), 노트북의 query_db와 같습니다
# 사용: python tools/query_db.py "SELECT ..."    SL-PKG 후공정 조립 DB(data/pkg.db)
import sqlite3, sys
from _common import show, path

args = sys.argv[1:]
db = 'pkg.db'
if args[:1] == ['--db']:
    db = {'mission': 'pkg.db'}.get(args[1], args[1])
    args = args[2:]
sql = ' '.join(args).strip().rstrip(';')
if not sql.lower().startswith(('select', 'with')):       # 가드레일, 조회 말고는 실행하지 않습니다
    show({'error': 'SELECT 문만 실행할 수 있습니다'})
    sys.exit(0)
con = sqlite3.connect(f'file:{path("data", db)}?mode=ro', uri=True)   # 파일도 읽기 전용으로 엽니다
try:
    cur = con.execute(sql)
    rows = cur.fetchmany(51)
    out = {'db': db, 'columns': [d[0] for d in cur.description], 'rows': [list(r) for r in rows[:50]]}
    if len(rows) > 50:
        out['note'] = '50행까지만 보여 줍니다. 집계(COUNT · SUM)나 WHERE 로 줄여 주세요'
    show(out)
except Exception as e:
    show({'error': str(e)})
finally:
    con.close()
