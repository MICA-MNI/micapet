FROM mambaorg/micromamba:2.4

# Set work directory
WORKDIR /app

# Set writable temp directory for micromamba
ENV TMPDIR=/tmp
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_ROOT_USER_ACTION=ignore

# Switch to root
USER root

# Install git system-wide
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy environment
COPY environment.yml /tmp/environment.yml

# Create environment (micapet) safely in /opt/conda/envs
RUN micromamba create -y -n micapet -f /tmp/environment.yml && \
    micromamba clean --all --yes

# Make micapet the default environment for subsequent commands
SHELL ["micromamba", "run", "-n", "micapet", "/bin/bash", "-c"]

# install enigmatoolbox from source
RUN git clone https://github.com/MICA-MNI/ENIGMA.git /tmp/enigmatoolbox && \
    cd /tmp/enigmatoolbox && \
    python setup.py install && \
    rm -rf /tmp/enigmatoolbox

# Copy rest of pipeline
COPY . .

# Default command
CMD ["python", "functions/01_master.py"]
