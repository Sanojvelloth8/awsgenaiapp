#!/usr/bin/env python3
import boto3
import json
import sys
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def create_index(collection_endpoint, index_name, region):
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, "aoss")
    
    client = OpenSearch(
        hosts=[{"host": collection_endpoint.replace("https://", ""), "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )
    
    index_body = {
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {"ef_construction": 512, "m": 16}
                    }
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
                "AMAZON_BEDROCK_METADATA": {"type": "text"}
            }
        }
    }
    
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=index_body)
        print(f"Index {index_name} created")
    else:
        print(f"Index {index_name} already exists")

if __name__ == "__main__":
    create_index(sys.argv[1], sys.argv[2], sys.argv[3])
