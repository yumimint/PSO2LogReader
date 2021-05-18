from ctypes import create_unicode_buffer, windll, wintypes
from time import time


def mciSendString(command):
    buf = create_unicode_buffer(wintypes.MAX_PATH)

    errorCode = int(
        windll.winmm.mciSendStringW(command, buf, wintypes.MAX_PATH, 0))

    if errorCode:
        errorBuffer = create_unicode_buffer(256)
        windll.winmm.mciGetErrorStringW(errorCode, errorBuffer, 255)
        raise RuntimeError(
            f'Error {errorCode}: {errorBuffer.value} for command: {command}'
        )

    return buf.value


def playsound(sound, volume=1.0):
    alias = str(time())
    mciSendString(f'open "{sound}" alias {alias} type mpegvideo')
    mciSendString(f'setaudio {alias} volume to {int(1000 * volume)}')
    mciSendString(f'play {alias}')
