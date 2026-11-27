"""원고(Markdown)에서 장 노트북, 프로젝트 노트북, 풀이 노트북을 만든다. build.py 가 이 모듈을 쓴다.

장 노트북(노트북/NN_장제목.ipynb)은 공유한다. 준비 셀, 예제 셀, 실습 빈칸 셀만 담는다.
개념 설명은 HTML 교재에 있고, 노트북에는 상자마다 짧은 안내만 둔다.
관통 프로젝트(:::실습 P3)는 장 노트북에 넣지 않고 프로젝트 노트북(노트북/프로젝트_3.ipynb)으로 만든다.
K단계 프로젝트 노트북은 앞 단계들의 풀이 코드에서 시작한다.
풀이 노트북(작업/풀이/<이름>_풀이.ipynb)은 공유하지 않는다. 실습 빈칸 대신 풀이 코드를 넣은 것으로,
tools/run_nb.py 로 실행해 예제와 풀이의 실제 실행 결과를 얻는 데 쓴다.

원고의 상자와 코드 셀
  :::예제 1-1 제목   안의 ```python 블록이 예제 셀이 된다. 태그 '예제:1-1:0'
  :::실습 1-2 제목   안의 ```python 블록이 빈칸 셀이 된다. 태그 '실습:1-2:0'
    :::풀이          실습 상자 안에 둔다. ```python 블록이 풀이 셀이 된다. 태그 '풀이:1-2:0'
상자 안에서 코드 밖의 글(풀이 상자 안은 제외)은 노트북의 안내 셀이 된다.
"""
import base64
import re
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook, new_output

BOX_KINDS = ('예제', '실습')

# 노트북에서는 CSS 변수를 쓸 수 없으므로 그림의 색을 밝은 화면 값으로 바꾼다
COLORS = {'--paper': '#f6f8f8', '--sheet': '#ffffff', '--ink': '#16252b', '--ink-soft': '#55676e',
          '--line': '#d3dcde', '--teal': '#0b5a66', '--teal-wash': '#e3eff0',
          '--amber': '#8a5a00', '--amber-wash': '#fbf1d8'}
QUOTED = ('요점', '주의', '보충')          # 노트북에서 인용 블록으로 그리는 상자


def notebook_name(manuscript_path):
    """장 노트북 이름. 원고 '01_LLM은_어떻게_글을_만드는가.md' → '01_LLM은_어떻게_글을_만드는가.ipynb'."""
    return f'{Path(manuscript_path).stem}.ipynb'


def solution_name(notebook):
    """풀이 노트북 이름. '01_제목.ipynb' → '01_제목_풀이.ipynb'."""
    return notebook.replace('.ipynb', '_풀이.ipynb')


def project_name(step):
    return f'프로젝트_{step}.ipynb'


def is_project(box):
    return box['kind'] == '실습' and box['code'].startswith('P')


def tag_of(role, code, index):
    return f'{role}:{code}:{index}'


def plain(text):
    return re.sub(r'\[\[([^\]]+)\]\]', r'\1', text).strip()


def parse(text):
    """원고에서 장 제목과 예제, 실습 상자를 순서대로 읽는다.

    (장 제목, 상자 목록)을 돌려준다. 상자는 dict다.
      kind, code, title: 상자 머리글의 종류, 번호, 제목
      section: 상자가 든 절(## 제목)
      guide: 코드 밖의 글
      cells: [(역할, 순서, 코드)]. 역할은 '예제', '실습'(빈칸), '풀이'
    """
    chapter_title, section, boxes = '', '', []
    stack, box, in_fence, code_lines, role = [], None, False, None, None
    counters = {}
    for line in text.split('\n'):
        stripped = line.strip()
        if code_lines is not None:                 # 상자 안의 파이썬 코드 블록
            if stripped == '```':
                key = (role, box['code'])
                counters[key] = counters.get(key, -1) + 1
                box['cells'].append((role, counters[key], '\n'.join(code_lines)))
                code_lines = None
            else:
                code_lines.append(line)
            continue
        in_solution = '풀이' in stack
        if stripped.startswith('```'):
            if not in_fence and box and stripped == '```python':
                role, code_lines = ('풀이' if in_solution else box['kind']), []
                continue
            in_fence = not in_fence
            if box and not in_solution:
                box['guide'].append(line)
            continue
        if in_fence:
            if box and not in_solution:
                box['guide'].append(line)
            continue
        if stripped.startswith(':::'):
            body = stripped[3:].strip()
            if body:
                kind, _, rest = body.partition(' ')
                if kind in BOX_KINDS and box is None:
                    code, _, title = rest.strip().partition(' ')
                    box = dict(kind=kind, code=code, title=title.strip(), section=section, guide=[], cells=[])
                elif box and kind != '풀이' and not in_solution:
                    box['guide'].append(line)
                stack.append(kind)
            else:
                kind = stack.pop() if stack else ''
                if box and kind == box['kind'] and not any(open_kind in BOX_KINDS for open_kind in stack):
                    box['guide'] = '\n'.join(box['guide']).strip()
                    boxes.append(box)
                    box = None
                elif box and kind != '풀이' and '풀이' not in stack:
                    box['guide'].append(line)
            continue
        if box is None:
            heading = re.match(r'^(#{1,2})\s+(.*?)\s*$', line)
            if heading and len(heading.group(1)) == 1 and not chapter_title:
                chapter_title = plain(heading.group(2))
            elif heading and len(heading.group(1)) == 2:
                section = plain(heading.group(2))
            continue
        if not in_solution:
            box['guide'].append(line)
    return chapter_title, boxes


