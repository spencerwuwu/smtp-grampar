import os
import codecs
import time
from subprocess import Popen, PIPE
from typing import List

from .config import ServerBindings
from .utils import *

def create_email_raw(server: bytes, 
                     user: bytes, 
                     data_bodies: List[bytes]) -> List[bytes]:
    payload = [
            b"HELO smtpgarden\r\n",
            b"MAIL FROM:<root@vm.xxx>\r\n",
            b"RCPT TO:<",
            user,
            b"@",
            server,
            b".smtp.garden", # For courier and courier-msa
            b">\r\n",
            b"DATA\r\n" ] + \
            data_bodies +\
            [b"\r\n.\r\n", b"QUIT\r\n"]
    return payload


def send_databody_n_collect(server: str, 
                         user: str, 
                         data_bodies: List[bytes], 
                         query_id: int, 
                         output_dir: str,
                         end_server: str = ""):
    """
    """
    if not end_server:
        end_server = server
    payload = create_email_raw(bytes(end_server, "latin1"), 
                               bytes(user, "latin1"), 
                               data_bodies)
    return send_payload_n_collect(server, payload, query_id, output_dir, end_server)


def send_payload_n_collect(server: str, 
                         payload: List[bytes], 
                         query_id: int, 
                         output_dir: str,
                         end_server: str = "")-> bool:
    """
    - Send payloads to *server* with `send_payload_n_recv`,
      and check maildir in *end_server*.
    - Return *True* if finds new mail in *end_server*'s maildir,
      else *False*.

    """
    if not end_server:
        end_server = server
    outdir = f"{output_dir}/{end_server}/{query_id}/"

    logger.info(f"+++ Sending payload to {server}-{end_server}, query_id={query_id}")
    sent = send_payload_n_recv(payload, ServerBindings[server])
    if not sent:
        logger.error(f"+++ Failed to send payload {server}-{end_server}, query_id={query_id}")
        return False

    # NOTE: wait longer if relay
    if server != end_server:
        # TODO: more reliable way to do this?
        time.sleep(0.1)
    # Change permission in server maildir and get a list of them
    recv_mails = get_server_maildir_items(end_server)
    recv_mails = [m for m in recv_mails.split("\n") if len(m)]

    logger.info(f"+++ Collecting mail from {end_server}, query_id={query_id}")
    if not recv_mails:
        logger.info(f"+++ No mail received for {end_server}, query_id={query_id}")
        fail_dir = outdir = f"{output_dir}/{server}/empty"
        if not os.path.exists(fail_dir):
            os.makedirs(fail_dir)
        with open(f"{fail_dir}/{query_id}_{server}_{end_server}.txt", "w") as fd:
            for line in payload:
                export = codecs.escape_encode(line)[0].decode()
                # or simiply
                # export = line.__repr__()
                fd.write(f"{export}\n")
        # Clean up the server maildir
        cleanup_server_maildir(end_server)
        return False

    logger.info(f"+++ Moving received mail(s) for {end_server}, query_id={query_id}")

    # Move mail out from server maildir to {output}
    mail_outdir = f"{output_dir}/{end_server}/{query_id}/recv/"
    if not os.path.exists(mail_outdir):
        os.makedirs(mail_outdir)

    with open(f"{outdir}/from_{server}.txt", "w") as fd:
        for bline in payload:
            export = codecs.escape_encode(bline)[0].decode()
            # or simiply
            # export = line.__repr__()
            fd.write(f"{export}\n")

    for mail in recv_mails:
        if not mail:
            continue
        new_name = mail.replace("/home/", "").replace("/Maildir/new", "").replace("/", "_")
        cmd = f"cp images/{end_server}/{mail} {mail_outdir}/{new_name}"
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        _,_ = p.communicate()

    # Clean up the server maildir
    cleanup_server_maildir(end_server)

    return True


def relay_echo_n_collect(end_server: str, output_dir: str, query_id: int)-> bool:
    """
    - Get the *echo* received request from f"{output_dir}/echo/{query_id}/recv/echo-recv.txt"
    - Replace "@echo.smtp.garden" with f"@{end_server}.smtp.garden"
    - Do `send_payload_n_collect(server=echo, ... ,end_server=end_server)`
    """
    payload_f = f"{output_dir}/echo/{query_id}/recv/echo-recv.txt"
    if not os.path.exists(payload_f):
        logger.warning(f"Cannot find {payload_f} to relay")
        return False

    payloads = []
    with open(payload_f, "r") as fd:
        data = fd.read().replace("@echo.smtp.garden", f"@{end_server}.smtp.garden")
    for l in data.split("\n"):
        if not l:
            continue
        linebytes = codecs.escape_decode(bytes(l, "latin1"))[0]
        payloads.append(linebytes)

    return send_payload_n_collect(end_server, payloads, query_id, output_dir)


