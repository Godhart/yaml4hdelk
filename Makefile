SERVER_PORT ?= 8089
DATA_DIR ?= $(shell pwd)/Demo

default: all

.PHONY: docker
docker:
	docker build -t godhart/yaml4schm:1.0 .

.PHONY: run
run:
	docker run --rm \
		-v "$(DATA_DIR):/data" \
		-e "SERVER_HOST=0.0.0.0" \
		-e "SERVER_PORT=80" \
		-e YAML4SCHM_FILES_DOMAIN_DATA=/data \
		-p "$(SERVER_PORT):80" \
		-u `id -u ${USER}`:`id -g ${USER}` \
		godhart/yaml4schm:1.0

.PHONY: dev
dev:
	docker run --rm -it \
		-v "$(DATA_DIR):/data" \
		-e "SERVER_HOST=0.0.0.0" \
		-e "SERVER_PORT=80" \
		-e YAML4SCHM_FILES_DOMAIN_DATA=/data \
		-p "$(SERVER_PORT):80" \
		-u `id -u ${USER}`:`id -g ${USER}` \
		--entrypoint "sh" \
		godhart/yaml4schm:1.0

all: docker run
