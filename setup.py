from setuptools import setup, find_packages

setup(
    name="autoplugin",
    version="0.1.2",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "pydantic",
        "uvicorn",
        "requests",
        "PyYAML",
    ],
    extras_require={
        "gen": ["langchain"],
    },
    author="Suvansh Sanjeev",
    author_email="suvansh@brilliantly.ai",
    description="Create ChatGPT plugins from Python code",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/suvansh/autoplugin",
    project_urls={        
        'Tracker': 'https://github.com/suvansh/autoplugin/issues',
        'Source': 'https://github.com/suvansh/autoplugin/',
        'Documentation': 'https://github.com/suvansh/AutoPlugin/blob/main/README.md',
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
