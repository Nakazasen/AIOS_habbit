-- F4: error code glossary (Bang ma loi / UWCA / SCT).
-- One shared table keyed by (code_family, code, code_sub):
--   C_CALL  : C + 4 digits, e.g. C0030        (source: 02XC_...Iris2020 VN.xls)
--   F_SYSTEM: F + 3-4 chars, wildcard X, e.g. F10X (source: UWCA...xls)
--   JAM     : 4 hex chars, e.g. 6000          (source: 02XC_...JAM...xls)
--   SCT_ADJ : 2 hex chars, e.g. 01            (source: SCT...xls)

CREATE TABLE IF NOT EXISTS error_glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_family TEXT NOT NULL
        CHECK (code_family IN ('C_CALL', 'F_SYSTEM', 'JAM', 'SCT_ADJ')),
    code TEXT NOT NULL,                 -- normalized lookup key (NFKC, upper)
    code_sub TEXT NOT NULL DEFAULT '',   -- detail: ErrDefine (SCT), '' otherwise
    name_ja TEXT,
    name_vi TEXT,
    name_en TEXT,
    cause TEXT,                          -- detection / cause text
    remedy TEXT,                         -- remedy / verification steps
    rank TEXT,                           -- C-call occurrence rank A/B/C/D
    unit TEXT,                           -- JAM unit, e.g. '00'
    models TEXT,                         -- applicable models, comma-joined
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (code_family, code, code_sub)
);

CREATE INDEX IF NOT EXISTS idx_glossary_code ON error_glossary (code_family, code);

-- Import log: re-importing an unchanged source file is skipped ("vất lại
-- file cũ thì bỏ qua"), unless force=True.
CREATE TABLE IF NOT EXISTS glossary_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    entries INTEGER NOT NULL DEFAULT 0,
    imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (source_file, file_sha256)
);
