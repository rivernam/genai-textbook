"""원고(Markdown)를 교재(HTML)로 바꾼다.

사용법: python build.py
입력:  원고/NN_장제목.md (장마다 한 파일. 00은 "시작하기 전에"), 용어집.md, 작업/실행결과/*.ipynb
출력:  교재/index.html, 교재/NN_장제목.html  (CSS, JS 를 파일 안에 모두 넣어 외부 연결 없이 열린다)
       노트북/NN_장제목.ipynb               (장 노트북. 준비, 예제, 실습 빈칸 셀. 공유한다)
       노트북/프로젝트_K.ipynb              (관통 프로젝트 K단계. 공유한다)
       작업/풀이/<노트북 이름>_풀이.ipynb   (빈칸 대신 풀이를 넣은 검증용 노트북. 공유하지 않는다)

예제와 풀이의 실행 결과는 원고에 적지 않는다. 풀이 노트북을 실행한 사본(tools/run_nb.py 가
작업/실행결과/ 에 만든다)에서 가져와 교재와 장 노트북에 넣는다. 원고의 코드를 고친 뒤 다시
실행하지 않았으면 그 셀의 결과는 싣지 않고 알려 준다.

순서:  python build.py  →  python tools/run_nb.py <풀이 노트북>  →  python build.py

원고에서 쓰는 추가 문법
  [[용어]]                    용어집 정의가 뜨는 낱말
  :::예제 1-1 제목 ... :::    예제 상자. 안의 ```python 블록은 장 노트북의 코드 셀이 되고,
                              교재에서는 코드 아래에 실행 결과가 자동으로 붙는다
  :::실습 1-2 제목 ... :::    개념 확인 실습 상자. ```python 블록은 장 노트북의 빈칸 셀이 된다
  :::실습 P3 제목 ... :::     관통 프로젝트 3단계 상자. 노트북은 프로젝트_3.ipynb
  :::풀이 ... :::             실습 상자 안의 접히는 풀이. ```python 블록 아래에 실행 결과가 붙는다
  <!-- 실행 위치: 폴더 -->    노트북 없이 폴더에서 하는 장. 예제, 실습 상자 머리글에 폴더 이름을 적는다
  :::탭 이름 ... :::          나란히 전환되는 탭. 이어서 쓰면 한 묶음이 된다
  :::결과 ... :::             실행 결과
  :::정답 ... :::             접히는 정답
  :::힌트 ... :::             접히는 힌트
  :::주의 ... :::  :::보충 ... :::   강조 상자
  :::요점 ... :::             절 첫머리의 요점
"""
import html
import re
import sys
from pathlib import Path

import markdown
import nbformat
from pygments.formatters import HtmlFormatter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'tools'))
import learn_nb  # noqa: E402
TEMPLATES = HERE / '교재_템플릿'

SETTINGS = {
    'title': '생성형 AI 교재',
    # 모든 쪽 하단에 들어가는 문구. 보안 등급이나 배포 범위 문구가 필요하면 여기에 더한다.
    'footer': 'GenAI Intensive 강의(삼성전자 DS 부문 교육)의 주제를 바탕으로 새로 쓴 교재입니다.',
}

# 차례에 보이는 부와 장 번호. 설계서 4.1절의 목차와 같게 둔다. 00은 부에 속하지 않는 "시작하기 전에"다.
PARTS = [
    ('1부 LLM의 원리', [1, 2, 3]),
    ('2부 LLM을 쓰는 방법', [4, 5, 6]),
    ('3부 검색과 RAG', [7, 8, 9, 10]),
    ('4부 모델 바꾸기', [11, 12]),
    ('5부 에이전트', [13, 14]),
    ('6부 운영', [15]),
]

SIMPLE_BLOCKS = {
    '결과': '<div class="result" markdown="1">',
    '정답': '<details class="answer" markdown="1">\n<summary>정답 보기</summary>',
    '힌트': '<details class="answer" markdown="1">\n<summary>힌트 보기</summary>',
    '풀이': '<details class="answer" markdown="1">\n<summary>풀이 보기</summary>',
    '주의': '<aside class="callout warn" markdown="1">',
    '보충': '<aside class="callout more" markdown="1">',
    '요점': '<div class="gist" markdown="1">',
}
CLOSERS = {'요점': '</div>', '결과': '</div>', '정답': '</details>', '힌트': '</details>', '풀이': '</details>', '주의': '</aside>', '보충': '</aside>',
           '탭': '</div>', '예제': '</section>', '실습': '</section>'}


