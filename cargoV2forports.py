#!/usr/bin/env python3
"""
Utility to generate a cargo.crates Portfile stanza for MacPorts given a V2
version of a Rust project's Cargo.lock file.
"""


import argparse
import re
import sys


STANZA_INDENT = 4
STANZA_FIELD_WIDTH = 38
STANZA_SPACER_WIDTH = 2


def fatal(*msg):
    """
    Print given message to standard error and exit with an exit code of 1,
    signalling error.
    """
    print(*msg, file=sys.stderr)
    sys.exit(1)


def strip_string(s):
    """
    Given a string, return it after removing all surrounding whitespace and
    quote marks (")
    """
    s = s.strip()
    s = s.strip('"')
    return s


def read_open_file(f):
    """
    Given an open file, return its contents and close it.
    """
    data = None
    data = f.read()
    f.close()
    return data


def get_package_blocks(text):
    """
    Given a string of text expected to be in the format of a V2 Cargo.lock
    file, find all package definition blocks and return the list of package
    definition blocks as a list of strings.
    """
    blocks = list()

    block_re = (
        r"("  # fmt: off
        r"\[\[package\]\]\s*"
        r"("
        r"(.+\n)+"
        r")"
        r")"
        r"(^\s*\n|$)"
    )

    for match in re.finditer(block_re, text, re.MULTILINE):
        if match:
            block = match.groups()[1]
            blocks.append(block)
    return blocks


def parse_package_block(text):
    """
    Given a package block string, parse the key/values therein and return it
    as a dictionary.
    """
    parsed = dict()
    lines = text.split("\n")
    for line in lines:
        if "=" in line:
            k, v = line.split("=", maxsplit=1)
        parsed[strip_string(k)] = strip_string(v)
    return parsed


def get_crate_line(block_dict):
    """
    Given a parsed package block as a dictionary, generate and return the
    Portfile crates line for it.
    """
    indent = STANZA_INDENT * " "

    spacer_width = STANZA_SPACER_WIDTH

    name = block_dict["name"]
    ver = block_dict["version"]
    cksum = block_dict["checksum"]

    name_len = len(name)
    ver_len = len(ver)

    gap_len = STANZA_FIELD_WIDTH - (name_len + ver_len)

    if gap_len <= 0:
        gap_len = 1
        spacer_width -= 1

    return (
        indent + name + (gap_len * " ") + ver + (spacer_width * " ") + cksum
    )  # fmt: off


def generate_crates_stanza(blocks_dict_list):
    """
    Given a list of package block dictionaries, return the Portfile
    cargo.crates stanza as a string.
    """
    num_blocks = len(blocks_dict_list)

    output = list()

    output.append("cargo.crates \\")

    for count, b in enumerate(blocks_dict_list):
        block = parse_package_block(b)

        if "checksum" not in block:
            continue

        line = get_crate_line(block)

        ending = "" if (count == (num_blocks - 1)) else " \\"
        output.append("{}{}".format(line, ending))

    return "\n".join(output)


def main():
    global STANZA_INDENT

    argparser = argparse.ArgumentParser(description=__doc__)

    argparser.add_argument(
        "lockfile",
        default="Cargo.lock",
        help="Path to the Cargo.lock file",
        nargs="?",
        type=argparse.FileType("r"),
    )

    argparser.add_argument(
        "-i",
        "--indent",
        default=STANZA_INDENT,
        help="Number of spaces to indent by",
        metavar="COUNT",
        type=int,
    )

    args = argparser.parse_args()
    STANZA_INDENT = args.indent

    contents = read_open_file(args.lockfile)
    blocks = get_package_blocks(contents)

    if not blocks:
        fatal(
            "No package definitions found: either not a Cargo.lock "
            + "file, or file is empty."
        )

    output = generate_crates_stanza(blocks)
    print(output)


if __name__ == "__main__":
    main()
