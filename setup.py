from setuptools import setup
import history_logging

setup(
    name='django-history-logging',
    version=history_logging.__version__,
    description='History logging.',
    long_description='History logging.',
    author='Bogdan Andrei Pop',
    url='https://github.com/bogdanpop/django-history-logging',
    packages=["history_logging"],
    include_package_data=True,
    requires=['django'],
)