class BuildError(Exception):
    pass


def fail(path, line, message):
    raise BuildError(f'{path.name}:{line}: {message}')


def slug(text):
    text = re.sub(r'`|\[\[|\]\]', '', text).strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'\s+', '-', text)


def read_glossary(path):
    """용어집.md의 표를 {용어: 정의}로 읽는다."""
    terms = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) >= 4 and cells[0] not in ('용어', '') and not set(cells[0]) <= set('-: '):
            terms[cells[0]] = cells[3]
    return terms


def replace_terms(line, terms, path, number):
    """인라인 코드 밖의 [[용어]]를 정의가 달린 낱말로 바꾼다."""
    def swap(match):
        name = match.group(1)
        if name not in terms:
            fail(path, number, f'용어집에 없는 용어입니다: {name}')
        return (f'<span class="term" tabindex="0" data-def="{html.escape(terms[name], quote=True)}">'
                f'{html.escape(name)}</span>')

    parts = re.split(r'(`[^`]*`)', line)
    return ''.join(part if part.startswith('`') else re.sub(r'\[\[([^\]]+)\]\]', swap, part)
                   for part in parts)


def box_where(kind, code, path):
    """예제·실습 상자 머리글에 적는 실행 위치.

    노트북 없이 폴더에서 하는 파트는 원고에 "<!-- 실행 위치: 폴더 이름 -->" 을 적는다.
    """
    folder = re.search(r'<!-- 실행 위치: (.+?) -->', Path(path).read_text(encoding='utf-8'))
    if folder:
        return f'폴더 <code>{html.escape(folder.group(1))}</code>'
    if kind == '실습' and code.startswith('P'):
        return f'노트북 <code>{learn_nb.project_name(code[1:])}</code>'
    return f'노트북 <code>{learn_nb.notebook_name(path)}</code>의 <code>{kind} {html.escape(code)}</code>'


def open_block(kind, rest, path, number):
    if kind in SIMPLE_BLOCKS:
        return SIMPLE_BLOCKS[kind]
    if kind == '탭':
        if not rest:
            fail(path, number, ':::탭 뒤에 탭 이름을 적어 주세요')
        return f'<div class="tab" data-tab="{html.escape(rest, quote=True)}" markdown="1">'
    if kind in ('예제', '실습'):
        code, _, title = rest.partition(' ')
        if not code:
            fail(path, number, f':::{kind} 뒤에 번호를 적어 주세요')
        css = 'example' if kind == '예제' else 'practice'
        return (f'<section class="box {css}" id="{kind}-{code}" markdown="1">\n'
                f'<header><span class="box-no">{kind} {html.escape(code)}</span>'
                f'<span class="box-title">{html.escape(title)}</span>'
                f'<span class="box-where">{box_where(kind, code, path)}</span></header>')
    fail(path, number, f'알 수 없는 상자 종류입니다: :::{kind}')


def chapter_number(path):
    """원고 파일 이름 앞의 두 자리 장 번호('01'). 없으면 빈 문자열."""
    found = re.match(r'(\d{2})_', Path(path).name)
    return found.group(1) if found else ''


FOLD_AFTER = 30      # 실행 결과가 이보다 5줄 넘게 길면 앞부분만 보이고 나머지는 접는다


def result_markup(output):
    """실행 결과 상자. 출력에 ```가 들어 있어도 깨지지 않게 ~~~~ 로 감싼다.

    모델의 응답을 그대로 출력하는 예제는 결과가 길다. 긴 결과는 앞 FOLD_AFTER 줄만 보이고
    나머지는 펼쳐 보게 한다. 학습 노트북에는 전체가 들어간다.
    """
    lines = output.splitlines()
    if len(lines) <= FOLD_AFTER + 5:
        return ['', '<div class="result" markdown="1">', '', '~~~~', output, '~~~~', '', '</div>', '']
    head, rest = '\n'.join(lines[:FOLD_AFTER]), '\n'.join(lines[FOLD_AFTER:])
    return ['', '<div class="result" markdown="1">', '', '~~~~', head, '~~~~', '',
            '<details class="more-result" markdown="1">',
            f'<summary>나머지 {len(lines) - FOLD_AFTER}줄 보기</summary>', '', '~~~~', rest, '~~~~', '',
            '</details>', '', '</div>', '']


