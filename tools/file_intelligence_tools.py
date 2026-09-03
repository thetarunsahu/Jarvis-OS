from files.file_index import FileIndex


class FileIntelligenceTools:
    def __init__(self, index=None):
        self.index = index or FileIndex()

    def index_files(self):
        """Index configured local paths for later natural-language retrieval."""
        return self.index.scan()

    def search_files(self, query, limit=10):
        """Search indexed files by filename, path, and extracted text."""
        matches = self.index.search(query=query, limit=limit)
        return {
            "query": query,
            "count": len(matches),
            "matches": matches,
        }

    def file_index_status(self):
        return self.index.stats()
