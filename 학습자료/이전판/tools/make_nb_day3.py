"""3일차 실습 노트북과 풀이 노트북의 공통 도구와 파트 1의 노트북을 만든다.

사용법: python make_nb_day3.py
출력: 노트북/3일차_실습.ipynb, 노트북/3일차_실습_풀이.ipynb (파트 1)

파트 2, 3의 make_nb_day3_part2.py, make_nb_day3_part3.py가 이 파일의 md, code, save, SETUP_*를 가져다 쓴다.
노트북은 노트북/ 폴더에서 실행한다(llm.py, embed.py, checks_d3*.py, data/가 같은 폴더에 있다).
"""
import re
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = Path(__file__).resolve().parents[1] / '노트북'


def md(text):
    return new_markdown_cell(text.strip('\n'))


def code(text, tag=None):
    cell = new_code_cell(text.strip('\n'))
    if tag:
        cell.metadata['tags'] = [tag]
    return cell


def save(name, cells):
    notebook = new_notebook(cells=cells)
    notebook.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    notebook.metadata['language_info'] = {'name': 'python'}
    nbformat.validate(notebook)
    nbformat.write(notebook, OUT / name)
    print(f'{name} {len(cells):,}셀')


import learn_nb  # noqa: E402  (같은 tools 폴더)

SETUP_TEXT = learn_nb.setup_text(Path(__file__).resolve().parents[1] / '교재_템플릿', '3일차')
SETUP_MD, SETUP_KEYS, SETUP_COMMON, SETUP_AFTER = [      # 안내, 준비 (1), 준비 (2), 오류 표
    part.strip('\n') for part in re.split(r'```python\n(.*?)\n```', SETUP_TEXT, flags=re.S)
    if part.strip()]

TODO = "raise NotImplementedError('이 부분을 채웁니다')"
