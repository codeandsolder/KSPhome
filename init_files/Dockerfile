FROM mcr.microsoft.com/dotnet/sdk:10.0

# Install Python, Git, 7-Zip, Mono, and other utilities
RUN apt-get update && apt-get install -y \
    python3 \
    git \
    p7zip-full \
    wget \
    unzip \
    mono-complete \
    patch \
    && rm -rf /var/lib/apt/lists/*

# Install ILSpy command line tool
RUN dotnet tool install --global ilspycmd --version 10.0.0.8079-preview1
ENV PATH="$PATH:/root/.dotnet/tools"

# Install de4dot
WORKDIR /opt
RUN wget https://github.com/kant2002/de4dot/releases/download/v3.2.0/de4dot-net48.zip \
    && unzip de4dot-net48.zip -d de4dot \
    && rm de4dot-net48.zip

# Set up workspace
WORKDIR /workspace
COPY . /app/
WORKDIR /workspace

ENTRYPOINT ["python3", "/app/docker_entrypoint.py"]