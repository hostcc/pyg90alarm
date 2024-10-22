"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.rst').read_text(encoding='utf-8')

setup(
    name='pyg90alarm',
    setup_requires=['setuptools_scm'],
    use_scm_version={
        "local_scheme": "no-local-version"
    },
    description='G90 Alarm system protocol',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/hostcc/pyg90alarm',
    author='Ilia Sotnikov',
    author_email='hostcc@gmail.com',

    # Classifiers help users find your project by categorizing it.
    #
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Home Automation',
        'Topic :: System :: Hardware',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3 :: Only',
    ],

    keywords='g90, alarm, protocol',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.8, <4',
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
            'sphinx',
            'sphinx-rtd-theme',
        ],
    },

    project_urls={
        'Bug Reports': 'https://github.com/hostcc/pyg90alarm/issues',
        'Source': 'https://github.com/hostcc/pyg90alarm/',
    },
)
