import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

try:
    import os
    import pathlib
    os.chdir(pathlib.Path(__file__).parent)
except:
    pass

la_rex = re.compile(r"/la ?([\da-zA-Z_+']+)")
brackets_rex = re.compile(r'(\d+)「(.+)」')
zen2han_alpha = str.maketrans(
    {chr(0xFF01 + i): chr(0x21 + i) for i in range(93)})
han2zen_alpha = str.maketrans(
    {chr(0x21 + i): chr(0xFF01 + i) for i in range(93)})


def name_regulator(name):
    m = brackets_rex.match(name)
    if m:
        # 「」内は全角にする
        num = m.group(1)
        name = m.group(2).translate(han2zen_alpha)
        return f'{num}「{name}」'

    # 「」なしは全体を全角にする
    return name.translate(han2zen_alpha)


url = 'http://pso2.swiki.jp/index.php?ロビーアクション'
res = requests.get(url, verify=False)
soup = BeautifulSoup(res.text, "html.parser")


def records():
    yield ['名称', 'コマンド', 'ループ', 'リアクション対応', 'トレード不可', '入手']

    lastnum = None
    dup = set()
    dups = []

    for tr in soup.find_all('tr'):
        td = tr.find_all("td")
        if len(td) > 10:
            continue
        if "/la" not in tr.text:
            continue
        span = td[0].find("span")
        if span:
            span.extract()

        td = [x.get_text().strip() for x in td]
        name, loop, la, src = tuple(td[x] for x in [0, 1, 5, 2])

        la = la_rex.match(la)
        if not la:
            continue
        la = la.group(1)
        loop = '1' if loop else '0'
        name = name_regulator(name)
        num = brackets_rex.match(name)
        num = int(num.group(1)) if num else None
        src = re.sub(r',|ｼｮｯﾌﾟ|備考', '', src)
        notrade = '1' if 'トレード不可' in tr.text else '0'
        reaction = '1' if 'リアクション対応' in tr.text else '0'
        rec = [name, la, loop, reaction, notrade, src]

        if lastnum:
            while num - lastnum > 1:
                lastnum += 1
                yield [f'{lastnum} --------欠番--------']

        if la in dup:
            dups.append(rec)
        dup.add(la)

        lastnum = num
        yield rec

    if dups:
        print('-' * 79)
        print(' error '.center(79, '-'))
        print('-' * 79)
        for rec in dups:
            print(','.join(rec))
        input('press enter to exit')


csvfile = Path('lobbyactions.csv')
with csvfile.open('w', encoding='utf-8') as f:
    sep = ','
    for rec in records():
        print(sep.join(rec), file=f)
        print(sep.join(rec))
