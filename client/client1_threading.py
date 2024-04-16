import json
import time
from typing import Dict, Any, List, Tuple

import threading
import requests, socket
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from itertools import repeat


def http_get_with_requests(url):
    headers = []
    timeout = 10

    response = requests.get(url, headers=headers, timeout=timeout, stream=True)

    s = socket.fromfd(response.raw.fileno(), socket.AF_INET, socket.SOCK_STREAM)
    print(f"{s.getsockname()} --> {s.getpeername()}")

    response_json = None
    try:
        response_json = response.json()
    except:
        pass

    response_content = None
    try:
        response_content = response.content
    except:
        pass

    print(response.status_code, response_json, response_content)
    return (response.status_code, response_json, response_content)


def http_get_with_requests_parallel(list_of_urls, threads):
    t1 = time.time()
    results = []
    #executor = ThreadPoolExecutor(max_workers=threads)
    #for result in executor.map(http_get_with_requests, list_of_urls):
    for i in range(threads):
        t = threading.Thread(target=http_get_with_requests, args=list_of_urls)
        t.start()
    #    t.join()
        #results.append(result)
    t2 = time.time()
    t = t2 - t1
    #return results, t


if __name__ == '__main__':

    # http_get_with_requests_parallel(['http://172.20.0.2:80'], 2)
    http_get_with_requests_parallel(['http://172.20.0.2:80'], 6)
    #print(results)