from setuptools import setup, find_packages

setup(
    name='uniswap-python',
    version='0.7.2',
    description='An unofficial Python wrapper for the decentralized exchange Uniswap',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/TimeGPT-forcasting-model/uniswap-python.git',
    author='Shane Fontaine, Erik Bjäreholt, Benedict Zhou',
    author_email='machespresso@gmail.com',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Information Technology',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='uniswap ethereum exchange trading',
    packages=find_packages(include=['uniswap', 'uniswap.*']),
    package_data={
        'uniswap': ['assets/*.abi', 'assets/*/*.abi'],
    },
    install_requires=[
        'web3>=6.0,<7.0',
        'click>=8.0.3,<9.0',
        'python-dotenv',
        'typing-extensions',
    ],
    entry_points={
        'console_scripts': [
            'unipy=uniswap:main',
        ],
    },
    extras_require={
        'dev': [
            'mypy',
            'black',
            'pytest>=6.0',
            'pytest-cov',
            'pytest-dotenv',
            'flake8',
            'Sphinx',
            'sphinx-book-theme',
            'sphinx-click',
            'pydata-sphinx-theme==0.13.1',
        ],
    },
    python_requires='>=3.7.2',
)
