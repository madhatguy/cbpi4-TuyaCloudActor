from setuptools import setup

from os import path


this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="cbpi4-TuyaCloudActor",
    version="0.0.1",
    description="CraftBeerPi4 Tuya Cloud Actor Plugin",
    author="",
    author_email="",
    url="",
    license="MIT",
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.rst", "*.yaml"],
        "cbpi4-TuyaCloudActor": ["*", "*.txt", "*.rst", "*.yaml"],
    },
    packages=["cbpi4-TuyaCloudActor"],
    # CBPi is the host application and is expected to already be installed
    # in the cbpi4 runtime environment. Keeping it out of install_requires
    # prevents pip from trying (and potentially failing) to install/upgrade cbpi.
    install_requires=["tuya-iot-py-sdk"],
    long_description=long_description,
    long_description_content_type="text/markdown",
)

