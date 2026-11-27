# 설치: python -m pip install transformers
# 예제 14-2는 1장의 토크나이저만 씁니다(모델은 내려받지 않습니다)
import shutil
import subprocess
import tempfile
from pathlib import Path

import embed
LOCAL_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
embed.ask_endpoint(LOCAL_MODEL)          # 토크나이저가 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL)

MATERIAL = Path(DATA) / '14장'           # 가상의 설비팀 작업 폴더 재료


def front_matter(path):
    """SKILL.md 맨 앞의 --- 두 줄 사이(front matter)를 읽어 {'name': ..., 'description': ...}로 돌려줍니다"""
    head = path.read_text(encoding='utf-8').split('---')[1]
    return dict(line.split(': ', 1) for line in head.strip().splitlines())


def make_project():
    """임시 폴더에 가상의 설비팀 작업 폴더를 만들고 경로를 돌려줍니다.

    규칙파일.md는 CLAUDE.md로, skills/는 .claude/skills/로, 기록/은 그대로 복사합니다.
    """
    project = Path(tempfile.mkdtemp(prefix='work14_'))
    shutil.copy(MATERIAL / '규칙파일.md', project / 'CLAUDE.md')
    shutil.copytree(MATERIAL / 'skills', project / '.claude' / 'skills')
    shutil.copytree(MATERIAL / '기록', project / '기록')
    return project


print('토크나이저:', LOCAL_MODEL, '/ 재료:', MATERIAL)
