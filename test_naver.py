import requests
from bs4 import BeautifulSoup
headers = {'User-Agent': 'Mozilla/5.0'}
url = 'https://finance.naver.com/sise/sise_deal_rank.naver?investor_gubun=1000&sosok=0'
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'cp949'
soup = BeautifulSoup(res.text, 'html.parser')
# 테이블 전체 구조 확인
tables = soup.select('table')
print(f"테이블 수: {len(tables)}")
for i, t in enumerate(tables[:3]):
    print(f"\n테이블 {i}:")
    rows = t.select('tr')
    for row in rows[:3]:
        print(row.text.strip()[:100])