"""Script to verify repository discovery and clone candidates."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import get_settings
from src.collection.github_client import GitHubClient

settings = get_settings()
client = GitHubClient(token=settings.github.token)

candidates = [
    ("commandlineparser", "commandline"),
    ("Humanizr", "Humanizer"),
    ("danielpalme", "ReportGenerator"),
    ("jbogard", "MediatR"),
]

for owner, name in candidates:
    try:
        r = client.get_repository(owner, name)
        print("Candidate:", r['full_name'], "Stars:", r['stars'], "Size:", r['size_kb'], "Branch:", r['default_branch'])
    except Exception as e:
        print("Error fetching:", owner, name, e)
