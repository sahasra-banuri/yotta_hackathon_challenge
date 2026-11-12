import csv
import io
import json
import html
import time
import requests
import streamlit as st


# ==========================================================
# CONFIGURATION
# ==========================================================

API_URL = "http://127.0.0.1:8000/api/v1"

TABLES = [
    "products",
    "orders",
    "order_items",
    "rejected_records",
    "pipeline_runs",
]

TERMINAL_STATUSES = {
    "SUCCESS",
    "FAILED",
    "SKIPPED",
    "ABANDONED",
}


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="E-Commerce Data Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# STYLING
# ==========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f7f8fc;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
    }

    [data-testid="stSidebar"] * {
        color: #f9fafb;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        padding: 18px 20px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
    }

    [data-testid="stMetricLabel"] {
        color: #64748b;
    }

    [data-testid="stMetricValue"] {
        color: #111827;
    }

    h1, h2, h3 {
        color: #111827;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# API HELPERS
# ==========================================================

def get_api(endpoint, params=None, timeout=20):
    """Send a GET request to FastAPI."""

    try:
        response = requests.get(
            f"{API_URL}/{endpoint}",
            params=params,
            timeout=timeout,
        )

        response.raise_for_status()
        return response.json()

    except requests.HTTPError as error:
        detail = (
            error.response.text
            if error.response is not None
            else str(error)
        )

        st.error(f"API request failed: {detail}")
        return None

    except requests.RequestException as error:
        st.error(f"Cannot connect to backend: {error}")
        return None


def post_api(endpoint):
    """Send a POST request to FastAPI."""

    try:
        response = requests.post(
            f"{API_URL}/{endpoint}",
            timeout=20,
        )

        response.raise_for_status()
        return response.json()

    except requests.HTTPError as error:

        if (
            error.response is not None
            and error.response.status_code == 409
        ):
            st.warning(
                "A pipeline execution is already in progress."
            )

        else:
            detail = (
                error.response.text
                if error.response is not None
                else str(error)
            )

            st.error(f"API request failed: {detail}")

        return None

    except requests.RequestException as error:
        st.error(f"Cannot connect to backend: {error}")
        return None


def extract_records(data, key):
    """Extract records from API responses."""

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        records = data.get(key, [])

        if isinstance(records, list):
            return records

    return []


def format_number(value):
    """Format numeric values."""

    try:
        return f"{int(value):,}"

    except (TypeError, ValueError):
        return str(value)


# ==========================================================
# CSV DOWNLOAD
# ==========================================================

def create_csv_download(records):
    """Create CSV data using Python's built-in csv module."""

    if not records:
        return b""

    output = io.StringIO()

    fieldnames = []

    for record in records:
        if isinstance(record, dict):
            for key in record:
                if key not in fieldnames:
                    fieldnames.append(key)

    if not fieldnames:
        return b""

    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )

    writer.writeheader()

    for record in records:

        if not isinstance(record, dict):
            continue

        cleaned_record = {}

        for key, value in record.items():

            if isinstance(value, (dict, list)):
                value = json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                )

            cleaned_record[key] = value

        writer.writerow(cleaned_record)

    return output.getvalue().encode("utf-8-sig")


# ==========================================================
# HTML TABLE RENDERER
# ==========================================================

