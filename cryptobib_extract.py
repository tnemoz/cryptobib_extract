#!/usr/bin/python
import argparse
import os
import re
from typing import Optional

from colorama import init, Fore, Style
import requests
from tqdm import tqdm


URL = "https://cryptobib.di.ens.fr/cryptobib/static/files/crypto.bib"
FILE_PATH = "/home/tristan/bigfiles/crypto.bib"

AUTHOR_SEARCH = re.compile(r"author += +([\"|\{])")
TITLE_SEARCH = re.compile(r"title += +([\"|\{])")
ENTRY_END = re.compile(r"}")
QUOTES_END_TOKEN = re.compile(r"\", *$")
BRACE_END_TOKEN = re.compile(r"\}, *$")

def update():
    print("Downloading crypto.bib file...")
    r = requests.get(URL, stream=True)
    total_size = int(r.headers.get('content-length', 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)

    with open(FILE_PATH, 'wb') as f:
        for data in r.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)

    progress_bar.close()

    if total_size != 0 and progress_bar.n != total_size:
        print("ERROR, something went wrong")

def root(author_to_find: Optional[str], title_to_find: Optional[str]):
    while True:
        line = yield

        if line.startswith("@"):
            potential_entry = yield from entry(
                first_line=line,
                author_to_find=author_to_find,
                title_to_find=title_to_find
            )

            if potential_entry is not None:
                print(potential_entry)
                print("=" * 50)

def entry(first_line: str, author_to_find: Optional[str], title_to_find: Optional[str]):
    full_entry = first_line
    is_author_matching: Optional[bool] = None
    is_title_matching: Optional[bool] = None

    while True:
        line = yield

        if author_to_find is not None and re.search(AUTHOR_SEARCH, line) is not None:
            is_author_matching, author_string = yield from key(line, author_to_find, AUTHOR_SEARCH)

            if not is_author_matching:
                return None

            full_entry += author_string

            if is_author_matching and (title_to_find is None or is_title_matching):
                while not (line := (yield)).startswith("}"):
                    full_entry += line

                return full_entry + line

            continue
        
        if title_to_find is not None and re.search(TITLE_SEARCH, line) is not None:
            is_title_matching, title_string = yield from key(line, title_to_find, TITLE_SEARCH)

            if not is_title_matching:
                return None

            full_entry += title_string

            if is_title_matching and (author_to_find is None or is_author_matching):
                while not (line := (yield)).startswith("}"):
                    full_entry += line

                return full_entry + line
            continue
        else:
            full_entry += line

        if line.startswith("}"):
            return None

def key(first_line: str, to_find: str, search_regex: re.Pattern):
    total_string = first_line
    line = first_line
    opening_token = re.search(search_regex, line).groups()[0]
    assert opening_token in ["\"", "{"], f"(author:{line}) Unrecognized opening token: {opening_token}"
    end_token_regex = QUOTES_END_TOKEN if opening_token == "\"" else BRACE_END_TOKEN

    while re.search(end_token_regex, line) is None:
        line = yield
        total_string += line
    
    res = re.search(to_find, total_string, re.IGNORECASE)
    found = res is not None

    if found:
        start, end = res.span()
        total_string = total_string[:start] + \
                Fore.RED + total_string[start:end] + Style.RESET_ALL + total_string[end:]

    return found, total_string


parser = argparse.ArgumentParser()
parser.add_argument("-a", "--author")
parser.add_argument("-t", "--title")
parser.add_argument("-u", "--update", action="store_true")
args = parser.parse_args()

if not os.path.isfile(FILE_PATH) or args.update:
    update()

assert args.author is not None or args.title is not None, "No parameter provided"

init()

with open(FILE_PATH, "r") as f:
    parser = root(args.author, args.title)
    next(parser)

    for line in f:
        parser.send(line)

