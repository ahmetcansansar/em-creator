all: run

build:
	sudo docker image build -t em-creator:latest . # To build the image

run:
	sudo docker run -it --entrypoint /bin/bash -v `cd ..; pwd`:/src/em-creator em-creator

run_bash:
	sudo docker run --interactive --tty em-creator
