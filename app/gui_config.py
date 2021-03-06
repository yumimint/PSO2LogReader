import tkinter as tk
import tkinter.ttk as ttk
import webbrowser

from . import main as Main
from .gui_tooltip import ToolTip

itemz = [
    # (code, text)
    (100, '獲得したメセタ・アイテムを集計して読み上げ', None),
    (101, 'カジノ遊戯の状況を読み上げ', None),
    (102, 'ロビアクを読み上げ', "○○が××した"),
    (103, '装備を読み上げ',
        "/skillring /costume /camouflage"),
    (104, 'シンボルアートを読み上げ', "○○のシンボルアート"),
    (105, 'スタンプを読み上げ', "○○のスタンプ"),
    (200, '報酬アイテム名をクリップボードへコピー', None),
    (203, 'リアクション対応ロビアクを見つけたら"/la reaction"をクリップボードへコピー',
        None),
    (300, '特定アイテムを獲得した時にサウンドを再生', None),
    (105, '特定アイテムを獲得した時に読み上げ', None),
    (301, '倉庫送りを検出した時に警告サウンドを再生', None),
]


class ConfigPane(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=32)

        self.boolvars = {}
        frame = ttk.LabelFrame(self, text="機能")
        for row, iten in enumerate(itemz):
            code, text, tip = iten
            bv = tk.BooleanVar()
            cb = tk.Checkbutton(frame, text=text, variable=bv)
            cb.grid(column=0, row=row, sticky="w")
            self.boolvars[code] = bv
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

        setattr(Main, "get_config", self.check)
        setattr(Main, "get_volume", self.vol.get)

    def check(self, code):
        return self.boolvars[code].get()

    def store(self, conf):
        conf.on = [
            code
            for code, var in self.boolvars.items()
            if var.get()
        ]
        conf.volume = self.vol.get()

    def load(self, conf):
        for code in conf.on:
            try:
                self.boolvars[code].set(True)
            except KeyError:
                pass
        self.vol.set(conf.volume)


def tk_scale_button1(event):
    # https://stackoverflow.com/questions/42817599/force-tkinter-scale-slider-to-snap-to-mouse/42819712
    event.widget.event_generate('<3>', x=event.x, y=event.y)
    return 'break'


def fix_tk_scale_behavior(widget):
    widget.bind('<1>', tk_scale_button1)


if __name__ == '__main__':
    root = tk.Tk()
    demo = ConfigPane(root)
    root.mainloop()