def code_cells(text):
    """원고의 모든 코드 셀을 (태그, 역할, 코드)로 순서대로 돌려준다."""
    return [(tag_of(role, box['code'], index), role, source)
            for box in parse(text)[1] for role, index, source in box['cells']]


def svg_to_image(match):
    """그림(inline SVG)을 노트북에서 보이는 이미지로 바꾼다."""
    figure = match.group(0)
    svg = re.search(r'<svg.*?</svg>', figure, flags=re.S).group(0)
    caption = re.search(r'<figcaption>(.*?)</figcaption>', figure, flags=re.S)
    label = re.search(r'aria-label="([^"]*)"', svg)
    view = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    for name, value in COLORS.items():
        svg = svg.replace(f'var({name})', value)
    background = f'<rect width="{view.group(1)}" height="{view.group(2)}" fill="#ffffff"/>'
    svg = re.sub(r'<svg ', f'<svg xmlns="http://www.w3.org/2000/svg" width="{view.group(1)}" '
                 f'height="{view.group(2)}" font-family="sans-serif" ', svg, count=1)
    svg = re.sub(r'(<svg[^>]*>)', r'\1' + background, svg, count=1)
    data = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    image = (f'<img alt="{label.group(1) if label else ""}" width="{view.group(1)}" '
             f'src="data:image/svg+xml;base64,{data}">')
    return image + (f'\n\n*{caption.group(1).strip()}*' if caption else '')


def to_notebook_markdown(text):
    """상자 안내 글의 추가 문법을 Jupyter가 그리는 Markdown으로 바꾼다."""
    text = re.sub(r'<figure>.*?</figure>', svg_to_image, text, flags=re.S)
    out, stack, in_fence = [], [], False

    def emit(line):
        out.append('> ' + line if stack and stack[-1] in QUOTED else line)

    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            emit(line)
            continue
        if in_fence:
            emit(line)
            continue
        if stripped.startswith(':::'):
            body = stripped[3:].strip()
            if not body:
                kind = stack.pop() if stack else ''
                out += ['', '</details>', ''] if kind in ('정답', '힌트') else ['']
                continue
            kind, _, rest = body.partition(' ')
            stack.append(kind)
            if kind == '탭':
                out += ['', f'**{rest}**', '']
            elif kind == '정답':
                out += ['', '<details><summary>정답 보기</summary>', '']
            elif kind == '힌트':
                out += ['', '<details><summary>힌트 보기</summary>', '']
            elif kind in QUOTED:
                out += ['', f'> **{kind}**', '>']
            else:
                out += ['', f'**{kind}**', '']
            continue
        emit(re.sub(r'\[\[([^\]]+)\]\]', r'\1', line))
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip('\n')


def setup_text(templates, chapter):
    """준비.md를 읽고, 준비 코드를 준비 (2) 셀에 끼워 넣는다.

    준비 코드는 모든 장에 공통인 준비_공통.py 와, 그 장에만 필요한 준비_<NN>.py(있을 때만)를 이어 붙인 것이다.
    """
    templates = Path(templates)
    text = (templates / '준비.md').read_text(encoding='utf-8')
    parts = [(templates / '준비_공통.py').read_text(encoding='utf-8').strip()]
    chapter_file = templates / f'준비_{chapter}.py'
    if chapter_file.exists():
        parts.append(chapter_file.read_text(encoding='utf-8').strip())
    return text.replace('{{장별 준비}}', '\n\n'.join(parts))


def setup_cells(setup_text):
    """준비.md를 설명 셀과 코드 셀로 나눈다."""
    cells = []
    for index, part in enumerate(re.split(r'```python\n(.*?)\n```', setup_text, flags=re.S)):
        if not part.strip():
            continue
        cells.append(new_code_cell(part) if index % 2 else new_markdown_cell(part.strip('\n')))
    return cells