"""
    Post-handling routines
"""
def parse_recv_body(server: str, mail_body: bytes)-> bytes:
    # TODO: Very hacky, may need to change
    if server in ["postfix"]:
        # Exclude the last byte for '\n'
        return mail_body.split(b" (UTC)\n", 1)[1][:-1]

    elif server in ["opensmtpd"]:
        #return mail_body.split(b" (UTC)\n", 1)[1][:-1]
        return mail_body.split(b" (UTC)\n", 1)[1]

    elif server in ["james-maildir"]:
        if b"(UTC)" not in mail_body:
            return b"<NULL?>" + mail_body
        # Cut out message
        # Remove ending \r\n\r\n
        return mail_body.split(b" (UTC)\r\n", 1)[1][:-4]

    elif server in ["dovecot"]:
        # Cut out message
        # (?) remove ending \n
        #return mail_body.split(b" +0000\n", 1)[1][:-1]
        return mail_body.split(b" +0000\n", 1)[1]

    elif server in ["exim"]:
        return mail_body.split(b" +0000\n", 1)[1][:-1]

    elif server in ["courier"]:
        # Cut out message
        chunk = mail_body.split(b" +0000\n", 1)[1]
        # (?) remove ending \n
        #chunk = chunk.rsplit(b"To: undisclosed-recipients: ;", 1)[0][:-1]
        #chunk = chunk.rsplit(b"To: undisclosed-recipients: ;", 1)[0]
        return chunk

    elif server in ["courier-msa"]:
        # Cut out message
        chunk = mail_body.split(b" +0000\n", 1)[1]
        # (?) remove ending \n
        #chunk = chunk.rsplit(b"Message-ID: <courier.", 1)[0][:-1]
        chunk = chunk.rsplit(b"Message-ID: <courier.", 1)[0]
        return chunk

    elif server in ["aiosmtpd"]:
        # Exclude the last single "\n"?
        return mail_body[1:-1] 

    elif server in ["echo"]:
        return mail_body
    raise NotImplementedError(f"{server} parse_recv_body not implemented")


#def compare_send_recv(server: str, 
#                      user: str, 
#                      data_body: bytes, 
#                      query_id: int, 
#                      output_dir: str)-> bool:
#    """
#    Candidate:
#        Compare the sent data_body and the first email receive (in bytes)
#    """
#    query_dir = f"{output_dir}/{server}/{query_id}/recv/"
#    mail_outdir = f"{output_dir}/{server}/{query_id}/recv/"
#
#    num_mail = len(os.listdir(mail_outdir))
#    if num_mail > 1:
#        logger.warning(f"{server} interprets as {num_mail} mails!")
#
#    recv_bodies = []
#    for m in os.listdir(mail_outdir):
#        mail = f"{mail_outdir}/{m}"
#        with open(mail, "rb") as fd:
#            mail_body = parse_recv_body(server, fd.read())
#            recv_bodies.append(mail_body)
#    mail_repr = data_body.__repr__()
#    msg = f"{mail_repr == recv_bodies[0]} {mail_repr} {recv_bodies[0]}"
#    logger.info(msg)
#    return mail_repr == recv_bodies[0]


def get_recv_bodies(server: str, query_id: int, output_dir: str)-> List[bytes]:
    """
    Just retrieve the mail body of the first mail received
    """
    query_dir = f"{output_dir}/{server}/{query_id}/recv/"
    mail_outdir = f"{output_dir}/{server}/{query_id}/recv/"

    num_mail = len(os.listdir(mail_outdir))
    if num_mail > 1:
        # TODO: do something with the num_mail?
        logger.warning(f"{server} interprets as {num_mail} mails!")

    parsed_bodies = []
    for m in os.listdir(mail_outdir):
        mail = f"{mail_outdir}/{m}"
        with open(mail, "rb") as fd:
            parsed_bodies.append(parse_recv_body(server, fd.read()))

    return parsed_bodies
