#!/usr/bin/env bash
set -euxo pipefail

docker compose --env-file .env.test up queue -d
docker compose --env-file .env.test up driver

set -a  # Export all the variables in .env.test
source ./.env.test
set +a

# For all the topics ensure there is a single message present
for topic_name in ${PIXL_PULSAR_EHR_TOPIC_NAME} ${PIXL_PULSAR_PACS_TOPIC_NAME}
do
  curl "http://localhost:8080/admin/v2/persistent/public/default/${topic_name}/internalStats" \
  | grep '"entriesAddedCounter":1'
done

docker compose --env-file .env.test down
