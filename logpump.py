import csv
import functools
import heapq
import logging
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


logger = logging.getLogger(__name__)


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
        logger.debug(f'LogFile({self.path.stem}, {newfile}) pos={self.pos}')

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
                logger.debug(f'{self.path.stem}: {e}')
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
            logger.warning(f'Drop {drop}')
        return expect

    def main():
        heap = []
        expect = None
        while True:
            entry = yield

            if expect is None or entry.sequence < expect:
                if expect is not None:
                    logger.info(f'sequense restart ({entry.sequence})')
                    flush(heap, expect)
                expect = entry.sequence

            heapq.heappush(heap, entry)
            while heap and heap[0].sequence == expect:
                entry = heapq.heappop(heap)
                callback(entry)
                expect += 1

            if heap:
                pend = ','.join(map(str, sorted([x.sequence for x in heap])))
                logger.debug(f"expect:{expect} pend:{pend}")
                ts = [x.timestamp for x in heap]
                if (max(ts) - min(ts)) > 3:
                    expect = flush(heap, expect)

    coro = main()
    next(coro)
    return coro.send


class LogFolder:
    def __init__(self, path, callback):
        logger.debug(f'LogFolder({str(path)})')
        self.path = path
        self.callback = seqregurator(callback)

        logs = list(self.path.glob("*Log*.txt"))
        categories = set([LogFile.cate(x.stem) for x in logs])

        def newestof(cate):
            logs_cate = filter(lambda x: x.stem.startswith(cate), logs)
            return max(logs_cate)

        self.logfiles = {
            str(x): LogFile(x) for x in [newestof(cate) for cate in categories]
        }

    def scan(self):
        for log in self.logfiles.values():
            for row in csv.reader(log.tail(), dialect=csv.excel_tab):
                entry = Entry(row, log.category)
                self.callback(entry)

    def newlog(self, path):
        self.logfiles[path] = LogFile(path, True)

    def remove(self, path):
        try:
            del self.logfiles[path]
            logger.debug('removed ' + path)
        except KeyError:
            pass


class LogPump:
    def __init__(self, callback):
        self.folderz = {}
        sega = MyDocuments().joinpath("SEGA")
        for subpath in [
            'PHANTASYSTARONLINE2/log',
            'PHANTASYSTARONLINE2_NGS/log',
            'PHANTASYSTARONLINE2_NGS/log_ngs',
            'PHANTASYSTARONLINE2_NGS_CBT/log',
            'PHANTASYSTARONLINE2_NGS_CBT/log_ngs',
        ]:
            path = sega.joinpath(subpath)
            if path.is_dir():
                self.folderz[path] = LogFolder(path, callback)

        self.observer = Observer()
        self.observer.schedule(self.Handler(self.folderz),
                               str(sega),
                               recursive=True)
        self.th = threading.Thread(target=self._main, daemon=True)

    class Handler(FileSystemEventHandler):
        def __init__(self, folderz):
            self.folderz = folderz

        def on_created(self, event):
            logger.debug(event)
            if not event.src_path.endswith(".txt"):
                return
            try:
                folder = self.folderz[Path(event.src_path).parent]
                folder.newlog(event.src_path)
            except KeyError:
                pass

        def on_deleted(self, event):
            logger.debug(event)
            if not event.src_path.endswith(".txt"):
                return
            try:
                folder = self.folderz[Path(event.src_path).parent]
                folder.remove(event.src_path)
            except KeyError:
                pass

        on_moved = on_deleted

    def _main(self):
        while self.keep_running:
            for folder in self.folderz.values():
                folder.scan()
            time.sleep(0.3)

    def start(self):
        self.keep_running = True
        self.observer.start()
        self.th.start()

    def stop(self):
        self.keep_running = False
        self.observer.stop()
        self.observer.join()
        self.th.join()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s : %(asctime)s : %(message)s')
    pump = LogPump(print)
    pump.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    pump.stop()