def preprocess(text, terms, path, outputs=None, missing=None):
    """추가 문법을 HTML로 바꾼다. (바뀐 Markdown, 제목 목록, id 목록)을 돌려준다.

    outputs 는 learn_nb.load_outputs() 의 결과다. 예제와 풀이의 코드 블록 아래에 최신 실행 결과를 붙인다.
    결과가 없거나 코드가 달라진 셀은 missing 목록에 태그('예제:1-1:0')로 적는다. 실습 빈칸 셀은 실행하지 않는다.
    """
    outputs = outputs or {}
    out, headings, ids = [], [], set()
    stack = []          # 열려 있는 상자 (종류, 줄 번호)
    in_fence = False
    queue = iter(learn_nb.code_cells(text))     # 상자 안 코드 블록의 태그. learn_nb.parse 와 같은 순서다
    cell_code = None
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            opening = not in_fence
            in_fence = not in_fence
            out.append(line)
            if opening and stripped == '```python' and any(kind in learn_nb.BOX_KINDS for kind, _ in stack):
                cell_code = []
            elif not opening and cell_code is not None:
                tag, role, _ = next(queue)
                if role != '실습':
                    output = learn_nb.fresh_output(outputs, tag, '\n'.join(cell_code))
                    if output is None:
                        if missing is not None:
                            missing.append(tag)
                    elif output and '건너뜁니다' not in output:
                        out += result_markup(output)
                cell_code = None
            continue
        if in_fence:
            if cell_code is not None:
                cell_code.append(line)
            out.append(line)
            continue

        if stripped.startswith(':::'):
            body = stripped[3:].strip()
            if not body:
                if not stack:
                    fail(path, number, '닫을 상자가 없는데 ::: 가 나왔습니다')
                kind, _ = stack.pop()
                out += ['', CLOSERS[kind], '']
            else:
                kind, _, rest = body.partition(' ')
                opened = open_block(kind, rest.strip(), path, number)
                if kind == '풀이' and not any(open_kind == '실습' for open_kind, _ in stack):
                    fail(path, number, ':::풀이 상자는 :::실습 상자 안에 둡니다')
                if kind in ('예제', '실습'):
                    ids.add(f'{kind}-{rest.strip().split(" ")[0]}')
                stack.append((kind, number))
                out += ['', opened, '']
            continue

        heading = re.match(r'^(#{1,3})\s+(.*?)\s*(?:\{([^}]*)\})?\s*$', line)
        if heading:
            level, title, tag = len(heading.group(1)), heading.group(2), heading.group(3)
            if tag:
                fail(path, number, f'제목에 {{{tag}}} 표시가 있습니다. 본문에 원본 쪽수를 두지 않습니다'
                     '(작성규칙 4절). 원본과의 대응은 작업/원본_대응표.md에 적습니다')
            anchor = slug(title)
            if anchor in ids:
                fail(path, number, f'같은 제목이 이미 있습니다: {title}')
            ids.add(anchor)
            headings.append((level, re.sub(r'`|\[\[|\]\]', '', title), anchor))
            title = replace_terms(title, terms, path, number)
            out.append(f'{"#" * level} {title} {{: #{anchor} }}')
            continue

        out.append(replace_terms(line, terms, path, number))

    if in_fence:
        fail(path, len(out), '코드 블록(```)을 닫지 않았습니다')
    if stack:
        kind, opened_at = stack[-1]
        fail(path, opened_at, f':::{kind} 상자를 닫지 않았습니다')
    return '\n'.join(out), headings, ids


def to_html(text):
    converter = markdown.Markdown(
        extensions=['fenced_code', 'codehilite', 'tables', 'md_in_html', 'attr_list', 'sane_lists'],
        extension_configs={'codehilite': {'guess_lang': False, 'css_class': 'codehilite'}})
    return converter.convert(text)


