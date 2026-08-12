from glob import glob

from setuptools import setup

package_name = 'hsm_generator'

# The controller runtime library of the hsm_controller directory is not installed as a
# Python package: it is the code the generator copies into the packages it produces, and
# a generated package installs it under its own name. Installing it here as well would
# shadow the generated one in the same workspace. It is shipped as data instead, together
# with the templates, and is located through the ament share directory.

setup(
    name=package_name,
    version='1.0.0',
    packages=[],
    py_modules=['gencode', 'hsm_generator'],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/templates', glob('templates/*.templ')),
        ('share/' + package_name + '/hsm_controller', glob('hsm_controller/*.py')),
        ('share/' + package_name + '/examples', glob('examples/*.graphml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alexey Fedoseev',
    maintainer_email='aleksey@fedoseev.net',
    description='The HSM-to-ROS2 code generator',
    license='LGPL-3.0-or-later',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'hsm_generator = hsm_generator:main',
        ],
    },
)
