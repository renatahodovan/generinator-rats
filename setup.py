# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import json

from os.path import dirname, join
from setuptools import find_packages, setup

with open(join(dirname(__file__), 'generinator_rats/VERSION'), 'rb') as f:
    version = f.read().decode('ascii').strip()

with open(join(dirname(__file__), 'generinator_rats/resources/dependencies.json'), 'r') as f:
    deps_json = json.load(f)
    runtime_req = deps_json['runtime_req']


setup(
    name='generinator-rats',
    version=version,
    packages=find_packages(),
    url='https://github.com/renatahodovan/generinator-rats',
    license='BSD',
    author='Renata Hodovan, Akos Kiss',
    author_email='hodovan@inf.u-szeged.hu, akiss@inf.u-szeged.hu',
    description='Generinator: Random Attributes, Tags & Style',
    long_description=open('README.rst').read(),
    install_requires=[runtime_req, 'chardet', 'pymongo'],
    zip_safe=False,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'generinator-rats-process = generinator_rats.process:execute',
            'generinator-rats = generinator_rats.generate:execute',
            'generinator-rats-install-antlr4 = generinator_rats.install:execute'
        ]
    },
)
