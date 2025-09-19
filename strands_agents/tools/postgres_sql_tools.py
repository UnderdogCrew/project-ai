import re
DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)
HAS_LIMIT_TAIL_RE = re.compile(r"(?is)\blimit\b\s+\d+(\s*,\s*\d+)?\s*;?\s*$")
from langchain_community.utilities import SQLDatabase
from strands_agents.tools.toolkit import Toolkit


def _safe_sql(q: str) -> str:
    # normalize
    q = q.strip()
    # block multiple statements (allow one optional trailing ;)
    if q.count(";") > 1 or (q.endswith(";") and ";" in q[:-1]):
        return "Error: multiple statements are not allowed."
    q = q.rstrip(";").strip()
    print(q)

    # read-only gate
    if not q.lower().startswith("select"):
        return "Error: only SELECT statements are allowed."
    if DENY_RE.search(q):
        return "Error: DML/DDL detected. Only read-only queries are permitted."
    print(q)
    # append LIMIT only if not already present at the end (robust to whitespace/newlines)
    if not HAS_LIMIT_TAIL_RE.search(q):
        q += " LIMIT 5"
    print(q)
    return q

class PostgresSqlTools(Toolkit):
    def __init__(
        self,
        db_url: str,
    ):
        super().__init__(name="postgres_sql")

        self.db_url = db_url

        self.register(self.execute_sql)

    def execute_sql(self, query: str) -> str:
        """Execute a READ-ONLY SQLite SELECT query and return results."""
        query = _safe_sql(query)
        print(query)
        q = query
        if q.startswith("Error:"):
            return q
        try:
            return SQLDatabase.from_uri(self.db_url).run(query)
        except Exception as e:
            print(e)
            return f"Error: {e}"