import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'orbibot_localization'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jewel Nath',
    maintainer_email='jewel.nath@orbitax.com',
    description='Enhanced localization package for OrbiBot with sensor fusion',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'measure_imu_noise = orbibot_localization.measure_imu_noise:main',
        ],
    },
)
