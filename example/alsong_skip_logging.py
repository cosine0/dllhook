# you can download alsong at http://www.altools.co.kr/Download/ALSong.aspx
# run: python -mdllhook "C:\Program Files (x86)\ESTsoft\ALSong\ALSong.exe" alsong_skip_logging.py
from __future__ import print_function
import datetime
import dllhook
import ctypes
import sqlite3
import os


db_file = os.path.expanduser(r'~\Desktop\alsong_skip_log')
cursor = None


@dllhook.hook_dll(u'ALSongCommon.dll', b'?AudioPlay@CAudio@@QAEHUAUDIO_ITEM@@@Z')
def play_hook(a1, a2, a3, a4, a5, a6):
    # arg6 == &file name (utf16-le, null-terminated)
    global cursor
    if cursor is None:
        cursor = sqlite3.connect(db_file,
                                 isolation_level=None).cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS alsong (time TEXT, action TEXT, name TEXT);')
    name = ctypes.wstring_at(a6)
    print(datetime.datetime.now().isoformat(), 'play', name)
    cursor.execute("INSERT INTO alsong (time, action, name) VALUES (current_timestamp, 'play', ?);", (name,))


@dllhook.hook_dll(u'ALSongCommon.dll', b'?AudioStop@CAudio@@QAEHXZ')
def stop_hook():
    global cursor
    if cursor is None:
        cursor = sqlite3.connect(db_file,
                                 isolation_level=None).cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS alsong (time TEXT, action TEXT, name TEXT);')
    print(datetime.datetime.now().isoformat(), 'stop')
    cursor.execute("insert into alsong (time, action) values (current_timestamp, 'stop');")


@dllhook.hook_dll(u'ALSongCommon.dll', b'?AudioPause@CAudio@@QAEHXZ')
def pause_hook():
    global cursor
    if cursor is None:
        cursor = sqlite3.connect(db_file,
                                 isolation_level=None).cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS alsong (time TEXT, action TEXT, name TEXT);')
    print(datetime.datetime.now().isoformat(), 'pause')
    cursor.execute("INSERT INTO alsong (time, action) VALUES (current_timestamp, 'pause');")


@dllhook.hook_dll(u'ALSongCommon.dll', b'?OnAudioResume@CAudio@@MAEXXZ')
def resume_hook():
    global cursor
    if cursor is None:
        cursor = sqlite3.connect(db_file,
                                 isolation_level=None).cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS alsong (time TEXT, action TEXT, name TEXT);')
    print(datetime.datetime.now().isoformat(), 'resume')
    cursor.execute("INSERT INTO alsong (time, action) VALUES (current_timestamp, 'resume');")
