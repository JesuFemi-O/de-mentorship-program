.PHONY: help up down restart logs ps clean clean-data \
        topics-list topics-describe topics-delete topics-consume \
        buckets buckets-list \
        connectors connectors-list connectors-status connectors-delete \
        deploy verify smoke

# Load .env if present
-include .env
export

COMPOSE_FILE = infrastructure/docker-compose.yml

CONNECT_URL ?= http://localhost:8083
KAFKA_BROKER ?= localhost:9092
S3_ENDPOINT ?= http://localhost:8333
S3_ACCESS_KEY ?= seaweed
S3_SECRET_KEY ?= seaweed123

# Convenience: run a kafka CLI command inside the broker container
KCMD = docker exec kafka

# Convenience: run aws cli with seaweed creds
AWSCMD = AWS_ACCESS_KEY_ID=$(S3_ACCESS_KEY) AWS_SECRET_ACCESS_KEY=$(S3_SECRET_KEY) \
         aws --endpoint-url $(S3_ENDPOINT)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------- Stack lifecycle ----------

up:  ## Start the full stack
	docker compose -f $(COMPOSE_FILE) up -d --build
	@echo "Waiting for services to become healthy..."
	@sleep 10
	@$(MAKE) --no-print-directory verify

down:  ## Stop and remove containers
	docker compose -f $(COMPOSE_FILE) down

restart:  ## Restart the stack
	docker compose -f $(COMPOSE_FILE) restart

logs:  ## Tail logs (use SVC=<service> to filter)
	docker compose -f $(COMPOSE_FILE) logs -f $(SVC)

ps:  ## Show running services
	docker compose -f $(COMPOSE_FILE) ps

clean:  ## Stop containers and remove volumes
	docker compose -f $(COMPOSE_FILE) down -v

clean-data:  ## Nuke all bind-mounted state (requires sudo)
	docker compose -f $(COMPOSE_FILE) down
	sudo rm -rf infrastructure/data/

# ---------- Topics ----------

topics-list:  ## List all topics
	@$(KCMD) kafka-topics --bootstrap-server kafka:29092 --list

topics-describe:  ## Describe a topic (use TOPIC=<name>)
	@$(KCMD) kafka-topics --bootstrap-server kafka:29092 \
	  --describe --topic $(TOPIC)

topics-delete:  ## Delete a topic (use TOPIC=<name>)
	@$(KCMD) kafka-topics --bootstrap-server kafka:29092 \
	  --delete --topic $(TOPIC)

topics-consume:  ## Tail a topic (use TOPIC=<name>, optionally N=<count>)
	@$(KCMD) kafka-console-consumer --bootstrap-server kafka:29092 \
	  --topic $(TOPIC) --from-beginning $(if $(N),--max-messages $(N),)

# ---------- Buckets ----------

buckets:  ## Create S3 buckets from infrastructure/buckets/buckets.json
	@jq -r '.buckets[].name' infrastructure/buckets/buckets.json | \
	  while read bucket; do \
	    echo "Creating bucket: $$bucket"; \
	    $(AWSCMD) s3 mb s3://$$bucket 2>/dev/null || echo "  (already exists)"; \
	  done

buckets-list:  ## List all buckets
	@$(AWSCMD) s3 ls

# ---------- Connectors ----------

connectors:  ## Deploy all connectors in infrastructure/connectors/*.json (idempotent)
	@for f in infrastructure/connectors/*.json; do \
	  name=$$(basename $$f .json); \
	  echo "Deploying connector: $$name"; \
	  curl -fsS -X PUT \
	    -H "Content-Type: application/json" \
	    --data @$$f \
	    $(CONNECT_URL)/connectors/$$name/config > /dev/null && echo "  OK" || echo "  FAILED"; \
	done

connectors-list:  ## List deployed connectors
	@curl -s $(CONNECT_URL)/connectors | jq

connectors-status:  ## Show status of all connectors
	@for c in $$(curl -s $(CONNECT_URL)/connectors | jq -r '.[]'); do \
	  echo "=== $$c ==="; \
	  curl -s $(CONNECT_URL)/connectors/$$c/status | jq '{name, connector: .connector.state, tasks: [.tasks[] | {id, state}]}'; \
	done

connectors-delete:  ## Delete all connectors defined in infrastructure/connectors/
	@for f in infrastructure/connectors/*.json; do \
	  name=$$(basename $$f .json); \
	  echo "Deleting connector: $$name"; \
	  curl -fsS -X DELETE $(CONNECT_URL)/connectors/$$name && echo "  OK" || echo "  not found"; \
	done

# ---------- Composite targets ----------

deploy: buckets connectors  ## Deploy buckets and connectors

verify:  ## Sanity-check the stack
	@echo "--- Kafka brokers ---"
	@$(KCMD) kafka-broker-api-versions --bootstrap-server kafka:29092 2>/dev/null | head -1 || echo "Kafka not ready"
	@echo "--- Schema Registry ---"
	@curl -fsS http://localhost:8081/subjects > /dev/null && echo "OK" || echo "FAILED"
	@echo "--- Kafka Connect ---"
	@curl -fsS $(CONNECT_URL)/ > /dev/null && echo "OK" || echo "FAILED"
	@echo "--- SeaweedFS S3 ---"
	@$(AWSCMD) s3 ls > /dev/null 2>&1 && echo "OK" || echo "FAILED"
	@echo "--- Postgres ---"
	@docker exec postgres pg_isready -U postgres > /dev/null && echo "OK" || echo "FAILED"

smoke:  ## Insert a test row to trigger CDC
	@docker exec postgres psql -U postgres -d cdcdemo -c \
	  "INSERT INTO inventory.customers (first_name, last_name, email) VALUES ('Test', 'User', 'test-$$(date +%s)@example.com');"
	@echo "Inserted. Check Console at http://localhost:8080 or run 'make connectors-status'."
