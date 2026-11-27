# 공유 전 Skill 점검 (예제 3-4). 사용: python tools/scan_skill.py inbox/weekly-summary-helper
#   공식 문서의 점검 목록 가운데 글자 패턴으로 찾을 수 있는 항목만 봅니다. 걸린 자리는 사람이 직접 읽습니다
import glob, os, re, sys
from _common import show

# 점검 항목 이름 → 걸리는 글자 패턴(정규식)
CHECKS = {'키': r'sk-ant-|api[_-]?key\s*=', '외부 주소': r'https?://|requests\.|urllib|curl ',
          '상위 경로': r'\.\./', '개인정보': r'\d{3}-\d{4}-\d{4}|사번\s*\d'}
EXECUTABLE_EXTENSIONS = ('.py', '.sh', '.js', '.ps1', '.bat')

for folder in sys.argv[1:]:
    found = {}      # 항목 이름 → 걸린 파일 목록(폴더 기준 상대 경로)
    # 1. 하위 폴더까지 모든 파일을 이름순으로 봅니다
    for file_path in sorted(glob.glob(os.path.join(folder, '**', '*'), recursive=True)):
        if os.path.isdir(file_path):
            continue
        rel = os.path.relpath(file_path, folder).replace('\\', '/')
        # 2. 실행 파일은 확장자로, 나머지 항목은 본문 글자 패턴으로 찾습니다
        if file_path.endswith(EXECUTABLE_EXTENSIONS):
            found.setdefault('실행 파일', []).append(rel)
        text = open(file_path, encoding='utf-8', errors='ignore').read()
        for name, pattern in CHECKS.items():
            if re.search(pattern, text):
                found.setdefault(name, []).append(rel)
    # 3. 폴더마다 결과를 JSON 한 줄로 냅니다
    show({'folder': folder.replace('\\', '/'), '걸린 항목': found or '없음'})
