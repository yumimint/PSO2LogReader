import collections
import csv
import io
import logging
import pathlib
import re
import threading
import time
import urllib.request


class UsersFile:
    data = {}

    def __init__(self, path, loader):
        self.mtime = 0
        self.path = pathlib.Path(path)
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
                continue

            dic[line] = current_audio
    logging.info(str(path) + " loaded")
    return dic


def la_dict_loader(path):
    with path.open(encoding='utf-8') as f:
        dic = read_la_dict(f)
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


def load_la_dict_online():
    url = 'https://raw.githubusercontent.com/yumimint/PSO2LogReader/main/lobbyactions.csv'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as src:
            f = io.TextIOWrapper(io.BytesIO(src.read()), encoding="utf-8")
        logging.info("lobbyactions.csv downloaded.")

    except Exception as e:
        logging.warning(e)
        return {}

    return read_la_dict(f)


class TalkativesDetector:
    """おしゃべり過多検出器"""

    def __init__(self, period=60):
        self.od = collections.OrderedDict()
        self.period = period

    def __call__(self, text):
        """一定期間内に同じtextがあればTrueを返す"""
        now = time.time()
        self.forget(now - self.period)
        exists = text in self.od
        self.od[text] = now
        self.od.move_to_end(text, last=True)
        return exists

    def forget(self, expiry):
        for t in list(self.od.values()):
            if t > expiry:
                break
            self.od.popitem(last=False)


class CasinoCounter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.count = 0
        self.bet = 0
        self.ret = 0
        self.hit = 0
        self.defeats = 0
        self.defeats_max = 0

    def update(self, bet, ret):
        self.count += 1
        self.bet += bet
        self.ret += ret
        if ret == 0:
            self.defeats += 1
            self.defeats_max = max(self.defeats_max, self.defeats)
        else:
            self.defeats = 0
            self.hit += 1

    @property
    def rate(self):
        if self.bet == 0:
            return 0
        return self.ret / self.bet

    @property
    def hitrate(self):
        if self.count == 0:
            return 0
        return self.hit / self.count

    @property
    def income(self):
        return self.ret - self.bet


class ItemCounter(dict):
    def add(self, item, num):
        if item not in self:
            self[item] = 0
        self[item] += num

    def sorted_items(self):
        ls = list(filter(lambda x: x[1] > 0, self.items()))
        ls.sort(key=lambda x: (-x[1], x[0]))
        return ls

    units = [
        (lambda item: re.search(r'(券|メダル|バッヂ|パス)', item) is not None, '枚'),
        (lambda item: '肉' in item, 'Kg'),
    ]

    @staticmethod
    def pair2name(pair):
        item, num = pair
        # item = item.translate(ItemCounter.zen2han_alpha)
        if item == 'メセタ':
            return f'{num:,}メセタ'
        if num == 1:
            return item
        unit = "個"
        for _ in ItemCounter.units:
            if _[0](item):
                unit = _[1]
                break
        return f'{item}({num}{unit})'

    # zen2han_alpha = str.maketrans(
    #     {chr(0xFF01 + i): chr(0x21 + i) for i in range(93)})


class DelayedReporter:
    delay = 30

    def __init__(self, callback):
        self.callback = callback
        self.counter = ItemCounter()
        self.added = threading.Event()
        self.mutex = threading.Lock()
        self.expiry = 0
        self.th = threading.Thread(target=self.main, daemon=True)

    def start(self):
        self.keep_running = True
        self.th.start()

    def stop(self):
        self.keep_running = False
        self.th.join()

    def put(self, item, num):
        with self.mutex:
            self.counter.add(item, num)
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
                counter = self.counter
                self.counter = ItemCounter()

            self.callback(counter)
