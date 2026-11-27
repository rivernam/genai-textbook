# 공유 묶음 만들기. 사용: python bench/pack_share.py <Skill 이름> [서브에이전트 이름 ...]
#   .claude/skills/<이름>/과 .claude/agents/<이름>.md를 zip 안에서도 같은 경로로 묶습니다
#   받은 사람은 자기 day08-cc 폴더에서 python -m zipfile -e share_<이름>.zip . 로 풀면 그 자리에 들어갑니다
#   settings.json, data/, 키는 넣지 않습니다
import os, sys, unicodedata, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from _common import path, utf8_out

utf8_out()

# 1. 인자 확인
if len(sys.argv) < 2:
    sys.exit('사용법: python bench/pack_share.py <Skill 이름> [서브에이전트 이름 ...]')
skill = sys.argv[1]
agents = sys.argv[2:]

# 2. 묶을 파일 모으기: Skill 폴더 안 파일 전부(숨김 파일, .pyc 제외)와 서브에이전트 문서
skill_dir = path('.claude', 'skills', skill)
items = []
for folder, _, files in os.walk(skill_dir):
    for name in files:
        if name.startswith('.') or name.endswith('.pyc'):
            continue
        items.append(os.path.join(folder, name))
for agent in agents:
    items.append(path('.claude', 'agents', agent + '.md'))

# 3. 없는 파일 확인: 모은 파일이 하나도 없으면 Skill 폴더 자체를 없는 것으로 알립니다
missing = [item for item in items if not os.path.exists(item)]
if not items:
    missing = [skill_dir]
if missing:
    missing_names = ', '.join(os.path.relpath(item, path()) for item in missing)
    sys.exit('없는 파일: ' + missing_names)

# 4. zip으로 묶기: zip 안 경로는 / 구분자로 통일하고 한글 파일 이름은 NFC로 맞춥니다
out = path(f'share_{skill}.zip')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
    for item in items:
        rel = os.path.relpath(item, path()).replace('\\', '/')
        arc = unicodedata.normalize('NFC', rel)
        archive.write(item, arc)
        print('넣음 ·', arc)
print('묶음 ·', os.path.basename(out))
