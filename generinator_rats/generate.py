# Copyright (c) 2016-2018 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging
import random
import string

from argparse import ArgumentParser
from os import getcwd, makedirs
from os.path import join
from pymongo import MongoClient

from .pkgdata import __version__

logger = logging.getLogger('generinator_rats')
logging.basicConfig(format='%(message)s')


class Generator(object):

    max_attr_per_tag = 5
    max_children_cnt = 10
    max_ruleset_cnt = 10
    max_rule_per_ruleset = 10
    max_selector_cnt = 5
    max_tag_cnt = 2000
    max_text_len = 1000
    universal_selector_prob = 30

    def __init__(self, uri, preload):
        self.preload = preload
        db = MongoClient(uri).get_default_database()
        if self.preload:
            self.tags = dict()
            self.attr = dict()
            self.css = dict()
            for doc in db.generinator_rats_html.find({}):
                if doc['type'] == 'tag':
                    self.tags[doc['name']] = dict(
                        attr=doc['attr'],
                        children=doc['children'])
                elif doc['type'] == 'attr':
                    self.attr[doc['name']] = doc['value']
            for doc in db.generinator_rats_css.find({}):
                self.css[doc['prop']] = doc['value']
        else:
            self.db_html = db.generinator_rats_html
            self.db_css = db.generinator_rats_css
        self.tag_cnt = 0
        self.id_cnt = 0

    def generate(self, tag_name):
        self.id_cnt = 0
        self.tag_cnt = 0
        return self.generate_tag(tag_name)

    def random_css_prop(self):
        if self.preload:
            prop_name = random.choice(list(self.css.keys()))
            return dict(
                prop=prop_name,
                value=self.css[prop_name])
        else:
            return next(self.db_css.aggregate([
                {'$sample': {'size': 1}},
                {'$project': {'prop': 1, 'value': 1, '_id': 0}}]))

    def attr_values(self, attr_name):
        if self.preload:
            return self.attr[attr_name]
        else:
            return self.db_html.find_one({'name': attr_name, 'type': 'attr'}, {'value': 1, '_id': 0})['value']

    def generate_property(self):
        prop = self.random_css_prop()
        return '{name}: {value}'.format(name=prop['prop'], value=random.choice(prop['value']))

    def generate_style_attr(self):
        return ', '.join([self.generate_property() for _ in range(random.randint(1, self.max_attr_per_tag))])

    # This does not test selector parser but does test rendering.
    def generate_selector(self):
        if random.randint(0, 100) < self.universal_selector_prob:
            return '*'
        options = list(range(self.id_cnt))
        selectors = []
        for _ in range(random.randint(1, min(self.max_selector_cnt, len(options)))):
            idx = random.choice(options)
            options.remove(idx)
            selectors.append('id_{idx}'.format(idx=idx))
        return ', '.join(selectors)

    def generate_stylesheet(self):
        rule_sets = []
        for _ in range(random.randint(1, self.max_ruleset_cnt)):
            rule_sets.append(',\n'.join([self.generate_property() for _ in range(random.randint(1, self.max_rule_per_ruleset))]))
        return '\n'.join(('{selector}\n{rule_set}'.format(selector=self.generate_selector(), rule_set=rule_set)) for rule_set in rule_sets)

    def generate_attributes(self, attr_names):
        attributes = ['id="id_{cnt}"'.format(cnt=self.id_cnt)]
        self.id_cnt += 1

        for name in attr_names:
            if name.lower() == 'style':
                attr = '{name}="{value}"'.format(name=name, value=self.generate_style_attr())
            else:
                attr_values = self.attr_values(name)
                if len(attr_values) == 0:
                    attr = name
                else:
                    attr_value = random.choice(attr_values)
                    attr = '{name}={value}'.format(name=name, value=attr_value)
            attributes.append(attr)

        return ' '.join(attributes)

    def generate_content(self, children):
        content = []
        for child in children:
            content.append(self.generate_tag(child))
        return '\n'.join(content)

    def generate_tag(self, tag_name):
        if self.preload:
            tag = self.tags[tag_name]
        else:
            tag = self.db_html.find_one({'name': tag_name, 'type': 'tag'}, {'attr': 1, 'children': 1, '_id': 0})

        attributes = []
        options = list(tag['attr'])
        for _ in range(random.randint(0, min(self.max_attr_per_tag, len(options)))):
            attr = random.choice(options)
            # Making sure that one attribute will be present only once.
            options.remove(attr)
            attributes.append(attr)
        attr_str = self.generate_attributes(attributes)

        content = ''
        if tag_name.lower() == 'style':
            content = self.generate_stylesheet()
        elif tag['children']:
            children = []
            if self.tag_cnt < self.max_tag_cnt:
                # By content generation multiple children with the same tag name are allowed.
                children_cnt = random.randint(0, self.max_children_cnt)
                self.tag_cnt += children_cnt
                for _ in range(children_cnt):
                    child = random.choice(tag['children'])
                    children.append(child)
            content = self.generate_content(children)

        if random.choice([True, False]):
            content += random.choice(string.ascii_letters) * random.randint(1, self.max_text_len)

        return '<{tag_name} {attributes}>{content}</{tag_name}>'.format(tag_name=tag_name,
                                                                        attributes=attr_str,
                                                                        content=content)


def generate(generator, n, out, tag):
    makedirs(out, exist_ok=True)
    for i in range(n):
        with open(join(out, '{idx}.{ext}'.format(idx=i, ext=tag)), 'wb') as f:
            f.write(generator.generate(tag).encode('utf-8', errors='ignore'))


def execute():
    parser = ArgumentParser(description='Generinator:RATS Generator')
    parser.add_argument('-l', '--log-level', metavar='LEVEL', default=logging.INFO,
                        help='set log level (default: INFO)')
    parser.add_argument('-n', metavar='NUM', default=1, type=int,
                        help='number of tests to generate (default: %(default)s)')
    parser.add_argument('-o', '--out', metavar='DIR', default=getcwd(),
                        help='output directory of generated tests (default: .)')
    parser.add_argument('--disable-preload', default=False, action='store_true',
                        help='disable optimization that loads the whole database to memory')
    parser.add_argument('--tag', choices=['html', 'svg'], default='html',
                        help='root tag name, also the extension of the generated files (default: %(default)s)')
    parser.add_argument('--uri', default='mongodb://localhost/fuzzinator',
                        help='URI of the database to generate from (default: %(default)s)')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    args = parser.parse_args()

    logger.setLevel(args.log_level)

    generate(generator=Generator(uri=args.uri, preload=not args.disable_preload),
             n=args.n,
             out=args.out,
             tag=args.tag)


if __name__ == '__main__':
    execute()
