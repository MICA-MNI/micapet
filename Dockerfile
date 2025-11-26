FROM continuumio/miniconda3:latest

# Set the working directory in the container
WORKDIR /app

# Copy the entire project into the container
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a conda environment and install dependencies
COPY environment.yml /app/environment.yml
RUN conda env create -f /app/environment.yml && conda clean -a -y

# Activate the conda environment
SHELL ["/bin/bash", "-c"]
RUN echo "conda activate micapet" >> ~/.bashrc
ENV PATH /opt/conda/envs/micapet/bin:$PATH

# Set the entrypoint to run the 01_master.py script
ENTRYPOINT ["python", "/app/functions/01_master.py"]
