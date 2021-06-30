import os
import pathlib
import random
import re

import bouyomichan
import chatcmd
import misc
from playsound import playsound

REPORT_ITEM_MAX = 10

os.chdir(pathlib.Path(__file__).parent)

casinocounter = misc.CasinoCounter()

spitem = misc.UsersFile(
    "spitem.txt",
    misc.SpItem.load, misc.SpItem)
la_dict = misc.UsersFile(
    "lobbyactions.csv",
    misc.la_dict_loader, misc.load_la_dict_online)


def chat_print(ent, text):
    pass


def info_print(text):
    pass


def casino_stateus(text):
    pass


def get_config(code):
    return False


def get_volume():
    return 1.0


def la_add(tpl):
    pass


def clipboard(text):
    pass


def add_inventory(name, num):
    pass


def random_sound():
    last = None
    while True:
        ls = list(spitem().sounds)
        ls.append("emergency-alert1.mp3")

        if len(ls) == 1:
            yield ls[0]
            continue

        while ls:
            sound = random.choice(ls)
            if sound is last:
                continue
            ls.remove(sound)
            yield sound
            last = sound


random_sound = random_sound()


def sound_test():
    sound = next(random_sound)
    if sound is not None:
        play_sound(sound)


def pushitem(item, num):
    add_inventory(item, num)
    reporter.put(item, num)
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


reporter = misc.DelayedReporter(report_handler)


def spitem_check_and_notify(item):
    dic = spitem()

    if item in dic:
        sound = dic[item]
        if get_config(105):
            talk(item)
        if get_config(300):
            play_sound(sound)
        return

    for pattern, sound in dic.rex:
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
        playsound(sound, get_volume())


##############################################################################


def handle_Chat(ent):
    time, seq, channel, id, name, mess = ent[:6]

    match = re.search(r'/[cmf]?la +([^ ]+)', mess)
    if match:
        cmd = match.group(1)
        dic = la_dict()
        if cmd in dic:
            la = dic[cmd]
            if get_config(102):
                la_name = re.sub(r'^\d+', '', la.name)  # 番号を除く
                talk(f'{name}が{la_name}した')
            if get_config(203) and "Reaction" in la.note:
                clipboard("/la reaction")

    equip = re.search(
        r'/(skillring|sr|costume|cs|camouflage|cmf) +([^ ]+)', mess)
    if equip and get_config(103):
        talk(f'{name}が{equip.group(2)}を装備した')

    stamp = re.search(r'/stamp +[^ ]+', mess)
    if stamp and get_config(105):
        talk(f'{name}のスタンプ')

    txt = chatcmd.strip(mess)
    if txt:
        talk(f'{name}「{txt}」')

    if "la" in locals():
        la_add(cmd)
        mess += " " + la.name

    chat_print(ent, mess)


def handle_SymbolChat(ent):
    time, seq, channel, id, name, said = ent[:6]
    chat_print(ent, said)
    if get_config(104):
        talk(f'{name}のシンボルアート')


def handle_Reward(ent):
    item, num = ent[-2], ent.Num
    if item == "Meseta":
        item = 'N-メセタ'
    pushitem(item, num)
    if get_config(200):
        clipboard(item)


def handle_StarGem(ent):
    num = int(ent[-3])
    if num > 0:
        pushitem("スタージェム", num)


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
        pushitem('N-メセタ' if ent.ngs else 'メセタ', meseta)


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

    meter = '■' * c.defeats + '□' * (c.defeats_max - c.defeats)
    casino_stateus(
        f"{meter} HitRate({c.hitrate:.3f}) "
        f"ReturnRate({c.rate:.2f}) Income({c.income:,})")


def on_entry(ent):
    g = globals()
    name = 'handle_' + ent.category
    if name in g:
        fn = g[name]
        fn(ent)
