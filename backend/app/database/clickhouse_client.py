from __future__ import annotations

import logging
from typing import Any
import clickhouse_connect
from clickhouse_connect.driver.client import Client

logger = logging.getLogger(__name__)


class ClickHouseClient:
    def __init__(
        self,
        host: str = "clickhouse",
        port: int = 8123,
        username: str = "default",
        password: str | None = None,
        database: str = "default",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password or ""
        self.database = database
        self._client: Client | None = None

    def get_client(self) -> Client:
        if self._client is None:
            logger.info("Connecting to ClickHouse at %s:%s/%s...", self.host, self.port, self.database)
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database,
                connect_timeout=10,
                send_receive_timeout=30,
            )
        return self._client

    def ping(self) -> bool:
        try:
            client = self.get_client()
            result = client.command("SELECT 1")
            return result == 1
        except Exception as e:
            logger.warning("ClickHouse ping failed: %s", e)
            return False

    def query(self, sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Executes a read query and returns rows as dictionaries with column names.
        Sanitizes NaN / Inf floats to None to avoid JSON serialization errors in JS.
        """
        import math
        client = self.get_client()
        query_result = client.query(sql, parameters=parameters)
        columns = query_result.column_names
        rows = query_result.result_rows
        cleaned_rows = []
        for row in rows:
            clean_row = {}
            for col, val in zip(columns, row):
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    clean_row[col] = None
                else:
                    clean_row[col] = val
            cleaned_rows.append(clean_row)
        return cleaned_rows

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
