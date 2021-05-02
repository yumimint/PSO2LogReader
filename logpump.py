import csv
import functools
import heapq
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import PatternMatchingEventHandler
# from watchdog.observers import Observer
# Observerだと意図した動作をしないのでPollingObserverを使う
from watchdog.observers.polling import PollingObserver

Observer = PollingObserver


class Entry(list):
    """ログのエントリを表現するクラス"""

    def __init__(self, row: list, category: str):
        super(Entry, self).__init__(row)
        if len(self) == 3:
            cols = self.pop().split("\t")
            self.extend(cols)
        self.append(category)
        self.timestamp = self.str2ts(self[0])
        self.sequence = int(self[1])

    def __eq__(self, other):
        return self.sequence == other.sequence

    def __lt__(self, other):
        return self.sequence < other.sequence

    def __str__(self):
        return " | ".join(self)

    @staticmethod
    @functools.lru_cache(maxsize=8)
    def str2ts(s):
        year = int(s[0:4])
        month = int(s[5:7])
        day = int(s[8:10])
        hour = int(s[11:13])
        minute = int(s[14:16])
        second = int(s[17:19])
        dt = datetime(year, month, day, hour, minute, second)
        # dt = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')
        return int(dt.timestamp())

    @property
    def category(self):
        return self[-1]

    # Meseta,Num等の数値を属性として取得する
    def __getattr__(self, name):
        rx = re.compile(name + r'\((-?\d+)\)')
        for s in filter(lambda x: name in x, self):
            res = rx.search(s)
            if res:
                return int(res.group(1))
        return None


def MyDocuments():
    import ctypes.wintypes
    CSIDL_PERSONAL = 5       # My Documents
    SHGFP_TYPE_CURRENT = 0   # Want current, not default value
    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(
        0, CSIDL_PERSONAL, 0, SHGFP_TYPE_CURRENT, buf)
    return Path(buf.value)


class LogFile:
    """
    ログファイルから未読部分を読み取る
    """

    def __init__(self, path, newfile=False):
        self.path = Path(path)
        self.pos = 2 if newfile else self.path.stat().st_size  # 2=BOM
        self.category = self.cate(self.path.stem)
        logging.debug(f'LogFile({self.path.stem}, {newfile}) pos={self.pos}')

    @staticmethod
    def cate(stem):
        return re.match(r'(.+)(Log|_log)', stem).group(1)

    class IncompleteLineError(Exception):
        def __init__(self):
            super().__init__('IncompleteLineError')

    def tail(self) -> list:
        while True:
            try:
                return self._tail()
            except (UnicodeError, self.IncompleteLineError) as e:
                logging.debug(f'{self.path.stem}: {e}')
                time.sleep(0.5)

    def _tail(self) -> list:
        ls = []
        with self.path.open(encoding='utf-16-le', newline='') as f:
            f.seek(self.pos, 0)
            while True:
                line = f.readline()
                if not line:
                    self.pos = f.tell()
                    return ls
                if not line.endswith('\n'):
                    raise self.IncompleteLineError
                ls.append(line)
                while line.count('"') % 2 == 1:
                    trail = f.readline()
                    if not trail or not trail.endswith('\n'):
                        raise self.IncompleteLineError
                    ls.append(trail)
                    line += trail


def seqregurator(callback):
    """callbackのsequence順を保障するwrapper"""

    def flush(heap, expect):
        drop = []
        while heap:
            entry = heapq.heappop(heap)
            callback(entry)
            drop += list(range(expect, entry.sequence))
            expect = entry.sequence + 1
        if drop:
            drop = ','.join(map(str, drop))
            logging.warning(f'Drop {drop}')
        return expect

    def main():
        heap = []
        expect = None
        while True:
            entry = yield

            if expect is None or entry.sequence < expect:
                if expect is not None:
                    logging.info(f'sequense restart ({entry.sequence})')
                    flush(heap, expect)
                expect = entry.sequence

            heapq.heappush(heap, entry)
            while heap and heap[0].sequence == expect:
                entry = heapq.heappop(heap)
                callback(entry)
                expect += 1

            if heap:
                pend = ','.join(map(str, sorted([x.sequence for x in heap])))
                logging.debug(f"expect:{expect} pend:{pend}")
                ts = [x.timestamp for x in heap]
                if (max(ts) - min(ts)) > 3:
                    expect = flush(heap, expect)

    coro = main()
    next(coro)
    return coro.send


class LogPump:
    """
    - ログファイルが更新されたらcallbackするオブザーバ
    - callback(entry: Entry)
    """

    pattern = '*Log*.txt'

    def __init__(self, path, callback):
        self.path = path
        self.callback = seqregurator(callback)
        event_handler = self.Handler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.path))
        self.initlogs()
        self.count = 0

    def initlogs(self):
        logging.debug('initlogs')
        logs = list(self.path.glob(self.pattern))
        categories = set([LogFile.cate(x.stem) for x in logs])

        def newestof(cate):
            logs_cate = filter(lambda x: x.stem.startswith(cate), logs)
            return max(logs_cate)

        self.logfiles = {
            str(x): LogFile(x) for x in [newestof(cate) for cate in categories]
        }

    class Handler(PatternMatchingEventHandler):
        def __init__(self, parent: 'LogPump'):
            super().__init__(patterns=LogPump.pattern,
                             ignore_directories=True)
            self.parent = parent

        def on_modified(self, event):
            self.parent.on_logupdate(event.src_path)

        def on_deleted(self, event):
            dic = self.parent.logfiles
            if event.src_path in dic:
                del dic[event.src_path]
                logging.debug('removed ' + Path(event.src_path).name)

        on_created = on_modified
        on_moved = on_deleted

    def start(self):
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def on_logupdate(self, path):
        log = self.logfiles.get(path)
        if not log:
            log = LogFile(path, True)
            self.logfiles[path] = log
        for row in csv.reader(log.tail(), dialect=csv.excel_tab):
            self.count += 1
            entry = Entry(row, log.category)
            self.callback(entry)


class LogPumpz:
    def __init__(self, callback):
        self.pumpz = []
        mydoc = MyDocuments()
        for path in [
            'SEGA/PHANTASYSTARONLINE2/log',
            'SEGA/PHANTASYSTARONLINE2_NGS/log',
            'SEGA/PHANTASYSTARONLINE2_NGS/log_ngs',
            'SEGA/PHANTASYSTARONLINE2_NGS_CBT/log',
            'SEGA/PHANTASYSTARONLINE2_NGS_CBT/log_ngs',
        ]:
            path = mydoc.joinpath(path)
            if path.is_dir():
                self.pumpz.append(LogPump(path, callback))

    def start(self):
        for reader in self.pumpz:
            reader.start()

    def stop(self):
        for reader in self.pumpz:
            reader.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s : %(asctime)s : %(message)s')
    pumpz = LogPumpz(print)
    pumpz.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    pumpz.stop()
