# 설치: python -m pip install sentence-transformers rank-bm25 pypdf
# 7장에서 씁니다. 문서를 읽고 검색하는 함수는 같은 폴더의 corpus.py에 있습니다
import numpy as np

import corpus
import embed

catalog = corpus.catalog()               # {문서 id: 메타데이터}. 문서 120건
questions = corpus.evalset()             # 평가 질문 62개. 키의 뜻은 data/README.md에 있습니다
embed.load()                             # 임베딩 모델을 불러옵니다. 처음 한 번 약 470MB를 내려받습니다
print(f'문서 {len(catalog)}건, 평가 질문 {len(questions)}개')
