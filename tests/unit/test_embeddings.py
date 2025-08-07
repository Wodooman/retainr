#!/usr/bin/env python3
"""Unit tests for EmbeddingService."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from chromadb.errors import ChromaError

from mcp_server.config import Settings
from mcp_server.embeddings import EmbeddingService
from mcp_server.models import MemoryEntry


@pytest.mark.unit
@pytest.mark.fast
class TestEmbeddingService:
    """Test the EmbeddingService class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def mock_settings(self, temp_dir):
        """Create mock settings for testing."""
        settings = Settings()
        settings.chroma_host = "localhost"
        settings.chroma_port = 8000
        settings.chroma_collection = "test_retainr"
        settings.embedding_model = "all-MiniLM-L6-v2"
        settings.model_cache_dir = temp_dir / "cache"
        return settings

    @pytest.fixture
    def sample_memory(self):
        """Create a sample memory entry."""
        return MemoryEntry(
            project="test-project",
            category="testing",
            content="# Test Memory\n\nThis is a test memory for unit testing.",
            tags=["test", "unit"],
            references=["test_file.py"],
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def mock_chroma_client(self):
        """Create a mock ChromaDB client."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.add.return_value = None
        mock_collection.query.return_value = {
            "ids": [["mem_1"]],
            "distances": [[0.5]],
            "metadatas": [[{"project": "test", "category": "testing"}]],
            "documents": [["Test content"]],
        }
        mock_collection.update.return_value = None
        mock_collection.count.return_value = 1
        return mock_client, mock_collection

    def test_embedding_service_initialization_success(self, mock_settings):
        """Test successful EmbeddingService initialization."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client_class.return_value = Mock()
            service = EmbeddingService()

            assert service.settings is not None
            assert service.model_name == mock_settings.embedding_model

    def test_embedding_service_initialization_with_custom_settings(self, mock_settings):
        """Test initialization with custom settings."""
        mock_settings.embedding_model = "custom-model"

        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client_class.return_value = Mock()
            service = EmbeddingService(mock_settings)

            assert service.model_name == "custom-model"

    def test_chroma_connection_success(self, mock_settings):
        """Test successful ChromaDB connection."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            service = EmbeddingService(mock_settings)
            client = service._get_chroma_client()

            assert client is not None
            mock_client_class.assert_called_once_with(host="localhost", port=8000)

    def test_chroma_connection_failure(self, mock_settings):
        """Test ChromaDB connection failure handling."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client_class.side_effect = ChromaError("Connection failed")

            service = EmbeddingService(mock_settings)

            with pytest.raises(ConnectionError, match="Failed to connect to ChromaDB"):
                service._get_chroma_client()

    @patch("sentence_transformers.SentenceTransformer")
    def test_embedding_generation_success(self, mock_transformer, mock_settings):
        """Test successful embedding generation."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_transformer.return_value = mock_model

        with patch("chromadb.HttpClient"):
            service = EmbeddingService(mock_settings)

            # Test embedding generation
            text = "Test content for embedding"
            embedding = service._generate_embedding(text)

            assert embedding == [0.1, 0.2, 0.3]
            mock_model.encode.assert_called_once_with([text])

    @patch("sentence_transformers.SentenceTransformer")
    def test_embedding_generation_failure(self, mock_transformer, mock_settings):
        """Test embedding generation failure handling."""
        # Setup mocks
        mock_transformer.side_effect = Exception("Model loading failed")

        with patch("chromadb.HttpClient"):
            service = EmbeddingService(mock_settings)

            with pytest.raises(RuntimeError, match="Failed to generate embedding"):
                service._generate_embedding("test content")

    def test_text_preparation_for_embedding(self, mock_settings):
        """Test text preparation for embedding generation."""
        with patch("chromadb.HttpClient"):
            service = EmbeddingService(mock_settings)

            # Test various text inputs
            test_cases = [
                ("Simple text", "Simple text"),
                ("Text\nwith\nnewlines", "Text with newlines"),
                ("Text\t\twith\ttabs", "Text with tabs"),
                ("  Text with spaces  ", "Text with spaces"),
                ("Text with # markdown", "Text with markdown"),
                ("", ""),
            ]

            for input_text, expected in test_cases:
                prepared = service._prepare_text_for_embedding(input_text)
                assert prepared == expected

    def test_index_memory_success(
        self, mock_settings, sample_memory, mock_chroma_client
    ):
        """Test successful memory indexing."""
        mock_client, mock_collection = mock_chroma_client

        with patch("chromadb.HttpClient", return_value=mock_client):
            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                # Test indexing
                service.index_memory("mem_1", sample_memory, "/path/to/file")

                # Verify collection was called correctly
                mock_collection.add.assert_called_once()
                call_args = mock_collection.add.call_args

                assert call_args[1]["ids"] == ["mem_1"]
                assert call_args[1]["embeddings"] == [[0.1, 0.2, 0.3]]
                assert call_args[1]["metadatas"][0]["project"] == "test-project"
                assert call_args[1]["metadatas"][0]["category"] == "testing"
                assert call_args[1]["documents"] == [
                    "# Test Memory\n\nThis is a test memory for unit testing."
                ]

    def test_index_memory_chroma_failure(self, mock_settings, sample_memory):
        """Test memory indexing with ChromaDB failure."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.add.side_effect = Exception("ChromaDB error")
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                with pytest.raises(RuntimeError, match="Failed to index memory"):
                    service.index_memory("mem_1", sample_memory, "/path/to/file")

    def test_search_memories_success(self, mock_settings, mock_chroma_client):
        """Test successful memory search."""
        mock_client, mock_collection = mock_chroma_client

        with patch("chromadb.HttpClient", return_value=mock_client):
            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                # Test search
                results = service.search_memories("test query", top_k=3)

                # Verify results
                assert len(results) == 1
                assert results[0].memory_id == "mem_1"
                assert results[0].score == 0.5
                assert results[0].entry.project == "test"
                assert results[0].entry.category == "testing"
                assert results[0].entry.content == "Test content"

    def test_search_memories_with_filters(self, mock_settings, mock_chroma_client):
        """Test memory search with project and tag filters."""
        mock_client, mock_collection = mock_chroma_client

        with patch("chromadb.HttpClient", return_value=mock_client):
            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                # Test search with filters
                _results = service.search_memories(
                    "test query", project="test-project", tags=["test", "unit"], top_k=5
                )

                # Verify query was called with proper filters
                mock_collection.query.assert_called_once()
                call_args = mock_collection.query.call_args

                assert call_args[1]["query_embeddings"] == [[0.1, 0.2, 0.3]]
                assert call_args[1]["n_results"] == 5
                # Verify where clause contains filters
                where_clause = call_args[1]["where"]
                assert "$and" in where_clause

    def test_search_memories_empty_results(self, mock_settings):
        """Test memory search with no results."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.return_value = {
                "ids": [[]],
                "distances": [[]],
                "metadatas": [[]],
                "documents": [[]],
            }
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                results = service.search_memories("nonexistent query")
                assert len(results) == 0

    def test_search_memories_chroma_failure(self, mock_settings):
        """Test memory search with ChromaDB failure."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.query.side_effect = Exception("ChromaDB search error")
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                with pytest.raises(RuntimeError, match="Failed to search memories"):
                    service.search_memories("test query")

    def test_update_memory_success(
        self, mock_settings, sample_memory, mock_chroma_client
    ):
        """Test successful memory update."""
        mock_client, mock_collection = mock_chroma_client

        with patch("chromadb.HttpClient", return_value=mock_client):
            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                # Test update
                service.update_memory("mem_1", sample_memory, "/path/to/file")

                # Verify update was called correctly
                mock_collection.update.assert_called_once()
                call_args = mock_collection.update.call_args

                assert call_args[1]["ids"] == ["mem_1"]
                assert call_args[1]["embeddings"] == [[0.1, 0.2, 0.3]]
                assert call_args[1]["metadatas"][0]["outdated"] is False

    def test_update_memory_chroma_failure(self, mock_settings, sample_memory):
        """Test memory update with ChromaDB failure."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.update.side_effect = Exception("ChromaDB update error")
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                with pytest.raises(RuntimeError, match="Failed to update memory"):
                    service.update_memory("mem_1", sample_memory, "/path/to/file")

    def test_get_collection_stats_success(self, mock_settings, mock_chroma_client):
        """Test successful collection statistics retrieval."""
        mock_client, mock_collection = mock_chroma_client
        mock_collection.count.return_value = 42

        with patch("chromadb.HttpClient", return_value=mock_client):
            service = EmbeddingService(mock_settings)

            stats = service.get_collection_stats()

            assert stats["total_memories"] == 42
            assert stats["collection_name"] == "test_retainr"

    def test_get_collection_stats_failure(self, mock_settings):
        """Test collection statistics with ChromaDB failure."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.count.side_effect = Exception("ChromaDB stats error")
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            service = EmbeddingService(mock_settings)

            with pytest.raises(RuntimeError, match="Failed to get collection stats"):
                service.get_collection_stats()

    def test_collection_creation_and_reuse(self, mock_settings):
        """Test that collection is created once and reused."""
        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            service = EmbeddingService(mock_settings)

            # Call _get_collection multiple times
            collection1 = service._get_collection()
            collection2 = service._get_collection()

            # Verify collection creation was called only once
            assert mock_client.get_or_create_collection.call_count == 1
            assert collection1 is collection2

    def test_distance_to_similarity_score_conversion(self, mock_settings):
        """Test distance to similarity score conversion."""
        with patch("chromadb.HttpClient"):
            service = EmbeddingService(mock_settings)

            # Test various distances
            test_cases = [
                (0.0, 1.0),  # Perfect match
                (0.5, 0.75),  # Good match
                (1.0, 0.5),  # Average match
                (2.0, 0.0),  # Poor match
            ]

            for distance, expected_score in test_cases:
                score = service._distance_to_similarity(distance)
                assert abs(score - expected_score) < 0.01

    def test_concurrent_operations_thread_safety(self, mock_settings, sample_memory):
        """Test thread safety during concurrent operations."""
        import threading

        with patch("chromadb.HttpClient") as mock_client_class:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_client_class.return_value = mock_client

            with patch.object(
                EmbeddingService, "_generate_embedding", return_value=[0.1, 0.2, 0.3]
            ):
                service = EmbeddingService(mock_settings)

                errors = []

                def index_operation():
                    try:
                        service.index_memory(
                            f"mem_{threading.current_thread().ident}",
                            sample_memory,
                            "/path",
                        )
                    except Exception as e:
                        errors.append(e)

                # Run multiple threads
                threads = []
                for _i in range(5):
                    thread = threading.Thread(target=index_operation)
                    threads.append(thread)
                    thread.start()

                # Wait for all threads to complete
                for thread in threads:
                    thread.join()

                # Verify no errors occurred
                assert len(errors) == 0
                assert mock_collection.add.call_count == 5
