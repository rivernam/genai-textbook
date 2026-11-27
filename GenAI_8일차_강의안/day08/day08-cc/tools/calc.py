# 계산 도구 (7일차 calc와 같음). 사용: python tools/calc.py "(14-9)/9*100"
import re, sys
from _common import show

expression = ' '.join(sys.argv[1:])

# 숫자, 사칙연산, 괄호만 허용합니다(거듭제곱 ** 은 막습니다)
if not re.fullmatch(r'[0-9+\-*/(). ]+', expression) or '**' in expression:
    show({'error': '사칙연산과 괄호만 계산합니다', 'expression': expression})
else:
    try:
        result = eval(expression, {'__builtins__': {}}, {})   # 내장 함수를 비운 채 계산합니다
        show({'expression': expression, 'result': result})
    except Exception as error:      # 0으로 나누기, 괄호가 맞지 않는 식
        show({'error': str(error), 'expression': expression})
