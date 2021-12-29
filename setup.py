"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='pyg90alarm',
    version='1.0.0',
    description='G90 Alarm system protocol',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/hostcc/pyg90alarm',
    author='Ilia Sotnikov',
    author_email='hostcc@gmail.com',

    # Classifiers help users find your project by categorizing it.
    #
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 3 - Alpha',
        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        # Pick your license as you wish
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],

    keywords='g90, alarm, protocol',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.6, <4',
    install_requires=[],

    extras_require={
        'dev': [
            'check-manifest',
        ],
        'test': [
            'coverage',
            'asynctest',
        ],
        'docs': [
            'Sphinx',
            'myst-parser',
        ],
    },

    project_urls={  # Optional
        'Bug Reports': 'https://github.com/hostcc/pyg90alarm/issues',
        'Source': 'https://github.com/hostcc/pyg90alarm/',
    },
)
