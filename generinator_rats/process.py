# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import chardet
import logging
import signal
import sys

from antlr4 import *
from argparse import ArgumentParser
from functools import wraps
from glob import glob
from os import getcwd, makedirs, listdir
from os.path import exists, isdir, join, split, splitext
from pkgutil import get_data
from pymongo import MongoClient
from subprocess import Popen, PIPE, STDOUT

from .pkgdata import __version__, antlr_default_path

logger = logging.getLogger('generinator_rats')
logging.basicConfig(format='%(message)s')


def prepare_parsing(antlr, work_dir):

    # Override ConsoleErrorListener to suppress parse issues in non-verbose mode.
    class ConsoleListener(error.ErrorListener.ConsoleErrorListener):
        def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
            logger.debug('line %d:%d %s' % (line, column, msg))
    error.ErrorListener.ConsoleErrorListener.INSTANCE = ConsoleListener()

    def build_grammars(target, sources):
        target_workdir = join(work_dir, target)
        makedirs(target_workdir, exist_ok=True)
        # Add the path of the built grammars to the Python path to be available at parsing.
        sys.path.append(target_workdir)

        # Copy the grammars from the package to the given working directory.
        for resource in sources:
            with open(join(target_workdir, resource), 'wb') as f:
                f.write(get_data(__package__, join('resources', resource)))

        grammar_list = ' '.join(sources)
        try:
            with Popen('java -jar %s -Dlanguage=Python3 %s' % (antlr, grammar_list),
                       stdout=PIPE, stderr=STDOUT, shell=True, cwd=target_workdir) as proc:
                output, exit_code = proc.stdout.read().decode(), proc.returncode
                if exit_code:
                    logger.critical('Building grammars (%s) failed: %s' % (grammar_list, output))
                    sys.exit(1)

            # Extract the name of lexer and parser from their path.
            lexer = splitext(split(glob(join(target_workdir, '*Lexer.py'))[0])[1])[0]
            parser = splitext(split(glob(join(target_workdir, '*Parser.py'))[0])[1])[0]
            listener = splitext(split(glob(join(target_workdir, '*Listener.py'))[0])[1])[0]

            return [getattr(__import__(x, globals(), locals(), [x], 0), x) for x in [lexer, parser, listener]]
        except Exception as e:
            logger.critical('Exception while loading parser modules: %s' % e)
            sys.exit(1)

    html_lexer, html_parser, html_listener = build_grammars('html', ['HTMLLexer.g4', 'HTMLParser.g4'])
    # TODO: it would be nice if someone would write a decent CSS grammar for ANTLR4.
    css_lexer, css_parser, css_listener = build_grammars('css', ['ScssLexer.g4', 'ScssParser.g4'])
    logger.debug('Parser grammars are processed...')

    class HTMLListener(html_listener):
        def __init__(self, uri, parser, src):
            # Save uri because it will be needed to pass when processing style tags.
            self.uri = uri
            self.parser = parser
            self.src = src
            self.db_html = MongoClient(uri).get_default_database().generinator_rats_html
            # Saving attributes in the following form:
            # {name: name, type: attr, values: []}
            self.attributes = dict()
            # Saving html tags in the following form:
            # {name: name, type: tag, children: [], attr: []}
            self.tags = dict()

        def exitEveryRule(self, ctx: ParserRuleContext):
            rule_name = self.parser.ruleNames[ctx.getRuleIndex()]

            if rule_name == 'htmlElement' and len(ctx.htmlTagName()) > 0:
                tag_name = ctx.htmlTagName()[0].children[0].symbol.text
                if tag_name not in self.tags:
                    self.tags[tag_name] = dict(children=set(), attributes=set())

                # Saving attributes.
                if ctx.htmlAttribute():
                    for attr in ctx.htmlAttribute():
                        attr_name = attr.htmlAttributeName().children[0].symbol.text
                        self.tags[tag_name]['attributes'].add(attr_name)
                        if attr_name not in self.attributes:
                            self.attributes[attr_name] = set()
                        if attr.htmlAttributeValue():
                            attr_value = attr.htmlAttributeValue().children[0].symbol.text
                            if attr_name == 'style':
                                self.process_style(attr_value, 'prop')
                            else:
                                self.attributes[attr_name].add(attr_value)
                        else:
                            self.attributes[attr_name].add('')

                # Saving child tags.
                if ctx.htmlContent() and ctx.htmlContent().htmlElement():
                    for element in ctx.htmlContent().htmlElement():
                        if element.htmlTagName():
                            self.tags[tag_name]['children'].add(element.htmlTagName()[0].children[0].symbol.text)

            elif rule_name == 'style':
                if len(ctx.children) > 1:
                    self.process_style(ctx.children[1].symbol.text, 'stylesheet')

        def process_style(self, src, rule):
            target_parser = css_parser(CommonTokenStream(css_lexer(InputStream(src))))
            parser_listener = CSSListener(self.uri, target_parser, src)
            target_parser.addParseListener(parser_listener)

            getattr(target_parser, rule)()

        # As a last step, save the collected information to database.
        def exitHtmlDocument(self, ctx):
            for tag_name in self.tags:
                self.db_html.update_one({'type': 'tag', 'name': tag_name},
                                        {'$addToSet': {'children': {'$each': list(self.tags[tag_name]['children'])}}},
                                        upsert=True)
                self.db_html.update_one({'type': 'tag', 'name': tag_name},
                                        {'$addToSet': {'attr': {'$each': list(self.tags[tag_name]['attributes'])}}},
                                        upsert=True)
            for attr_name in self.attributes:
                self.db_html.update_one({'type': 'attr', 'name': attr_name},
                                        {'$addToSet': {'value': {'$each': list(self.attributes[attr_name])}}},
                                        upsert=True)

    def boundaries(node):
        if isinstance(node, tree.Tree.TerminalNodeImpl):
            return node.symbol.start, node.symbol.stop

        # If the node does not have any children then the boundaries are defined by
        # its parent's boundaries.
        if not node.children:
            current = node
            parent = node.parentCtx
            # TODO: something buggy is here.
            while parent and len(parent.children) == 1:
                current = parent
                parent = current.parentCtx

            idx = parent.children.index(current)
            if idx > 0:
                return boundaries(parent.children[idx - 1])
            if idx < len(parent.children) - 1:
                return boundaries(parent.children[idx + 1])
            assert False, 'Boundary computation failure.'

        if isinstance(node.children[0], tree.Tree.TerminalNodeImpl):
            start = node.children[0].symbol.start
        else:
            start = node.children[0].start.start

        if isinstance(node.children[-1], tree.Tree.TerminalNodeImpl):
            stop = node.children[-1].symbol.stop + 1
        else:
            stop = node.children[-1].stop.stop + 1

        return start, stop

    class CSSListener(css_listener):
        def __init__(self, uri, parser, src):
            self.db_css = MongoClient(uri).get_default_database().generinator_rats_css
            self.parser = parser
            self.src = src
            self.css = dict()

        def exitEveryRule(self, ctx:ParserRuleContext):
            rule_name = self.parser.ruleNames[ctx.getRuleIndex()]

            if rule_name == 'prop':
                prop_name = ctx.identifier().children[0].symbol.text
                if prop_name not in self.css:
                    self.css[prop_name] = set()

                if ctx.values():
                    # TODO: this could be further refined:
                    # More detailed description of the value can improve
                    # the effectiveness of the fuzzer.
                    start, stop = boundaries(ctx.values())
                    self.css[prop_name].add(self.src[start:stop])

        def exitStylesheet(self, ctx):
            for prop in self.css:
                self.db_css.update_one({'prop': prop},
                                       {'$addToSet': {'value': {'$each': list(self.css[prop])}}},
                                       upsert=True)

    # This dictionary will be used as the parameter of the input processing.
    return dict(
        html=dict(lexer=html_lexer, parser=html_parser, listener=HTMLListener, start_rule='htmlDocument'),
        css=dict(lexer=css_lexer, parser=css_parser, listener=CSSListener, start_rule='stylesheet')
    )


