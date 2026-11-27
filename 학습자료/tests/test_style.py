"""원고에 작성규칙의 "피할 표현"이 없는지 검사한다.

검사 패턴은 작성규칙.md 의 "피할 표현" 표 마지막 열에서 읽는다. 규칙을 고치면 검사도 함께 바뀐다.
코드 블록, 표, 그림, "원본과 달라진 점" 절(원본 문장을 인용한다)은 검사하지 않는다.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_patterns():
    text = (ROOT / '작성규칙.md').read_text(encoding='utf-8')
    section = text.split('### 피할 표현')[1].split('\n## ')[0]
    patterns = []
    for line in section.splitlines():
        if not line.startswith('|') or line.startswith('| ---') or line.startswith('| 유형'):
            continue
        # 표의 열은 " | " 로 나뉜다. 패턴 안의 | 와 구분하려고 마지막 열은 백틱 안에서 읽는다
        found = re.search(r'`([^`]+)` \|$', line)
        kind = line.split(' | ')[0].strip('| ')
        patterns.append((kind, re.compile(found.group(1), re.M)))
    return patterns


def prose_of(path):
    """검사할 문단을 (줄 번호, 글)로 돌려준다."""
    text = path.read_text(encoding='utf-8').split('## 원본과 달라진 점')[0]
    text = re.sub(r'<figure>.*?</figure>', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    lines, in_fence = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith(('|', ':::')) or not line.strip():
            continue
        lines.append((number, re.sub(r'`[^`]*`', '`코드`', line)))
    return lines


MANUSCRIPTS = sorted((ROOT / '원고').glob('[0-9][0-9]_*.md'))


def test_patterns_are_loaded():
    assert len(load_patterns()) >= 7


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: path.name)
def test_no_discouraged_expressions(path):
    problems = []
    for number, line in prose_of(path):
        for kind, pattern in load_patterns():
            found = pattern.search(line)
            if found:
                problems.append(f'{path.name}:{number}: [{kind}] "{found.group(0)}" → {line.strip()[:70]}')
    assert not problems, '작성규칙의 피할 표현이 있습니다:\n' + '\n'.join(problems)


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: path.name)
def test_no_discouraged_expressions_in_table_headers(path):
    """표의 머리글도 검사한다. 표의 본문은 원본 인용과 짧은 구가 많아 검사하지 않는다."""
    text = path.read_text(encoding='utf-8').split('## 원본과 달라진 점')[0]
    lines = text.splitlines()
    problems = []
    for number, line in enumerate(lines[:-1], 1):
        if line.startswith('|') and lines[number].startswith('| ---'):
            clean = re.sub(r'`[^`]*`', '`코드`', line)
            for kind, pattern in load_patterns():
                found = pattern.search(clean)
                if found:
                    problems.append(f'{path.name}:{number}: [{kind}] "{found.group(0)}" → {line.strip()[:70]}')
    assert not problems, '표 머리글에 작성규칙의 피할 표현이 있습니다:\n' + '\n'.join(problems)


NOTEBOOK_TEXTS =sorted((ROOT / '노트북').glob('*실습*.ipynb')) + [ROOT / '교재_템플릿' / '준비.md']


@pytest.mark.parametrize('path', NOTEBOOK_TEXTS, ids=lambda path: path.name)
def test_no_discouraged_expressions_in_notebook_text(path):
    """실습 노트북의 설명 셀과 준비 안내에도 같은 규칙을 적용한다. 원고만 검사하면 이쪽의 같은 표현이 남는다."""
    if path.suffix == '.ipynb':
        import nbformat
        chunks = [cell.source for cell in nbformat.read(path, as_version=4).cells if cell.cell_type == 'markdown']
    else:
        chunks = [path.read_text(encoding='utf-8')]
    problems = []
    for chunk in chunks:
        for _, line in prose_lines(chunk):
            clean = re.sub(r'`[^`]*`', '`코드`', line)
            for kind, pattern in load_patterns():
                found = pattern.search(clean)
                if found:
                    problems.append(f'{path.name}: [{kind}] "{found.group(0)}" → {line.strip()[:70]}')
    assert not problems, '작성규칙의 피할 표현이 있습니다:\n' + '\n'.join(problems)


MATERIAL_LINES = ('SL-FAB 반도체', '게시일:', 'title_of[')   # 재료와 임베딩 입력. 바꾸면 모델 입력이 달라진다


def code_lines(text):
    """원고의 파이썬 코드 블록 줄을 (줄 번호, 줄)로 돌려준다. 문서 예시를 담은 다른 코드 블록은 재료이므로 뺀다."""
    lines, in_fence, is_python = [], False, False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            is_python = in_fence and line.strip() == '```python'
            continue
        if in_fence and is_python:
            lines.append((number, line))
    return lines


def dotted(line):
    """출력 문구, 주석, 예외 메시지에 가운뎃점 나열이 있으면 True. 프롬프트 안의 'A·B' 표기와 재료 줄은 제외한다."""
    if any(marker in line for marker in MATERIAL_LINES):
        return False
    return bool(re.search(r" · |'·'|['\"]· | ·['\"]", line))


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: path.name)
def test_no_middle_dot_in_code_output(path):
    """작성규칙 6절의 "가운뎃점 나열 금지"를 코드의 출력 문구와 주석에도 적용한다. 독자는 출력도 읽는다."""
    problems = [f'{path.name}:{number}: {line.strip()[:80]}'
                for number, line in code_lines(path.read_text(encoding='utf-8')) if dotted(line)]
    assert not problems, '코드의 출력 문구나 주석에 가운뎃점 나열이 있습니다. 쉼표로 씁니다:\n' + '\n'.join(problems)


@pytest.mark.parametrize('path', sorted((ROOT / '노트북').glob('*실습*.ipynb')), ids=lambda path: path.name)
def test_no_middle_dot_in_practice_code(path):
    import nbformat
    problems = [line.strip()[:80] for cell in nbformat.read(path, as_version=4).cells if cell.cell_type == 'code'
                for line in cell.source.splitlines() if dotted(line)]
    assert not problems, '실습 노트북 코드의 출력 문구나 주석에 가운뎃점 나열이 있습니다:\n' + '\n'.join(problems)


SPACING_MATERIAL = ('3mm 는', 'equipment 는', 'null 로 둔다', 'SOP-ETCH-007 의 상한', 'SPEC-030 은', 'example.com 으로',
                    '5678 로', 'docx가 아닙니다', '{name} 의 본문', 'PM 이', 'urgent 는')   # 프롬프트, 재료, 테스트 입력
PARTICLE = re.compile(r"[A-Za-z0-9_)\]}%`] (를|을|가|는|은|에서는|에서|에게|에|으로|로|와|과|의|도|만|이다|이면|이므로|이고|"
                      r"이라고|라고|부터|까지|보다|처럼|입니다|이며|다)(?=[\s.,'\")\]:;!?]|$)")
UNIT = re.compile(r"\{[^{}]*\} (건|개|줄|쪽|자|토큰|초|위|행|차원|바이트|회|셀)(?=[\s,.'\")]|$)"
                  r"|,\s*'(건|개|줄|쪽|자|토큰|초|위|행|차원|바이트|회)[,.']")


def spaced(line):
    """주석, 출력 문구, 예외 메시지에서 한글 조사나 단위를 영문, 숫자 뒤에 띄어 쓰면 True. 프롬프트와 재료 줄은 제외한다."""
    if any(marker in line for marker in SPACING_MATERIAL):
        return False
    return bool(PARTICLE.search(line) or UNIT.search(line))


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: path.name)
def test_no_spaced_particle_in_code(path):
    """작성규칙 6절의 띄어쓰기(조사와 단위는 붙여 쓴다)를 코드의 주석과 출력 문구에도 적용한다."""
    problems = [f'{path.name}:{number}: {line.strip()[:80]}'
                for number, line in code_lines(path.read_text(encoding='utf-8')) if spaced(line)]
    assert not problems, '코드의 주석이나 출력 문구에 띄어 쓴 조사나 단위가 있습니다:\n' + '\n'.join(problems)


SHARED_CODE = sorted([*(ROOT / '노트북').glob('*.py'), *(ROOT / '교재_템플릿').glob('*.py'), *(ROOT / 'tools').glob('make_*.py'),
                      *(ROOT / '노트북').glob('코딩도구_실습*/**/*.py')])


@pytest.mark.parametrize('path', SHARED_CODE, ids=lambda path: path.name)
def test_no_spaced_particle_in_shared_code(path):
    problems = [f'{path.name}:{number}: {line.strip()[:80]}'
                for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1) if spaced(line)]
    assert not problems, '주석이나 출력 문구에 띄어 쓴 조사나 단위가 있습니다:\n' + '\n'.join(problems)


def sentences(text):
    text = re.sub(r'`[^`]*`|\[\[|\]\]|\([^)]*\)', '', text)
    return [part.strip() for part in re.split(r'(?<=[다요]\.)\s+', text) if len(part.strip()) > 12]


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: path.name)
def test_gist_does_not_repeat_a_body_sentence(path):
    """요점의 문장과 거의 같은 문장이 그 절의 본문에 또 나오면 실패한다."""
    from difflib import SequenceMatcher
    text = path.read_text(encoding='utf-8').split('## 원본과 달라진 점')[0]
    problems = []
    for section in re.split(r'\n(?=## )', text):
        found = re.search(r':::요점\n(.*?)\n:::\n(.*)', section, flags=re.S)
        if not found:
            continue
        body = '\n'.join(line for _, line in prose_lines(found.group(2)))
        for gist in sentences(found.group(1)):
            for sentence in sentences(body):
                if SequenceMatcher(None, gist, sentence).ratio() > 0.8:
                    problems.append(f'{section.splitlines()[0]}: 요점 "{gist}" ≈ 본문 "{sentence}"')
    assert not problems, '요점과 거의 같은 문장이 본문에 있습니다:\n' + '\n'.join(problems)


def prose_lines(text):
    """글에서 코드 블록, 표, 상자 표시를 뺀 줄을 (줄 번호, 글)로 돌려준다."""
    lines, in_fence = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith(('|', ':::', '<')) or not line.strip():
            continue
        lines.append((number, line))
    return lines


def abbreviations():
    """용어집에서 약어(대문자로 된 용어)와 그 원어(영문 열의 첫 항목)를 읽는다."""
    found = {}
    for line in (ROOT / '용어집.md').read_text(encoding='utf-8').splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) >= 4 and re.fullmatch(r'[A-Z][A-Za-z0-9-]*[A-Z][A-Za-z0-9-]*', cells[0]):
            full = cells[1].split(',')[0].strip()
            if ' ' in full:
                found[cells[0]] = full
    return found


@pytest.mark.parametrize('path', MANUSCRIPTS, ids=lambda path: path.name)
def test_abbreviation_is_spelled_out_first(path):
    """약어는 장에서 처음 나오는 문장에 "약어(원어)"로 쓴다. 제목 줄은 세지 않는다."""
    problems = []
    # 제목 줄과, 다른 장을 이름으로 가리키는 곳(예: 5장 "LLM API")은 세지 않는다
    lines = [(number, re.sub(r'\d+장 "[^"]*"', '', line)) for number, line in prose_of(path) if not line.startswith('#')]
    for short, full in abbreviations().items():
        word = re.compile(r'(?<![A-Za-z])' + re.escape(short) + r'(?![A-Za-z])')
        first = next(((number, line) for number, line in lines if word.search(line)), None)
        if first is None:
            continue
        number, line = first
        expanded = re.search(re.escape(short) + r'(\]\])?\(' + re.escape(full), line, flags=re.I)
        if not expanded:
            problems.append(f'{path.name}:{number}: {short} → 처음 나오는 곳에 "{short}({full})"로 씁니다: {line.strip()[:60]}')
    assert not problems, '\n'.join(problems)
