#!/usr/bin/env python
# Copyright 2022 Espressif Systems (Shanghai) Co., Ltd.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

try:
    from setuptools import find_packages, setup
except ImportError:
    print(
        "Package setuptools is missing from your Python installation. "
        "Please see the installation section in the esp_cryptoauth_utility documentation"
        " for instructions on how to install it."
    )
    exit(1)

VERSION = '0.9.0'

long_description = """
==========
esp_cryptoauth_utility
==========
The python utility helps to configure and provision ATECC608 chip connected to ESP32 module. 

The esp_cryptoauth_utility is `hosted on github <https://github.com/espressif/esp-cryptoauthlib/tree/master/esp_cryptoauth_utility>`_.

Documentation
-------------
Visit online `esp_cryptoauth_utility documentation <https://github.com/espressif/esp-cryptoauthlib/tree/master/esp_cryptoauth_utility#readme/>`_ \
or run ``secure_cert_mfg.py.py -h``.

License
-------
The License for the project can be found `here <https://github.com/espressif/esp-cryptoauthlib/blob/master/esp_cryptoauth_utility/LICENSE>`_
"""

setup(
    name="esp_cryptoauth_utility",
    version=VERSION,
    description="A python utility which helps to configure and provision ATECC608 chip connected to ESP32 module",
    long_description=long_description,
    url="https://github.com/espressif/esp-cryptoauthlib/tree/master/esp_cryptoauth_utility",
    project_urls={
        "Documentation": "https://github.com/espressif/esp-cryptoauthlib/tree/master/esp_cryptoauth_utility#readme",
        "Source": "https://github.com/espressif/esp-cryptoauthlib/tree/master/esp_cryptoauth_utility",
    },
    author="Espressif Systems",
    author_email="",
    classifiers=[
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Topic :: Software Development :: Embedded Systems",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    setup_requires=(["wheel"] if "bdist_wheel" in sys.argv else []),
    install_requires=[
        "cryptography==3.4.8",
        "pyasn1_modules==0.1.5",
        "pyasn1==0.3.7",
        "python-jose==3.1.0",
    ],
    packages=find_packages(),
    scripts=["secure_cert_mfg.py"],
)
