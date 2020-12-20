"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='kodi_wol_listener',
    version='0.1.0',
    description='Waits for an incoming WOL pattern on UDP port 42429 and runs kodi when received',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/frosch01/rpi_vdr_kodi',
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: Console',
                 'Operating System :: POSIX :: Linux',
                 'Intended Audience :: End Users/Desktop',
                 'Topic :: Desktop Environment',
                 'Programming Language :: Python :: 3.7'],
    keywords='kodi, wol, wake-on-lan, kore',
    python_requires='>=3.7, <4',
    install_requires=['coloredlogs', 'getmac'],
    entry_points={
        'console_scripts': [
            'kodi_wol_listener=kodi_wol_listener:main',
        ]
    }
)
