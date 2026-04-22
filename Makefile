.PHONY: test lint build up up-cloud up-gpu down logs spark k8s-apply k8s-status k8s-delete help

BACKEND_IMAGE  = ghcr.io/$(shell git config user.name | tr '[:upper:]' '[:lower:]' | tr ' ' '-')/researchmind-backend
FRONTEND_IMAGE = ghcr.io/$(shell git config user.name | tr '[:upper:]' '[:lower:]' | tr ' ' '-')/researchmind-frontend
INPUT         ?= data/urls.csv

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

test: ## Run backend tests
	cd backend && ../.venv/bin/python -m pytest tests/ -v --tb=short 2>/dev/null || \
	  .venv/bin/python -m pytest tests/ -v --tb=short

lint: ## Lint backend with ruff
	cd backend && .venv/bin/ruff check app/ tests/ --fix

build: ## Build Docker images locally
	docker build -t $(BACKEND_IMAGE):local ./backend
	docker build -t $(FRONTEND_IMAGE):local ./frontend

up: ## Start local stack (Ollama + Qdrant embedded)
	uvicorn app.main:app --port 8001 --reload --app-dir backend &
	cd frontend && .venv/bin/streamlit run app.py &

up-cloud: ## Start cloud stack (Groq + Qdrant Cloud) — needs .env.cloud
	docker compose -f docker-compose.yml -f docker-compose.cloud.yml --env-file .env.cloud up -d

down: ## Stop all compose services
	docker compose down

logs: ## Tail backend logs
	docker compose logs -f backend

up-gpu: ## Start GPU stack (vLLM + Qwen2.5-7B) — requires NVIDIA GPU
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

spark: ## Run PySpark batch ingestion — INPUT=data/urls.csv
	docker build -t researchmind-spark ./spark
	docker run --rm \
	  -v $(PWD)/$(INPUT):/data/input.csv:ro \
	  -e QDRANT_HOST=$(or $(QDRANT_HOST),localhost) \
	  -e QDRANT_PORT=$(or $(QDRANT_PORT),6333) \
	  researchmind-spark \
	  spark-submit /opt/spark-jobs/batch_ingest.py --input /data/input.csv

k8s-apply: ## Apply all k8s manifests (namespace first, then rest)
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/secrets.yaml -n researchmind
	kubectl apply -f k8s/qdrant.yaml -n researchmind
	kubectl apply -f k8s/litellm.yaml -n researchmind
	kubectl apply -f k8s/backend.yaml -n researchmind
	kubectl apply -f k8s/frontend.yaml -n researchmind
	kubectl apply -f k8s/ingress.yaml -n researchmind

k8s-status: ## Show pod/service status
	kubectl get pods,svc,ingress -n researchmind

k8s-delete: ## Tear down all k8s resources
	kubectl delete namespace researchmind
