"""\
Python           _              _
   _ __  ___  __| |___ _ _ _ _ (_)______
  | '  \/ _ \/ _` / -_) '_| ' \| |_ / -_)
  |_|_|_\___/\__,_\___|_| |_||_|_/__\___|\
"""

from __future__ import absolute_import, print_function

import sys
import logging
import optparse
import os

from lib2to3.main import warn, StdoutRefactoringTool
from lib2to3 import refactor

from libmodernize import __version__
from libmodernize.fixes import lib2to3_fix_names, six_fix_names, opt_in_fix_names

import re
import json

"""
re-route stdout
"""


class ListStream:
    def __init__(self):
        self.data = {'result': {}, 'original_diff': ''}

    def write(self, s):
        self.data['original_diff'] += s

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        sys.stdout = sys.__stdout__


usage = __doc__ + """\
 %s

Usage: modernize [options] file|dir ...
""" % __version__
final = {}


def format_usage(usage):
    """Method that doesn't output "Usage:" prefix"""
    return usage


def main(args=None):
    """Main program.

    Returns a suggested exit status (0, 1, 2).
    """
    # Set up option parser
    parser = optparse.OptionParser(usage=usage,
                                   version="modernize %s" % __version__)
    parser.formatter.format_usage = format_usage
    parser.add_option("-v", "--verbose", action="store_true",
                      help="Show more verbose logging.")
    parser.add_option("--no-diffs", action="store_true",
                      help="Don't show diffs of the refactoring.")
    parser.add_option("-l", "--list-fixes", action="store_true",
                      help="List standard transformations.")
    parser.add_option("-d", "--doctests_only", action="store_true",
                      help="Fix up doctests only.")
    parser.add_option("-f", "--fix", action="append", default=[],
                      help="Each FIX specifies a transformation; '-f default' includes default fixers.")
    parser.add_option("--fixers-here", action="store_true",
                      help="Add current working directory to python path (so fixers can be found)")
    parser.add_option("-j", "--processes", action="store", default=1,
                      type="int", help="Run 2to3 concurrently.")
    parser.add_option("-x", "--nofix", action="append", default=[],
                      help="Prevent a fixer from being run.")
    parser.add_option("-p", "--print-function", action="store_true",
                      help="Modify the grammar so that print() is a function.")
    parser.add_option("-w", "--write", action="store_true",
                      help="Write back modified files.")
    parser.add_option("-n", "--nobackups", action="store_true", default=False,
                      help="Don't write backups for modified files.")
    parser.add_option("--six-unicode", action="store_true", default=False,
                      help="Wrap unicode literals in six.u().")
    parser.add_option("--future-unicode", action="store_true", default=False,
                      help="Use 'from __future__ import unicode_literals'"
                           "(only useful for Python 2.6+).")
    parser.add_option("--no-six", action="store_true", default=False,
                      help="Exclude fixes that depend on the six package.")
    parser.add_option("--enforce", action="store_true", default=False,
                      help="Returns non-zero exit code if any fixers had to be applied.  "
                           "Useful for enforcing Python 3 compatibility.")

    fixer_pkg = 'libmodernize.fixes'
    avail_fixes = set(refactor.get_fixers_from_package(fixer_pkg))
    avail_fixes.update(lib2to3_fix_names)

    # Parse command line arguments
    refactor_stdin = False
    flags = {}
    options, args = parser.parse_args(args)
    if not options.write and options.no_diffs:
        warn("Not writing files and not printing diffs; that's not very useful.")
    if not options.write and options.nobackups:
        parser.error("Can't use '-n' without '-w'.")
    if options.list_fixes:
        print("Standard transformations available for the -f/--fix and -x/--nofix options:")
        for fixname in sorted(avail_fixes):
            print("    {}  ({})".format(fixname, fixname.split(".fix_", 1)[1]))
        print()
        if not args:
            return 0
    if not args:
        print("At least one file or directory argument required.", file=sys.stderr)
        print("Use --help to show usage.", file=sys.stderr)
        return 2
    if "-" in args:
        refactor_stdin = True
        if options.write:
            print("Can't write to stdin.", file=sys.stderr)
            return 2
    if options.print_function:
        flags["print_function"] = True
    if options.fixers_here:
        sys.path.append(os.getcwd())

    # Set up logging handler
    level = logging.DEBUG if options.verbose else logging.INFO
    logging.basicConfig(format='%(name)s: %(message)s', level=level)

    # Initialize the refactoring tool
    unwanted_fixes = set()
    splitfixes = []
    for fix in options.nofix:
        splitfixes.extend(fix.split(','))
    for fix in splitfixes:
        matched = None
        for tgt in avail_fixes:
            if tgt == fix or tgt.endswith(".fix_{}".format(fix)):
                matched = tgt
                unwanted_fixes.add(matched)
                break
        else:
            print("Error: fix '{}' was not found".format(fix),
                  file=sys.stderr)
            return 2

    default_fixes = avail_fixes.difference(opt_in_fix_names)

    # Remove unicode fixers depending on command line options
    if options.six_unicode:
        unwanted_fixes.add('libmodernize.fixes.fix_unicode_future')
    elif options.future_unicode:
        unwanted_fixes.add('libmodernize.fixes.fix_unicode')
    else:
        unwanted_fixes.add('libmodernize.fixes.fix_unicode')
        unwanted_fixes.add('libmodernize.fixes.fix_unicode_future')

    if options.no_six:
        unwanted_fixes.update(six_fix_names)

    explicit = set()
    if options.fix:
        default_present = False
        splitfixes = []
        for fix in options.fix:
            splitfixes.extend(fix.split(','))
        for fix in splitfixes:
            if fix == "default":
                default_present = True
            else:
                matched = None
                for tgt in avail_fixes:
                    if tgt == fix or tgt.endswith(".fix_{}".format(fix)):
                        matched = tgt
                        explicit.add(matched)
                        break
                else:
                    # A non-standard fix -- trust user to have supplied path
                    explicit.add(fix)
        requested = default_fixes.union(explicit) if default_present else explicit
    else:
        requested = default_fixes
    fixer_names = requested.difference(unwanted_fixes)  # Filter out unwanted fixers
    explicit = explicit.intersection(fixer_names)  # Filter `explicit` fixers vs remaining fixers

    print(" Loading the following fixers:", file=sys.stderr)
    if fixer_names:
        for fixname in sorted(fixer_names):
            print("    {}  ({})".format(fixname, fixname.split(".fix_", 1)[1]), file=sys.stderr)
    else:
        print("    (None)", file=sys.stderr)
    print(" Applying the following explicit transformations:", file=sys.stderr)
    if explicit:
        for fixname in sorted(explicit):
            print("    {}  ({})".format(fixname, fixname.split(".fix_", 1)[1]), file=sys.stderr)
    else:
        print("    (None)", file=sys.stderr)
    print(file=sys.stderr)

    # Refactor all files and directories passed as arguments
    list3 = sorted(fixer_names)

    for n in list(list3):
        lib23process([n], flags, explicit, options, refactor_stdin, args)

    json_data = json.dumps(final)
    print(json_data)
    return


