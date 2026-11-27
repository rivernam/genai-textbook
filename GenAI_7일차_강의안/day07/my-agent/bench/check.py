# 미션 검사 스크립트 · 사용: python bench/check.py d8m1
#   검사 기준은 data/checks/<미션>.json에 있습니다(data/는 Claude Code가 직접 읽지 못하게 막혀 있습니다).
#   질문형 미션은 answers/<미션>.md의 「## Q1」 같은 제목 아래 답을 읽어 채점합니다.
#   출력 끝의 「점수 N/M」과 「남은 실패」를 요청별 비교표에 그대로 옮겨 적습니다.
import datetime, glob, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

GRADES = ('OUT', 'A', 'B', 'C')
GRADE_TOKEN = re.compile(r'(?<![A-Za-z0-9-])(OUT|A|B|C)(?![A-Za-z0-9-])')
FORM = ['[정비 문의 답변서]', '1. 문의 요약:', '2. 답변:', '3. 근거 문서:', '4. 안전 주의:', '5. 확인 필요 사항:']
NO_DOC = '문서에서 확인되지 않습니다'
CITE_PATTERN = re.compile(r'\[([A-Z]+-[A-Z]+-\d{3})_(v\d+\.\d+)\]')
PII_PATTERN = re.compile(r'01[016789][- ]?\d{3,4}[- ]?\d{4}|\bS\d{6}\b')


def root_path(*parts):
    return os.path.join(ROOT, *parts)


def read(rel_path):
    hits = sorted(glob.glob(root_path(rel_path)))
    if not hits:
        return None
    return open(hits[0], encoding='utf-8-sig', errors='replace').read()   # 메모장 BOM도 읽습니다


def answers(mission_id):
    text = read(os.path.join('answers', mission_id + '.md'))
    if text is None:
        return None
    by_question, current = {}, None
    for line in text.splitlines():
        match = re.match(r'^#{1,4}\s*(Q\d+)\b', line.strip())
        if match:
            current = match.group(1)
            by_question[current] = []
        elif current:
            by_question[current].append(line)
    return {question: '\n'.join(lines).strip() for question, lines in by_question.items()}


def grade_of(text):
    """답에서 판정 등급 하나를 고른다: 「2. 답변:」 줄 → 「등급」 옆 → 처음 나온 등급 순서."""
    grade_rx = r'(?<![A-Za-z])(OUT|A|B|C)(?![A-Za-z])'
    lines = [line for line in text.splitlines() if line.strip().startswith('2.')] or [text]
    for scope in (lines[0], text):
        match = re.search(grade_rx + r'\s*등급|등급[은는이가:\s*]*' + grade_rx.replace('(OUT', '(?:OUT').replace('|C)', '|C)'), scope)
        if match:
            found = re.findall(grade_rx, match.group(0))
            if found:
                return found[0]
    match = re.search(grade_rx, lines[0])
    return match.group(1) if match else None


def form_ok(text):
    positions = [text.find(header) for header in FORM]
    return all(position >= 0 for position in positions) and positions == sorted(positions)


def run_tool(command):
    try:
        proc = subprocess.run([sys.executable] + command, cwd=ROOT, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=30)
    except Exception as e:
        return None, f'실행 실패 {e}'
    lines = [line for line in proc.stdout.strip().splitlines() if line.strip()]
    if len(lines) != 1:
        return None, f'JSON 한 줄이 아님 (출력 {len(lines)}줄)' + (f' · 오류 {proc.stderr.strip().splitlines()[-1][:60]}' if proc.stderr.strip() else '')
    try:
        return json.loads(lines[0]), ''
    except Exception:
        return None, 'JSON 이 아님: ' + lines[0][:60]


def check_tool(check):
    if not os.path.exists(root_path(check['cmd'][0])):
        return False, f"{check['cmd'][0]} 없음"
    result, error = run_tool(check['cmd'])
    if result is None:
        return False, error
    if check.get('expect_error'):
        return ('error' in result), ('error 칸 없음: ' + json.dumps(result, ensure_ascii=False)[:60]) if 'error' not in result else ''
    for key in check.get('expect_keys', []):
        if key not in result:
            return False, f'{key} 칸 없음 (받은 칸: {", ".join(result)})'
    for key, expected in check.get('expect', {}).items():
        if result.get(key) != expected:
            return False, f'{key} 받은 값 {result.get(key)!r}, 기대 {expected!r}'
    return True, ''


