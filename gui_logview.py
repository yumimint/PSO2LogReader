import queue
import tkinter as tk
import tkinter.ttk as ttk


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

    def append(self, text, tag="PUBLIC"):
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
