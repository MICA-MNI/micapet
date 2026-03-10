#####################################################################
# Stage 1 — Build Conda Environment
#####################################################################
FROM continuumio/miniconda3:latest AS conda_stage

WORKDIR /app
COPY environment.yml .

RUN conda env create -n mica-pet -f environment.yml && \
    conda clean -a -y

#####################################################################
# Stage 2 — Final Image
#####################################################################
FROM debian:bullseye-slim
USER root

# Set environment variables
# ENV LANG="en_US.UTF-8" \
#     LC_ALL="en_US.UTF-8" \
ENV LC_ALL=C \
    FREESURFER_HOME="/opt/freesurfer-7.4.1" \
    SUBJECTS_DIR="$FREESURFER_HOME/subjects" \
    PATH="/opt/freesurfer-7.4.1/bin:$FREESURFER_HOME/mni/bin:$PATH" \
    ANTSPATH="/opt/ants" \
    PATH="/opt/ants:$PATH" \
    C3DPATH="/opt/convert3d-1.0.0" \
    PATH="/opt/convert3d-1.0.0/bin:$PATH" \
    CONDA_DIR="/opt/miniconda-latest" \
    PATH="/opt/miniconda-latest/bin:$PATH"
    
#####################################################################
# Install Dependencies
#####################################################################
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip wget bzip2 \
    bc perl tcsh nano file dc python3 python3-pip \
    libgomp1 libxmu6 libxt6 libglu1-mesa-dev \
    libgl1-mesa-dri libgl1-mesa-dev libxft2 libxinerama1 \
    libxcursor1 libxrandr2 libxrender1 libice6 \
    libfontconfig1 libfreetype6 libopenblas0 \
    build-essential \
    libseccomp-dev \
    pkg-config \
    uidmap \
    fakeroot \
    tzdata \
    squashfs-tools \
    dh-apparmor \
    cryptsetup \
    libgpgme11-dev \
    libssl-dev \
    uuid-dev \
    golang-go \
    xvfb \
    x11-utils \
    curl wget git && \
    apt-get install -y connectome-workbench fuse3 fuse-overlayfs squashfuse fuse2fs gocryptfs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

#####################################################################
# Install Apptainer 1.2.4
#####################################################################
ENV GOVERSION=1.25.4 OS=linux ARCH=amd64 VERSION=3.0.3 
# change this as you need 
RUN wget -O /tmp/go${GOVERSION}.${OS}-${ARCH}.tar.gz \
    https://dl.google.com/go/go${GOVERSION}.${OS}-${ARCH}.tar.gz \
    && tar -C /usr/local -xzf /tmp/go${GOVERSION}.${OS}-${ARCH}.tar.gz \
    && echo 'export GOPATH=${HOME}/go' >> ~/.bashrc \
    && echo 'export PATH=/usr/local/go/bin:${PATH}:${GOPATH}/bin' >> ~/.bashrc 
ENV PATH="/usr/local/go/bin:${PATH}:${GOPATH}/bin"

RUN git clone https://github.com/apptainer/apptainer.git /usr/local/src/apptainer && \
    cd /usr/local/src/apptainer && \
    git checkout v1.2.4 && \
    ./mconfig --without-suid && \
    make -C builddir && \
    make -C builddir install && \
    rm -rf /usr/local/src/apptainer

#####################################################################
# Install FreeSurfer (minimal)
#####################################################################
# Copy resources directory (containing FS tar.gz if available)
COPY resources/ /tmp/resources/

RUN if [ -f /tmp/resources/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz ]; then \
        echo "Found local FreeSurfer archive"; \
        mv /tmp/resources/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz /tmp/fs.tar.gz; \
    else \
        echo "Downloading FreeSurfer archive..."; \
        wget -O /tmp/fs.tar.gz https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.4.1/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz; \
    fi && \
    mkdir -p $FREESURFER_HOME && \
    tar -xzf /tmp/fs.tar.gz -C $FREESURFER_HOME --strip-components=1 \
    --exclude='average/mult-comp-cor' \
    --exclude='lib/qt' \
    --exclude='lib/cuda' \
    --exclude='trctrain' \
    --exclude='subjects/bert' \
    --exclude='subjects/V1_average' \
    --exclude='subjects/cvs_*' \
    --exclude='subjects/fsaverage3' \
    --exclude='subjects/fsaverage4' \
    --exclude='subjects/fsaverage5' \
    --exclude='subjects/fsaverage6' \
    --exclude='subjects/fsaverage_sym' \
    && rm /tmp/fs.tar.gz \
    && mv /opt/freesurfer-7.4.1/freesurfer /opt/freesurfer_tmp \
    && rm -r /opt/freesurfer-7.4.1 \
    && mv /opt/freesurfer_tmp /opt/freesurfer-7.4.1

#####################################################################
# Install ANTs
#####################################################################
ENV ANTSPATH=/opt/ants
ENV PATH=$ANTSPATH/bin:$PATH

RUN curl -fsSL -o /tmp/ants.zip \
    https://github.com/ANTsX/ANTs/releases/download/v2.4.3/ants-2.4.3-centos7-X64-gcc.zip && \
    unzip /tmp/ants.zip -d /opt && mv /opt/ants-2.4.3 $ANTSPATH && \
    rm /tmp/ants.zip

# #####################################################################
# # Install C3D
# #####################################################################
# ENV C3DPATH=/opt/c3d
# ENV PATH=$C3DPATH/bin:$PATH

# RUN mkdir -p $C3DPATH && \
#     curl -fsSL https://sourceforge.net/projects/c3d/files/c3d/1.0.0/c3d-1.0.0-Linux-x86_64.tar.gz/download \
#         | tar -xz --strip-components=1 -C $C3DPATH

#####################################################################
# Install AFNI 3dresample
#####################################################################
ENV AFNIPATH=/opt/AFNI
ENV PATH=$AFNIPATH/bin:$PATH

RUN mkdir -p $AFNIPATH && \
    mv -r /tmp/resources/AFNI /opt/AFNI 

#####################################################################
# Install Miniconda & copy env
#####################################################################
RUN curl -fsSL -o /tmp/miniconda.sh \
    https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && rm /tmp/miniconda.sh

ENV CONDA_DIR=/opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH

COPY --from=conda_stage /opt/conda/envs/mica-pet /opt/conda/envs/mica-pet

# RUN pip install --upgrade --force-reinstall git+https://github.com/MICA-MNI/BrainSpace.git

# RUN conda run -n mica-pet pip install --extra-index-url https://wheels.vtk.org vtk-osmesa

#####################################################################
# Copy Application
#####################################################################
WORKDIR /app

# Copy the entire application structure
COPY . /app

# Ensure correct permissions
RUN chmod +x /app/run.py

ENV PATH=$FREESURFER_HOME/bin:$PATH \
    VTK_DEFAULT_OPENGL_WINDOW='vtkOSOpenGLRenderWindow' \
    MESA_GL_VERSION_OVERRIDE=3.3

# Set the entrypoint to the Snakebids app (run.py)
ENTRYPOINT ["conda", "run", "-n", "mica-pet", "python", "/app/run.py"]

# docker build -t micalab/micapet .

