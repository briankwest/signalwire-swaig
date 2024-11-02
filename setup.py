from setuptools import setup, find_packages

setup(
    name="signalwire-swaig",
    version="0.1.8",
    include_package_data=True,
    install_requires=[
        "Flask==3.0.3",
        "flask_httpauth==4.8.0",
        "setuptools==66.1.1",
    ],
    description="A SignalWire SWAIG interface for AI Agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Brian West",
    author_email="brian@signalwire.com",
    url="https://github.com/briankwest/signalwire-swaig",
    packages=find_packages(),
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
