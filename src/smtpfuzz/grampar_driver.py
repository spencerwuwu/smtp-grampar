from typing import List, Mapping, Tuple
import os
from loguru import logger
import string
import random
import shutil

from smtpfuzz.io import send_payload_n_collect
from smtpfuzz.fuzz import pairwise_diff


def exec_echo(payloads, server, query_id, output_dir, verbose=False):
    ret = send_payload_n_collect(server, payloads, 
                                 query_id, output_dir, "echo")
    if not ret:
        logger.warning(f"xx No mail received {server} -> echo")
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


def query_garden_header(servers: List, 
                        payloads: List[bytes],
                        verbose: bool=False
                        )-> Mapping[str, Tuple[bool, str]]:

    output_dir = "/tmp/smtp_output/"
    os.system(f"rm -rf {output_dir}")
    os.makedirs(output_dir)

    query_id = 0

    results = {}
    for server in servers:
        recv = exec_echo(payloads, server, query_id, output_dir, 
                           verbose=False)

        # Focus on header fields, special handlings
        if server == "aiosmtpd":
            data_keyword = "data\\r\\n"
        else:
            data_keyword = "DATA\\r\\n"

        # NOTE: checks whether a server "accepts"
        complete = data_keyword in recv

        # NOTE: sanitize
        header = recv.split(data_keyword)[0]
        if server == "msmtp":
            if header.startswith("QUIT"):
                header = header.split("\\r\\n", 2)[-1]
            else:
                header = header.split("\\r\\n", 1)[-1]
        else:
            header = header.split("\\r\\n", 1)[-1]
        header = header.lower()
        header = header.replace(server, "SERVER")

        results[server] = (complete, header)

        query_id += 1

    return results


def query_garden_body(servers: List, 
                        payloads: List[bytes],
                        verbose: bool=False
                        )-> Mapping[str, Tuple[bool, str]]:

    output_dir = "/tmp/smtp_output/"
    os.system(f"rm -rf {output_dir}")
    os.makedirs(output_dir)

    query_id = 0

    results = {}
    for server in servers:
        recv = exec_echo(payloads, server, query_id, output_dir, 
                           verbose=False)
        if server == "aiosmtpd":
            data_keyword = "data\\r\\n"
        else:
            data_keyword = "DATA\\r\\n"

        # NOTE: checks whether a server "accepts"
        complete = data_keyword in recv

        # Focus on between `HEAD`-`TAIL` keyword
        #   and after `TAIL`, special handlings (with parse_body_output.py?)
        body = recv.split("HEAD")[-1]
        if server == "aiosmtpd":
            body = body.replace("quit", "QUIT")


        results[server] = (complete, body)

        query_id += 1

    return results


def query_garden_full(servers: List[str],
                      payloads: List[bytes],
                      verbose: bool=False
                      )-> Mapping[str, Tuple[bool, Tuple[str, str]]]:
    def _get_rand_str(size=5):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))

    # Create output dir
    output_dir = '/tmp/smtp_out_' + _get_rand_str()
    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
        except OSError as e:
            logger.error(f"Error: {e}")
            exit(1)

    logger.info("Querying SMTP")
    logger.debug("@ {}", output_dir)

    query_id = 0
    results = {}
    for server in servers:
        recv = exec_echo(payloads, server, query_id, output_dir, 
                         verbose=False)
        if server == "aiosmtpd":
            data_keyword = "data\\r\\n"
        else:
            data_keyword = "DATA\\r\\n"

        # NOTE: checks whether a server "accepts"
        complete = data_keyword in recv
        if not complete:
            results[server] = (False, ("", ""))
            continue

        header = recv.split(data_keyword)[0]
        # NOTE: sanitize header
        header = recv.split(data_keyword)[0]
        if server == "msmtp":
            if header.startswith("QUIT"):
                header = header.split("\\r\\n", 2)[-1]
            else:
                header = header.split("\\r\\n", 1)[-1]
        else:
            header = header.split("\\r\\n", 1)[-1]
        header = header.lower()
        header = header.replace(server, "SERVER")

        body = recv.split("HEAD", 1)[-1]
        # NOTE: sanitize body
        if server == "aiosmtpd":
            body = body.replace("quit", "QUIT")
            body = body.replace("X-Peer: 172.19.0.1\\r\\n", "")
        body = body.rsplit("QUIT", 1)[0]

        results[server] = (complete, (header, body))

        query_id += 1

    return results