def toc_html(headings):
    items = [f'<li class="l{level}"><a href="#{anchor}">{html.escape(title)}</a></li>'
             for level, title, anchor in headings]
    return '<ul>\n' + '\n'.join(items) + '\n</ul>'


def pygments_css():
    light = HtmlFormatter(style='friendly').get_style_defs('.codehilite')
    dark = HtmlFormatter(style='nord').get_style_defs(':root[data-theme="dark"] .codehilite')
    return light + '\n' + dark


def render_page(template, *, title, toc, content, nav):
    replacements = {
        '{{title}}': html.escape(title), '{{site}}': html.escape(SETTINGS['title']),
        '{{footer}}': html.escape(SETTINGS['footer']), '{{nav}}': nav,
        '{{toc}}': toc, '{{content}}': content,
        '{{style}}': (TEMPLATES / 'style.css').read_text(encoding='utf-8') + '\n' + pygments_css(),
        '{{script}}': (TEMPLATES / 'app.js').read_text(encoding='utf-8'),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def chapter_label(path):
    """상단 메뉴와 차례에 쓰는 짧은 이름. '01_...' → '1장', '00_...' → '시작하기 전에'."""
    number = chapter_number(path)
    return '시작하기 전에' if number == '00' else f'{int(number)}장'


def write_notebook(notebook, folder, name):
    # 셀 id를 위치로 정해, 내용이 같으면 빌드할 때마다 같은 파일이 나오게 합니다(git diff를 줄이려고)
    for index, cell in enumerate(notebook.cells):
        cell['id'] = f'cell-{index:03d}'
    folder.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, folder / name)


def build_chapter(path, terms, root, project_outputs):
    """장 하나를 HTML 본문으로 바꾸고, 코드가 있으면 장 노트북과 풀이 노트북을 쓴다. (본문, 제목 목록)을 돌려준다."""
    manuscript = path.read_text(encoding='utf-8')
    name = learn_nb.notebook_name(path)
    outputs = learn_nb.load_outputs(root / '작업' / '실행결과' / learn_nb.solution_name(name))
    outputs.update(project_outputs)
    missing = []
    if learn_nb.has_cells(manuscript):
        setup_text = learn_nb.setup_text(TEMPLATES, chapter_number(path))
        html_name = f'{path.stem}.html'
        write_notebook(learn_nb.chapter_notebook(manuscript, setup_text, outputs, html_name), root / '노트북', name)
        write_notebook(learn_nb.chapter_notebook(manuscript, setup_text, solution=True),
                       root / '작업' / '풀이', learn_nb.solution_name(name))
        print(f'{name}  장 노트북 (풀이: 작업/풀이/{learn_nb.solution_name(name)})')
    text, headings, ids = preprocess(manuscript, terms, path, outputs, missing)
    if missing:
        print(f'  실행 결과가 없거나 코드가 바뀐 셀 {len(missing)}개: {", ".join(missing[:8])}'
              + (' …' if len(missing) > 8 else ''))
        print(f'  → python tools/run_nb.py <풀이 노트북> 로 실행한 뒤 다시 빌드하세요')
    rendered = to_html(text)
    for target in re.findall(r'href="#([^"]+)"', rendered):
        if target not in ids:
            fail(path, 1, f'없는 곳을 가리키는 링크입니다: #{target}')
    return f'<article class="part">\n{rendered}\n</article>', headings


