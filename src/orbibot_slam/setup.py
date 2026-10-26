from setuptools import find_packages, setup

package_name = 'orbibot_slam'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/slam.launch.py', 'launch/slam_localization.launch.py']),
        ('share/' + package_name + '/config', ['config/slam_params.yaml', 'config/slam_localization_params.yaml']),
        ('share/' + package_name + '/rviz', ['rviz/slam.rviz']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jewel Nath',
    maintainer_email='58494211+jewel-nath@users.noreply.github.com',
    description='SLAM package for OrbiBot using slam_toolbox',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
