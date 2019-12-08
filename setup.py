# Copyright (c) 2016-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from os.path import dirname, join
from setuptools import find_packages, setup

with open(join(dirname(__file__), 'generinator_rats/VERSION'), 'rb') as f:
    version = f.read().decode('ascii').strip()

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
    install_requires=['antlerinator==4.7.2', 'chardet', 'pymongo'],
    zip_safe=False,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'generinator-rats-process = generinator_rats.process:execute',
            'generinator-rats = generinator_rats.generate:execute',
        ]
    },
)
