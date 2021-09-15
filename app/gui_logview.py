import tkinter as tk
import tkinter.ttk as ttk


class LogView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid(sticky=tk.NSEW)

        text = tk.Text(self,
                       state=tk.DISABLED,
                       foreground="white",
                       background="black",
                       )
        text.grid(row=0, column=0, sticky=tk.NSEW)

        for name, color in [
            ('PUBLIC', '#ffffff'),
            ('GROUP', '#88ff88'),
            ('REPLY', '#FF6699'),
            ('GUILD', '#F59F01'),
            ('PARTY', 'cyan'),
        ]:
            text.tag_configure(name, foreground=color)

        ysb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.yview)
        text.configure(yscrollcommand=self.ysbset)
        ysb.grid(row=0, column=1, sticky=tk.NS)

        self.text = text
        self.ysb = ysb
        self.follow = True

    def append(self, text, tag="PUBLIC"):
        self.text.configure(state=tk.NORMAL)
        self.text.insert('end', text, tag)
        self.text.configure(state=tk.DISABLED)
        if self.follow:
            self.text.see('end')

    def _set_follow_flag(self):
        pos = self.ysb.get()
        self.follow = pos[1] >= 1.0

    def yview(self, *args):
        self.text.yview(*args)
        self._set_follow_flag()

    def ysbset(self, *args):
        self.ysb.set(*args)
        self._set_follow_flag()
