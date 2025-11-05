
from multiprocessing import Pool
from typing import List, Mapping

from smtpfuzz.config import ServerBindings
from smtpfuzz.utils import cleanup_server_maildir
from smtpfuzz.io import get_recv_bodies
from smtpfuzz.io import send_databody_n_collect, send_payload_n_collect

from smtpfuzz.grid import print_grid

import itertools

def generate_fuzz_strings(charset: List[bytes], 
                          max_length: int = 5, 
                          unique: bool = False, 
                          permutations: bool = True)->bytes:
    """
    Generate test strings using the given charset.
    
    Parameters:
    - charset (str): A string of characters to combine.
    - max_length (int): Max length of each generated string.
    - unique (bool): If True, don't repeat characters in a string.
    - permutations (bool): If True, generate permutations instead of combinations.
    
    Yields:
    - Generated string combinations/permutations.
    """
    for length in range(1, max_length + 1):
        if permutations:
            if unique:
                iter_func = itertools.permutations(charset, length)
            else:
                iter_func = itertools.product(charset, repeat=length)
        else:
            if unique:
                iter_func = itertools.combinations(charset, length)
            else:
                iter_func = itertools.combinations_with_replacement(charset, length)
        
        for item in iter_func:
            yield b"".join(item)

def simple_diff(a:bytes, b:bytes)-> bool:
    if a == b:
        return True
    return False

# TODO: results now have type Mapping[str,List[bytes]]
def pairwise_diff(results: Mapping,
                  diff_method=simple_diff)-> Mapping[str, bool]:
    """
    Input:
        results: Mapping[str, {whatever}]
    Output:
        { str(sorted([server_a, server_b])): same/diff }
    """
    # TODO: only compare directly now
    diff = {}
    for server_a, recv_a in results.items():
        for server_b, recv_b  in results.items():
            if server_a == server_b:
                continue
            pair = str(sorted([server_a, server_b]))
            if pair in diff:
                continue
            if recv_a is None or recv_b is None:
                diff[pair] = None
            else:
                diff[pair] = diff_method(recv_a, recv_b) 
    return diff


def server_exec(server, user, mail_bodies, query_id, output_dir):
    """
    Task for a single server
    """
    ret = send_databody_n_collect(server, user, mail_bodies, query_id, output_dir)
    if not ret:
        result = []
    else:
        recv_bodies = get_recv_bodies(server, query_id, output_dir)
        result = recv_bodies

    cleanup_server_maildir(server)
    return result


def server_raw_list(server, payloads, query_id, output_dir, end_server=""):
    """
    Task for a sending bytestring array
    """
    if not end_server:
        end_server = server
    ret = send_payload_n_collect(server, payloads, query_id, output_dir, end_server)
    if not ret:
        result = []
    else:
        recv_bodies = get_recv_bodies(end_server, query_id, output_dir)
        result = recv_bodies

    cleanup_server_maildir(end_server)
    return result


def diff_exec(servers: List, 
              query_id: int,
              user: str,
              mail_bodes: List[bytes],
              output_dir: str,
              verbose: bool)-> Mapping[str, bool]:

    results = {}
    server_jobs = []

    for server in servers:
        results[server] = None
        server_jobs.append((server, user, mail_bodies, query_id, output_dir))

    with Pool(processes=len(servers)) as pool:
        pool_results = pool.starmap(server_exec, server_jobs)

    results = dict(zip(servers, pool_results))


    if verbose:
        print(f"+{query_id:05d}:", mail_body)
        for server, results in results.items():
            if not results:
                print(f"{server:20s} ({len(result.replace(b'<NULL?>',b'')):3d}): ",  result)
            else:
                is_head = True
                for result in results:
                    if is_head:
                        print(f"{server:20s} (  -): ",  result)
                    else:
                        print(f"{'':20s} (  -): ",  result)
        print()
        #diff_result = pairwise_diff(results)
        #print_grid(servers, diff_result)
        print("-----\n")
    
    return diff_result
