import queue
import threading
from ctypes import create_unicode_buffer, windll, wintypes
from time import time

q = queue.Queue()


def playsound(sound, volume=1.0):
    q.put((sound, volume))


aliasz = {}


def _daemon():
    while True:
        sound, volume = q.get()

        if sound in aliasz:
            alias = aliasz[sound]
        else:
            alias = str(time())
            try:
                mciSendString(f'open "{sound}" alias {alias} type mpegvideo')
            except Exception:
                continue
            aliasz[sound] = alias

        mciSendString(f'setaudio {alias} volume to {int(1000 * volume)}')
        mciSendString(f'seek {alias} to start')
        mciSendString(f'play {alias}')


th = threading.Thread(target=_daemon, daemon=True)
th.start()


def mciSendString(command):
    buf = create_unicode_buffer(wintypes.MAX_PATH)

    errorCode = int(
        windll.winmm.mciSendStringW(command, buf, len(buf), 0))

    if errorCode:
        errorBuffer = create_unicode_buffer(wintypes.MAX_PATH)
        windll.winmm.mciGetErrorStringW(
            errorCode, errorBuffer, len(errorBuffer))
        raise RuntimeError(f'{errorBuffer.value} ({errorCode})')

    return buf.value
