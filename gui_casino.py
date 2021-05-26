import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import main as Main


class CasinoPane(tk.Frame):
    singleton = None

    def __init__(self, master):
        CasinoPane.singleton = self
        super().__init__(master)
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
