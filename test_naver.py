import requests
from bs4 import BeautifulSoup
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
url = 'https://finance.naver.com/sise/sise_deal_rank.naver?investor_gubun=1000&sosok=0'
res = requests.get(url, headers=headers, timeout=10)
res.encoding = 'cp949'
soup = BeautifulSoup(res.text, 'html.parser')
rows = soup.select('tr')
for row in rows:
    cols = row.select('td')
    if len(cols) >= 3:
        name_tag = row.select_one('a.company')
        if name_tag and '삼성전기' in name_tag.text:
            print(f"cols 총 {len(cols)}개")
            for i, col in enumerate(cols):
                print(f"[{i}]: '{col.text.strip()}'")
            break