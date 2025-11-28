from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings
import os

class VectorStore:
    def __init__(self, collection_name="ticker_reports"):
        self.collection_name = collection_name
        # For Lambda, use in-memory mode
        self.client = QdrantClient(":memory:")
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.initialize_collection()

    def initialize_collection(self):
        """Initialize Qdrant collection"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection with 1536 dimensions (OpenAI embeddings)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
        except Exception as e:
            print(f"Error initializing collection: {str(e)}")

    def store_report(self, ticker, report_text, metadata=None):
        """Store report in vector database"""
        try:
            # Generate embedding
            embedding = self.embeddings.embed_query(report_text)

            # Prepare metadata
            if metadata is None:
                metadata = {}
            metadata['ticker'] = ticker

            # Generate unique ID
            point_id = hash(f"{ticker}_{metadata.get('date', '')}")

            # Store in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "ticker": ticker,
                            "report": report_text,
                            **metadata
                        }
                    )
                ]
            )
            return True
        except Exception as e:
            print(f"Error storing report: {str(e)}")
            return False

    def search_similar_reports(self, query, ticker=None, limit=5):
        """Search for similar reports"""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)

            # Build filter
            query_filter = None
            if ticker:
                query_filter = {
                    "must": [
                        {"key": "ticker", "match": {"value": ticker}}
                    ]
                }

            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit
            )

            return [
                {
                    "ticker": r.payload.get("ticker"),
                    "report": r.payload.get("report"),
                    "score": r.score,
                    "metadata": r.payload
                }
                for r in results
            ]
        except Exception as e:
            print(f"Error searching reports: {str(e)}")
            return []
