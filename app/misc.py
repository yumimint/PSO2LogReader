import collections
import csv
import heapq
import io
import logging
import pathlib
import re
import statistics
import time
import urllib.request

logger = logging.getLogger(__name__)


class UsersFile:
    data = None

    def __init__(self, filename, loader, loader2=None):
        self.mtime = 0
        self.path = pathlib.Path(filename)
        self.loader = loader
        self.loader2 = loader2

    def __call__(self):
        try:
            t = self.path.stat().st_mtime
            if self.mtime < t:
                self.data = self.loader(self.path)
                self.mtime = t
        except FileNotFoundError:
            if self.data is None and self.loader2 is not None:
                self.data = self.loader2()
        return self.data


class SpItem(dict):
    def __init__(self):
        self.rex = set()
        self.sounds = set()

    @classmethod
    def load(cls, path):
        self = cls()
        current_audio = None
        with path.open(encoding="utf-8") as f:
            for line in f.readlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_audio = line[1:-1]
                    self.sounds.add(current_audio)
                    continue
                if line.startswith("/") and line.endswith("/"):
                    pattern = re.compile(line[1:-1])
                    self.rex.add((pattern, current_audio))
                    continue
                self[line] = current_audio
        logger.info(str(path) + " loaded")
        return self


def la_dict_loader(path):
    with path.open(encoding='utf-8') as f:
        dic = LaDict.load(f)
    logger.info(str(path) + " loaded")
    return dic


LobbyAction = collections.namedtuple("LobbyAction", "name cmd note")


class LaDict(dict):
    @classmethod
    def load(cls, f):
        dic = cls()
        f.readline()  # skip header line
        for row in csv.reader(f):
            # 0:名称 1:コマンド 2:ループ 3:リアクション対応 4:トレード不可 5:指の動きに対応 6:入手
            if len(row) < 4:
                continue
            name, cmd = row[:2]
            if not cmd:
                continue
            note = []
            if row[2] == "1":
                note.append("Loop")
            if row[3] == "1":
                note.append("Reaction")
            if row[4] == "1":
                note.append("NoTrade")
            if row[5] == "1":
                note.append("Finger")
            dic[cmd] = LobbyAction(name, cmd, " ".join(note))
        return dic

    def __call__(self, cmd):
        if cmd not in self:
            return None
        return self[cmd]


def load_la_dict_online():
    url = 'https://raw.githubusercontent.com/yumimint/PSO2LogReader/main/lobbyactions.csv'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as src:
            f = io.TextIOWrapper(io.BytesIO(src.read()), encoding="utf-8")
        logger.info("lobbyactions.csv downloaded.")

    except Exception as e:
        logger.warning(e)
        return {}

    return LaDict.load(f)


class TalkativesDetector:
    """おしゃべり過多検出器"""

    def __init__(self):
        self.heap = []

    def __call__(self, text, period=60):
        """一定期間内に同じtextがあればTrueを返す"""
        now = time.time()
        self.forget(now)
        exists = any(map(lambda x: x[1] == text, self.heap))
        heapq.heappush(self.heap, (now + period, text))
        return exists

    def forget(self, expiry):
        heap = self.heap
        while heap and heap[0][0] < expiry:
            heapq.heappop(heap)


class CasinoCounter:
    def __init__(self):
        self.deq = collections.deque(maxlen=30)
        self.reset()

    def reset(self):
        self.count = 0
        self.bet = 0
        self.ret = 0
        self.hit = 0
        self.defeats = 0
        self.defeats_max = 0
        self.deq.clear()

    def update(self, bet, ret):
        self.count += 1
        self.bet += bet
        self.ret += ret
        self.deq.append(min(1, ret))
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
        # return self.hit / self.count
        return statistics.mean(self.deq)

    @property
    def income(self):
        return self.ret - self.bet


class ItemCounter(collections.Counter):
    def add(self, item, num):
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
        if item.endswith('メセタ'):
            return f'{num:,}メセタ'
        if num == 1:
            return item
        unit = "個"
        for _ in ItemCounter.units:
            if _[0](item):
                unit = _[1]
                break
        return f'{item}({num}{unit})'


class DelayedReporter:
    delay = 30

    def __init__(self, callback):
        self.callback = callback
        self.counter = ItemCounter()
        self.expiry = 0
        self.added = False
        self.coro = self.main()

    def update(self):
        next(self.coro)

    def put(self, item, num):
        self.counter.add(item, num)
        self.expiry = time.time() + self.delay
        self.added = True

    def main(self):
        while True:
            while not self.added:
                yield

            while self.added:
                self.added = False
                while time.time() < self.expiry:
                    yield

            counter = self.counter
            self.counter = ItemCounter()

            self.callback(counter)
