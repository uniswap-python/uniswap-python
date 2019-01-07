#!/usr/bin/env python

from setuptools import setup, find_packages

install_requires = [
    'web3',
]

tests_require = [
    'pytest',
    ]

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="uniswap-python",
    version="0.3.3",
    author="Shane Fontaine",
    author_email="shane6fontaine@gmail.com",
    license='MIT',
    description="An unofficial python wrapper for the Uniswap exchange",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shanefontaine/uniswap-python",
    packages=find_packages(),
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
    },
    keywords=['uniswap', 'uniswap-exchange', 'uniswap-api', 'orderbook', 'dex',
              'trade', 'ethereum', 'ETH', 'client', 'api', 'wrapper',
              'exchange', 'crypto', 'currency', 'trading', 'trading-api',
              'decentralized-exchange'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development :: Libraries :: Python Modules',
        "License :: OSI Approved :: MIT License",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        "Programming Language :: Python :: 3.6",
    ],
)
