import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='cloudlab',
    version='1.2.0',
    author='Randy May',
    description='A tool for quickly provisioning lab environments on AWS.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/wrmay/cloudlab',
    packages=setuptools.find_packages(),
    package_data={ 'cloudlab': ['plans/*','resources/*']},
    entry_points = {
        'console_scripts' : ['cloudlab=cloudlab.commandline:run']
    },
    license='MIT',
    install_requires=['jinja2>=3.1.4', 'PyYaml>=6.0.2']
)
