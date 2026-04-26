from importlib.metadata import version

__version__ = version("bedrock-bio")

from .describe_table import describe_table
from .list_tables import list_tables
from .load_table import load_table

__all__ = ["describe_table", "list_tables", "load_table"]
