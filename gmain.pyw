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

import logpump
import main as Main

logger = logging.getLogger(__name__)


class LogView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid(sticky="news")
        self.createWidget()
        self.q = queue.Queue()

    def createWidget(self):
        text = tk.Text(self)
        text.configure(bg='black', fg='white')
        text.pack(side="left", fill="both")

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
        # ysb.grid(row=0, column=1, sticky="ns")
        ysb.pack(side="right", fill="y")

        text.configure(yscrollcommand=ysb.set,
                       font=Font(family='メイリオ', size=12))

        self.pack(fill="both")

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
    singleton = None

    itemz = [
        ('拾得物を読み上げ', 100),
        ('カジノ遊戯の状況を読み上げ', 101),
        ('ロビアクを読み上げ', 102),
        ('装備を読み上げ', 103),
        ('シンボルアートを読み上げ', 104),
        ('報酬アイテム名をクリップボードへコピー', 200),
        ('ロビアクのコマンドをクリップボードへコピー', 201),
        ('ロビアクのチケット名をクリップボードへコピー', 202),
        ('特定アイテムを獲得した時にサウンドを再生', 300),
        ('特定アイテムを獲得した時に読み上げ', 105),
        ('倉庫送りを検出した時に警告サウンドを再生', 301),
    ]

    exclusion = [{201, 202}]

    def __init__(self, master):
        ConfigUI.singleton = self
        super(ConfigUI, self).__init__(master)

        self.boolvars = {}
        self.boolvars2 = {}
        for row, iten in enumerate(self.itemz):
            text, code = iten
            bv = tk.BooleanVar()
            cb = tk.Checkbutton(
                self, text=text, variable=bv, command=self.test)
            cb.grid(column=0, row=row, sticky="w")
            setattr(cb, "ud_code", code)
            cb.bind("<1>", self.on_click)
            self.boolvars[code] = bv
            self.boolvars2[code] = False

        self.pack(fill="both")
        self.load_config()

    last_code = 0

    def on_click(self, event):
        self.last_code = event.widget.ud_code

    def check(self, code, **kwargs):
        return self.boolvars2[code]

    def test(self):
        code = self.last_code

        if self.boolvars[code].get():
            for xset in self.exclusion:
                if code in xset:
                    for xcode in xset - {code}:
                        self.boolvars[xcode].set(False)
                        self.boolvars2[xcode] = False

        # print(f"{code}:", "on" if self.check(code) else "off")
        for key, var in self.boolvars.items():
            self.boolvars2[key] = var.get()

    config_path = Path(__file__).with_name("config.json")

    def save_config(self):
        with self.config_path.open("wt", encoding="utf-8") as fp:
            obj = {
                "on": [code
                       for code in self.boolvars2.keys()
                       if self.boolvars2[code]]
            }
            json.dump(obj, fp)

    def load_config(self):
        try:
            with self.config_path.open("rt", encoding="utf-8") as fp:
                obj = json.load(fp)
        except FileNotFoundError:
            return

        print(obj)

        for code in obj["on"]:
            try:
                self.boolvars[code].set(True)
                self.boolvars2[code] = True
            except KeyError:
                pass


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
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self.view = {}

        notebook = ttk.Notebook(self)
        for tag, name in self.viewz:
            view = LogView(notebook)
            notebook.add(view, text=name)
            self.view[tag] = view

        config = ConfigUI(notebook)
        self.config = config
        notebook.add(config, text="設定")
        notebook.pack(fill="both")

        # self.sv = sv = tk.StringVar()
        # tk.Label(self, bd=1, textvariable=sv,
        #          relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)
        # statusbar.grid(row=1, column=0, sticky="we")

        setattr(Main, "get_config", config.check)
        setattr(Main, "chat_print", self.chat_print)
        setattr(Main, "info_print", self.info_print)

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

        self.keep_running = True
        while self.keep_running:
            self.update()

            # viewに溜まったqueueを処理する
            for view in self.view.values():
                view.update()

            if not q.empty():
                Main.on_entry(q.get())

            time.sleep(0.2)
            # self.sv.set(datetime.datetime.now())

        self.destroy()
        Main.report.stop()
        pump.stop()
        self.config.save_config()


def main():
    os.chdir(Path(__file__).parent)

    appmtx = ctypes.windll.kernel32.CreateMutexW(None, False, 'PSO2LogReadr')

    if ctypes.windll.kernel32.GetLastError() != 0:
        ctypes.windll.user32.MessageBoxW(
            None, "すでに起動しています", "PSO2LogReadr", 0x10)
        exit(1)

    App().mainloop()

    ctypes.windll.kernel32.ReleaseMutex(appmtx)


if __name__ == '__main__':
    main()
