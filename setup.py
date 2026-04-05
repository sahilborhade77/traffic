from setuptools import setup, find_packages

setup(
    name="traffic_ai",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        # Core dependencies are listed in requirements.txt
    ],
    author="Sahil Borhade",
    description="Smart AI Traffic Intelligence System with YOLOv8, RL (PPO), and LSTM Prediction",
    url="https://github.com/sahilborhade77/traffic",
    python_requires=">=3.10",
)
