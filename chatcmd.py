import re

cmd_rex = [
    'toge|moya|[apt]',
    '(mn|vo|symbol|' 'spage|swp|' 'mainpalette|mpal|'
    'subpalette|spal|' 'myset|ms|' 'myfashion|mf)' r'\d+',
    r'(face\d|fc\d|ce(all)?)' '( +(on|off))?',
    r'uioff( +\d+)?',
    r'ci\d+( +\d+)?( +t[1-5])?( +\d+)?',
    '(skillring|sr|' 'costume|cs|' 'camouflage|cmf)' ' +[^ ]+',
    r'[cfm]?la +[^ ]+( +ss?(\d+(\.\d+)?))?',
    r'ce\d( +s(\d+(\.\d+)?))?',
]
cmd_rex = r'^/(' + '|'.join(cmd_rex) + r') ?'
cmd_rex = re.compile(cmd_rex)
color_rex = re.compile(r'{(red|bei|gre|vio|blk|ora|yel|blu|pur|gra|whi|def)}')


def strip(text):
    text = color_rex.sub('', text)
    prev = None

    while text and text != prev:
        prev = text.lstrip()
        text = cmd_rex.sub('', text).lstrip()

    return text
