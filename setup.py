from setuptools import setup

APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'iconfile': 'app_icon.icns',
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
        'NSHumanReadableCopyright': 'Copyright (c) 2020 Wai Lam Fergus Yip',
        'CFBundleVersion': '1.0.0'
    },
    'packages': ['rumps'],
}

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    app=APP,
    name='DrinkMore',
    author='Fergus Yip',
    author_email='fergus.yipwailam@gmail.com',
    url='https://github.com/FergusYip/DrinkMoreApp',
    description=
    'DrinkMore is a Python 3 app for Mac to remind you to drink more water.',
    long_description=long_description,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=['rumps'],
    classifiers=["License :: OSI Approved :: MIT License"],
)
