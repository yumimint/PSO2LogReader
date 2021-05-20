import ctypes.wintypes
import json
import logging
import queue
import tkinter as tk
import webbrowser
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


class ToolTip():
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Motion>", self.motion)
        self.widget.bind("<Leave>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event):
        self.schedule()

    def motion(self, event):
        self.unschedule()
        self.schedule()

    def leave(self, event):
        self.unschedule()
        self.id = self.widget.after(500, self.hideTooltip)

    def schedule(self):
        if self.tw:
            return
        self.unschedule()
        self.id = self.widget.after(500, self.showTooltip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showTooltip(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)
        x, y = self.widget.winfo_pointerxy()
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.geometry(f"+{x+10}+{y+10}")
        label = tk.Label(self.tw, text=self.text, background="lightyellow",
                         relief="solid", borderwidth=1, justify="left")
        label.pack(ipadx=10)

    def hideTooltip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()


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


def tk_scale_button1(event):
    # https://stackoverflow.com/questions/42817599/force-tkinter-scale-slider-to-snap-to-mouse/42819712
    event.widget.event_generate('<3>', x=event.x, y=event.y)
    return 'break'


def fix_tk_scale_behavior(widget):
    widget.bind('<1>', tk_scale_button1)


class ConfigUI(ttk.Frame):
    itemz = [
        # (code, text)
        (100, '獲得したメセタ・アイテムを集計して読み上げ', None),
        (101, 'カジノ遊戯の状況を読み上げ', None),
        (102, 'ロビアクを読み上げ', "○○が××した"),
        (103, '装備を読み上げ',
         "/skillring /costume /camouflage"),
        (104, 'シンボルアートを読み上げ', "○○のシンボルアート"),
        (200, '報酬アイテム名をクリップボードへコピー', None),
        (203, 'リアクション対応ロビアクを見つけたら"/la reaction"をクリップボードへコピー',
         None),
        (201, 'ロビアクのコマンドをクリップボードへコピー',
         "コマンドがコピーされます。"
         "\nロビアクを手動で真似したいときに便利です。"),
        (202, 'ロビアクのチケット名をクリップボードへコピー',
         "チケット名がコピーされます。"
         "\nマイショップで検索するときに便利です。"),
        (300, '特定アイテムを獲得した時にサウンドを再生', None),
        (105, '特定アイテムを獲得した時に読み上げ', None),
        (301, '倉庫送りを検出した時に警告サウンドを再生', None),
    ]

    exclusion = [{201, 202}]

    def __init__(self, master):
        super(ConfigUI, self).__init__(master, padding=10)

        self.boolvars = {}
        frame = ttk.LabelFrame(self, text="機能")
        for row, iten in enumerate(self.itemz):
            code, text, tip = iten
            bv = tk.BooleanVar()
            cb = tk.Checkbutton(
                frame, text=text, variable=bv, command=self.checkbox_modified)
            cb.grid(column=0, row=row, sticky="w")
            setattr(cb, "ud_code", code)
            cb.bind("<1>", self.on_click)
            self.boolvars[code] = [bv, False]
            if tip:
                ToolTip(cb, tip)
        frame.pack(fill=tk.X)

        frame = ttk.LabelFrame(self, padding=10, text="サウンド")
        _ = ttk.Label(frame, text="音量")
        _.pack(side=tk.LEFT)

        self.vol = tk.DoubleVar()
        _ = ttk.Scale(frame, variable=self.vol, length=200)
        _.pack(side=tk.LEFT, padx=24)
        fix_tk_scale_behavior(_)

        _ = ttk.Button(frame, text="テスト", command=Main.sound_test)
        _.pack(side=tk.LEFT)
        frame.pack(fill=tk.X)

        url = "https://github.com/yumimint/PSO2LogReader"
        _ = ttk.Label(self, text=url, foreground="blue", cursor="hand2")
        _.bind("<1>", lambda event: webbrowser.open(url))
        _.pack(side=tk.BOTTOM)

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
