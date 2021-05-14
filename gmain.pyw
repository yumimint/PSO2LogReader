import ctypes.wintypes
import json
import logging
import os
import queue
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter.font import Font

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import logpump
import main as Main

logger = logging.getLogger(__name__)


class LogView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        # self.rowconfigure(0, weight=1)
        # self.columnconfigure(0, weight=1)
        self.createWidget()
        self.q = queue.Queue()  # スレッドセーフにするためのキュー

    def createWidget(self):
        text = tk.Text(self)
        text.configure(bg='black', fg='white')
        text.grid(row=0, column=0, sticky="news")

        for name, color in [
            ('PUBLIC', '#ffffff'),
            ('GROUP', '#88ff88'),
            ('REPLY', '#ff88ff'),
            ('GUILD', 'orange'),
            ('PARTY', 'cyan'),
            ('info', 'yellow'),
        ]:
            text.tag_configure(name, foreground=color)

        ysb = ttk.Scrollbar(self, orient='vertical', command=text.yview)
        ysb.grid(row=0, column=1, sticky="ns")

        text.configure(yscrollcommand=ysb.set,
                       font=Font(family='メイリオ', size=12))

        self.text = text
        self.ysb = ysb

    def append(self, text, tag):
        self.q.put((text, tag))

    def update(self):
        while not self.q.empty():
            text, tag = self.q.get()
            pos = self.ysb.get()
            follow = pos[1] > 0.99
            self.text.configure(state='normal')
            self.text.insert('end', text, tag)
            self.text.configure(state='disabled')
            if follow:
                self.text.see('end')


class ConfigUI(tk.Frame):
    itemz = [
        # (code, text)
        (100, '拾得物を読み上げ'),
        (101, 'カジノ遊戯の状況を読み上げ'),
        (102, 'ロビアクを読み上げ'),
        (103, '装備を読み上げ'),
        (104, 'シンボルアートを読み上げ'),
        (200, '報酬アイテム名をクリップボードへコピー'),
        (201, 'ロビアクのコマンドをクリップボードへコピー'),
        (202, 'ロビアクのチケット名をクリップボードへコピー'),
        (300, '特定アイテムを獲得した時にサウンドを再生'),
        (105, '特定アイテムを獲得した時に読み上げ'),
        (301, '倉庫送りを検出した時に警告サウンドを再生'),
    ]

    exclusion = [{201, 202}]
    config_path = Path(__file__).with_name("config.json")

    def __init__(self, master):
        super(ConfigUI, self).__init__(master)

        self.boolvars = {}
        for row, iten in enumerate(self.itemz):
            code, text = iten
            bv = tk.BooleanVar()
            cb = tk.Checkbutton(
                self, text=text, variable=bv, command=self.checkbox_modified)
            cb.grid(column=0, row=row, sticky="w", ipadx=8)
            setattr(cb, "ud_code", code)
            cb.bind("<1>", self.on_click)
            self.boolvars[code] = [bv, False]

        self.pack(expand=1)
        self.load()

    def on_click(self, event):
        self.last_code = event.widget.ud_code

    def check(self, code, *args):
        return self.boolvars[code][1]

    def checkbox_modified(self):
        code = self.last_code
        v = self.boolvars[code]
        v[1] = v[0].get()

        # 排他制御
        if v[1]:
            for xset in self.exclusion:
                if code in xset:
                    for xcode in xset - {code}:
                        v = self.boolvars[xcode]
                        v[0].set(False)
                        v[1] = False

    def save(self):
        obj = {
            "on": [code
                   for code in self.boolvars.keys()
                   if self.boolvars[code][1]]
        }
        with self.config_path.open("wt", encoding="utf-8") as fp:
            json.dump(obj, fp)

    def load(self):
        try:
            with self.config_path.open("rt", encoding="utf-8") as fp:
                obj = json.load(fp)
        except FileNotFoundError:
            return

        for code in obj["on"]:
            try:
                self.boolvars[code][0].set(True)
                self.boolvars[code][1] = True
            except KeyError:
                pass


class CasinoCoinFig(tk.Frame):
    singleton = None

    def __init__(self, master):
        CasinoCoinFig.singleton = self
        super(CasinoCoinFig, self).__init__(master)

        fig = Figure()
        canvas = FigureCanvasTkAgg(fig, self)
        self.canvas = canvas

        self.plt = fig.add_subplot(111)
        # self.toolbar = NavigationToolbar2Tk(canvas, self)
        # self.toolbar.update()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.pack(expand=1)

    @classmethod
    def plot(cls, *args):
        self = cls.singleton
        self.plt.plot(*args)
        self.canvas.draw()


class App(tk.Tk):
    viewz = [
        ('ALL', '全て'),
        ('PUBLIC', '周囲'),
        ('PARTY', 'パーティー'),
        ('GUILD', 'チーム'),
        ('GROUP', 'グループ'),
        ('REPLY', 'ウィスパー'),
        ('info', 'アイテム'),
    ]

    def __init__(self):
        super(App, self).__init__()
        self.title('PSO2LogReadr')
        # self.geometry('400x600')
        self.createWidget()
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        setattr(Main, "get_config", self.config.check)
        setattr(Main, "chat_print", self.chat_print)
        setattr(Main, "info_print", self.info_print)

    def createWidget(self):
        frame = self
        self.view = {}

        notebook = ttk.Notebook(frame)

        for tag, name in self.viewz:
            view = LogView(notebook)
            notebook.add(view, text=name)
            self.view[tag] = view

        self.ccfig = CasinoCoinFig(notebook)
        notebook.add(self.ccfig, text="カジノ")

        self.config = ConfigUI(notebook)
        notebook.add(self.config, text="設定")

        notebook.enable_traversal()
        notebook.pack(expand=1)

    def close_window(self):
        self.keep_running = False

    def chat_print(self, ent, text):
        time, seq, channel, id, name = ent[:5]

        time = time[-8:]
        channel = 'GROUP' if channel == 'CHANNEL' else channel

        text = f"{time} {name} {text}\n"
        self.view['ALL'].append(text, channel)
        try:
            self.view[channel].append(text, channel)
        except KeyError:
            pass

    def info_print(self, text):
        self.view['info'].append(text + "\n", "info")

    def mainloop(self):
        q = queue.Queue()
        pump = logpump.LogPump(q.put)
        pump.start()
        Main.report.start()
        ccy = []

        self.keep_running = True
        while self.keep_running:
            self.update()

            # viewに溜まったqueueを処理する
            for view in self.view.values():
                view.update()

            while not q.empty():
                ent = q.get()
                Main.on_entry(ent)
                if ent.category == "Amusement":
                    ccy.append(int(ent[-2]))
                    CasinoCoinFig.plot(range(len(ccy)), ccy)

            time.sleep(0.1)

        self.destroy()
        Main.report.stop()
        pump.stop()
        self.config.save()


def main():
    os.chdir(Path(__file__).parent)
    ctypes.windll.kernel32.SetConsoleTitleW("PSO2LogReader")
    appmtx = ctypes.windll.kernel32.CreateMutexW(None, False, 'PSO2LogReadr')

    if ctypes.windll.kernel32.GetLastError() != 0:
        ctypes.windll.user32.MessageBoxW(
            None, "すでに起動しています", "PSO2LogReadr", 0x10)
        exit(1)

    App().mainloop()

    ctypes.windll.kernel32.ReleaseMutex(appmtx)


if __name__ == '__main__':
    main()
