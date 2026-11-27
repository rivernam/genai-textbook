# 설치: python -m pip install transformers
# 3장의 예제 3-1과 실습 3-1은 1장의 토크나이저만 씁니다(모델은 내려받지 않습니다)
import embed
LOCAL_MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
embed.ask_endpoint(LOCAL_MODEL)          # 토크나이저가 PC에 없고 HF_ENDPOINT가 비어 있으면 주소를 묻습니다
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL)
print('토크나이저:', LOCAL_MODEL)
