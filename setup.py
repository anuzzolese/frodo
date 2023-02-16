from setuptools import setup, find_packages

install_requires=[
   'flask',
   'rdflib',
   'nltk',
   'shortuuid',
   'fredclient @ git+https://github.com/anuzzolese/fredclient'
]

setup(name='frodo', version='1.0.0',
    packages=find_packages(), install_requires=install_requires)
