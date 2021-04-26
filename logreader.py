# %%

import urllib.request
import collections
import csv
import ctypes
import io
import logging
import re
import sys
import threading
import time
from pathlib import Path

import bouyomichan
import colorama
import playsound
import pyperclip
from colorama import Back, Fore, Style

import chatcmd
import logpump

colorama.init(autoreset=True)

logging.basicConfig(level=logging.INFO, format='\
%(levelname)s : %(asctime)s : %(message)s')


ChatColors = {
    'PUBLIC': 'WHITE',
    'GROUP': 'GREEN',
    'REPLY': 'MAGENTA',
    'GUILD': 'LIGHTRED_EX',
    'PARTY': 'CYAN',
}


class UsersFile:
    data = {}

    def __init__(self, path, loader):
        self.mtime = 0
        self.path = Path(path)
        self.loader = loader

    def __call__(self):
        try:
            t = self.path.stat().st_mtime
            if self.mtime < t:
                self.data = self.loader(self.path)
                self.mtime = t
        except FileNotFoundError:
            pass
        return self.data


def spitem_loader(path):
    """spitem.txtをパースする"""
    rex = set()
    dic = {"regexp": rex}
    current_audio = None
    with path.open(encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_audio = line[1:-1]
                continue
            if line.startswith("/") and line.endswith("/"):
                pattern = re.compile(line[1:-1])
                rex.add((pattern, current_audio))
            dic[line] = current_audio
    logging.info(str(path) + " loaded")
    return dic


def read_la_dict(f):
    dic = {}
    f.readline()  # skip header line
    for row in csv.reader(f):
        if len(row) < 2:
            continue
        name, cmd = row[:2]
        if not cmd:
            continue
        dic[cmd] = name
    return dic


def la_dict_loader(path):
    with path.open(encoding='utf-8') as f:
        dic = read_la_dict(f)
    logging.info(str(path) + " loaded")
    return dic

spitem = UsersFile("spitem.txt", spitem_loader)

la_csv = "lobbyactions.csv"
la_dict = UsersFile(la_csv, la_dict_loader)

if not Path(la_csv).is_file():
    try:
        url = 'https://raw.githubusercontent.com/yumimint/PSO2LogReader/main/lobbyactions.csv'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as src, Path(la_csv).open("wb") as dst:
            dst.write(src.read())
            # f = io.TextIOWrapper(io.BytesIO(res.read()), encoding="utf-8")
            # dic = read_la_dict(f)

    except Exception as e:
        print(e, file=sys.stderr)


def spitem_check_and_notify(item):
    dic = spitem()

    if item in dic:
        sound = dic[item]
        playsound.playsound(sound, block=False)
        return

    for pattern, sound in dic["regexp"]:
        if pattern.match(item):
            playsound.playsound(sound, block=False)


class TalkativesDetector:
    """おしゃべり過多検出器"""

    def __init__(self, duration=60):
        self.od = collections.OrderedDict()
        self.duration = duration

    def __call__(self, text):
        """一定期間内に同じtextがあればTrueを返す"""
        now = time.time()
        self.forget(now - self.duration)
        exists = text in self.od
        self.od[text] = now
        self.od.move_to_end(text, last=True)
        return exists

    def forget(self, expiry):
        for t in list(self.od.values()):
            if t > expiry:
                break
            self.od.popitem(last=False)


talkactive = TalkativesDetector()


def talk(text):
    if not talkactive(text):
        bouyomichan.talk(text)


class ItemCounter(dict):
    def add(self, item, num):
        if item not in self:
            self[item] = 0
        self[item] += num

    def names(self):
        ls = list(filter(lambda x: x[1] > 0, self.items()))
        ls.sort(key=lambda x: (-x[1], x[0]))
        return map(lambda x: self.pair2name(*x), ls)

    units = [
        (lambda item: 'メダル' in item, '枚'),
        (lambda item: '券' in item, '枚'),
        (lambda item: '肉' in item, 'Kg'),
        (lambda item: True, '個'),
    ]

    @staticmethod
    def pair2name(item, num):
        # item = item.translate(ItemCounter.zen2han_alpha)
        if item == 'メセタ':
            return f'{num:,}メセタ'
        if num == 1:
            return item
        for _ in ItemCounter.units:
            if _[0](item):
                unit = _[1]
                break
        return f'{item}({num}{unit})'

    # zen2han_alpha = str.maketrans(
    #     {chr(0xFF01 + i): chr(0x21 + i) for i in range(93)})


class DelayedReporter:
    delay = 30

    def __init__(self):
        self.count = ItemCounter()
        self.added = threading.Event()
        self.mutex = threading.Lock()
        self.expiry = 0
        self.th = threading.Thread(target=self.main, daemon=True)
        self.keep_running = True

    def start(self):
        self.th.start()

    def stop(self):
        self.keep_running = False
        self.th.join()

    def put(self, item, num):
        with self.mutex:
            self.count.add(item, num)
            self.expiry = time.time() + self.delay
        self.added.set()

    def main(self):
        while self.keep_running:
            if not self.added.wait(timeout=1):
                continue

            while self.added.is_set():
                self.added.clear()
                s = self.expiry - time.time()
                if s > 0:
                    time.sleep(s)

            with self.mutex:
                names = self.count.names()
                self.count.clear()

            text = ' '.join(names)
            talk(text)
            print(Fore.YELLOW + text)


class CasinoCounter:
    """ Amusement
    """

    printed = False

    def __init__(self):
        self.reset()
        self.badcount = [0] * 6

    def reset(self):
        self.count = 0
        self.bet = 0
        self.ret = 0
        self.hit = 0
        self.defeats = 0
        self.defeats_max = 0

    def add(self, bet, ret):
        self.count += 1
        self.bet += bet
        self.ret += ret
        if ret == 0:
            self.defeats += 1
            self.defeats_max = max(self.defeats_max, self.defeats)
            if self.defeats > 1 and bet <= 5:
                self.badcount[bet] += 1
        else:
            self.defeats = 0
            self.hit += 1

    @property
    def rate(self): return self.ret / self.bet

    @property
    def hitrate(self):
        return self.hit / self.count

    @property
    def income(self): return self.ret - self.bet

    @property
    def meter(self):
        m, n = self.defeats, self.defeats_max - self.defeats
        return 'x' * m + '.' * n

    @property
    def toobad(self):
        return self.defeats > 0 and self.defeats == self.defeats_max

    def __call__(self, ent):
        if ent[2] in ['UsePass', 'Buy']:
            return

        bet, ret, before, after = map(int, ent[5:9])

        self.add(bet, ret)

        c = self
        if ret:
            talk(f"{ret}枚当たり 累計{c.income} ヒット率{c.hitrate:.3f}")
        elif c.defeats > 2:
            talk(f'{c.defeats}連敗 ')

        print(
            # ent[0],
            c.meter,
            f'{bet}',
            f'{ret:3d}',
            f'{c.hit}/{c.count}({c.hitrate:.3f})',
            f'Total({after:,})',
            f'Rate({c.rate:.2f}) In({c.income:,})',
            # *self.badcount,
            '   ',
            end='\r')

        CasinoCounter.printed = True

    @classmethod
    def linefeed(klass):
        if klass.printed:
            klass.printed = False
            print("")


def chat_print(ent, text):
    time, seq, channel, id, name = ent[:5]
    time = time[-8:]
    channel = 'GROUP' if channel == 'CHANNEL' else channel
    try:
        col = ChatColors[channel]
    except IndexError:
        col = 'RESET'

    # name = getattr(Back, col) + Fore.BLACK + name + Style.RESET_ALL
    text = getattr(Fore, col) + text

    CasinoCounter.linefeed()

    print(f"{time} {name} {text}")


def handle_Chat(ent):
    """ Chat
    """
    time, seq, channel, id, name, mess = ent[:6]

    if channel == 'PARTY' and handle_Amusement.count:
        handle_Amusement.reset()
        # talk('カウンタをリセットしました')

    _ = re.search(r'/[cmf]?la +([^ ]+)', mess)
    la = ''
    if _:
        cmd = _.group(1)
        dic = la_dict()
        if cmd in dic:
            la = re.sub(r'^\d+', '', dic[cmd])
            talk(f'{name}が{la}した')
            la = ' ' + Fore.RESET + dic[cmd]

    chat_print(ent, mess + la)

    _ = re.search(r'/(skillring|sr|costume|cs|camouflage|cmf) +([^ ]+)', mess)
    if _:
        item = _.group(2)
        talk(f'{name}が{item}を装備した')

    txt = chatcmd.strip(mess)
    if txt:
        talk(f'{name}「{txt}」')


def handle_SymbolChat(ent):
    time, seq, channel, id, name, said = ent[:6]
    chat_print(ent, said)
    talk(f'{name}のシンボルアート')


# pickup = ItemCounter()

report = DelayedReporter()
report.start()


def pushitem(item, num):
    # pickup.add(item, num)
    report.put(item, num)
    spitem_check_and_notify(item)


def handle_Reward(ent):
    """ Reward
    """
    item, num = ent[5], ent.Num
    pushitem(item, num)
    pyperclip.copy(item)


def handle_Action(ent):
    """ Action
    """
    act, item, num, meseta = ent[2], ent[5], ent.Num, ent.Meseta
    num = 1 if num is None else num

    if act == '[DisplayToShop-SetValue]':
        return

    if act == '[Warehouse-Meseta]':
        return

    if act == '[Pickup]' and meseta is None:
        pushitem(item, num)

    # if 'Sell' in act and meseta is None:
    #     pickup.add(item, -num)

    if meseta:
        pushitem('メセタ', meseta)


def handle_Craft(ent):
    """ Craft
    """
    act, item, num = ent[2], ent[5], ent.Num
    if 'Material' in act and num is not None:
        pushitem(item, num)


def handle_Scratch(ent):
    """ Scratch
    """
    # 0                     1   2                           3           4           5           6                           7
    # 2020-02-04T22:23:40	209	アウェイクアドミニスター	Received	14386271	モモーロ	574「スクナヒメポーズ２」	Num(1)
    if 'Received' in ent[3]:
        item, num = ent[6], ent.Num
        pushitem(item, num)


handle_Amusement = CasinoCounter()


def on_entry(ent):
    # print(ent)
    g = globals()
    name = 'handle_' + ent.category
    if name in g:
        fn = g[name]
        fn(ent)


def main():
    ctypes.windll.kernel32.SetConsoleTitleW("PSO2 Log Reader")
    pumpz = logpump.LogPumpz(on_entry)
    pumpz.start()
    print(Fore.GREEN + "START")
    try:
        while True:
            line = input().strip()
            if line == "exit":
                break
    except KeyboardInterrupt:
        pass
    pumpz.stop()
    print("done")


# %%
if __name__ == "__main__":
    main()
