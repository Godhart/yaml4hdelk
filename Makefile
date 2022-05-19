SERVER_PORT ?= 8089
DATA_DIR ?= $(shell pwd)/Demo

default: all

.PHONY: docker
docker:
	docker build -t godhart/yaml4schm:1.0 .

.PHONY: run
run:
	docker run --rm \
		--network=host \
		-v "$(DATA_DIR):/data" \
		-e "SERVER_PORT=$(SERVER_PORT)" \
		-e YAML4SCHM_FILES_DOMAIN_DATA=/data \
		-u `id -u ${USER}`:`id -g ${USER}` \
		yaml4schm:1.0

.PHONY: dev
dev:
	docker run --rm -it \
		--network=host \
		-v "$(DATA_DIR):/data" \
		-e "SERVER_PORT=$(SERVER_PORT)" \
		-e YAML4SCHM_FILES_DOMAIN_DATA=/data \
		-u `id -u ${USER}`:`id -g ${USER}` \
		--entrypoint "sh" \
		yaml4schm:1.0

all: docker run
