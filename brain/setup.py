from setuptools import find_packages, setup

package_name = 'brain'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='youzhe02',
    maintainer_email='timu@timuai.com',
    description='Robot Brain',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'brain = brain.robot_brain:main',
            'ota = brain.robot_ota:main',
        ],
    },
)
