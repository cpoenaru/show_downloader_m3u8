# -*- coding: utf-8 -*-
""" M3U8 manual downloader in given path """
import sys
import os
import requests
from m3u8_dl import cli


def main() -> None:
    """ Main program """
    assert len(sys.argv) == 3, "Usage: python manual.py url output_path"
    req = requests.get(sys.argv[1], timeout=5)
    content = req.content.decode().split('\n')
    for uri in content:
        if uri.startswith('https'):
            sys.argv[1] = uri
            break
    else:
        raise AssertionError(f"Cannot find URI\n\n{content}")
    os.makedirs(os.path.dirname(sys.argv[2]), exist_ok=True)
    cli.main()


if __name__ == '__main__':
    main()