class TimeoutError(Exception):
    pass


def timeout(seconds=10):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError()

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            result = None
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


# Making sure that we don't get stuck into the parsing of a large test case.
@timeout(60)
def process_file(uri, path, lexer, parser, listener, start_rule):
    logger.info(path)
    try:
        with open(path, 'rb') as f:
            byts = f.read()
            enc = chardet.detect(byts)['encoding'] or 'utf-8'
            src = byts.decode(enc, errors='ignore')
        target_parser = parser(CommonTokenStream(lexer(InputStream(src))))
        parser_listener = listener(uri, target_parser, src)
        target_parser.addParseListener(parser_listener)

        getattr(target_parser, start_rule)()
    except Exception as e:
        logger.warning(e)


def process(uri, path, configs):
    if isdir(path):
        for fn in listdir(path):
            process(uri, join(path, fn), configs)
    else:
        ext = splitext(path)[1][1:]
        if ext in ['html', 'svg', 'xhtml', 'htm']:
            process_file(uri, path, **configs['html'])
        elif ext in ['css']:
            process_file(uri, path, **configs['css'])


def execute():
    parser = ArgumentParser(description='Generinator:RATS Processor')
    parser.add_argument('input', nargs='+', help='files or directories to gather information from')
    parser.add_argument('--antlr', metavar='FILE', default=antlr_default_path, help='path of the antlr jar file (default: %(default)s)')
    parser.add_argument('-l', '--log-level', metavar='LEVEL', default=logging.INFO, help='set log level (default: INFO)')
    parser.add_argument('--uri', default='mongodb://localhost/fuzzinator', help='URI of the database to store gathered information (default: %(default)s)')
    parser.add_argument('-o', '--out', metavar='DIR', default=getcwd(), help='temporary working directory (default: .)')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    args = parser.parse_args()

    logger.setLevel(args.log_level)
    makedirs(args.out, exist_ok=True)

    configs = prepare_parsing(args.antlr, args.out)

    for test in args.input:
        if not exists(test):
            logger.warning('{test} does not exists.'.format(test=test))
        else:
            process(args.uri, test, configs)


if __name__ == '__main__':
    execute()
