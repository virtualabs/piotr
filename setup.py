import os
import sys
from setuptools import setup, find_packages

if sys.version_info[0] < 3:
    with open('README.rst') as f:
        long_description = f.read()
else:
    with open('README.rst', encoding='utf-8') as f:
        long_description = f.read()

setup(
    name='piotr',
    version='1.0.2',
    description='Piotr is an instrumentation tool for qemu-system-arm able to emulate ARM-based embedded devices.',
    long_description=long_description,
    url='https://github.com/virtualabs/piotr',
    author='virtualabs',
    author_email='virtualabs@gmail.com',
    packages=find_packages('src'),
    package_dir={"":"src"},
    package_data = {
        'piotr':[
            'data/*'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux'
    ],
    entry_points = {
        'console_scripts': [
            'piotr=piotr:main',
            'piotr-shell=piotr.shell:guest_shell',
            'piotr-ps=piotr.shell:host_ps',
            'piotr-debug=piotr.shell:debug_process'
        ],
    },
    install_requires = [
        'blessings',
        'psutil',
        'pyyaml'
    ],
    python_requires='>=3.5',
    test_suite='tests'
)
