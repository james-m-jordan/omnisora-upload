from setuptools import setup, find_packages

setup(
    name="omnisora-upload",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "flask",
        "flask-cors",
        "boto3",
        "gunicorn",
        "python-dotenv",
        "openai"
    ]
)