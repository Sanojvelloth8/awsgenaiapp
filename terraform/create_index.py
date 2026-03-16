#!/usr/bin/env python3
import boto3
import sys
import time
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth


def create_index(collection_endpoint: str, index_name: str, region: str,
                 retries: int = 10, delay: int = 30):
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, "aoss")

    client = OpenSearch(
        hosts=[{
            "host": collection_endpoint.replace("https://", ""),
            "port": 443,
        }],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
    )

    index_body = {
        "settings": {"index.knn": True},
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16},
                    },
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
                "AMAZON_BEDROCK_METADATA":   {"type": "text"},
            }
        },
    }

    for attempt in range(retries):
        try:
            if client.indices.exists(index=index_name):
                print(f"Index '{index_name}' already exists.")
                return
            client.indices.create(index=index_name, body=index_body)
            print(f"Index '{index_name}' created successfully.")
            return
        except Exception as e:
            if attempt < retries - 1:
                print(f"Attempt {attempt + 1}/{retries} failed: {e}. "
                      f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"All {retries} attempts failed. Last error: {e}")
                raise


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: create_index.py <endpoint> <index_name> <region>")
        sys.exit(1)
    create_index(sys.argv[1], sys.argv[2], sys.argv[3])
