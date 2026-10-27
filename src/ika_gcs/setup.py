from glob import glob

from setuptools import setup

package_name = 'ika_gcs'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/web', glob('web/*.*')),
        ('share/' + package_name + '/web/vendor', glob('web/vendor/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Ali Talha',
    maintainer_email='alitlhq@icloud.com',
    description='Tarayıcı tabanlı host kontrol arayüzü (rosbridge)',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'robot_pose_node = ika_gcs.robot_pose_node:main',
        ],
    },
)
