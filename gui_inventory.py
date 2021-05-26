import tkinter as tk
from collections import Counter, OrderedDict
from tkinter import ttk

import main as Main


class InventoryView(tk.Frame):
    dataCols = ["アイテム", "数量"]

    def __init__(self, master):
        super().__init__(master)

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

        setattr(Main, "add_inventory", self.add)

    def add(self, name, num=1):
        self.counter[name] += num
        if name in self.odict:
            item = self.odict[name]
            self.tree.set(item, "数量", self.counter[name])
        else:
            item = self.tree.insert(
                "", "end", values=[name, self.counter[name]])
            self.odict[name] = item

        self.odict.move_to_end(name, last=False)

        for indx, child in enumerate(
                zip(self.odict.values(),
                    self.tree.get_children())):
            if child[0] == child[1]:
                print(indx)
                break
            self.tree.move(child[0], "", indx)


if __name__ == '__main__':
    root = tk.Tk()
    demo = InventoryView(root)
    root.mainloop()
