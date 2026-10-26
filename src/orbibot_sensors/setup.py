import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'orbibot_sensors'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jewel Nath',
    maintainer_email='58494211+jewel-nath@users.noreply.github.com',
    description='Sensor integration package for OrbiBot - RPLidar A1 and Intel RealSense D435',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'obstacle_detector = orbibot_sensors.obstacle_detector:main',
        ],
    },
)
