from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'orbibot_bringup'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jewel Nath',
    maintainer_email='jewel.nath@orbitax.com',
    description='System launch files and bringup configurations for OrbiBot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'cmd_vel_idle = orbibot_bringup.cmd_vel_idle:main',
            'cmd_vel_source = orbibot_bringup.cmd_vel_source:main',
        ],
    },
)
