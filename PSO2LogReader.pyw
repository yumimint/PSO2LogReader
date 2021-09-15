import os
import pathlib

from app.gmain import main

os.chdir(pathlib.Path(__file__).parent)
main()
