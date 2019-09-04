from setuptools import setup

with open('requirements.txt') as read_file:
    REQUIRED = read_file.read().splitlines()

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='adaptivetuning',
    version='0.0.1',
    description='blablabla',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    py_modules=['adaptivetuning'],
    install_requires=REQUIRED,
    author='Arne Kramer-Sunderbrink',
    author_email='herr-kramer-sunderbrink@t-online.de',
    keywords=['music, dissonance, adatptive tuning'],
    url='https://github.com/ArneKramerSunderbrink/adaptivetuning',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Topic :: Multimedia :: Sound/Audio'
    ],
)