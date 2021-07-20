FROM fedora:latest

RUN dnf -y update && dnf -y install git which pip bison flex root python3-root root-montecarlo-eg zlib-devel vim flex bison flex-devel bison-devel && dnf clean all

WORKDIR /src

COPY ./download_and_run_emc.sh .
COPY ./requirements.txt .

# ENTRYPOINT /src/download_and_run_emc.sh
