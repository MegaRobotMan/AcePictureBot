from config import update
from git import Repo

from urllib.request import urlopen
from shutil import ignore_patterns
from hashlib import md5
import xml.etree.ElementTree as Etree
import subprocess
import shutil
import time
import stat
import sys
import os

base_dir = os.path.dirname(os.path.realpath(__file__))
backup_dir = os.path.join(base_dir, "_backup")
update_dir = os.path.join(base_dir, "_update")
updated_py = True


def close_main_process():
    while True:
        if not os.path.exists(update['is_busy_file']):
            try:
                main_process.kill()
            except NameError:
                # In first update
                return
            return
        time.sleep(5)


def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def update_self():
    global updated_py
    updated_py = False
    try:
        most_recent_commit = open(update['recent_commit_file'], 'r').read()
    except FileNotFoundError:
        most_recent_commit = ""
    rss = urlopen(update['repository_rss']).read().decode("utf-8")
    xml = Etree.fromstring(rss)
    latest_commit_id = xml[5].findtext(r"{http://www.w3.org/2005/Atom}id")
    if most_recent_commit == latest_commit_id:
        # No new commit
        return False
    print("[New Git Commit]")
    print("[{0}]".format(latest_commit_id))
    # New commit!
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir, onerror=del_rw)
    shutil.copytree(base_dir, backup_dir, ignore=ignore_patterns('main_container.py', 'is_busy.txt',
                                                                 'images', 'user_ignore'))
    if not os.path.exists(update_dir):
        os.makedirs(update_dir)
    else:
        # Needs to be empty
        shutil.rmtree(update_dir, onerror=del_rw)
        os.makedirs(update_dir)
    Repo.clone_from(update['repository'], update_dir)
    for src_dir, dirs, files in os.walk(update_dir):
        if ".git" in src_dir:
            continue
        dst_dir = src_dir.replace(update_dir, base_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if md5(open(src_file, 'rb').read()).hexdigest() ==\
               md5(open(dst_file, 'rb').read()).hexdigest():
                # No change in file
                continue
            else:
                if ".py" in str(src_file):
                    updated_py = True
                    close_main_process()

            if os.path.exists(dst_file):
                os.remove(dst_file)
            print("[Updating: {0}]".format(src_file))
            shutil.move(src_file, dst_dir)
    shutil.rmtree(update_dir, onerror=del_rw)
    with open(update['recent_commit_file'], "w") as f:
        f.write(latest_commit_id)
    print("[Finished Updating]")
    return True

if __name__ == '__main__':
    if os.path.exists(update['is_busy_file']):
        os.remove(update['is_busy_file'])
    if update['auto_update']:
        update_self()
    try:
        main_process = subprocess.Popen(update['python_process'])
    except (KeyboardInterrupt, SystemExit):
        main_process.kill()
        sys.exit(0)

    while True:
        if update['auto_update']:
            if update_self():
                if updated_py:
                    try:
                        main_process = subprocess.Popen(update['python_process'])
                    except (KeyboardInterrupt, SystemExit):
                        main_process.kill()
                        sys.exit(0)
        time.sleep(60)
