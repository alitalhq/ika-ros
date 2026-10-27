from setuptools import setup

package_name = 'ika_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Ali Talha',
    maintainer_email='alitlhq@icloud.com',
    description='Sürüş modu yönetimi, /cmd_vel çoklayıcı, acil durdurma ve lidar freni',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mode_manager_node = ika_control.mode_manager_node:main',
        ],
    },
)
