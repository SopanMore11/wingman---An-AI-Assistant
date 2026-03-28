def load_md_file(file_path):
    """Utility function to load markdown content from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading markdown file: {e}")
        return ""