import ctypes.wintypes
import json
import queue
import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path

from . import logpump
from . import main as Main
from .gui_casino import CasinoPane
from .gui_config import ConfigPane
from .gui_inventory import InventoryView
from .gui_lalistview import LaListView
from .gui_logview import LogView


class AppConfig:
    _path = Path("config.json")

    on = [100, 101, 102, 103, 104, 105, 300, 105, 301]
    volume = 0.25
    fontsize = 11
    geometry = ""
    rawlog = False

    def load(self):
        try:
            with self._path.open("rt", encoding="utf-8") as fp:
                for attr, val in json.load(fp).items():
                    setattr(self, attr, val)
        except FileNotFoundError:
            pass

    def save(self):
        obj = {
            attr: getattr(self, attr)
            for attr in filter(lambda s: not s.startswith("_"), dir(self))
            if attr not in ["save", "load"]
        }

        with self._path.open("wt", encoding="utf-8") as fp:
            json.dump(obj, fp)


class App(tk.Tk):
    def __init__(self, conf: AppConfig):
        super().__init__()
        self.conf = conf
        self.title('PSO2LogReadr')
        self.iconbitmap("PSO2LogReader.ico")
        self.geometry(conf.geometry)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.view = {}
        notebook = ttk.Notebook(self)
        notebook.enable_traversal()
        notebook.pack(fill=tk.BOTH, expand=True)

        def add_view(tag, name):
            view = LogView(notebook)
            notebook.add(view, text=name)
            self.view[tag] = view
            view.text.bind("<MouseWheel>", self.mouse_wheel)

        for tag, name in [
            ('ALL', '全て'),
            ('PUBLIC', '周囲'),
            ('PARTY', 'パーティー'),
            ('GUILD', 'チーム'),
            ('GROUP', 'グループ'),
            ('REPLY', 'ウィスパー'),
        ]:
            add_view(tag, name)

        self.inventory = InventoryView(notebook)
        notebook.add(self.inventory, text="アイテム")

        self.casino = CasinoPane(notebook)
        notebook.add(self.casino, text="カジノ")

        self.laview = LaListView(notebook)
        notebook.add(self.laview, text="ロビアク")

        self.config = ConfigPane(notebook)
        self.config.load(self.conf)
        notebook.add(self.config, text="設定")

        if self.conf.rawlog:
            add_view("rawlog", "生ログ")

        self.set_viewfontsize(conf.fontsize)
        setattr(Main, "chat_print", self.chat_print)
        setattr(Main, "clipboard", self.clipboard)

    def clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def mouse_wheel(self, event):
        if event.state & 4:  # Ctrl
            fontsize = self.conf.fontsize
            if event.delta > 0:
                fontsize = min(fontsize + 1, 24)
            if event.delta < 0:
                fontsize = max(fontsize - 1, 6)
            if self.conf.fontsize != fontsize:
                self.conf.fontsize = fontsize
                self.set_viewfontsize(fontsize)
            return "break"

    def set_viewfontsize(self, size):
        font = (None, size)
        for view in self.view.values():
            view.text.configure(font=font)

    def _close(self):
        self.keep_running = False
        self.config.store(self.conf)
        self.conf.geometry = self.geometry()

    def chat_print(self, ent, text):
        time, seq, channel, id, name = ent[: 5]

        time = time[-8:]
        channel = 'GROUP' if channel == 'CHANNEL' else channel

        text = f"{time} {name}\n{text}\n"
        self.view['ALL'].append(text, channel)
        try:
            self.view[channel].append(text, channel)
        except KeyError:
            pass

    def mainloop(self):
        q = queue.Queue()
        pump = logpump.LogPump(q.put)
        pump.start()

        self.keep_running = True

        if self.conf.rawlog:
            rawlog = self.view["rawlog"]

            def rawlogger(ent):
                rawlog.append(str(ent) + "\n")
        else:
            def rawlogger(ent):
                pass

        def loop():
            while not q.empty():
                ent = q.get_nowait()
                rawlogger(ent)
                Main.on_entry(ent)

            self.casino.update()
            Main.reporter.update()

            if self.keep_running:
                self.after(500, loop)
            else:
                self.destroy()

        self.after(500, loop)

        super(App, self).mainloop()

        pump.stop()


def main():
    ctypes.windll.kernel32.SetConsoleTitleW("PSO2LogReader")
    appmtx = ctypes.windll.kernel32.CreateMutexW(None, False, 'PSO2LogReadr')

    if ctypes.windll.kernel32.GetLastError() != 0:
        ctypes.windll.user32.MessageBoxW(
            None, "すでに起動しています", "PSO2LogReadr", 0x10)
        exit(1)

    conf = AppConfig()
    conf.load()
    App(conf).mainloop()
    conf.save()

    ctypes.windll.kernel32.ReleaseMutex(appmtx)
