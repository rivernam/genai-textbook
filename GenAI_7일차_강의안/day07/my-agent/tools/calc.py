# 계산 도구 · 노트북의 calc와 같습니다 · 사용: python tools/calc.py "(1250-1180)/1250*100"
import re, sys
from _common import show

expression = ' '.join(sys.argv[1:])
if not re.fullmatch(r'[0-9+\-*/(). ]+', expression) or '**' in expression:  # 사칙연산과 괄호만 받습니다
    show({'error': '사칙연산과 괄호만 계산합니다', 'expression': expression})
else:
    try:
        show({'expression': expression, 'result': eval(expression, {'__builtins__': {}}, {})})
    except Exception as e:          # 0으로 나누기, 괄호가 맞지 않는 식
        show({'error': str(e), 'expression': expression})
