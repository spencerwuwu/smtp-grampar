#!/usr/bin/env python3
import os
import sys
import argparse
import codecs

from loguru import logger

#from smtpfuzz.config import ServerBindings
from smtpfuzz.io import send_payload_n_collect, get_recv_bodies, relay_echo_n_collect
#from smtpfuzz.fuzz import pairwise_diff
#from smtpfuzz.grid import print_grid

logger.remove()
#logger.add(sys.stderr, level="DEBUG")
#logger.add(sys.stderr, level="INFO")
logger.add(sys.stderr, level="WARNING")


def _test_relay(payload, server, query_id, output_dir, verbose=False):
    ret = send_payload_n_collect(server, payload, query_id, output_dir, "echo")
    if not ret:
        logger.error(f"xx No mail received {server} -> echo")
        return ""
        #exit(1)

    mail_outdir = f"{output_dir}/echo/{query_id}/recv/"
    if verbose:
        print(f"++ ECHO Received from {server}:")
    all_mail = ""
    for m in os.listdir(mail_outdir):
        mail = f"{mail_outdir}/{m}"
        with open(mail, "r") as fd:
            mail_content = fd.read()
        if verbose:
            print(mail_content)
        all_mail += mail_content

    return all_mail


if __name__ == "__main__":

    output_dir = "/tmp/smtp_output/"
    os.system(f"rm -rf {output_dir}")
    os.makedirs(output_dir)

    payload_file = sys.argv[1]

    verbose = False

    payload = []
    with open(f"{payload_file}", "r") as fd:
        for line in fd:
            linebytes = codecs.escape_decode(bytes(line[0:-1], "latin-1"))[0]
            payload.append(linebytes)
            if verbose:
                print(line[0:-1])
    if verbose:
        print(f"\n.....................................\n")

    servers = [
            "postfix", 
            "msmtp", 
            "exim", 
            "opensmtpd", 
            "nullmailer", 
            "aiosmtpd", 
            "james-maildir",
            ]

    query_id = 0
    for server in servers:
        recv = _test_relay(payload, server, query_id, output_dir, True)
        query_id += 1

