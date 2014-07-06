#!/usr/bin/env python
import os

from distutils.core import setup


install_requires = [
    'oauthclient==1.0.0',
]

setup(name='boxclient',
      version='1.2.0',
      description='Box API v2.0 client',
      author='Roberto Aguilar',
      author_email='r@rreboto.com',
      packages=['box'],
      long_description=open('README.md').read(),
      url='http://github.com/rca/box',
      license='LICENSE',
      install_requires=install_requires,
)
