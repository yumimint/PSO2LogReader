import tkinter as tk
from collections import OrderedDict
from tkinter import ttk

from . import main as Main

tr_table = {
    chr(0xFF01 + i): chr(0x21 + i)
    for i in range(0x7e - 0x21)
}

tr_table.update({"　": " "})

tr_table.update({
    chr(0x3041 + i): chr(0x30a1 + i)
    for i in range(0x3096 - 0x3041 + 1)
})

tr_table = str.maketrans(tr_table)


class LaListView(tk.Frame):
    dataCols = ('名称', 'コマンド', '備考')

    def __init__(self, master):
        super().__init__(master)

        self.pack(expand=True, fill=tk.BOTH)

        ##############
        # 検索エントリ
        f = tk.Frame(self)
        f.pack(side=tk.TOP, fill=tk.BOTH)
        _ = tk.Label(f, text="絞り込み")
        _.pack(side=tk.LEFT)
        self.sv = sv = tk.StringVar()
        self.ent = _ = tk.Entry(f, textvariable=sv)
        _.pack(side=tk.LEFT, fill=tk.X)

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
            self.tree.column(c, width=110)

        #####################
        # ポップアップメニュー
        self.popup_menu = tk.Menu(self.tree, tearoff=0)
        _ = self.popup_menu.add_command
        _(label="名称をコピー", command=self.copy_ticket)
        _(label="コマンドをコピー", command=lambda: self.copy_command("/la"))
        _(label="男性/mla", command=lambda: self.copy_command("/mla"))
        _(label="女性/fla", command=lambda: self.copy_command("/fla"))
        _(label="異性/cla", command=lambda: self.copy_command("/cla"))

        ############
        # データ挿入
        self.odict = OrderedDict()
        self.sdict = {}
        for la in Main.la_dict().values():
            self.insert_la(la)

        #
        #
        self.sv.trace_add("write", lambda var, indx, mode: self.search())
        self.tree.bind("<Button-3>", self.popup)
        self.tree.bind("<Double-Button-1>", self.dclick)
        setattr(Main, "la_add", self.add)

    def insert_la(self, la):
        item = self.tree.insert("", "end", values=la)
        self.odict[la.cmd] = item
        key = "\t".join(la).translate(tr_table).lower()
        self.sdict[key] = item

    def search(self, *args):
        # print(args)
        target = self.sv.get().translate(tr_table).lower()
        tree = self.tree
        for index, item in enumerate(self.odict.values()):
            tree.move(item, "", index)
        self.ent.configure(background="white")
        if not target:
            return
        hit = False
        for key, item in self.sdict.items():
            if target in key:
                hit = True
            else:
                tree.detach(item)
        self.ent.configure(background="lightgreen" if hit else "pink")

    def popup(self, event):
        event.widget.event_generate('<1>', x=event.x, y=event.y)
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.popup_menu.grab_release()

    def copy_ticket(self):
        tree = self.tree
        item = tree.set(tree.selection())
        self.clipboard_clear()
        self.clipboard_append(item['名称'])

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
                self.clipboard_append(item["名称"])
            else:
                self.clipboard_append("/la " + item["コマンド"])

    def add(self, cmd):
        if cmd not in self.odict:
            dict = Main.la_dict()
            if cmd in dict:
                self.insert_la(dict[cmd])
            else:
                return

        self.odict.move_to_end(cmd, last=False)
        self.search()


if __name__ == '__main__':
    root = tk.Tk()
    demo = LaListView(root)

    # def gen():
    #     while True:
    #         ls = list(Main.la_dict().keys())
    #         import random
    #         while ls:
    #             cmd = random.choice(ls)
    #             ls.remove(cmd)
    #             yield cmd

    # gen = gen()

    # demo.tree.bind("<MouseWheel>", lambda event: demo.add(next(gen)))
    root.geometry("480x480")
    root.mainloop()
