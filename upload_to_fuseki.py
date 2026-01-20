#!/usr/bin/env python3
"""
Fusekiにクリーンな状態でRDFデータをアップロードするスクリプト
"""
import requests
import sys
from pathlib import Path

FUSEKI_URL = "http://172.28.64.1:3030/NewsKG"
RDF_FILE = Path("output/knowledge_graph_v2_normalized.ttl")

def clear_fuseki(fuseki_url: str):
    """Fusekiのデータセットをクリア"""
    update_url = f"{fuseki_url}/update"
    response = requests.post(
        update_url,
        data="CLEAR DEFAULT",
        headers={"Content-Type": "application/sparql-update"}
    )
    response.raise_for_status()
    print("✓ Fusekiデータセットをクリアしました")

def upload_rdf(fuseki_url: str, rdf_file: Path):
    """RDFファイルをアップロード"""
    data_url = f"{fuseki_url}/data"
    
    print(f"アップロード中: {rdf_file}")
    with open(rdf_file, 'rb') as f:
        response = requests.post(
            data_url,
            data=f,
            headers={"Content-Type": "text/turtle; charset=utf-8"}
        )
    response.raise_for_status()
    print(f"✓ {rdf_file.name} をアップロードしました")

def count_triples(fuseki_url: str) -> int:
    """トリプル数をカウント"""
    query_url = f"{fuseki_url}/query"
    response = requests.get(
        query_url,
        params={"query": "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"}
    )
    response.raise_for_status()
    return int(response.json()['results']['bindings'][0]['count']['value'])

if __name__ == "__main__":
    print("=" * 60)
    print("Fusekiアップロードスクリプト")
    print("=" * 60)
    
    if not RDF_FILE.exists():
        print(f"エラー: {RDF_FILE} が見つかりません")
        sys.exit(1)
    
    print(f"\nFuseki URL: {FUSEKI_URL}")
    print(f"RDFファイル: {RDF_FILE}\n")
    
    try:
        clear_fuseki(FUSEKI_URL)
        upload_rdf(FUSEKI_URL, RDF_FILE)
        
        count = count_triples(FUSEKI_URL)
        print(f"\n✓ アップロード完了: {count:,} トリプル")
        
    except requests.exceptions.RequestException as e:
        print(f"\nエラー: {e}")
        sys.exit(1)
