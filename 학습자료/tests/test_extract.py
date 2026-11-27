import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / 'GenAI_2일차_배포용' / '1_강의안' / 'GenAI_2일차_강의안.pdf'
SCRIPT = ROOT / '학습자료' / 'tools' / 'extract.py'


def test_extract_day2_text(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT), str(PDF), str(tmp_path)], check=True)
    text = (tmp_path / 'slides.txt').read_text(encoding='utf-8')
    assert len(re.findall(r'^===== p\.\d+ =====$', text, re.M)) == 424
    page25 = text.split('===== p.25 =====')[1].split('===== p.26 =====')[0]
    assert 'LLM API 기초' in page25


def test_extract_images(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT), str(PDF), str(tmp_path), '--images', '25-26'], check=True)
    names = sorted(p.name for p in (tmp_path / 'img').glob('*.png'))
    assert names == ['p025.png', 'p026.png']
