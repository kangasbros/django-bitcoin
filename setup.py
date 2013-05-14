from setuptools import setup


template_patterns = ['templates/*.html',
                     'templates/*/*.html',
                     'templates/*/*/*.html',
                     ]

package_name = 'django-bitcoin'
packages = ['django_bitcoin',
            'django_bitcoin.management',
            'django_bitcoin.management.commands',
            'django_bitcoin.templatetags',
            'django_bitcoin.templates',
            'django_bitcoin.migrations',
            'django_bitcoin.jsonrpc']

long_description = open("README.rst") + "\n" + open("CHANGES.rst")

setup(name='django-bitcoin',
      version='0.1',
      description='Bitcoin application integration for Django web framework',
      author='Jeremias Kangas',
      url='https://github.com/kangasbros/django-bitcoin',
      requires=["qrcode (>2.3.1)", "South (>0.7.4)"],
      license="MIT",
      packages=packages,
      package_data=dict((package_name, template_patterns) for package_name in packages),
      )
