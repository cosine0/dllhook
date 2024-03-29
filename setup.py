import os
from setuptools import setup, find_packages

version = '0.1.2'
package_name = "dllhook"
package_description = """
Hook x86 dll or executable instruction with python script injecting embedded python interpreter. 
""".strip()

packages = find_packages()
install_requires = ['boltons', 'cffi', 'six', 'capstone']


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join("..", path, filename))
    return paths


setup(
    name=package_name,
    version=version,
    description=package_description,
    packages=packages,
    package_data={'dllhook': package_files('dllhook/mayhem')},
    license="GPLv3",
    author="Bumsu Hyeon",
    author_email="ksitht@gmail.com",
    install_requires=install_requires,
    classifiers=[
        'Topic :: Security',
        'Environment :: Console',
        'Operating System :: Microsoft :: Windows',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Intended Audience :: Developers'
    ],
    url='https://github.com/cosine0/dllhook'
)
