# 설치: 파트 3의 예제는 python -m pip install sentence-transformers scikit-learn도 필요합니다
DATA = 'data/2일차'
SYSTEM = open(f'{DATA}/분류_규칙.txt', encoding='utf-8').read()

# 100만 토큰당 달러 (입력, 출력). Anthropic 공개 가격, 2026-11-03 확인.
# 소형은 입력이 10만 토큰 이하인 요청의 단가입니다. 넘으면 (0.50, 2.50)입니다.
# 사내 API를 쓴다면 사내 과금 기준으로 바꿉니다. 과금이 없으면 (0, 0)으로 둡니다.
PRICE = {'소형': (0.10, 0.50), '기본': (2.00, 10.00), '대형': (4.00, 20.00)}


def cost_usd(input_tokens, output_tokens, model='기본'):
    """토큰 수와 단가로 요금(달러)을 계산합니다."""
    input_price, output_price = PRICE[model]
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
