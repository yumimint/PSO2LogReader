import ctypes.wintypes
import json
import logging
import queue
from ssl import OPENSSL_VERSION
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import logpump
import main as Main

# from tkinter.font import Font


# matplotlib.use('TkAgg')
logger = logging.getLogger(__name__)

config_path = Path(__file__).with_name("config.json")

try:
    with config_path.open("rt", encoding="utf-8") as fp:
        config_obj = json.load(fp)
    del fp
except FileNotFoundError:
    config_obj = {
        "on": [100, 101, 102, 103, 104, 300, 105, 301],
        "volume": 0.25,
    }


class LogView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid(sticky=tk.NSEW)
        self.q = queue.Queue()  # スレッドセーフにするためのキュー

        text = tk.Text(self,
                       state='disabled',
                       foreground="white",
                       background="black",
                       )
        text.grid(row=0, column=0, sticky=tk.NSEW)

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
        text.configure(yscrollcommand=ysb.set)
        ysb.grid(row=0, column=1, sticky=tk.NS)

        self.text = text
        self.ysb = ysb

        # self.popup_menu = tk.Menu(text, tearoff=0)
        # self.popup_menu.add_command(label="ログを消去",
        #                             command=self.delete_selected)
        # self.popup_menu.add_command(label="Select All",
        #                             command=self.select_all)
        # text.bind("<Button-3>", self.popup)

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    # def delete_selected(self):
    #     self.text.delete("end")

    # def select_all(self):
    #     print(self.text.info())

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


class ConfigUI(ttk.Frame):
    itemz = [
        # (code, text)
        (100, '獲得したメセタ・アイテムを集計して読み上げ'),
        (101, 'カジノ遊戯の状況を読み上げ'),
        (102, 'ロビアクを読み上げ'),
        (103, '装備を読み上げ'),
        (104, 'シンボルアートを読み上げ'),
        (200, '報酬アイテム名をクリップボードへコピー'),
        (203, 'リアクション対応ロビアクを見つけたら"/la reaction"をクリップボードへコピー'),
        (201, 'ロビアクのコマンドをクリップボードへコピー'),
        (202, 'ロビアクのチケット名をクリップボードへコピー'),
        (300, '特定アイテムを獲得した時にサウンドを再生'),
        (105, '特定アイテムを獲得した時に読み上げ'),
        (301, '倉庫送りを検出した時に警告サウンドを再生'),
    ]

    exclusion = [{201, 202}]

    def __init__(self, master):
        super(ConfigUI, self).__init__(master)

        self.boolvars = {}
        frame = ttk.Frame(self)
        for row, iten in enumerate(self.itemz):
            code, text = iten
            bv = tk.BooleanVar()
            cb = tk.Checkbutton(
                frame, text=text, variable=bv, command=self.checkbox_modified)
            cb.grid(column=0, row=row, sticky="w")
            setattr(cb, "ud_code", code)
            cb.bind("<1>", self.on_click)
            self.boolvars[code] = [bv, False]
        frame.pack(fill=tk.X)

        ttk.Label(self, text="音量").pack(side=tk.LEFT)
        self.vol = tk.DoubleVar()
        ttk.Scale(self, variable=self.vol).pack(side=tk.LEFT)
        ttk.Button(self, text="サウンドテスト",
                   command=Main.sound_test).pack(side=tk.LEFT)

        self.pack(expand=True)
        self.load(config_obj)

    def on_click(self, event):
        self.last_code = event.widget.ud_code

    def check(self, code):
        # スレッドセーフ
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

    def store(self, obj):
        obj["on"] = [
            code
            for code in self.boolvars.keys()
            if self.boolvars[code][1]
        ]
        obj["volume"] = self.vol.get()

    def load(self, obj):
        for code in obj["on"]:
            try:
                self.boolvars[code][0].set(True)
                self.boolvars[code][1] = True
            except KeyError:
                pass
        if "volume" in obj:
            self.vol.set(obj["volume"])


