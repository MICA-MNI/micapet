FROM debian:bullseye-slim

USER root

# ==========================================
# 1. Environment Variables & Paths
# ==========================================
ENV DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C \
    FREESURFER_HOME="/micapet/freesurfer" \ 
    ANTSPATH="/opt/ants" \
    AFNIPATH="/opt/AFNI" \
    CONDA_DIR="/opt/conda" \
    GOVERSION=1.25.4 \
    OS=linux \
    ARCH=amd64 \
    GOPATH="/root/go" \
    VTK_DEFAULT_OPENGL_WINDOW='vtkOSOpenGLRenderWindow' \
    MESA_GL_VERSION_OVERRIDE=3.3 \
    MICA_PET_VERSION="v.alpha.0.6"

    # FREESURFER_HOME="/opt/freesurfer-7.4.1" \

# Combine all binary directories safely into a single PATH declaration
ENV PATH="${CONDA_DIR}/bin:${FREESURFER_HOME}/bin:${FREESURFER_HOME}/mni/bin:${ANTSPATH}/bin:${AFNIPATH}:/usr/local/go/bin:${GOPATH}/bin:${PATH}"

# ==========================================
# 2. System Dependencies
# ==========================================
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip wget bzip2 git \
    bc perl tcsh nano file dc python3 python3-pip \
    libgomp1 libxmu6 libtiff5 libxt6 libglu1-mesa-dev \
    libgl1-mesa-dri libgl1-mesa-dev libxft2 libxinerama1 \
    libxcursor1 libxrandr2 libxrender1 libice6 \
    libfontconfig1 libfreetype6 libopenblas0 \
    build-essential libseccomp-dev pkg-config uidmap fakeroot \
    tzdata squashfs-tools dh-apparmor cryptsetup libgpgme11-dev \
    libssl-dev uuid-dev golang-go xvfb x11-utils \
    connectome-workbench fuse3 fuse-overlayfs squashfuse fuse2fs gocryptfs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# 3. Install Go & Apptainer (1.2.4)
# ==========================================
RUN wget -O /tmp/go.tar.gz https://dl.google.com/go/go${GOVERSION}.${OS}-${ARCH}.tar.gz \
    && tar -C /usr/local -xzf /tmp/go.tar.gz \
    && rm /tmp/go.tar.gz

RUN git clone https://github.com/apptainer/apptainer.git /usr/local/src/apptainer \
    && cd /usr/local/src/apptainer \
    && git checkout v1.2.4 \
    && ./mconfig --without-suid \
    && make -C builddir \
    && make -C builddir install \
    && rm -rf /usr/local/src/apptainer

# ==========================================
# 4. Process Context Resources (FreeSurfer, AFNI, LamaReg)
# ==========================================
# We copy resources once to a temporary scratch space to avoid cache/layer bloating.
COPY resources/ /tmp/resources/

# Install FreeSurfer (minimal extraction)
# RUN if [ -f /tmp/resources/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz ]; then \
#         echo "Found local FreeSurfer archive"; \
#         mv /tmp/resources/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz /tmp/fs.tar.gz; \
#     else \
#         echo "Downloading FreeSurfer archive..."; \
#         wget -O /tmp/fs.tar.gz https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.4.1/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz; \
#     fi \
#     && mkdir -p $FREESURFER_HOME \
#     && tar -xzf /tmp/fs.tar.gz -C $FREESURFER_HOME --strip-components=1 \
#     --exclude='average/mult-comp-cor' \
#     --exclude='lib/qt' \
#     --exclude='lib/cuda' \
#     --exclude='trctrain' \
#     --exclude='subjects/bert' \
#     --exclude='subjects/V1_average' \
#     --exclude='subjects/cvs_*' \
#     --exclude='subjects/fsaverage3' \
#     --exclude='subjects/fsaverage4' \
#     --exclude='subjects/fsaverage5' \
#     --exclude='subjects/fsaverage6' \
#     --exclude='subjects/fsaverage_sym' \
#     && rm -f /tmp/fs.tar.gz \
#     && mv /opt/freesurfer-7.4.1/freesurfer /opt/freesurfer_tmp \
#     && rm -r /opt/freesurfer-7.4.1 \
#     && mv /opt/freesurfer_tmp /opt/freesurfer-7.4.1

# # Install ANTs
RUN curl -fsSL -o /tmp/ants.zip https://github.com/ANTsX/ANTs/releases/download/v2.4.3/ants-2.4.3-centos7-X64-gcc.zip \
    && unzip /tmp/ants.zip -d /opt \
    && mv /opt/ants-2.4.3 $ANTSPATH \
    && rm /tmp/ants.zip

# Install AFNI 3dresample
RUN mkdir -p $AFNIPATH \
    && if [ -d /tmp/resources/AFNI ]; then mv /tmp/resources/AFNI/* $AFNIPATH/; fi \
    && chmod +x $AFNIPATH/3dresample

# ==========================================
# 5. Conda Environment Setup
# ==========================================
RUN curl -fsSL -o /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p $CONDA_DIR \
    && rm /tmp/miniconda.sh

# Copy environment description file
COPY environment.yml /tmp/environment.yml

# Accept the Anaconda Terms of Service non-interactively, then build
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main \
    && conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r \
    && conda env create -n mica-pet -f /tmp/environment.yml \
    && conda clean -a -y \
    && rm /tmp/environment.yml

# Install Lamareg models directly into the freshly created conda environment
RUN mkdir -p $CONDA_DIR/envs/mica-pet/lib/python3.10/site-packages/lamareg/scripts/models \
    && if [ -d /tmp/resources/lamareg ]; then mv /tmp/resources/lamareg/* $CONDA_DIR/envs/mica-pet/lib/python3.10/site-packages/lamareg/scripts/models/; fi \
    && rm -rf /tmp/resources  
    # Wipe out the temp resource directory completely to save space

# Addresses missing libgcrypt.so.11 dependency error
# RUN conda run -n mica-pet conda remove -n mica-pet --force -y vtk \
#     && conda run -n mica-pet pip install --no-cache-dir "vtk==9.2.6"
    
# ==========================================
# 6. Copy Application
# ==========================================
WORKDIR /app
COPY . /app

# Ensure correct permissions & remove redundant resources to minimize final image size
RUN chmod +x /app/run.py \
    && rm -rf /app/resources/lamareg \
    && rm -rf /app/resources/AFNI
    # && rm /app/resources/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz \

# Set the entrypoint to run seamlessly within the conda environment context
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "mica-pet", "python", "/app/run.py"]