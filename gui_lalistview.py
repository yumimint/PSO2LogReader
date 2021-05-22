import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

import main as Main


class LaListView(tk.Frame):
    dataCols = ('チケット', 'コマンド', '備考')

    def __init__(self, master):
        super(LaListView, self).__init__(master)

        f = self
        f.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.Y)

        # create the tree and scrollbars
        self.tree = ttk.Treeview(columns=self.dataCols,
                                 show='headings',
                                 selectmode="browse")

        ysb = ttk.Scrollbar(orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)

        # add tree and scrollbars to frame
        self.tree.grid(in_=f, row=0, column=0, sticky=tk.NSEW)
        ysb.grid(in_=f, row=0, column=1, sticky=tk.NS)

        # set frame resize priorities
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        tree = self.tree
        measure = Font().measure
        # configure column headings
        for c in self.dataCols:
            tree.heading(c, text=c)
            tree.column(c, width=measure(c))

        self.popup_menu = tk.Menu(tree, tearoff=0)
        self.tree.bind("<Button-3>", self.popup)
        _ = self.popup_menu.add_command
        _(label="チケットをコピー", command=self.copy_ticket)
        _(label="コマンドをコピー", command=lambda: self.copy_command("/la"))
        _(label="男性/mla", command=lambda: self.copy_command("/mla"))
        _(label="女性/fla", command=lambda: self.copy_command("/fla"))
        _(label="異性/cla", command=lambda: self.copy_command("/cla"))

        self.tree.bind("<Double-Button-1>", self.dclick)

        self.itemz = {}

        setattr(Main, "la_add", self.add)

    def popup(self, event):
        if not self.tree.selection():
            return
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def copy_ticket(self):
        tree = self.tree
        item = tree.set(tree.selection())
        self.clipboard_clear()
        self.clipboard_append(item['チケット'])

    def copy_command(self, cmd):
        tree = self.tree
        item = tree.set(tree.selection())
        self.clipboard_clear()
        self.clipboard_append(f"{cmd} {item['コマンド']}")

    def dclick(self, event):
        tree = self.tree
        sel = tree.selection()
        if sel:
            item = tree.set(sel)
            col = tree.identify_column(event.x)
            self.clipboard_clear()
            if col == "#1":
                self.clipboard_append(item["チケット"])
            else:
                self.clipboard_append(item["コマンド"])

    def add(self, item):
        tree = self.tree
        if item in self.itemz:
            def reorder():
                top = self.itemz[item]
                yield top
                for child in tree.get_children(""):
                    if child != top:
                        yield child
            for index, item in enumerate(reorder()):
                tree.move(item, "", index)
        else:
            self.itemz[item] = tree.insert('', 0, values=item)
            # adjust column widths if necessary
            measure = Font().measure
            for idx, val in enumerate(item):
                c = self.dataCols[idx]
                iwidth = measure(val)
                if tree.column(c, 'width') < iwidth:
                    tree.column(c, width=iwidth)


if __name__ == '__main__':
    root = tk.Tk()
    demo = LaListView(root)

    def g():
        while True:
            ls = [
                ("Argentina", "BuenosAires", "ARS"),
                ("Australia", "Canberra", "AUD"),
                ("Brazil", "Brazilia", "BRL"),
            ]
            while ls:
                import random
                i = random.choice(ls)
                ls.remove(i)
                yield i

    g = g()
    demo.tree.bind("<MouseWheel>", lambda event: demo.add(next(g)))

    root.mainloop()
