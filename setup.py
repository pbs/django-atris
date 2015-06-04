from setuptools import setup
import atris

setup(
    name='django-atris',
    version=atris.__version__,
    description='Django history logging.',
    long_description='Django history logger that keeps track of changes on a'
                     'global level.',
    author='Bogdan Andrei Pop',
    author_email='bpop2232@gmail.com',
    url='https://github.com/pbs/django-atris',
    packages=["atris"],
    include_package_data=True,
    requires=['django'],
)
