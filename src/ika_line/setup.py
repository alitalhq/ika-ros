from setuptools import setup

package_name = 'ika_line'

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
    description='QTR-RC / dijital IR çizgi sensörü sürücüsü ve PD çizgi izleme',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'line_sensor_node = ika_line.line_sensor_node:main',
            'line_follower_node = ika_line.line_follower_node:main',
            'line_check = ika_line.line_check:main',
        ],
    },
)