class CasinoCoinFig(tk.Frame):
    singleton = None

    def __init__(self, master):
        CasinoCoinFig.singleton = self
        super(CasinoCoinFig, self).__init__(master)
        self.pack(expand=True)

        # ステータスバー
        statusline = tk.StringVar()
        setattr(Main, "casino_stateus", lambda text: statusline.set(text))
        self.label = tk.Label(self, textvariable=statusline,
                              bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.label.pack(side=tk.BOTTOM, fill=tk.X)

        # matplotlib
        self.fig = Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        widget = self.canvas.get_tk_widget()

        widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        # self.toolbar.update()

        # context menu
        self.popup_menu = tk.Menu(widget, tearoff=0)
        self.popup_menu.add_command(label="カウンタをリセット",
                                    command=Main.casinocounter.reset)
        self.popup_menu.add_command(label="グラフをリセット",
                                    command=self.cc_reset)
        widget.bind("<Button-3>", self.popup)

        self.cc_reset()

    def popup(self, event):
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def cc_reset(self):
        self.income = []
        self.hitrate = []
        self.cccount = None
        self.draw()

    def update(self):
        cc = Main.casinocounter
        if self.cccount != cc.count:
            self.cccount = cc.count
            self.income.append(cc.income)
            self.hitrate.append(cc.hitrate)
            self.draw()

    def draw(self):
        fig = self.fig
        fig.clear()
        plt1 = fig.add_subplot(211)
        plt2 = fig.add_subplot(212)
        plt1.set_ylabel("INCOME")
        plt2.set_ylabel("HIT RATE")
        plt1.plot(range(len(self.income)), self.income, "red")
        plt2.plot(range(len(self.hitrate)), self.hitrate, "blue")
        fig.canvas.draw()
        fig.canvas.flush_events()


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
        self.iconbitmap(Path(__file__).with_name("PSO2LogReader.ico"))
        try:
            self.geometry(config_obj["geometry"])
        except KeyError:
            pass
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.view = {}
        notebook = ttk.Notebook(self)
        notebook.enable_traversal()
        notebook.pack(fill=tk.BOTH, expand=True)

        for tag, name in self.viewz:
            view = LogView(notebook)
            notebook.add(view, text=name)
            self.view[tag] = view

        self.ccfig = CasinoCoinFig(notebook)
        notebook.add(self.ccfig, text="カジノ")

        self.config = ConfigUI(notebook)
        notebook.add(self.config, text="設定")

        setattr(Main, "get_config", self.config.check)
        setattr(Main, "get_volume", self.config.vol.get)
        setattr(Main, "chat_print", self.chat_print)
        setattr(Main, "info_print", self.info_print)

    def _close(self):
        self.keep_running = False
        self.config.store(config_obj)
        config_obj["geometry"] = self.geometry()

    def chat_print(self, ent, text):
        time, seq, channel, id, name = ent[: 5]

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

        def loop():
            while not q.empty():
                ent = q.get()
                Main.on_entry(ent)

            # viewに溜まったqueueを処理する
            for view in self.view.values():
                view.update()

            self.ccfig.update()

            if self.keep_running:
                self.after(500, loop)
            else:
                self.destroy()

        self.after(500, loop)

        super(App, self).mainloop()

        Main.report.stop()
        pump.stop()


def main():
    ctypes.windll.kernel32.SetConsoleTitleW("PSO2LogReader")
    appmtx = ctypes.windll.kernel32.CreateMutexW(None, False, 'PSO2LogReadr')

    if ctypes.windll.kernel32.GetLastError() != 0:
        ctypes.windll.user32.MessageBoxW(
            None, "すでに起動しています", "PSO2LogReadr", 0x10)
        exit(1)

    App().mainloop()

    with config_path.open("wt", encoding="utf-8") as fp:
        json.dump(config_obj, fp)

    ctypes.windll.kernel32.ReleaseMutex(appmtx)


if __name__ == '__main__':
    main()
