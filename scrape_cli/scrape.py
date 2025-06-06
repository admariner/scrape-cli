#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scrape: Extract HTML elements using an XPath query or CSS3 selector.
#
# Example usage:
# $ curl 'https://en.wikipedia.org/wiki/List_of_sovereign_states' -s \
# | scrape -e 'table.wikitable > tbody > tr > td > b > a'
#
# Dependencies: lxml, cssselect, requests
#
# Author: http://jeroenjanssens.com

import os
import sys
import re
import argparse
import requests
from lxml import etree
from cssselect import GenericTranslator

# Read version from __init__.py
init_file = os.path.join(os.path.dirname(__file__), '__init__.py')
with open(init_file) as f:
    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", f.read())
    __version__ = version_match.group(1) if version_match else "unknown"

from sys import exit

def clean_text(text):
    """
    Clean text by:
    - Removing multiple consecutive empty lines (max 1 empty line)
    - Replacing multiple spaces with single space
    - Removing leading whitespace from lines
    """
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    # Replace any sequence of 3 or more newlines with just 2 newlines (max 1 empty line)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Replace newlines with whitespace followed by more newlines with just 2 newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Remove leading and trailing whitespace from each line
    text = '\n'.join(line.strip() for line in text.split('\n'))
    # Remove trailing whitespace at the end
    text = text.strip()
    return text

def convert_css_to_xpath(expression):
    try:
        return GenericTranslator().css_to_xpath(expression)
    except Exception as e:
        print(f"Error converting CSS selector to XPath: {e}")
        sys.exit(1)

def is_xpath(expression):
    """
    Check if the expression is XPath by looking for common XPath patterns:
    - Starts with / or //
    - Contains XPath axes (::)
    - Contains node tests with parentheses
    - Contains predicates with square brackets
    - Contains position functions like last() or position()
    """
    xpath_patterns = [
        r'^/',                    # Starts with single or double slash
        r'::',                    # Contains axis specifier
        r'\([^)]*\)',            # Contains parentheses
        r'\[[^\]]*\]',           # Contains square brackets
        r'last\(\)',             # XPath functions
        r'position\(\)',
        r'contains\(',
        r'text\(\)',
        r'@',                    # Attribute selector
    ]

    return any(re.search(pattern, expression) for pattern in xpath_patterns)

