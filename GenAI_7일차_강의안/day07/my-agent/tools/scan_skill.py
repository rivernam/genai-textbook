# 공유 전 Skill 점검 (예제 3-4) · 사용: python tools/scan_skill.py inbox/weekly-summary-helper
#   공식 문서의 점검 목록 가운데 글자 패턴으로 찾을 수 있는 항목만 봅니다. 걸린 자리는 사람이 직접 읽습니다
import glob, os, re, sys
from _common import show

CHECKS = {'키': r'sk-ant-|api[_-]?key\s*=', '외부 주소': r'https?://|requests\.|urllib|curl ',
          '상위 경로': r'\.\./', '개인정보': r'\d{3}-\d{4}-\d{4}|사번\s*\d'}
for folder in sys.argv[1:]:
    found = {}
    for file_path in sorted(glob.glob(os.path.join(folder, '**', '*'), recursive=True)):
        if os.path.isdir(file_path):
            continue
        rel_path = os.path.relpath(file_path, folder).replace('\\', '/')
        if file_path.endswith(('.py', '.sh', '.js', '.ps1', '.bat')):
            found.setdefault('실행 파일', []).append(rel_path)
        content = open(file_path, encoding='utf-8', errors='ignore').read()
        for check_name, pattern in CHECKS.items():
            if re.search(pattern, content):
                found.setdefault(check_name, []).append(rel_path)
    show({'folder': folder.replace('\\', '/'), '걸린 항목': found or '없음'})
