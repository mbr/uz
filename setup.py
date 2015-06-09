#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='uz',
    version='0.2',
    description='uz extracts files of all sorts',
    long_description=read('README.rst'),
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    url='http://github.com/mbr/uz',
    license='MIT',
    packages=find_packages(exclude=['tests']),
    install_requires=['click', 'backports.lzma'],
    entry_points={
        'console_scripts': [
            'uz = uz.cli:uz',
        ],
    }
)
