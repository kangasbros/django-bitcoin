#!/usr/bin/env python

from setuptools import setup, find_packages

tests_require = [
    'django',
    # also requires the disqus fork of haystack
]

setup(
    name='django_bitcoin',
    version=".".join(map(str, __import__('django_bitcoin').__version__)),
    author='Jeremias Kangas',
    author_email='jeremias.kangas@gmail.com',
    description='BItcoin development for django',
    url='http://github.com/kangasbros/django-bitcoin',
    install_requires=[
        'django',
    ],
    tests_require=tests_require,
    #extras_require={'test': tests_require},
    #test_suite='djangoratings.runtests.runtests',
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development"
    ],
)
