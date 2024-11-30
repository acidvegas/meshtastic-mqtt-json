from setuptools import setup, find_packages

setup(
    name="meshtastic-mqtt-json",
    version='0.1.1',
    author='acidvegas',
    author_email='acid.vegas@acid.vegas',
    description='A lightweight Python library for parsing Meshtastic MQTT messages',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/acidvegas/meshtastic_mqtt_json',
    project_urls={
        'Bug Tracker'   : 'https://github.com/acidvegas/meshtastic_mqtt_json/issues',
        'Documentation' : 'https://github.com/acidvegas/meshtastic_mqtt_json#readme',
        'Source Code'   : 'https://github.com/acidvegas/meshtastic_mqtt_json',
    },
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Communications',
    ],
    python_requires='>=3.6',
    install_requires=[
        'cryptography',
        'protobuf',
        'meshtastic',
        'paho-mqtt',
    ],
    entry_points={
        'console_scripts': [
            'meshtastic-mqtt-json=meshtastic_mqtt_json.client:main',
        ],
    },
) 