#!/usr/bin/env python3
import os
import sys
from subprocess import Popen, PIPE


def do_chmod():
    host_uid = os.getenv("HOST_UID") 
    host_gid = os.getenv("HOST_GID") 

    # Special handling for echo server
    if os.path.exists("/home/echo-recv.txt"):
        cmd = f"chown {host_uid}:{host_gid} /home/echo-recv.txt"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        _,_  = p.communicate()
        print("/home/echo-recv.txt")
        return

    for item in os.listdir("/home/"):

        if not item.startswith("user"):
            continue
        user = item
        cmd = f"chmod -R 755 /home/{user}"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        _,_  = p.communicate()

        maildir = f"/home/{user}/Maildir/new/"

        mails = [mail for mail in os.listdir(maildir) if not mail.startswith(".gitignore")]
        for mail in mails:
            mail_full = f"{maildir}/{mail}"
            print(mail_full)
            cmd = f"chown {host_uid}:{host_gid} {mail_full}"
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            p.communicate()
            cmd = f"chmod 777 {mail_full}"
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            _,_  = p.communicate()


def do_cleanup():
    # Special handling for echo server
    cmd = f"rm -f /home/echo-recv.txt"
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    _,_  = p.communicate()

    for user in os.listdir("/home/"):
        if not user.startswith("user"):
            continue
        maildir = f"/home/{user}/Maildir/new/"
        mails = [mail for mail in os.listdir(maildir) if not mail.startswith(".gitignore")]
        for mail in mails:
            mail_full = f"{maildir}/{mail}"
            cmd = f"rm {mail_full}"
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            _,_  = p.communicate()


cmd = sys.argv[1]

if cmd == "chmod":
    do_chmod()

if cmd == "cleanup":
    do_cleanup()
    
