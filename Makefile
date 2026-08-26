.PHONY: help install run docker-build docker-up clean

help:
	@echo "TelosVM Compiler Makefile"
	@echo "  install      - Install Python dependencies"
	@echo "  run          - Run the FastAPI development server"
	@echo "  docker-build - Build the Docker image"
	@echo "  docker-up    - Run the service via Docker Compose"
	@echo "  clean        - Remove __pycache__ and build artifacts"

install:
	pip install -e .
	pip install -r requirements.txt

run-api:
	uvicorn src.telosvm.api:app --reload --host 0.0.0.0 --port 8000

run-cli:
	telos --help

docker-build:
	docker build -t usir-compiler:latest .

docker-up:
	docker-compose up --build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
