# %%

import ctypes
import logging
import re
import sys
import urllib.request
from pathlib import Path

import colorama
import playsound
import pyperclip
from colorama import Back, Fore, Style

import bouyomichan
import chatcmd
import logpump
import misc

VERSION = "ver 210428"

colorama.init(autoreset=True)

logging.basicConfig(level=logging.INFO, format='\
%(levelname)s : %(asctime)s : %(message)s')

ChatColors = {
    'PUBLIC': 'WHITE',
    'GROUP': 'GREEN',
    'REPLY': 'MAGENTA',
    'GUILD': 'LIGHTRED_EX',
    'PARTY': 'CYAN',
}

spitem = misc.UsersFile("spitem.txt", misc.spitem_loader)
la_csv = "lobbyactions.csv"
la_dict = misc.UsersFile(la_csv, misc.la_dict_loader)


def pushitem(item, num):
    report.put(item, num)
    spitem_check_and_notify(item)


def report_handler(text):
    print(Fore.YELLOW + text)
    talk(text)


report = misc.DelayedReporter(report_handler)
report.start()

if not Path(la_csv).is_file():
    try:
        url = 'https://raw.githubusercontent.com/yumimint/PSO2LogReader/main/lobbyactions.csv'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as src, Path(la_csv).open("wb") as dst:
            dst.write(src.read())
            # f = io.TextIOWrapper(io.BytesIO(res.read()), encoding="utf-8")
            # dic = read_la_dict(f)

        del url, req, src, dst

    except Exception as e:
        print(e, file=sys.stderr)


def spitem_check_and_notify(item):
    dic = spitem()

    if item in dic:
        sound = dic[item]
        play_sound(sound)
        return

    try:
        for pattern, sound in dic["regexp"]:
            if pattern.match(item):
                play_sound(sound)
                return
    except KeyError:
        logging.warning("わんわん")
        pass


talkactive = misc.TalkativesDetector()
talkactive_sound = misc.TalkativesDetector(1)


def talk(text):
    if not talkactive(text):
        bouyomichan.talk(text)


def play_sound(sound):
    if not talkactive_sound(sound):
        playsound.playsound(sound, block=False)


def chat_print(ent, text):
    time, seq, channel, id, name = ent[:5]
    del seq, id

    time = time[-8:]
    channel = 'GROUP' if channel == 'CHANNEL' else channel
    try:
        col = ChatColors[channel]
    except IndexError:
        col = 'RESET'

    # name = getattr(Back, col) + Fore.BLACK + name + Style.RESET_ALL
    text = getattr(Fore, col) + text

    print(f"{time} {name} {text}")


def handle_Chat(ent):
    """ Chat
    """
    time, seq, channel, id, name, mess = ent[:6]
    del time, seq, id

    if channel == 'PARTY' and handle_Amusement.count:
        handle_Amusement.reset()
        # talk('カウンタをリセットしました')

    _ = re.search(r'/[cmf]?la +([^ ]+)', mess)
    la = ''
    if _:
        cmd = _.group(1)
        dic = la_dict()
        if cmd in dic:
            la = re.sub(r'^\d+', '', dic[cmd])
            talk(f'{name}が{la}した')
            la = ' ' + Fore.RESET + dic[cmd]

    chat_print(ent, mess + la)

    _ = re.search(r'/(skillring|sr|costume|cs|camouflage|cmf) +([^ ]+)', mess)
    if _:
        item = _.group(2)
        talk(f'{name}が{item}を装備した')

    txt = chatcmd.strip(mess)
    if txt:
        talk(f'{name}「{txt}」')


def handle_SymbolChat(ent):
    time, seq, channel, id, name, said = ent[:6]
    chat_print(ent, said)
    talk(f'{name}のシンボルアート')
    del time, seq, channel, id


def handle_Reward(ent):
    item, num = ent[5], ent.Num
    pushitem(item, num)
    pyperclip.copy(item)


def handle_Action(ent):
    act, item, num, meseta = ent[2], ent[5], ent.Num, ent.Meseta
    num = 1 if num is None else num

    if act == '[DisplayToShop-SetValue]':
        return

    if act == '[Warehouse-Meseta]':
        return

    if act == '[Pickup]' and meseta is None:
        pushitem(item, num)

    # if 'Sell' in act and meseta is None:
    #     pickup.add(item, -num)

    if meseta:
        pushitem('メセタ', meseta)


def handle_Craft(ent):
    act, item, num = ent[2], ent[5], ent.Num
    if 'Material' in act and num is not None:
        pushitem(item, num)


def handle_Scratch(ent):
    if 'Received' in ent[3]:
        item, num = ent[6], ent.Num
        pushitem(item, num)


handle_Amusement = misc.CasinoCounter(talk)


def on_entry(ent):
    # print(ent)
    g = globals()
    name = 'handle_' + ent.category
    if name in g:
        fn = g[name]
        fn(ent)


def main():
    ctypes.windll.kernel32.SetConsoleTitleW(f"PSO2LogReader {VERSION}")
    pumpz = logpump.LogPumpz(on_entry)
    pumpz.start()
    print(Fore.GREEN + "START")
    try:
        while True:
            line = input().strip()
            if line == "exit":
                break
            handle_Amusement.report()
    except KeyboardInterrupt:
        pass
    pumpz.stop()
    report.stop()
    print("done")


# %%
if __name__ == "__main__":
    main()
