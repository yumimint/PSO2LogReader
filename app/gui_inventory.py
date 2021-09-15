import tkinter as tk
from collections import Counter, OrderedDict
from datetime import datetime
from tkinter import ttk

from . import main as Main


class InventoryView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.pack(expand=True, fill=tk.BOTH)

        notebook = self.notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.counterz = [CountView(notebook)]
        notebook.add(self.counterz[0], text="総計")
        notebook.add(tk.Frame(notebook), text="+")

        popup = self.popup = tk.Menu(self, tearoff=0)
        self.bv = tk.BooleanVar()
        popup.add_checkbutton(
            label="停止", command=self._pause, variable=self.bv)
        popup.add_separator()
        popup.add_command(label="閉じる", command=self._close)

        notebook.bind("<<NotebookTabChanged>>", self._change)
        notebook.bind("<Button-3>", self._button3)
        setattr(Main, "add_inventory", self.add)

    def _close(self):
        self.notebook.forget(self._indx)
        del self.counterz[self._indx]
        self.notebook.select(self._indx - 1)

    def _pause(self):
        state = self.bv.get()
        self.counterz[self._indx].pause = state
        text = self.notebook.tab(self._indx)["text"]
        text = "*" + text if state else text[1:]
        self.notebook.tab(self._indx, text=text)

    def _button3(self, event):
        notebook = self.notebook
        notebook.event_generate("<1>", x=event.x, y=event.y)
        tabs = notebook.tabs()
        indx = tabs.index(notebook.select())
        if indx > 0 and indx < len(tabs) - 1:
            try:
                self._indx = indx
                self.bv.set(self.counterz[self._indx].pause)
                self.popup.tk_popup(event.x_root, event.y_root + 20, 0)
            finally:
                self.popup.grab_release()

    def _change(self, event):
        notebook = self.notebook
        tabs = notebook.tabs()
        # 右端のタブが選択されたらCountViewを追加する
        if tabs[-1] == notebook.select():
            text = datetime.now().strftime("%H:%M:%S")
            cv = CountView(notebook)
            self.counterz.append(cv)
            notebook.insert(len(tabs) - 1, cv, text=text)
            notebook.select(notebook.tabs()[-2])

    def add(self, name, num):
        for c in self.counterz:
            if not c.pause:
                c.add(name, num)


class CountView(tk.Frame):
    dataCols = ["アイテム", "数量"]

    def __init__(self, master):
        super().__init__(master)
        self.pause = False
        self.pack(expand=True, fill=tk.BOTH)

        #################################
        # create the tree and scrollbars
        f = tk.Frame(self)
        f.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.Y)
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(columns=self.dataCols,
                                 show='headings',
                                 selectmode="browse")
        ysb = ttk.Scrollbar(orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        # add tree and scrollbars to frame
        self.tree.grid(in_=f, row=0, column=0, sticky=tk.NSEW)
        ysb.grid(in_=f, row=0, column=1, sticky=tk.NS)
        # configure column headings
        for c in self.dataCols:
            self.tree.heading(c, text=c)
            # self.tree.column(c, width=110)

        self.counter = Counter()
        self.odict = OrderedDict()

        self.tree.bind("<Double-Button-1>", self._dclick)

        popup = self.popup = tk.Menu(self, tearoff=0)
        popup.add_command(label="コピー", command=self._copy)
        self.tree.bind("<Button-3>", self._button3)

    def _copy(self):
        self.clipboard_clear()
        for name, num in self.counter.items():
            text = f"{name}\t{num:,}\n"
            self.clipboard_append(text)

    def _button3(self, event):
        try:
            self.popup.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup.grab_release()

    def _dclick(self, event):
        tree = self.tree
        sel = tree.selection()
        if sel:
            item = tree.set(sel)
            self.clipboard_clear()
            self.clipboard_append(item["アイテム"])

    def add(self, name, num=1):
        self.counter[name] += num
        num_str = f"{self.counter[name]:,}"

        if name in self.odict:
            item = self.odict[name]
            self.tree.set(item, "数量", num_str)
        else:
            item = self.tree.insert(
                "", "end", values=[name, num_str])
            self.odict[name] = item

        self.odict.move_to_end(name, last=False)

        for indx, child in enumerate(
                zip(self.odict.values(),
                    self.tree.get_children())):
            if child[0] == child[1]:
                break
            self.tree.move(child[0], "", indx)


if __name__ == '__main__':
    root = tk.Tk()
    demo = InventoryView(root)
    root.mainloop()
