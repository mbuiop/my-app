from setuptools import setup, find_packages
import os

# خواندن محتوای README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# خواندن requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="galactic-cinematic-game",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="یک بازی فضایی سینمایی با گرافیک سه‌بعدی حرفه‌ای",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/galactic-cinematic-game",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "galactic-game=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.ini"],
    },
    options={
        'build_exe': {
            'includes': ['pygame', 'OpenGL', 'numpy'],
            'include_files': [],
        }
    },
)
