import os
from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name='ssws',
        version='1.0.0',
        description='Server-Side Web Socket Service',
        long_description='Server-Side Web Socket Service provides a server-driven Web Socket messaging mechanism for deployment behind nginx',
        classifiers=[
            "Programming Language :: Python",
            "Framework :: Django",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
        author='VRPlumber Consulting Inc.',
        author_email='mcfletch@vrplumber.com',
        url='https://github.com/mcfletch/ssws',
        keywords='',
        packages=find_packages(),
        include_package_data=True,
        license='MIT',
        # Dev-only requirements:
        # nose
        # pychecker
        # coverage
        # globalsub
        package_data = {
            'ssws': [
            ],
        },
        install_requires=[
            'twisted',
            'txws',
        ],
        scripts = [
        ],
        entry_points = dict(
            console_scripts = [
                'ssws-server=ssws.service:main', 
                'ssws-session=ssws.sync:session_main', 
                'ssws-message=ssws.sync:message_main', 
            ],
        ),
    )

