import tkinter as tk

# https://www.ishikawasekkei.com/index.php/2020/05/17/python-tkinter-gui-programing-tooltip/


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
        # self.id = self.widget.after(500, self.hideTooltip)
        self.hideTooltip()

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
