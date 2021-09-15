import logging
from ctypes import create_unicode_buffer, windll
from ctypes.wintypes import MAX_PATH

logger = logging.getLogger(__name__)


class mciError(RuntimeError):
    def __init__(self, code: int):
        buf = create_unicode_buffer(MAX_PATH)
        windll.winmm.mciGetErrorStringW(code, buf, len(buf))
        super().__init__(f'mciError({code}):{buf.value}')


def playsound(sound, volume=1.0) -> float:
    try:
        alias = playsound.dic.get(sound)
        if alias is None:
            alias = str(playsound.count)
            playsound.dic[sound] = alias
            playsound.count += 1
            mciSendString(f'open "{sound}" alias {alias} type mpegvideo')

        mciSendString(f'setaudio {alias} volume to {int(1000 * volume)}')
        mciSendString(f'seek {alias} to start')
        mciSendString(f'play {alias}')
        return int(mciSendString(f'status {alias} length')) / 1000
    except mciError as e:
        logger.error(e)


playsound.dic = {}
playsound.count = 0


def mciSendString(command: str) -> str:
    buf = create_unicode_buffer(MAX_PATH)
    rc = windll.winmm.mciSendStringW(command, buf, len(buf), None)
    if rc != 0:
        raise mciError(rc, command)
    logger.debug(f"mci: {command} -> [{buf.value}]")
    return buf.value
