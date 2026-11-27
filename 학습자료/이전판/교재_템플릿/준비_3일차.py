# 설치: python -m pip install sentence-transformers scikit-learn pypdf python-docx openpyxl pandas
import numpy as np

import embed

DATA = 'data/3일차'
CORPUS = 'data/2일차/corpus'      # 2일차와 같은 문서 253건
OUT = 'out'                        # 예제가 만드는 파일을 두는 폴더
os.makedirs(OUT, exist_ok=True)
