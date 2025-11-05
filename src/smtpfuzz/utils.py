import docker
import codecs
import socket
from typing import List
from loguru import logger
import time
import sys

""" 
   Utilities 
"""
def get_server_container(server : str):
    client = docker.from_env()
    for container in client.containers.list():
        if container.name.startswith(f"smtp-garden-dev-{server}"):
            return client, container
    logger.error(f"No running container found for '{server}' (smtp-garden-dev-{server}-*)")
    exit(1)


def get_server_maildir_items(server)-> str:
    client, container = get_server_container(server)
    try:
        command = f"python3 /root/in-container-action.py chmod"
        logger.debug(f"[*] Running: {command}")
        exec_log = client.api.exec_create(container.id, command)
        output = client.api.exec_start(exec_log['Id']).decode()
        logger.debug(f"[*] Returned: \n{output}")
        return output
    except Exception as e:
        logger.warning(f"failed to execute in-container-action.py chmod: {e}")
        return ""


def cleanup_server_maildir(server):
    client, container = get_server_container(server)
    try:
        command = f"python3 /root/in-container-action.py cleanup"
        logger.debug(f"[*] Running: {command}")
        exec_log = client.api.exec_create(container.id, command)
        output = client.api.exec_start(exec_log['Id']).decode()
        logger.debug(f"[*] Returned: \n{output}")
    except Exception as e:
        logger.warning(f"failed to execute in-container-action.py cleanup: {e}")


""" 
   Network I/O
"""
def safe_sendall(sock, data, max_retries=3, delay_seconds=0.5):
    attempts = 0
    while attempts < max_retries:
        try:
            sock.sendall(data)
            return True  # Data sent, exit the function
        except socket.error as e:
            logger.warning(f"Socket error during send: {e}. Retrying...")
            attempts += 1
            if attempts < max_retries:
                time.sleep(delay_seconds)
            else:
                logger.error(f"Failed to send data after {max_retries} attempts.")
                return False  # All retries exhausted
        except Exception as e:
            logger.warning(f"An unexpected error occurred: {e}. Retrying...")
            attempts += 1
            if attempts < max_retries:
                time.sleep(delay_seconds)
            else:
                logger.error(f"Failed to send data after {max_retries} attempts due to unexpected error.")
                return False
    return False # Should not be reached if max_retries is handled correctly


def send_email_to_socket(email: List[bytes], s: socket.socket)-> bool:
    peer_name = s.getpeername()
    sock_name = s.getsockname()
    for linebytes in email:
        #linebytes = codecs.escape_decode(bytes(line, "latin1"))[0]
        logger.debug(f"Sending  [{sock_name}]: {linebytes!r}")
        #s.sendall(linebytes)
        if not safe_sendall(s, linebytes):
            return False
        reply = None
        try:
            reply = s.recv(1024)
        except socket.timeout:
            # NOTE: peer timeout is normal behavior during DATA transmission
            #logger.debug("Socket timeout, peer {peer_name}")
            continue
        else:
            if reply != None:
                if len(reply) == 0 or reply.startswith(b"2") or reply.startswith(b"3"):
                    logger.debug(f"Received [{peer_name}]: {reply!r}")
                else:
                    logger.warning(f"Received [{peer_name}]: {reply!r}")
            else:
                logger.warning("No reply from {peer_name} (Something may have gone wrong)")
    return True
    

def send_payload_n_recv(payload_list: List[bytes], port:int, 
                        hostname:str = "localhost")-> bool:
    """
    Network utilities
    """
    logger.debug(f"++ Sending payload to {hostname}:{port}")

    ESTABLISH_FAIL = False
    ESTABLISH_OK   = True

    def establish_conn(s, servername, port):
        s.settimeout(5)
        try:
            s.connect((servername, port))
        except socket.gaierror:
            logger.error(f"Unable to identify host {servername}.")
            return ESTABLISH_FAIL
        except ConnectionRefusedError:
            logger.error(f"Connection refused by {servername}:{port}")
            return ESTABLISH_FAIL
        return ESTABLISH_OK

    def get_banner(s):
        banner = ""
        try:
            banner = s.recv(1024)
        except socket.timeout:
            sys.exit("No SMTP banner received within timeout period, quitting.")
        return banner

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        sock_ok = establish_conn(s, hostname, port)
        if not sock_ok:
            return False
        banner = get_banner(s)
        logger.debug(f"Received [{s.getpeername()}]: {banner!r}")
        s.settimeout(0.50)
        return send_email_to_socket(payload_list, s)
