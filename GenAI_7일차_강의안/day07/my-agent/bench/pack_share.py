# 공유 묶음 만들기 · 사용: python bench/pack_share.py <Skill 이름> [서브에이전트 이름 ...]
#   .claude/skills/<이름>/과 .claude/agents/<이름>.md를 zip 안에서도 같은 경로로 묶습니다
#   받은 사람은 자기 my-agent 폴더에서 python -m zipfile -e share_<이름>.zip . 로 풀면 그 자리에 들어갑니다
#   settings.json, data/, 키는 넣지 않습니다
import os, sys, unicodedata, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from _common import path, utf8_out

utf8_out()
if len(sys.argv) < 2:
    sys.exit('사용법: python bench/pack_share.py <Skill 이름> [서브에이전트 이름 ...]')
skill, agents = sys.argv[1], sys.argv[2:]
items = []
for folder, _, files in os.walk(path('.claude', 'skills', skill)):
    for file_name in files:
        if file_name.startswith('.') or file_name.endswith('.pyc'):
            continue
        items.append(os.path.join(folder, file_name))
items += [path('.claude', 'agents', agent + '.md') for agent in agents]
missing = [file_path for file_path in items if not os.path.exists(file_path)] or ([] if items else [path('.claude', 'skills', skill)])
if missing:
    sys.exit('없는 파일: ' + ', '.join(os.path.relpath(file_path, path()) for file_path in missing))
zip_path = path(f'share_{skill}.zip')
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
    for file_path in items:
        arc_name = unicodedata.normalize('NFC', os.path.relpath(file_path, path()).replace('\\', '/'))
        zip_file.write(file_path, arc_name)
        print('넣음 ·', arc_name)
print('묶음 ·', os.path.basename(zip_path))