def load_outputs(executed_path):
    """실행한 노트북에서 {태그: (코드, 출력 글)}을 읽는다. 파일이 없으면 빈 사전."""
    executed_path = Path(executed_path)
    if not executed_path.exists():
        return {}
    outputs = {}
    for cell in nbformat.read(executed_path, as_version=4).cells:
        tags = cell.get('metadata', {}).get('tags', [])
        if cell.cell_type != 'code' or not tags:
            continue
        # 표준 오류(경고, 진행 표시줄)는 싣지 않는다. 코드가 print로 출력한 것만 실행 결과다
        text = ''.join(output.get('text', '') for output in cell.outputs
                       if output.output_type == 'stream' and output.get('name') != 'stderr')
        outputs[tags[0]] = (cell.source.strip(), text.rstrip('\n'))
    return outputs


def fresh_output(outputs, tag, source):
    """원고의 코드와 같은 코드로 실행한 결과가 있으면 그 출력을, 없으면 None을 돌려준다."""
    found = outputs.get(tag)
    if found and found[0] == source.strip():
        return found[1]
    return None


def box_cells(box, outputs, solution):
    """상자 하나를 안내 셀과 코드 셀로 만든다. 장 노트북은 빈칸 셀을, 풀이 노트북은 풀이 셀을 넣는다."""
    head = f'## {box["kind"]} {box["code"]}. {plain(box["title"])}'
    if box['section']:
        head += f'\n\n교재의 절: "{box["section"]}"'
    if box['guide']:
        head += '\n\n' + to_notebook_markdown(box['guide'])
    cells = [new_markdown_cell(head)]
    for role, index, source in box['cells']:
        if (role == '실습' and solution) or (role == '풀이' and not solution):
            continue
        cell = new_code_cell(source)
        tag = tag_of(role, box['code'], index)
        cell.metadata['tags'] = [tag]
        text = fresh_output(outputs, tag, source) if role == '예제' else None
        if text:
            cell.outputs = [new_output('stream', name='stdout', text=text + '\n')]
        cells.append(cell)
    return cells


def finish(cells):
    notebook = new_notebook(cells=cells)
    notebook.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    notebook.metadata['language_info'] = {'name': 'python'}
    nbformat.validate(notebook)
    return notebook


def chapter_boxes(text):
    return [box for box in parse(text)[1] if not is_project(box)]


def has_cells(text):
    """장 노트북을 만들 코드가 있으면 True. 관통 프로젝트 상자의 코드는 세지 않는다."""
    return any(box['cells'] for box in chapter_boxes(text))


def chapter_notebook(text, setup_text, outputs=None, html_name='', solution=False):
    """장 노트북(solution=False) 또는 풀이 노트북(solution=True)을 만든다."""
    title, _ = parse(text)
    if solution:
        intro = f'# {title} (풀이)\n\n검증용 풀이 노트북입니다. 공유하지 않습니다.'
    else:
        intro = (f'# {title}\n\n이 장의 예제와 실습을 실행하는 노트북입니다. 개념 설명은 HTML 교재 '
                 f'`{html_name}`에 있습니다. 위에서부터 차례로 실행합니다. 실습의 풀이는 교재의 실습 상자에 접혀 있습니다.')
    cells = [new_markdown_cell(intro)] + setup_cells(setup_text)
    for box in chapter_boxes(text):
        cells += box_cells(box, outputs or {}, solution)
    return finish(cells)


def project_notebook(step, steps, setup_text, outputs=None, solution=False):
    """K단계 프로젝트 노트북. steps는 {단계 번호: (상자, HTML 이름)}이다. 앞 단계들의 풀이 코드에서 시작한다.

    앞 단계마다 첫 풀이 셀(그 단계의 함수 정의)만 넣는다. 둘째 이후 풀이 셀은 그 단계의 배치 실행이나 평가처럼
    결과를 확인하는 셀이라, 넣으면 뒤 단계 노트북을 열 때마다 API를 다시 부른다.
    """
    box, html_name = steps[step]
    if solution:
        intro = f'# 관통 프로젝트 {step}단계 (풀이)\n\n검증용 풀이 노트북입니다. 공유하지 않습니다.'
    else:
        intro = (f'# 관통 프로젝트 {step}단계: {plain(box["title"])}\n\n과제 설명은 HTML 교재 `{html_name}`의 '
                 f'"실습 {box["code"]}" 상자에 있습니다. 위에서부터 차례로 실행합니다.')
    cells = [new_markdown_cell(intro)] + setup_cells(setup_text)
    for earlier in sorted(number for number in steps if number < step):
        earlier_box = steps[earlier][0]
        solved = [(index, source) for role, index, source in earlier_box['cells'] if role == '풀이' and index == 0]
        if not solved:
            continue
        cells.append(new_markdown_cell(f'## 앞 단계의 코드: {earlier}단계 풀이'))
        for index, source in solved:
            cell = new_code_cell(source)
            cell.metadata['tags'] = [tag_of('풀이', earlier_box['code'], index)]
            cells.append(cell)
    cells += box_cells(box, outputs or {}, solution)
    return finish(cells)
