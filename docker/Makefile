all: run

build:
	sudo docker image build -t em-creator:latest . # To build the image

run:
	sudo docker run -it --entrypoint /bin/bash -v `cd ..; pwd`:/src/em-creator em-creator

save:
	sudo docker save -o em-creator.tar.gz em-creator
