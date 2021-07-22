FROM fedora:latest

WORKDIR /src
COPY ./requirements.txt ./download_and_run_emc.sh .
RUN dnf -y update && dnf -y install git which pip bison flex bison-devel flex-devel root python3-root root-montecarlo-eg zlib-devel vim && dnf clean all\
    && pip3 install -r requirements.txt

# ENTRYPOINT /src/download_and_run_emc.sh