def render_records(
    records,
    table_name="records",
    allow_download=True,
):
    """
    Render records as HTML.

    This deliberately avoids st.dataframe(), which can trigger
    PyArrow imports on this Windows environment.
    """

    if not records:
        st.info("No records to display.")
        return

    if isinstance(records, dict):
        records = [records]

    if not isinstance(records, list):
        st.write(records)
        return

    if not all(isinstance(record, dict) for record in records):
        st.json(records)
        return

    columns = []

    for record in records:

        for column in record:

            if column not in columns:
                columns.append(column)

    header_html = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in columns
    )

    rows_html = []

    for record in records:

        cells = []

        for column in columns:

            value = record.get(column, "")

            if value is None:
                value = ""

            elif isinstance(value, (dict, list)):
                value = json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                )

            cells.append(
                f"<td>{html.escape(str(value))}</td>"
            )

        rows_html.append(
            "<tr>" + "".join(cells) + "</tr>"
        )

    table_html = f"""
    <!DOCTYPE html>
    <html>
    <head>

        <meta charset="UTF-8">

        <style>

            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                background: white;
            }}

            .table-container {{
                width: 100%;
                overflow-x: auto;
                border: 1px solid #e5e7eb;
                border-radius: 9px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                font-size: 13px;
                color: #1f2937;
            }}

            th {{
                background: #eef2f7;
                color: #334155;
                text-align: left;
                padding: 13px;
                border: 1px solid #dbe1e8;
                white-space: nowrap;
                position: sticky;
                top: 0;
            }}

            td {{
                padding: 12px;
                border-bottom: 1px solid #edf0f4;
                border-right: 1px solid #edf0f4;
                overflow-wrap: anywhere;
                min-width: 100px;
                max-width: 350px;
                vertical-align: top;
            }}

            tr:hover {{
                background: #f8fafc;
            }}

        </style>

    </head>

    <body>

        <div class="table-container">

            <table>

                <thead>
                    <tr>{header_html}</tr>
                </thead>

                <tbody>
                    {''.join(rows_html)}
                </tbody>

            </table>

        </div>

    </body>
    </html>
    """

    component_height = min(
        650,
        max(150, 55 + len(records) * 45),
    )

    st.components.v1.html(
        table_html,
        height=component_height,
        scrolling=True,
    )

    st.caption(
        f"{len(records):,} record(s) displayed"
    )

    if allow_download:

        st.download_button(
            label="⬇ Download current page as CSV",
            data=create_csv_download(records),
            file_name=f"{table_name}.csv",
            mime="text/csv",
            key=f"download_{table_name}",
        )


# ==========================================================
# STATUS HELPERS
# ==========================================================

def display_status(status):

    status = str(status or "UNKNOWN").upper()

    if status == "SUCCESS":
        st.success("SUCCESS")

    elif status == "FAILED":
        st.error("FAILED")

    elif status in {"RUNNING", "ABANDONED"}:
        st.warning(status)

    elif status in {"QUEUED", "SKIPPED"}:
        st.info(status)

    else:
        st.write(status)


def show_run_details(run):

    fields = [
        "run_id",
        "file_name",
        "file_type",
        "status",
        "total_records",
        "valid_records",
        "rejected_records",
        "processing_time",
        "peak_memory_mb",
        "started_at",
        "completed_at",
    ]

    for field in fields:

        if field in run:

            value = run[field]

            label = field.replace(
                "_", " "
            ).title()

            st.write(
                f"**{label}:** "
                f"{value if value is not None else 'N/A'}"
            )


# ==========================================================
# PERFORMANCE CHART WITHOUT PANDAS
# ==========================================================

