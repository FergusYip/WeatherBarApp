from setuptools import setup

APP = ['app.py']
DATA_FILES = ['menubar_alert_icon.ico']
OPTIONS = {
    'iconfile': 'app_icon.icns',
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
        'NSHumanReadableCopyright': 'Copyright (c) 2020 Wai Lam Fergus Yip',
        'CFBundleVersion': '1.1.0'
    },
    'packages': ['rumps', 'requests', 'geopy'],
}

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    app=APP,
    name='WeatherBar',
    author='Fergus Yip',
    author_email='fergus.yipwailam@gmail.com',
    url='https://github.com/FergusYip/WeatherBarApp',
    description=
    'WeatherBar is a MacOs menu bar app that displays the current weather.',
    long_description=long_description,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=['rumps', 'requests', 'geopy'],
    classifiers=["License :: OSI Approved :: MIT License"],
)
