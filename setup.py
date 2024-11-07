# -*- coding: utf-8 -*-

"""
--------------------------------------------
project: zibuyu_LLM
author: 子不语
date: 2024/5/11
contact: 【公众号】思维兵工厂
description: 
--------------------------------------------
"""

from setuptools import setup, find_packages

with open('./Readme.md', 'r', encoding='utf-8') as file:
    long_description = file.read()

VERSION = '0.0.1'
DESCRIPTION = '个人工具-蓝奏云API调用'

setup(
    name='zibuyu_lanzou',
    version=VERSION,
    description='子不语个人工具包-蓝奏云API调用',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='子不语',
    packages=find_packages('./zibuyu_lanzou'),
    license='MIT',
    package_dir={'': './zibuyu_lanzou'},
    keywords=['zibuyu', 'zibuyu_lanzou', 'lanzou'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12'
    ],
    install_requires=[
        'fake-useragent',
        'requests',
        'requests-toolbelt',
    ],
    python_requires='>=3.9'
)
