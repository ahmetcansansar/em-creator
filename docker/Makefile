all: run

build:
	sudo docker image build -t em-creator:latest . # To build the image

run:
	sudo docker run -it --entrypoint /bin/sh -v ./:/src/em-creator localhost/em-creator:latest
