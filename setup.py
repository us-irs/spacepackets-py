#!/usr/bin/env python3
"""
We do the package handling in the static setup.cfg but include an empty setup.py
to allow editable installs https://packaging.python.org/tutorials/packaging-projects/
and provide extensibility
"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup()