def check_answer(check, answers_by_q):
    if answers_by_q is None:
        return False, '답 파일 없음'
    text = answers_by_q.get(check['q'])
    if not text:
        return False, f"{check['q']} 답 없음"
    reasons = []
    if 'grade' in check:
        found = grade_of(text)
        if found != check['grade']:
            reasons.append(f'등급 {found or "없음"}, 기대 {check["grade"]}')
    for word in check.get('must', []):
        if word not in text:
            reasons.append(f'「{word}」 없음')
    for word in check.get('must_not', []):
        if word in text:
            reasons.append(f'「{word}」 있음')
    cites = set(f'{doc_id}_{version}' for doc_id, version in CITE_PATTERN.findall(text))
    if check.get('cite'):
        matched = [cite for cite in cites if cite.split('_')[0] in check['cite'] or cite in check['cite']]
        if not matched:
            reasons.append('근거 인용 [문서번호_판] 없음' if not cites else f'인용 {", ".join(sorted(cites))} 가 근거 문서가 아님')
    for banned in check.get('cite_not', []):
        if banned in cites:
            reasons.append(f'{banned} 인용')
    if check.get('say_no') and NO_DOC not in text:
        reasons.append(f'「{NO_DOC}」 없음')
    if check.get('form') and not form_ok(text):
        reasons.append('답변서 여섯 줄 양식 아님')
    for pattern in check.get('re', []):
        if not re.search(pattern, text, re.M):
            reasons.append(check.get('why', f'{pattern} 못 찾음'))
    for keyword, pattern in check.get('line_re', {}).items():
        lines = [line for line in text.splitlines() if keyword in line]
        if not any(re.search(pattern, line) for line in lines):
            reasons.append(check.get('why', f'{keyword} 줄에 {pattern} 없음'))
    if check.get('pii'):
        if PII_PATTERN.search(text) or any(name in text for name in check.get('names', [])):
            reasons.append('개인정보 남음')
    return (not reasons), ' · '.join(reasons)


def grades_in(text, expected):
    reasons = []
    for bond_id, grade in expected.items():
        lines = [line for line in text.splitlines() if bond_id in line]
        if not lines:
            reasons.append(f'{bond_id} 줄 없음')
            continue
        found_grade = None
        for line in lines:
            tokens = GRADE_TOKEN.findall(line[line.find(bond_id) + len(bond_id):])
            if tokens:
                found_grade = tokens[0]
                break
        if found_grade != grade:
            reasons.append(f'{bond_id} 등급 {found_grade or "없음"}, 기대 {grade}')
    return (not reasons), ' · '.join(reasons)


def check_grades(check, answers_by_q):
    if answers_by_q is None:
        return False, '답 파일 없음'
    text = answers_by_q.get(check['q'])
    if not text:
        return False, f"{check['q']} 답 없음"
    return grades_in(text, check['grades'])


def check_filegrades(check):
    text = read(check['path'])
    if text is None:
        return False, f"{check['path']} 없음"
    return grades_in(text, check['grades'])


def check_zip(check):
    import zipfile
    hits = sorted(glob.glob(root_path(check['path'])))
    if not hits:
        return False, f"{check['path']} 없음"
    names = zipfile.ZipFile(hits[-1]).namelist()
    if not any(name.startswith(check['has']) for name in names):
        return False, f"zip 안에 {check['has']} 경로 없음"
    bad_names = [name for name in names if any(banned in name for banned in check.get('has_not', []))]
    if bad_names:
        return False, '넣으면 안 되는 파일: ' + ', '.join(bad_names[:3])
    return True, ''


def check_file(check):
    text = read(check['path'])
    if text is None:
        return False, f"{check['path']} 없음"
    for pattern in check.get('re', []):
        if not re.search(pattern, text, re.M | re.S):
            return False, check.get('why', f'{pattern} 못 찾음')
    for pattern in check.get('re_not', []):
        if re.search(pattern, text, re.M | re.S):
            return False, check.get('why_not', f'{pattern} 있음')
    return True, ''


def main():
    if len(sys.argv) < 2:
        print('사용: python bench/check.py <미션>   예: python bench/check.py d8m1')
        return
    mission_id = sys.argv[1]
    spec_path = root_path('data', 'checks', mission_id + '.json')
    if not os.path.exists(spec_path):
        print(f'{mission_id} 검사 기준이 없습니다. 미션 이름을 확인하세요(d8m1 · d8m2 · d8m3).')
        return
    spec = json.load(open(spec_path, encoding='utf-8'))
    answers_by_q = answers(mission_id) if any(check['kind'] in ('answer', 'grades') for check in spec['checks']) else None
    now_text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"[검사] {spec['title']} · {now_text}")
    passed, fails = 0, []
    for check in spec['checks']:
        checker = {'tool': check_tool, 'answer': lambda check: check_answer(check, answers_by_q), 'file': check_file,
                   'grades': lambda check: check_grades(check, answers_by_q), 'filegrades': check_filegrades, 'zip': check_zip}[check['kind']]
        ok, reason = checker(check)
        passed += ok
        if not ok:
            fails.append(check['label'])
        print(f"  {'통과' if ok else '실패'}  {check['label']}" + ('' if ok else f'   ({reason})'))
    total = len(spec['checks'])
    print(f'점수 {passed}/{total}')
    print('남은 실패: ' + (', '.join(fails) if fails else '없음'))
    os.makedirs(root_path('answers'), exist_ok=True)
    with open(root_path('answers', 'check_log.txt'), 'a', encoding='utf-8') as log_file:
        log_file.write(f"{now_text}\t{mission_id}\t{passed}/{total}\t{', '.join(fails) or '없음'}\n")


if __name__ == '__main__':
    main()