def lib23process(fixer_names, flags, explicit, options, refactor_stdin, args):
    rt = StdoutRefactoringTool(sorted(fixer_names), flags, sorted(explicit),
                               options.nobackups, not options.no_diffs)
    if not rt.errors:
        if refactor_stdin:
            rt.refactor_stdin()
        else:
            try:

                with ListStream() as stream:
                    # stream.data['fixer'] = fixer_names[0];
                    rt.refactor(args, options.write, options.doctests_only,
                                options.processes)
                final[fixer_names[0]] = process_unified_diff(stream.data)

            except refactor.MultiprocessingUnsupported:  # pragma: no cover
                assert options.processes > 1
                print("Sorry, -j isn't supported on this platform.",
                      file=sys.stderr)
                return 1
        rt.summarize()

    # Return error status (0 if rt.errors is zero)
    return_code = int(bool(rt.errors))
    # If we are enforcing python 3 compatibility, return a non-zero exit code if we had to modify
    # any files.
    if options.enforce and rt.files:
        return_code |= 2
    return return_code


def process_unified_diff(stream):
    original_diff = stream['original_diff']
    if original_diff:
        lines = original_diff.split("\n")
        linenum = 0
        linenumnew = 0
        suggestedfix = {}
        suggestedfix2 = {}
        isfirsthit = True
        hunkstart = ''
        linenr = 0

        pat_diff = re.compile(r'@@ (.[0-9]+\,?[0-9]*) (.[0-9]+\,?[0-9]*) @@')
        for line in lines:

            if line.startswith('--') or line.startswith('++'):
                continue
            if line.startswith('@@'):
                isfirsthit = False
                hunkstart = line
                left, right = pat_diff.match(line).group(1, 2)
                lstart = left.split(',')[0][1:]
                rstart = right.split(',')[0][1:]
                suggestedfix[hunkstart] = {'message': '', 'linenr': 0}
                linenum = int(lstart)
                linenumnew = int(rstart)
                suggestedfix2[hunkstart] = {}
            elif line.startswith('+'):
                if not isfirsthit:
                    isfirsthit = True
                    linenr = linenumnew
                    suggestedfix2[hunkstart][linenr] = ''
                # suggestedfix[hunkstart]['linenr'] = linenr
                suggestedfix2[hunkstart][linenr] += line + "\n"
                linenumnew += 1
            elif line.startswith('-'):
                if not isfirsthit:
                    isfirsthit = True
                    linenr = linenum
                    suggestedfix2[hunkstart][linenr] = ''
                    # suggestedfix[difstart]['linenr'] = linenr

                suggestedfix2[hunkstart][linenr] += line + "\n"
                linenum += 1
            elif line.startswith(' '):  # consider a context line as a start of a sub hunk
                linenum += 1
                linenumnew += 1
                isfirsthit = False
                linenr += 1
                continue

        stream['result'] = suggestedfix2

    return stream
