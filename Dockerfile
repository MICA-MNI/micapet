FROM continuumio/miniconda3:latest

WORKDIR /app

# Install system dependencies (rarely changes)
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy only the environment file so that conda layer is reusable
COPY environment.yml .

# Create the conda environment (expensive; keep it early for caching)
RUN conda env create -f environment.yml && conda clean -ay
ENV PATH="/opt/conda/envs/micapet/bin:${PATH}"

# Install FastSurfer (put before copying entire repo)
ENV FASTSURFER_HOME="/opt/FastSurfer"
RUN git clone --depth 1 --branch v2.4.2 \
    https://github.com/Deep-MI/FastSurfer.git $FASTSURFER_HOME

# Now copy the project (frequent changes → placed at end)
COPY . /app

# ENTRYPOINT
ENTRYPOINT ["python", "/app/functions/01_master.py"]
