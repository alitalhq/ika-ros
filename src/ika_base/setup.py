from setuptools import setup

package_name = 'ika_base'

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
    description='Diferansiyel sürüş: enkoder geri beslemeli motor kontrolü ve teker odometrisi',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ika_base_node = ika_base.base_node:main',
            'hw_check = ika_base.hw_check:main',
        ],
    },
)
