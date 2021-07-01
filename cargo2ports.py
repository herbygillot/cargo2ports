#!/usr/bin/env python3
"""
Utility to generate a cargo.crates stanza for a MacPorts Portfile given a
Rust project's Cargo.lock file.
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


def get_packages(text):
    """
    Given a string of text expected to be in the format of a V2 Cargo.lock
    file, find all package definition blocks and return the list of packages
    as a list of dictionaries.
    """
    packages = list()

    block_re = (
        r"\[\[package\]\]\s*"  # fmt: off
        r"("  # fmt: off
        r"(.+\n)+"  # fmt: off
        r")"  # fmt: off
        r"(^\s*\n|$)"  # fmt: off
    )

    for match in re.finditer(block_re, text, re.MULTILINE):
        if match:
            block = match.groups()[0]
            package = parse_package_block(block)
            packages.append(package)
    return packages


def get_packages_from_metadata(text):
    """
    Given a string of text expected to be in the format of a V1 Cargo.lock
    file, return the packages defined in the metadata section as a list of
    dictionaries.
    """
    packages = list()

    metadata_re = (
        r"^\[metadata\]\s*"  # fmt: off
        r"("  # fmt: off
        r"^((\"checksum\s*.*)|\s*\n)+"  # fmt: off
        r")"  # fmt: off
    )

    match = re.search(metadata_re, text, re.MULTILINE)

    if not match:
        return packages

    metadata_lines = match.groups()[0].split("\n")

    for line in metadata_lines:
        tokens = re.split("\s+", line)
        if len(tokens) >= 6:
            package = dict()

            tokens = list(map(strip_string, tokens))

            package["name"] = tokens[1]
            package["version"] = tokens[2]
            package["checksum"] = tokens[5]

            packages.append(package)

    return packages


def parse_package_block(text):
    """
    Given a package block string, parse the key/values therein and return it
    as a dictionary.
    """
    parsed = dict()
    lines = text.split("\n")
    for line in lines:
        if "=" in line:
            keyvals = line.split("=", maxsplit=1)
            k, v = map(strip_string, keyvals)
            parsed[k] = v
    return parsed


def get_crate_line(package_dict):
    """
    Given a parsed package block as a dictionary, generate and return the
    Portfile crates line for it.
    """
    indent = STANZA_INDENT * " "

    spacer_width = STANZA_SPACER_WIDTH

    name = package_dict["name"]
    ver = package_dict["version"]
    cksum = package_dict["checksum"]

    name_len = len(name)
    ver_len = len(ver)

    gap_len = STANZA_FIELD_WIDTH - (name_len + ver_len)

    if gap_len <= 0:
        gap_len = 1
        spacer_width -= 1

    return (
        indent + name + (gap_len * " ") + ver + (spacer_width * " ") + cksum
    )  # fmt: off


def generate_crates_stanza(pkg_dicts):
    """
    Given a list of packages as dictionaries, return the Portfile cargo.crates
    stanza as a string.
    """
    num_blocks = len(pkg_dicts)

    output = list()

    output.append("cargo.crates \\")

    for count, pkg in enumerate(pkg_dicts):
        if "checksum" not in pkg:
            continue

        line = get_crate_line(pkg)

        ending = "" if (count == (num_blocks - 1)) else " \\"
        output.append("{}{}".format(line, ending))

    return "\n".join(output)


def is_v1_lockfile(text):
    """
    Return True if the given file contents are a V1 Cargo.lock file, False
    otherwise.
    """
    return True if re.search("^\[metadata\]", text, re.MULTILINE) else False


def main():
    global STANZA_INDENT
    global STANZA_FIELD_WIDTH

    argparser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

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

    argparser.add_argument(
        "-w",
        "--width",
        default=STANZA_FIELD_WIDTH,
        help=(
            "How many characters and spaces wide the name/version field "
            "should be"
        ),
        type=int,
    )

    args = argparser.parse_args()

    STANZA_INDENT = args.indent
    STANZA_FIELD_WIDTH = args.width

    contents = read_open_file(args.lockfile)

    if is_v1_lockfile(contents):
        packages = get_packages_from_metadata(contents)
    else:
        packages = get_packages(contents)

    if not packages:
        fatal(
            "No package definitions found: either not a Cargo.lock "
            + "file, or file is empty."
        )

    output = generate_crates_stanza(packages)
    print(output)
