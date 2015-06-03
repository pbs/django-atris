from setuptools import setup
import history_logging

setup(
    name='django-atris',
    version=atris.__version__,
    description='Django history logging.',
    long_description='Django history logger that keeps track of changes on a'
                     'global level.',
    author='Bogdan Andrei Pop',
    url='https://github.com/bogdanpop/django-history-logging',
    packages=["atris"],
    include_package_data=True,
    requires=['django'],
)
