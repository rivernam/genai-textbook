# 제출 묶음 만들기 · 사용: python bench/pack_submit.py 8   →  day08.zip
#   제출 양식과 미션에서 만들거나 고친 파일만 경로를 살려 묶습니다. data/, rules/, 키는 넣지 않습니다
import glob, os, sys, unicodedata, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from _common import path, utf8_out

utf8_out()
day = (sys.argv[1:] or ['8'])[0]
FILES_BY_DAY = {'7': ['missions/제출_7일차.md', 'CLAUDE.md'],
                '8': ['missions/제출_8일차.md', 'CLAUDE.md', '.claude/settings.json', '.claude/skills/**/*', '.claude/agents/*.md',
                      'answers/*', 'out/*', 'logs/agent_log.jsonl', 'missions/d8m3/*.md', 'share_*.zip']}[day]
zip_path = path(f'day0{day}.zip')
count = 0
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
    for pattern in FILES_BY_DAY:
        for file_path in sorted(glob.glob(path(pattern), recursive=True)):
            if os.path.isdir(file_path) or file_path.endswith('.pyc'):
                continue
            arc_name = unicodedata.normalize('NFC', os.path.relpath(file_path, path()).replace('\\', '/'))
            zip_file.write(file_path, arc_name)
            count += 1
            print('넣음 ·', arc_name)
print(f'묶음 · {os.path.basename(zip_path)} · 파일 {count}개')
