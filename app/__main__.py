import logging
import os
import pathlib

from .gmain import main

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s : %(asctime)s : %(message)s')
    os.chdir(pathlib.Path(__file__).parent.parent)
    main()
