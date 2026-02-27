from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'orbibot_webgui'

# Build data_files list for frontend dist, preserving subdirectory structure
frontend_data_files = []
frontend_dist = 'frontend/dist'
if os.path.isdir(frontend_dist):
    for dirpath, dirnames, filenames in os.walk(frontend_dist):
        if filenames:
            install_dir = os.path.join('share', package_name, dirpath)
            files = [os.path.join(dirpath, f) for f in filenames]
            frontend_data_files.append((install_dir, files))

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name, ['README.md']),
        # Install launch files
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        # Install config files
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ] + frontend_data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jewel Nath',
    maintainer_email='jewel.nath@orbitax.com',
    description='Web-based dashboard for OrbiBot monitoring and control',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'webrtc_server = orbibot_webgui.webrtc_server:main',
        ],
    },
)