def main():
    # Command line argument parser definition
    parser = argparse.ArgumentParser(
        description='Extract HTML elements using an XPath query or CSS3 selector.',
        epilog='Example: cat page.html | python scrape.py -e "//a/@href"'
    )

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    # Check for incorrect argument order (-eb instead of -be)
    if '-eb' in ' '.join(sys.argv):
        sys.exit("Error: The correct order is -be (body first, then expression). Please use -be instead of -eb.")
    # Defines the HTML input argument (can be a file, URL or stdin)
    parser.add_argument('html', nargs='?', type=str, default='',
                        help="HTML input (file, URL or stdin, default: stdin)", metavar="HTML")
    # Defines the optional argument to extract from the tag
    parser.add_argument('-a', '--argument', default="",
                        help="Argument to extract from the tag")
    # Option to include the result within HTML and BODY tags
    parser.add_argument('-b', '--body', action='store_true', default=False,
                        help="Include result in HTML and BODY tags")
    # Option to extract only text content
    parser.add_argument('-t', '--text', action='store_true', default=False,
                        help="Extract only text content (useful for LLMs)")
    # Allows to specify one or more XPath or CSS3 selector expressions
    parser.add_argument('-e', '--expression', default=[], action='append',
                        help="XPath query or CSS3 selector")
    # Option to verify the existence of elements matching the expression
    parser.add_argument('-x', '--check_existence', action='store_true', default=False,
                        help="Returns an exit value indicating existence")
    # Option to avoid initial HTML parsing, useful in specific cases like CData
    parser.add_argument('-r', '--rawinput', action='store_true', default=False,
                        help="Do not parse HTML before passing to etree (useful for CData)")
    parser.add_argument('--check-existence', dest='check_existence', action='store_true')
    args = parser.parse_args()

    # Check that at least one expression is provided by the user (unless using -t option)
    if not args.expression and not args.text:
        parser.print_help()
        sys.exit(
            "Error: you must provide at least one XPath query or CSS3 selector using the -e option, or use -t to extract text."
        )

    # Determine the source of the input: URL, file, or stdin
    if args.html:
        if args.html.startswith('http://') or args.html.startswith('https://'):
            # If the input is a URL, download the HTML content
            try:
                response = requests.get(args.html)
                response.raise_for_status()
                inp = response.content
            except requests.RequestException as e:
                print(f"Error downloading HTML: {e}")
                sys.exit(1)
        else:
            # If the input is a local file, try to open it
            try:
                inp = open(args.html, 'rb').read()
            except FileNotFoundError:
                print(f"Error: The file '{args.html}' was not found.")
                sys.exit(1)
    else:
        # If the input is from stdin
        try:
            inp = sys.stdin.buffer.read()
            if not inp:
                print("Error: No input received from stdin")
                sys.exit(1)
        except Exception as e:
            print(f"Error reading input: {e}")
            sys.exit(1)

    # Check for empty or invalid input
    if not inp:
        print("Error: Input is empty or invalid")
        sys.exit(1)

    # Convert CSS selectors to XPath if necessary
    if args.text and not args.expression:
        # If -t is used without expressions, default to body text excluding scripts and styles
        expression = ['//body//text()[not(ancestor::script) and not(ancestor::style)]']
    else:
        expression = [e if is_xpath(e) else convert_css_to_xpath(e) for e in args.expression]

    # Create an HTML parser with options for error recovery
    html_parser = etree.HTMLParser(encoding='utf-8', recover=True)

    def detect_charset(html_bytes):
        """Try to detect charset from meta tag"""
        try:
            # Look for charset in first 1024 bytes to be efficient
            head = html_bytes[:1024].decode('ascii', errors='ignore').lower()
            meta = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', head)
            if meta:
                return meta.group(1)
        except:
            pass
        return None

    # Try to parse the HTML input
    try:
        # First try to detect charset from meta tag
        charset = detect_charset(inp)
        if charset:
            try:
                inp = inp.decode(charset).encode('utf-8')
            except (UnicodeDecodeError, LookupError):
                # If detected charset fails, fall back to default behavior
                pass

        # Try UTF-8 first, fallback to ISO-8859-1 if that fails
        try:
            if args.rawinput:
                document = etree.fromstring(inp)
            else:
                document = etree.fromstring(inp, html_parser)
        except UnicodeDecodeError:
            # If UTF-8 fails, try ISO-8859-1
            inp = inp.decode('iso-8859-1').encode('utf-8')
            if args.rawinput:
                document = etree.fromstring(inp)
            else:
                document = etree.fromstring(inp, html_parser)
    except (etree.XMLSyntaxError, UnicodeDecodeError) as e:
        # Print an error in case of syntax issues in the HTML
        print(f"Error parsing HTML: {e}")
        sys.exit(1)

    results = []
    # For each expression, perform the search in the parsed HTML
    for e in expression:
        els = list(document.xpath(e))

        # If check-existence is enabled, return 0 or 1 depending on the existence of elements
        if args.check_existence:
            sys.exit(1 if len(els) == 0 else 0)

        # Extract the text or content of the found elements
        for el in els:
            if isinstance(el, str):
                # If the element is a string, use the text directly
                text = el
                # Clean the text when using -t option
                if args.text:
                    text = clean_text(text)
            elif args.text:
                # If -t option is used, extract only text content
                if hasattr(el, 'text_content'):
                    text = el.text_content()
                else:
                    text = ''.join(el.itertext())
                # Clean the text when using -t option
                text = clean_text(text)
            elif not args.argument:
                # If no attribute is specified, return the element as HTML string
                text = etree.tostring(el, pretty_print=True).decode('utf-8')
            else:
                # Otherwise, extract the specified attribute
                text = el.get(args.argument)
            if text is not None:
                results.append(text.strip())

    # Apply final cleaning when using -t option
    if args.text and results:
        final_text = '\n'.join(results)
        final_text = clean_text(final_text)
        results = [final_text] if final_text else []

    # Output handling
    if args.body and not args.text:
        sys.stdout.write("<!DOCTYPE html>\n<html>\n<body>\n")
        for result in results:
            sys.stdout.write(result + "\n")
        sys.stdout.write("</body>\n</html>\n")
    else:
        # Normal output (or text-only output when -t is used)
        for result in results:
            sys.stdout.write(result + "\n")

        sys.stdout.flush()

if __name__ == "__main__":
    exit(main())
