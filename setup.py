from setuptools import setup
import history_logging

tests_require = ["Django>=1.4", "webtest==2.0.6", "django-webtest==1.7"]
try:
    from unittest import skipUnless
except ImportError:  # Python 2.6 compatibility
    tests_require.append("unittest2")

setup(
    name='django-history-logging',
    version=history_logging.__version__,
    description='History logging.',
    long_description='History logging.',
    author='Bogdan Andrei Pop',
    url='https://github.com/bogdanpop/django-history-logging',
    packages=["history_logging"],
    include_package_data=True,
)
