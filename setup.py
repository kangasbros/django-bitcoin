from distutils.core import setup

template_patterns = [
    'templates/*.html',
    'templates/*/*.html',
    'templates/*/*/*.html',
    ]

package_name = 'django-bitcoin'

setup(name='django-bitcoin',
      version='0.1',
      description='bitcoin payment management for django',
      author='Jeremias Kangas',
      url='https://github.com/kangasbros/django-bitcoin',
      requires=["qrcode (>2.3.1)", "South (>0.7.4)"],
      packages=['django_bitcoin', 
                'django_bitcoin.management',
                'django_bitcoin.management.commands',
                'django_bitcoin.templatetags',
                'django_bitcoin.templates',
                'django_bitcoin.migrations',
                'django_bitcoin.jsonrpc'],
     package_data=dict( (package_name, template_patterns)
                   for package_name in packages ),
     )

