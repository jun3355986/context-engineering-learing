#!/usr/bin/env python3
"""U05 实验用的假 MCP 服务器：只通过 stdio 声明工具，调用时回一句固定的话。不联网。

用法（由 u05_mcp.py 自动拉起）：
  python3 u05_fake_mcp.py tracker      # 10 个「问题单」工具
  python3 u05_fake_mcp.py database     # 10 个「数据库」工具
  python3 u05_fake_mcp.py monitor      # 10 个「监控告警」工具
  python3 u05_fake_mcp.py bulk 40      # 40 个名字相近、描述一样长的凑数工具（同 U01）

三个真实风格的服务器故意留了几对「名字像、用途不同」的工具
（tracker 的 list_issues / monitor 的 list_incidents 等），用来看检索会不会混。
"""
import json
import sys

# (工具名, 描述, 参数名列表)
CATALOG = {
    "tracker": [
        ("create_issue", "Create a new issue in the project tracker with a title, a body and optional labels.", ["title", "body", "labels"]),
        ("update_issue", "Update the title, body or state of an existing issue in the project tracker.", ["issue_id", "title", "body"]),
        ("close_issue", "Close an issue in the project tracker and optionally leave a closing comment.", ["issue_id", "comment"]),
        ("list_issues", "List issues in the project tracker, filtered by state, assignee or label.", ["state", "assignee", "label"]),
        ("search_issues", "Full-text search over issue titles and bodies in the project tracker.", ["query", "limit"]),
        ("get_issue", "Fetch one issue from the project tracker, including its comments and labels.", ["issue_id"]),
        ("add_comment", "Add a comment to an issue in the project tracker.", ["issue_id", "body"]),
        ("assign_issue", "Assign an issue in the project tracker to a team member.", ["issue_id", "assignee"]),
        ("add_label", "Attach a label to an issue in the project tracker.", ["issue_id", "label"]),
        ("list_labels", "List all labels defined in the project tracker.", ["limit"]),
    ],
    "database": [
        ("run_query", "Run a read-only SQL query against the production database and return the rows.", ["sql", "limit"]),
        ("explain_query", "Show the execution plan of a SQL query without running it.", ["sql"]),
        ("list_tables", "List all tables in the database with their approximate row counts.", ["schema"]),
        ("describe_table", "Describe the columns, types and constraints of one database table.", ["table"]),
        ("list_indexes", "List the indexes defined on one database table.", ["table"]),
        ("create_index", "Create an index on one or more columns of a database table.", ["table", "columns", "unique"]),
        ("drop_index", "Drop an index from a database table.", ["table", "index"]),
        ("get_row_count", "Count the rows of a database table, optionally with a WHERE condition.", ["table", "where"]),
        ("export_table", "Export a database table to a CSV file and return the file path.", ["table", "path"]),
        ("import_csv", "Import rows from a CSV file into a database table.", ["table", "path"]),
    ],
    "monitor": [
        ("list_alerts", "List the alerts that are currently firing in the monitoring system.", ["severity", "service"]),
        ("get_alert", "Fetch the details and history of one alert in the monitoring system.", ["alert_id"]),
        ("ack_alert", "Acknowledge a firing alert so that it stops paging the on-call engineer.", ["alert_id"]),
        ("silence_alert", "Silence an alert for a given number of minutes.", ["alert_id", "minutes"]),
        ("query_metrics", "Query a time series metric from the monitoring system over a time range.", ["metric", "from", "to"]),
        ("list_dashboards", "List the dashboards available in the monitoring system.", ["folder"]),
        ("get_dashboard", "Fetch the panels and queries of one monitoring dashboard.", ["dashboard_id"]),
        ("list_incidents", "List incidents opened in the monitoring system, filtered by status.", ["status", "service"]),
        ("create_incident", "Open a new incident in the monitoring system and page the responders.", ["title", "severity"]),
        ("resolve_incident", "Mark an incident in the monitoring system as resolved.", ["incident_id", "summary"]),
    ],
}


def bulk(n):
    return [
        (
            f"fake_tool_{i:02d}",
            f"Fake tool number {i} used only to measure how much room MCP tool "
            "definitions take in a Codex request. It does nothing. "
            "This sentence is padding so each description is about three hundred "
            "bytes long, which is a typical size for a real MCP tool description.",
            ["query", "limit", "verbose"],
        )
        for i in range(n)
    ]


def build_tools(kind, n):
    rows = bulk(n) if kind == "bulk" else CATALOG[kind]
    tools = []
    for name, desc, params in rows:
        props = {p: {"type": "string", "description": f"The {p.replace('_', ' ')}."} for p in params}
        tools.append(
            {
                "name": name,
                "description": desc,
                "inputSchema": {"type": "object", "properties": props, "required": params[:1]},
            }
        )
    return tools


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


def main():
    kind = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    tools = build_tools(kind, n)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method, msg_id = msg.get("method"), msg.get("id")
        if method == "initialize":
            reply(
                msg_id,
                {
                    "protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-03-26"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": kind, "version": "0.0.1"},
                },
            )
        elif method == "tools/list":
            reply(msg_id, {"tools": tools})
        elif method == "tools/call":
            name = msg.get("params", {}).get("name")
            reply(msg_id, {"content": [{"type": "text", "text": f"[{kind}.{name}] OK (fake)"}]})
        elif msg_id is not None:
            reply(msg_id, {})


if __name__ == "__main__":
    main()
