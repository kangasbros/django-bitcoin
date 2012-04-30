from distutils.core import setup

setup(name='django-bitcoin',
      version='0.1',
      description='bitcoin payment management for django',
      author='Jeremias Kangas',
      url='https://github.com/kangasbros/django-bitcoin',
      requires=["qrcode (>2.3.1)", "South (>0.7.4)"],
      packages=['django_bitcoin', 
                'django_bitcoin.management',
                'django_bitcoin.management.commands',
                'django_bitcoin.jsonrpc'],
     )