def build_projects(chapters, root):
    """관통 프로젝트 상자(:::실습 PK)를 모아 단계마다 프로젝트 노트북과 풀이 노트북을 쓴다.

    단계마다 그 단계 풀이 노트북의 실행 결과에서 그 단계 상자의 태그만 골라 돌려준다.
    """
    steps = {}
    for path in chapters:
        for box in learn_nb.parse(path.read_text(encoding='utf-8'))[1]:
            if learn_nb.is_project(box):
                step = int(box['code'][1:])
                if step in steps:
                    fail(path, 1, f'관통 프로젝트 {step}단계 상자가 두 번 나옵니다')
                steps[step] = (box, f'{path.stem}.html', path)
    outputs = {}
    for step, (box, html_name, path) in sorted(steps.items()):
        view = {number: (found, html) for number, (found, html, _) in steps.items()}
        name = learn_nb.project_name(step)
        ran = learn_nb.load_outputs(root / '작업' / '실행결과' / learn_nb.solution_name(name))
        mine = {tag: value for tag, value in ran.items() if tag.split(':')[1] == box['code']}
        outputs.update(mine)
        setup_text = learn_nb.setup_text(TEMPLATES, chapter_number(path))
        write_notebook(learn_nb.project_notebook(step, view, setup_text, mine), root / '노트북', name)
        write_notebook(learn_nb.project_notebook(step, view, setup_text, solution=True),
                       root / '작업' / '풀이', learn_nb.solution_name(name))
        print(f'{name}  프로젝트 노트북')
    return outputs


def build(root=HERE):
    root = Path(root)
    try:
        _build(root)
    except BuildError as error:
        print(f'빌드 실패: {error}', file=sys.stderr)
        raise SystemExit(1)


def _build(root):
    terms = read_glossary(root / '용어집.md')
    template = (TEMPLATES / 'page.html').read_text(encoding='utf-8')
    out_dir = root / '교재'
    out_dir.mkdir(exist_ok=True)

    # 장 원고만 읽는다. 이름이 두 자리 번호로 시작하지 않는 파일(메모 등)은 교재에 넣지 않는다
    chapters = sorted(path for path in (root / '원고').glob('*.md') if chapter_number(path))
    project_outputs = build_projects(chapters, root)
    built = []
    for path in chapters:
        content, headings = build_chapter(path, terms, root, project_outputs)
        built.append((path, content, headings))

    def nav_for(current):
        links = ['<a href="index.html"' + (' class="here"' if current == 'index' else '') + '>차례</a>']
        links += [f'<a href="{path.stem}.html"' + (' class="here"' if path.stem == current else '')
                  + f'>{chapter_label(path)}</a>' for path, _, _ in built]
        return '\n'.join(links)

    for path, content, headings in built:
        title = headings[0][1] if headings else path.stem
        page = render_page(template, title=title, toc=toc_html(headings), content=content, nav=nav_for(path.stem))
        (out_dir / f'{path.stem}.html').write_text(page, encoding='utf-8')
        print(f'{path.stem}.html  제목 {len(headings)}개')

    def chapter_item(path, headings):
        title = headings[0][1] if headings else path.stem
        return f'<li><a href="{path.stem}.html">{html.escape(title)}</a></li>'

    by_number = {int(chapter_number(path)): (path, headings) for path, _, headings in built}
    sections = []
    if 0 in by_number:
        sections.append(f'<section class="day"><ul>{chapter_item(*by_number[0])}</ul></section>')
    for part_title, numbers in PARTS:
        items = ''.join(chapter_item(*by_number[number]) for number in numbers if number in by_number)
        if items:
            sections.append(f'<section class="day"><h2>{html.escape(part_title)}</h2><ul>{items}</ul></section>')
    glossary_rows = ''.join(
        f'<tr id="용어-{slug(term)}"><th>{html.escape(term)}</th><td>{html.escape(meaning)}</td></tr>'
        for term, meaning in sorted(terms.items()))
    index_content = (
        '<article class="part">'
        f'<h1 id="차례">{html.escape(SETTINGS["title"])}</h1>'
        '<p>생성형 AI의 용어와 원리를 설명하는 교재입니다. 이 교재만 읽어도 예제의 코드와 실행 결과를 볼 수 있습니다. '
        '직접 실행하려면 장마다 같은 이름의 장 노트북을, 관통 프로젝트는 프로젝트 노트북을 엽니다.</p>'
        + ''.join(sections) +
        '<h2 id="용어집">용어집</h2>'
        f'<table class="glossary"><tbody>{glossary_rows}</tbody></table>'
        '</article>')
    index_toc = toc_html([(1, '차례', '차례'), (2, '용어집', '용어집')])
    (out_dir / 'index.html').write_text(
        render_page(template, title='차례', toc=index_toc, content=index_content, nav=nav_for('index')),
        encoding='utf-8')
    print('index.html')


if __name__ == '__main__':
    build()
