# %%

import ctypes
import logging
import os
import re
from pathlib import Path

import colorama
import playsound
import pyperclip
from colorama import Fore

import bouyomichan
import chatcmd
import logpump
import misc

VERSION = "ver 210504"

REPORT_ITEM_MAX = 10

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

casinocounter = misc.CasinoCounter()
spitem = misc.UsersFile("spitem.txt", misc.spitem_loader)
la_dict = misc.UsersFile("lobbyactions.csv", misc.la_dict_loader)
if len(la_dict()) == 0:
    la_dict.data = misc.load_la_dict_online()


def get_config(code, default=True):
    return default


def pushitem(item, num):
    report.put(item, num)
    spitem_check_and_notify(item)


def report_handler(counter: misc.ItemCounter):
    pairs = counter.sorted_items()
    names = list(map(misc.ItemCounter.pair2name, pairs))

    info_print("\n".join(names + ["--"]))

    # 拾得物を読み上げリポート
    if get_config(100):
        if REPORT_ITEM_MAX is not None:
            n = len(names)
            if n > REPORT_ITEM_MAX:
                names = names[:REPORT_ITEM_MAX] + \
                    [f"残り{n - REPORT_ITEM_MAX}件省略"]
        talk(" ".join(names))


report = misc.DelayedReporter(report_handler)


def spitem_check_and_notify(item):
    dic = spitem()

    if item in dic:
        if get_config(105):
            talk(item)
        sound = dic[item]
        if get_config(300):
            play_sound(sound)
        return

    if "regexp" in dic:
        for pattern, sound in dic["regexp"]:
            if pattern.match(item):
                if get_config(105):
                    talk(item)
                if get_config(300):
                    play_sound(sound)
                return


talkactive = misc.TalkativesDetector()
talkactive_sound = misc.TalkativesDetector()


def talk(text, guard_time=60):
    if not talkactive(text, guard_time):
        bouyomichan.talk(text)


def play_sound(sound, guard_time=1):
    if not talkactive_sound(sound, guard_time):
        playsound.playsound(sound, block=False)


def chat_print(ent, text):
    time, seq, channel, id, name = ent[:5]

    time = time[-8:]
    channel = 'GROUP' if channel == 'CHANNEL' else channel
    try:
        col = ChatColors[channel]
    except IndexError:
        col = 'RESET'

    # name = getattr(Back, col) + Fore.BLACK + name + Style.RESET_ALL
    text = getattr(Fore, col) + text

    print(f"{time} {name} {text}")


def info_print(text):
    print(Fore.YELLOW + text)


##############################################################################


def handle_Chat(ent):
    time, seq, channel, id, name, mess = ent[:6]

    if channel == 'PARTY' and casinocounter.count:
        casinocounter.reset()
        # talk('カウンタをリセットしました')

    _ = re.search(r'/[cmf]?la +([^ ]+)', mess)
    la = ''
    if _:
        cmd = _.group(1)
        dic = la_dict()
        if cmd in dic:
            la = re.sub(r'^\d+', '', dic[cmd])
            if get_config(102):
                talk(f'{name}が{la}した')
            la = ' ' + dic[cmd]
            if get_config(201, False):
                pyperclip.copy(_.group(0))
            elif get_config(202, False):
                pyperclip.copy(dic[cmd])

    chat_print(ent, mess + la)

    _ = re.search(
        r'/(skillring|sr|costume|cs|camouflage|cmf) +([^ ]+)', mess)
    if _:
        item = _.group(2)
        if get_config(103):
            talk(f'{name}が{item}を装備した')

    txt = chatcmd.strip(mess)
    if txt:
        talk(f'{name}「{txt}」')


def handle_SymbolChat(ent):
    time, seq, channel, id, name, said = ent[:6]
    chat_print(ent, said)
    if get_config(104):
        talk(f'{name}のシンボルアート')


def handle_Reward(ent):
    item, num = ent[5], ent.Num
    pushitem(item, num)
    if get_config(200):
        pyperclip.copy(item)


def handle_Action(ent):
    act, item, num, meseta = ent[2], ent[5], ent.Num, ent.Meseta
    num = 1 if num is None else num

    if act == '[DisplayToShop-SetValue]':
        return

    if act == '[Warehouse-Meseta]':
        return

    if get_config(301) and act.startswith('[Pickup-ToWarehouse'):
        guard_time = 15
        play_sound("emergency-alert1.mp3", guard_time)
        talk("警告！アイテムパックが満杯です！", guard_time)

    if act.startswith('[Pickup') and meseta is None:
        pushitem(item, num)

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


def handle_Amusement(ent):
    if ent[2] in ['UsePass', 'Buy']:
        return

    bet, ret, before, after = map(int, ent[5:9])

    c = casinocounter
    c.update(bet, ret)

    if get_config(101):
        if ret:
            bouyomichan.talk(f"{ret}枚当たり 累計{c.income} ヒット率{c.hitrate:.3f}")
        elif c.defeats > 2:
            bouyomichan.talk(f'{c.defeats}連敗 ')

    meter = '#' * c.defeats + '_' * (c.defeats_max - c.defeats)

    title = f"PSO2LogReader {VERSION} -- {meter} HitRate({c.hitrate:.3f}) ReturnRate({c.rate:.2f}) In({c.income:,})"
    ctypes.windll.kernel32.SetConsoleTitleW(title)


def on_entry(ent):
    # print(ent)
    g = globals()
    name = 'handle_' + ent.category
    if name in g:
        fn = g[name]
        fn(ent)


def main():
    os.chdir(Path(__file__).parent)

    ctypes.windll.kernel32.SetConsoleTitleW(f"PSO2LogReader {VERSION}")
    pump = logpump.LogPump(on_entry)
    pump.start()
    report.start()
    print(Fore.GREEN + "START")
    try:
        while True:
            line = input().strip()
            if line == "exit":
                break
    except KeyboardInterrupt:
        pass
    pump.stop()
    report.stop()
    print("done")


# %%
if __name__ == "__main__":
    main()