def render_horizontal_bars(values, title, unit):
    """Render performance comparison bars using HTML components."""

    st.subheader(title)

    if not values:
        st.info("No measurements available.")
        return

    numeric_values = {}

    for label, value in values.items():
        try:
            numeric_values[str(label)] = float(value)
        except (TypeError, ValueError):
            continue

    if not numeric_values:
        st.info("No valid performance measurements available.")
        return

    maximum = max(numeric_values.values())

    if maximum <= 0:
        maximum = 1

    bars_html = ""

    for label, value in numeric_values.items():

        percentage = max(
            0,
            min(100, (value / maximum) * 100)
        )

        safe_label = html.escape(label)
        safe_unit = html.escape(unit)

        bars_html += f"""
        <div class="bar-item">

            <div class="bar-heading">
                <span>{safe_label}</span>
                <strong>{value:.2f} {safe_unit}</strong>
            </div>

            <div class="bar-background">
                <div class="bar-fill"
                     style="width: {percentage:.2f}%;">
                </div>
            </div>

        </div>
        """

    complete_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>

            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 12px;
                background: #f7f8fc;
            }}

            .bar-item {{
                margin-bottom: 25px;
            }}

            .bar-heading {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 9px;
                font-size: 14px;
                color: #334155;
            }}

            .bar-heading strong {{
                color: #111827;
            }}

            .bar-background {{
                width: 100%;
                height: 18px;
                background: #e5e7eb;
                border-radius: 10px;
                overflow: hidden;
            }}

            .bar-fill {{
                height: 100%;
                background: #4776c5;
                border-radius: 10px;
                transition: width 0.3s ease;
            }}

        </style>
    </head>

    <body>
        {bars_html}
    </body>
    </html>
    """

    st.components.v1.html(
        complete_html,
        height=max(100, len(numeric_values) * 65 + 20),
        scrolling=False,
    )

# ==========================================================
# SIDEBAR NAVIGATION
# ==========================================================

with st.sidebar:

    st.markdown("# ⚡ DATA PLATFORM")

    st.caption("E-COMMERCE PIPELINE MONITOR")

    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "Pipeline Execution",
            "Data Explorer",
            "Database",
            "Execution History",
            "Data Quality",
            "Performance",
        ],
    )

    st.divider()

    st.markdown("### TECHNOLOGY STACK")

    st.caption("Python")
    st.caption("FastAPI")
    st.caption("SQLAlchemy")
    st.caption("SQLite")
    st.caption("Streamlit")

    st.divider()

    st.caption("Scalable E-Commerce Data Pipeline")
    st.caption("Version 1.0")


# ==========================================================
# APPLICATION HEADER
# ==========================================================

st.title("⚡ E-Commerce Data Platform")

st.caption(
    "Data ingestion  ·  Validation  ·  Transformation  ·  "
    "Publishing  ·  Monitoring"
)

st.divider()


# ==========================================================
# 1. OVERVIEW
# ==========================================================

if page == "Overview":

    st.header("Platform Overview")

    st.caption(
        "Monitor pipeline activity, business data and infrastructure."
    )

    stats = get_api("stats")

    health = get_api("health")

    database = get_api("database/overview")

    history = get_api(
        "pipeline/runs",
        params={"limit": 10, "offset": 0},
    )

    if stats:

        st.subheader("Business Metrics")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Products",
            format_number(stats.get("products", 0)),
        )

        col2.metric(
            "Total Orders",
            format_number(stats.get("orders", 0)),
        )

        col3.metric(
            "Order Items",
            format_number(stats.get("order_items", 0)),
        )

        col4, col5, col6 = st.columns(3)

        col4.metric(
            "Active Products",
            format_number(stats.get("active_products", 0)),
        )

        col5.metric(
            "Rejected Records",
            format_number(stats.get("rejected_records", 0)),
        )

        col6.metric(
            "Pipeline Executions",
            format_number(stats.get("pipeline_runs", 0)),
        )

    st.divider()

    st.subheader("Infrastructure Status")

    col1, col2, col3 = st.columns(3)

    with col1:

        if health:

            st.success("● Backend Connected")

            st.caption("FastAPI service is responding.")

        else:

            st.error("● Backend Unavailable")

    with col2:

        if health and health.get("database") == "connected":

            st.success("● Database Connected")

            st.caption("SQLite connection is operational.")

        else:

            st.error("● Database Unavailable")

    with col3:

        if database:

            st.success("● Database Available")

            st.caption(
                f"{database.get('table_count', 0)} tables detected."
            )

        else:

            st.error("● Database Information Unavailable")

    if database:

        st.divider()

        st.subheader("Database Snapshot")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Database",
            database.get("database", "N/A"),
        )

        col2.metric(
            "Database Size",
            f"{database.get('database_size_mb', 0)} MB",
        )

        col3.metric(
            "Database Tables",
            database.get("table_count", 0),
        )

    st.divider()

    st.subheader("Recent Pipeline Executions")

    if history:

        runs = extract_records(history, "runs")

        if runs:

            for run in runs[:5]:

                with st.container(border=True):

                    col1, col2, col3 = st.columns([3, 1, 2])

                    col1.write(
                        f"**{run.get('file_name', 'Pipeline')}**"
                    )

                    col2.write(
                        run.get("status", "UNKNOWN")
                    )

                    col3.caption(
                        str(run.get("started_at", "N/A"))
                    )

                    with st.expander("Execution details"):

                        show_run_details(run)

        else:

            st.info("No execution history is available.")

    if st.button("↻ Refresh overview"):
        st.rerun()


# ==========================================================
# 2. PIPELINE EXECUTION
# ==========================================================

elif page == "Pipeline Execution":

    st.header("Pipeline Execution")

    st.caption(
        "Trigger and monitor the end-to-end data processing workflow."
    )

    health = get_api("health")

    if not health:

        st.error(
            "The backend is unavailable. "
            "Start FastAPI before running the pipeline."
        )

        st.stop()

    st.success("Backend is ready.")

    st.info(
        "This runs the pipeline against the configured source files "
        "and publishes results to the SQLite database."
    )

    confirmed = st.checkbox(
        "I understand that this action executes the pipeline."
    )

    if st.button(
        "▶ Execute Pipeline",
        type="primary",
        disabled=not confirmed,
    ):

        response = post_api("pipeline/run")

        if response:

            task_id = response.get("task_id")

            if not task_id:

                st.error(
                    "The backend did not return a task ID."
                )

            else:

                st.write("**Task ID**")

                st.code(task_id)

                status_placeholder = st.empty()

                progress_bar = st.progress(0)

                for attempt in range(180):

                    task = get_api(
                        f"pipeline/tasks/{task_id}",
                        timeout=20,
                    )

                    if task is None:

                        status_placeholder.warning(
                            "Unable to retrieve task status. Retrying..."
                        )

                        time.sleep(2)

                        continue

                    status = str(
                        task.get("status", "UNKNOWN")
                    ).upper()

                    status_placeholder.info(
                        f"Execution status: {status}"
                    )

                    if status in TERMINAL_STATUSES:

                        progress_bar.progress(100)

                        display_status(status)

                        st.subheader("Execution Result")

                        st.write(
                            task.get(
                                "message",
                                "Execution finished.",
                            )
                        )

                        if task.get("error"):

                            st.error(task["error"])

                        run_id = task.get("run_id")

                        if run_id:

                            if status == "SKIPPED":

                                st.write(
                                    "**Previous successful Run ID**"
                                )

                            else:

                                st.write("**Run ID**")

                            st.code(run_id)

                            run = get_api(
                                f"pipeline/runs/{run_id}"
                            )

                            if run:

                                st.subheader("Execution Details")

                                show_run_details(run)

                        break

                    progress_bar.progress(
                        min(
                            int((attempt + 1) / 180 * 95),
                            95,
                        )
                    )

                    time.sleep(2)

                else:

                    st.warning(
                        "The task has not reached a final status "
                        "within the monitoring window. "
                        "Check Execution History later."
                    )

    st.divider()

    st.subheader("Retrieve an Existing Execution")

    run_id_input = st.text_input(
        "Pipeline Run ID",
        placeholder="Paste an existing Run ID",
    )

    if st.button("Retrieve execution"):

        if run_id_input.strip():

            run = get_api(
                f"pipeline/runs/{run_id_input.strip()}"
            )

            if run:

                display_status(run.get("status"))

                show_run_details(run)

        else:

            st.warning("Enter a Run ID first.")


# ==========================================================
# 3. DATA EXPLORER
# ==========================================================

elif page == "Data Explorer":

    st.header("Data Explorer")

    st.caption(
        "Browse and inspect individual records stored in the database."
    )

    selected_table = st.selectbox(
        "Select database table",
        TABLES,
    )

    if (
        st.session_state.get("selected_explorer_table")
        != selected_table
    ):

        st.session_state["selected_explorer_table"] = selected_table

        st.session_state["explorer_offset"] = 0

    page_size = st.selectbox(
        "Records per page",
        [10, 25, 50, 100, 200],
        index=2,
    )

    offset = st.session_state.get(
        "explorer_offset",
        0,
    )

    data = get_api(
        f"database/tables/{selected_table}",
        params={
            "limit": page_size,
            "offset": offset,
        },
    )

    if data:

        records = extract_records(
            data,
            "records",
        )

        total = int(
            data.get("total_records", 0)
        )

        # Prevent an invalid offset if the selected table
        # has fewer records than the previous selection.
        if offset >= total and total > 0:

            st.session_state["explorer_offset"] = 0

            st.rerun()

        st.divider()

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Selected Table",
            selected_table,
        )

        col2.metric(
            "Total Records",
            format_number(total),
        )

        col3.metric(
            "Records Displayed",
            len(records),
        )

        st.subheader("Table Records")

        render_records(
            records,
            selected_table,
        )

        first_record = offset + 1 if records else 0

        last_record = offset + len(records)

        st.caption(
            f"Displaying records {first_record:,}–"
            f"{last_record:,} of {total:,}."
        )

        previous_col, next_col = st.columns(2)

        with previous_col:

            if st.button(
                "← Previous page",
                disabled=offset <= 0,
            ):

                st.session_state["explorer_offset"] = max(
                    0,
                    offset - page_size,
                )

                st.rerun()

        with next_col:

            if st.button(
                "Next page →",
                disabled=(offset + page_size >= total),
            ):

                st.session_state["explorer_offset"] = (
                    offset + page_size
                )

                st.rerun()

    else:

        st.error(
            "Unable to retrieve records from the selected table."
        )


# ==========================================================
# 4. DATABASE
# ==========================================================

elif page == "Database":

    st.header("Database")

    st.caption(
        "Inspect database structure, storage and table schemas."
    )

    database = get_api("database/overview")

    if database:

        st.subheader("Database Information")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Database Name",
            database.get("database", "N/A"),
        )

        col2.metric(
            "Storage Size",
            f"{database.get('database_size_mb', 0)} MB",
        )

        col3.metric(
            "Total Tables",
            database.get("table_count", 0),
        )

        st.divider()

        st.subheader("Database Tables")

        for table in database.get("tables", []):

            table_name = table.get(
                "table_name",
                "Unknown",
            )

            with st.container(border=True):

                col1, col2, col3 = st.columns([3, 1, 1])

                col1.markdown(
                    f"### `{table_name}`"
                )

                col2.metric(
                    "Records",
                    format_number(
                        table.get("record_count", 0)
                    ),
                )

                col3.metric(
                    "Columns",
                    table.get("columns", 0),
                )

                with st.expander("View table schema"):

                    schema = table.get("schema", [])

                    if schema:

                        render_records(
                            schema,
                            f"{table_name}_schema",
                            allow_download=False,
                        )

                    else:

                        st.info(
                            "No schema information returned."
                        )

        st.divider()

        st.info(
            "This interface provides read-only database inspection. "
            "Database records are accessed through FastAPI."
        )

        st.caption(
            "Database Engine: SQLite  |  ORM: SQLAlchemy"
        )

    else:

        st.error(
            "Unable to retrieve database information."
        )

    if st.button("↻ Refresh database information"):
        st.rerun()


# ==========================================================
# 5. EXECUTION HISTORY
# ==========================================================

elif page == "Execution History":

    st.header("Execution History")

    st.caption(
        "Review and filter stored pipeline executions."
    )

    data = get_api(
        "pipeline/runs",
        params={
            "limit": 100,
            "offset": 0,
        },
    )

    if data:

        runs = extract_records(
            data,
            "runs",
        )

        counts = {
            "SUCCESS": 0,
            "FAILED": 0,
            "ABANDONED": 0,
            "RUNNING": 0,
        }

        for run in runs:

            status = str(
                run.get("status", "UNKNOWN")
            ).upper()

            counts[status] = counts.get(status, 0) + 1

        st.metric(
            "Total Stored Executions",
            format_number(
                data.get("total_runs", len(runs))
            ),
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Successful",
            counts["SUCCESS"],
        )

        col2.metric(
            "Failed",
            counts["FAILED"],
        )

        col3.metric(
            "Abandoned",
            counts["ABANDONED"],
        )

        col4.metric(
            "Running",
            counts["RUNNING"],
        )

        st.divider()

        selected_status = st.selectbox(
            "Filter by status",
            [
                "ALL",
                "SUCCESS",
                "FAILED",
                "ABANDONED",
                "RUNNING",
            ],
        )

        filtered_runs = runs

        if selected_status != "ALL":

            filtered_runs = [
                run
                for run in runs
                if str(
                    run.get("status", "")
                ).upper() == selected_status
            ]

        st.write(
            f"Showing {len(filtered_runs)} execution(s)."
        )

        if not filtered_runs:

            st.info(
                "No stored executions match this filter."
            )

        for index, run in enumerate(filtered_runs):

            with st.container(border=True):

                st.markdown(
                    f"### Execution {index + 1}"
                )

                st.write(
                    f"**Source:** {run.get('file_name', 'N/A')}"
                )

                display_status(
                    run.get("status")
                )

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Total Records",
                    format_number(
                        run.get("total_records", 0)
                    ),
                )

                col2.metric(
                    "Valid Records",
                    format_number(
                        run.get("valid_records", 0)
                    ),
                )

                col3.metric(
                    "Rejected Records",
                    format_number(
                        run.get("rejected_records", 0)
                    ),
                )

                with st.expander("Full execution details"):

                    show_run_details(run)

    else:

        st.error(
            "Unable to retrieve execution history."
        )

    if st.button("↻ Refresh execution history"):
        st.rerun()


# ==========================================================
# 6. DATA QUALITY
# ==========================================================

elif page == "Data Quality":

    st.header("Data Quality")

    st.caption(
        "Inspect rejected records and validation failures."
    )

    data = get_api(
        "rejections",
        params={
            "limit": 500,
            "offset": 0,
        },
    )

    if data:

        records = extract_records(
            data,
            "records",
        )

        total = data.get(
            "total_rejections",
            len(records),
        )

        st.metric(
            "Total Rejected Records",
            format_number(total),
        )

        st.divider()

        if records:

            reasons = {}

            for record in records:

                reason = record.get(
                    "rejection_reason",
                    "Unknown",
                )

                reasons[reason] = (
                    reasons.get(reason, 0) + 1
                )

            st.subheader("Rejection Breakdown")

            breakdown_records = [
                {
                    "Rejection Reason": reason,
                    "Count": count,
                }
                for reason, count in reasons.items()
            ]

            render_records(
                breakdown_records,
                "rejection_breakdown",
                allow_download=False,
            )

            st.divider()

            st.subheader("Rejected Records")

            for index, record in enumerate(records):

                record_id = record.get(
                    "record_id",
                    "Unknown ID",
                )

                with st.expander(
                    f"Rejected Record {index + 1} | {record_id}"
                ):

                    st.write(
                        "**Rejection Reason:**",
                        record.get(
                            "rejection_reason",
                            "N/A",
                        ),
                    )

                    st.write(
                        "**Source File:**",
                        record.get(
                            "source_file",
                            "N/A",
                        ),
                    )

                    st.write(
                        "**Record ID:**",
                        record_id,
                    )

                    st.write(
                        "**Run ID:**",
                        record.get(
                            "run_id",
                            "N/A",
                        ),
                    )

                    st.write("**Raw Record:**")

                    st.json(
                        record.get("raw_record")
                    )

        else:

            st.success(
                "No rejected records found."
            )

    else:

        st.error(
            "Unable to retrieve rejected records."
        )

    if st.button("↻ Refresh data quality"):
        st.rerun()


# ==========================================================
# 7. PERFORMANCE
# ==========================================================

# ==========================================================
# 7. PERFORMANCE
# ==========================================================

elif page == "Performance":

    st.header("Performance Monitoring")

    st.caption(
        "Compare pipeline performance across small, medium "
        "and large datasets."
    )

    data = get_api(
        "pipeline/runs",
        params={
            "limit": 100,
            "offset": 0,
        },
    )

    if data:

        runs = extract_records(data, "runs")

        successful_runs = [
            run for run in runs
            if str(run.get("status", "")).upper() == "SUCCESS"
        ]

        # Identify benchmark executions by workload size.
        benchmark_targets = {
            "Small": 14,
            "Medium": 20000,
            "Large": 110000,
        }

        benchmark_ranges = {
            "Small": (1, 100),
            "Medium": (15000, 30000),
            "Large": (100000, 150000),
        }

        selected_runs = {}

        for label, target in benchmark_targets.items():

            minimum, maximum = benchmark_ranges[label]

            candidates = [
                run for run in successful_runs
                if minimum <= int(run.get("total_records") or 0) <= maximum
                and run.get("processing_time") is not None
                and run.get("peak_memory_mb") is not None
            ]

            if candidates:

                selected_runs[label] = min(
                    candidates,
                    key=lambda run: abs(
                        int(run.get("total_records", 0)) - target
                    ),
                )

        if selected_runs:

            # --------------------------------------------------
            # BENCHMARK SUMMARY
            # --------------------------------------------------

            st.subheader("Benchmark Overview")

            small_col, medium_col, large_col = st.columns(3)

            for column, label in [
                (small_col, "Small"),
                (medium_col, "Medium"),
                (large_col, "Large"),
            ]:

                with column:

                    if label in selected_runs:

                        run = selected_runs[label]

                        st.metric(
                            f"{label} Dataset",
                            f"{int(run['total_records']):,} records",
                        )

                        st.success("SUCCESS")

                    else:

                        st.metric(
                            f"{label} Dataset",
                            "Not available",
                        )

                        st.warning("Benchmark missing")

            st.divider()

            # --------------------------------------------------
            # PERFORMANCE METRICS
            # --------------------------------------------------

            st.subheader("Performance Comparison")

            performance_records = []

            processing_values = {}
            memory_values = {}
            throughput_values = {}

            for label in ["Small", "Medium", "Large"]:

                if label not in selected_runs:
                    continue

                run = selected_runs[label]

                total_records = int(
                    run.get("total_records", 0)
                )

                processing_time = float(
                    run["processing_time"]
                )

                peak_memory = float(
                    run["peak_memory_mb"]
                )

                throughput = (
                    total_records / processing_time
                    if processing_time > 0
                    else 0
                )

                performance_records.append({
                    "Dataset": label,
                    "Records Processed": total_records,
                    "Valid Records": run.get("valid_records", 0),
                    "Rejected Records": run.get("rejected_records", 0),
                    "Processing Time (sec)": round(
                        processing_time, 4
                    ),
                    "Peak Memory (MB)": round(
                        peak_memory, 2
                    ),
                    "Throughput (records/sec)": round(
                        throughput, 2
                    ),
                    "Status": run.get("status"),
                })

                processing_values[label] = processing_time

                memory_values[label] = peak_memory

                throughput_values[label] = throughput

            render_records(
                performance_records,
                "benchmark_comparison",
                allow_download=True,
            )

            st.divider()

            # --------------------------------------------------
            # PROCESSING TIME
            # --------------------------------------------------

            render_horizontal_bars(
                processing_values,
                "Processing Time Comparison",
                "sec",
            )

            st.divider()

            # --------------------------------------------------
            # MEMORY CONSUMPTION
            # --------------------------------------------------

            render_horizontal_bars(
                memory_values,
                "Memory Consumption Comparison",
                "MB",
            )

            st.divider()

            # --------------------------------------------------
            # THROUGHPUT
            # --------------------------------------------------

            render_horizontal_bars(
                throughput_values,
                "Processing Throughput Comparison",
                "records/sec",
            )

            st.divider()

            # --------------------------------------------------
            # INTERPRETATION
            # --------------------------------------------------

            st.subheader("Benchmark Interpretation")

            if len(selected_runs) == 3:

                st.success(
                    "All three benchmark workload sizes "
                    "have successful executions."
                )

                st.markdown(
                    """
                    **What these measurements demonstrate:**

                    - Processing time across different workload sizes.
                    - Peak memory consumption during execution.
                    - Records processed per second.
                    - Successful processing of different dataset sizes.

                    These measurements provide an initial performance
                    comparison. They are not a controlled scalability
                    experiment because the workloads and execution
                    conditions may differ.
                    """
                )

            else:

                missing = [
                    label
                    for label in benchmark_targets
                    if label not in selected_runs
                ]

                st.warning(
                    "Missing benchmark categories: "
                    + ", ".join(missing)
                )

            # --------------------------------------------------
            # EXECUTION IDENTIFIERS
            # --------------------------------------------------

            with st.expander("View benchmark execution IDs"):

                for label, run in selected_runs.items():

                    st.write(f"**{label} Dataset**")

                    st.code(run.get("run_id", "N/A"))

        else:

            st.info(
                "No matching successful benchmark executions "
                "were found."
            )

    else:

        st.error(
            "Unable to retrieve performance information."
        )

    if st.button("↻ Refresh performance"):

        st.rerun()
        
# ==========================================================
# FOOTER
# ==========================================================

st.divider()

st.caption(
    "SCALABLE E-COMMERCE DATA PIPELINE  |  "
    "Python · FastAPI · SQLAlchemy · SQLite · Streamlit"
)