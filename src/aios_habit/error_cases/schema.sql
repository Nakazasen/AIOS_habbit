-- F1: error_cases schema — KDTPS error investigation cases (Step 0)
-- Business rules sourced from the legacy kdtps-error-manager
-- (src/core/database.py, src/utils/config.py).
-- Every import writes one batch (provenance); every case remembers
-- its exact source file / sha256 / sheet / row.

CREATE TABLE IF NOT EXISTS import_batches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file   TEXT NOT NULL,   -- source Excel file name
    file_sha256   TEXT NOT NULL,   -- sha256 of the file at import time (provenance)
    sheet_name    TEXT NOT NULL,   -- sheet that was read
    sheet_type    TEXT CHECK (sheet_type IN ('Máy in', 'KIT')),
    department    TEXT,            -- department (col O filter, if any)
    line_filter   TEXT,            -- line filter (col D) if any, JSON list
    header_row    INTEGER,         -- header row that was used
    imported_at   TEXT NOT NULL DEFAULT (datetime('now')),
    rows_read     INTEGER NOT NULL DEFAULT 0,
    rows_imported INTEGER NOT NULL DEFAULT 0,
    rows_skipped  INTEGER NOT NULL DEFAULT 0,  -- green cells / missing no_dvd / dupes
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS error_cases (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id         INTEGER REFERENCES import_batches (id),
    source_row       INTEGER,        -- row number in the source sheet (provenance)

    -- Business columns, A–Y mapping of the legacy app (config.py)
    no_dvd           TEXT NOT NULL,  -- A: issue number
    sheet_type       TEXT CHECK (sheet_type IN ('Máy in', 'KIT')),
    department       TEXT,           -- O: responsible department
    machine_type     TEXT,           -- C: machine type
    line             TEXT,           -- D: production line
    error_code_c     TEXT,           -- G: Cxxx error code
    error_code_h     TEXT,           -- H: Jxxx/Fxxx error code
    investigation    TEXT,           -- N: investigation content
    handler          TEXT,           -- S: person in charge
    is_completed     TEXT NOT NULL DEFAULT '',  -- V: 'o' = done
    needs_jp_support TEXT NOT NULL DEFAULT '',  -- Y: 'o' = needs JP support

    -- Event time: the real occurrence date when the source carries one
    -- (history_29 column C "生産日 / Ngày tháng sản xuất", ISO 'YYYY-MM-DD').
    -- NULL = unknown; trend/recurrence then fall back to created_at (import time).
    occurred_at      TEXT,

    raw_json         TEXT NOT NULL,  -- all A–Y values as JSON (full fidelity)
    skip_cells       TEXT NOT NULL DEFAULT '[]',  -- JSON list of green-skipped columns

    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE (no_dvd, sheet_type, department)
);

CREATE INDEX IF NOT EXISTS idx_error_cases_no_dvd ON error_cases (no_dvd);
CREATE INDEX IF NOT EXISTS idx_error_cases_line ON error_cases (line);
CREATE INDEX IF NOT EXISTS idx_error_cases_batch ON error_cases (batch_id);

-- F2: re-importing an unchanged source file is skipped ("vất lại file cũ
-- thì bỏ qua") — the importer checks this key before opening a batch.
CREATE UNIQUE INDEX IF NOT EXISTS uq_import_batches_file
    ON import_batches (source_file, file_sha256, sheet_name);

-- Wider dedup key for the 29-column history format, where (year, NO)
-- alone is not unique (same NO. reused for different machine/line).
CREATE UNIQUE INDEX IF NOT EXISTS uq_error_cases_history
    ON error_cases (no_dvd, machine_type, line);
