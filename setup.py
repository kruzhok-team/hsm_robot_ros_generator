from setuptools import setup

package_name = 'hsm_generator'

# The controller runtime library of the hsm_controller directory is not installed as a
# Python package: it is the code the generator copies into the packages it produces, and
# a generated package installs it under its own name. Installing it here as well would
# shadow the generated one in the same workspace.

setup(
    name=package_name,
    version='1.0.0',
    packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
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
        ],
    },
)
