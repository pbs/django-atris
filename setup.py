from glob import glob
from os.path import basename
from os.path import splitext
from setuptools import setup
from setuptools import find_packages

setup(
    name='django-atris',
    version='0.1.11',
    description='Django history logging.',
    long_description=(
        'Django history logger that keeps track of changes on a global '
        'level.'),
    author='Bogdan Andrei Pop',
    author_email='bpop2232@gmail.com',
    url='https://github.com/pbs/django-atris',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'Django>=1.7,<1.9',
    ]
)
