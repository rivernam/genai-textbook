# 실습 도구 공용. 결과를 JSON 한 줄로 내고, 한글이 Windows에서 깨지지 않게 UTF-8로 출력합니다
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # 실습 폴더(my-agent)


def utf8_out():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def show(obj):
    utf8_out()
    print(json.dumps(obj, ensure_ascii=False))


def path(*p):
    return os.path.join(ROOT, *p)
