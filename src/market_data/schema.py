"""SQLite schema for raw, source-attributed market data."""

SCHEMA_VERSION = "1.2.0"

DDL_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS schema_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_registry (
        source_name TEXT NOT NULL,
        provider_type TEXT NOT NULL,
        dataset TEXT NOT NULL,
        market_support TEXT NOT NULL,
        adjust_support TEXT NOT NULL,
        field_support TEXT NOT NULL,
        status TEXT NOT NULL,
        availability TEXT NOT NULL,
        enabled INTEGER NOT NULL CHECK (enabled IN (0,1)),
        enabled_for_mvp INTEGER NOT NULL CHECK (enabled_for_mvp IN (0,1)),
        priority TEXT NOT NULL,
        license_type TEXT NOT NULL,
        future_provider INTEGER NOT NULL DEFAULT 0 CHECK (future_provider IN (0,1)),
        last_verified_at TEXT,
        notes TEXT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (source_name, provider_type, dataset)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_basic (
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        full_name TEXT,
        exchange TEXT NOT NULL CHECK (exchange IN ('SSE','SZSE','BSE','UNKNOWN')),
        market TEXT NOT NULL CHECK (market IN ('SH_MAIN','STAR','SZ_MAIN','GEM','BSE','UNKNOWN')),
        security_type TEXT NOT NULL DEFAULT 'A_SHARE',
        list_date TEXT,
        delist_date TEXT,
        is_currently_listed INTEGER CHECK (is_currently_listed IN (0,1) OR is_currently_listed IS NULL),
        source TEXT NOT NULL,
        source_updated_at TEXT,
        first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (code, exchange)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS market_daily (
        code TEXT NOT NULL,
        exchange TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        pre_close REAL,
        volume REAL,
        amount REAL,
        turnover_rate REAL,
        amplitude_pct REAL,
        change_pct_source REAL,
        change_amount_source REAL,
        adjust_type TEXT NOT NULL DEFAULT 'RAW',
        source TEXT NOT NULL,
        source_record_hash TEXT,
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (code, exchange, date, adjust_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS index_basic (
        index_code TEXT NOT NULL,
        index_name TEXT NOT NULL,
        exchange TEXT NOT NULL,
        publisher TEXT,
        category TEXT,
        is_core INTEGER NOT NULL DEFAULT 0 CHECK (is_core IN (0,1)),
        launch_date TEXT,
        source TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (index_code, exchange)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS index_daily (
        index_code TEXT NOT NULL,
        exchange TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        pre_close REAL,
        volume REAL,
        amount REAL,
        change_pct_source REAL,
        source TEXT NOT NULL,
        source_record_hash TEXT,
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (index_code, exchange, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_status (
        code TEXT NOT NULL,
        exchange TEXT NOT NULL,
        date TEXT NOT NULL,
        is_st INTEGER CHECK (is_st IN (0,1) OR is_st IS NULL),
        is_star_st INTEGER CHECK (is_star_st IN (0,1) OR is_star_st IS NULL),
        is_suspended INTEGER CHECK (is_suspended IN (0,1) OR is_suspended IS NULL),
        is_new_stock INTEGER CHECK (is_new_stock IN (0,1) OR is_new_stock IS NULL),
        is_delisting_period INTEGER CHECK (is_delisting_period IN (0,1) OR is_delisting_period IS NULL),
        has_price_limit INTEGER CHECK (has_price_limit IN (0,1) OR has_price_limit IS NULL),
        limit_up_pct REAL,
        limit_down_pct REAL,
        limit_up_price REAL,
        limit_down_price REAL,
        is_limit_up INTEGER CHECK (is_limit_up IN (0,1) OR is_limit_up IS NULL),
        is_limit_down INTEGER CHECK (is_limit_down IN (0,1) OR is_limit_down IS NULL),
        is_limit_touched INTEGER CHECK (is_limit_touched IN (0,1) OR is_limit_touched IS NULL),
        is_limit_broken INTEGER CHECK (is_limit_broken IN (0,1) OR is_limit_broken IS NULL),
        status_source TEXT,
        status_quality TEXT NOT NULL DEFAULT 'UNKNOWN',
        is_inferred INTEGER NOT NULL DEFAULT 0 CHECK (is_inferred IN (0,1)),
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (code, exchange, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sector_basic (
        sector_system TEXT NOT NULL,
        sector_type TEXT NOT NULL CHECK (sector_type IN ('INDUSTRY','CONCEPT','STYLE','OTHER')),
        sector_code TEXT NOT NULL,
        sector_name TEXT NOT NULL,
        level INTEGER,
        parent_sector_code TEXT,
        valid_from TEXT,
        valid_to TEXT,
        classification_version TEXT NOT NULL DEFAULT 'UNKNOWN',
        classification_basis TEXT NOT NULL DEFAULT 'UNKNOWN',
        quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',
        source TEXT NOT NULL,
        source_updated_at TEXT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (sector_system, sector_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sector_membership (
        sector_system TEXT NOT NULL,
        sector_code TEXT NOT NULL,
        code TEXT NOT NULL,
        exchange TEXT NOT NULL,
        valid_from TEXT,
        valid_to TEXT,
        membership_weight REAL,
        snapshot_date TEXT NOT NULL,
        is_historical_verified INTEGER NOT NULL DEFAULT 0 CHECK (is_historical_verified IN (0,1)),
        membership_basis TEXT NOT NULL DEFAULT 'CURRENT_SNAPSHOT',
        quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',
        source TEXT NOT NULL,
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (sector_system, sector_code, code, exchange, snapshot_date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sector_daily (
        sector_system TEXT NOT NULL,
        sector_code TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        pre_close REAL,
        volume REAL,
        amount REAL,
        volume_unit TEXT NOT NULL DEFAULT 'UNKNOWN',
        amount_unit TEXT NOT NULL DEFAULT 'UNKNOWN',
        change_pct_source REAL,
        quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',
        source TEXT NOT NULL,
        source_record_hash TEXT,
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (sector_system, sector_code, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trading_calendar (
        date TEXT NOT NULL,
        market TEXT NOT NULL,
        is_trading_day INTEGER NOT NULL CHECK (is_trading_day IN (0,1)),
        session_type TEXT,
        source TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (date, market)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_log (
        run_id TEXT PRIMARY KEY,
        dataset TEXT NOT NULL,
        entity_id TEXT,
        start_date TEXT,
        end_date TEXT,
        source TEXT NOT NULL,
        status TEXT NOT NULL,
        requested_count INTEGER NOT NULL DEFAULT 0,
        received_count INTEGER NOT NULL DEFAULT 0,
        inserted_count INTEGER NOT NULL DEFAULT 0,
        updated_count INTEGER NOT NULL DEFAULT 0,
        rejected_count INTEGER NOT NULL DEFAULT 0,
        retry_count INTEGER NOT NULL DEFAULT 0,
        error_type TEXT,
        error_message TEXT,
        started_at TEXT NOT NULL,
        finished_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_checkpoint (
        dataset TEXT NOT NULL,
        code TEXT NOT NULL,
        exchange TEXT NOT NULL,
        market TEXT NOT NULL,
        request_start TEXT NOT NULL,
        request_end TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('PENDING','DOWNLOADING','VALIDATING','COMMITTED','FAILED','UNKNOWN')),
        last_success_date TEXT,
        rows_written INTEGER NOT NULL DEFAULT 0,
        provider TEXT,
        batch_id TEXT,
        attempt_count INTEGER NOT NULL DEFAULT 0,
        error TEXT,
        completed_at TEXT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (dataset,code,exchange,request_start,request_end)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS data_quality_issue (
        issue_id TEXT PRIMARY KEY,
        dataset TEXT NOT NULL,
        entity_id TEXT,
        date TEXT,
        issue_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        observed_value TEXT,
        expected_rule TEXT,
        source TEXT,
        run_id TEXT,
        status TEXT NOT NULL DEFAULT 'OPEN',
        detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        resolved_at TEXT,
        resolution_note TEXT,
        FOREIGN KEY (run_id) REFERENCES ingestion_log(run_id)
    )
    """,
)

INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_source_registry_enabled ON source_registry(dataset, enabled_for_mvp, status)",
    "CREATE INDEX IF NOT EXISTS idx_stock_basic_market ON stock_basic(market)",
    "CREATE INDEX IF NOT EXISTS idx_stock_basic_listing ON stock_basic(is_currently_listed, list_date, delist_date)",
    "CREATE INDEX IF NOT EXISTS idx_market_daily_date ON market_daily(date)",
    "CREATE INDEX IF NOT EXISTS idx_market_daily_code_date ON market_daily(code, exchange, date)",
    "CREATE INDEX IF NOT EXISTS idx_market_daily_source_date ON market_daily(source, date)",
    "CREATE INDEX IF NOT EXISTS idx_index_daily_date ON index_daily(date)",
    "CREATE INDEX IF NOT EXISTS idx_index_daily_code_date ON index_daily(index_code, exchange, date)",
    "CREATE INDEX IF NOT EXISTS idx_stock_status_date ON stock_status(date)",
    "CREATE INDEX IF NOT EXISTS idx_sector_membership_stock ON sector_membership(code, exchange, snapshot_date)",
    "CREATE INDEX IF NOT EXISTS idx_sector_membership_sector ON sector_membership(sector_system, sector_code, snapshot_date)",
    "CREATE INDEX IF NOT EXISTS idx_sector_daily_date ON sector_daily(date)",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_log_dataset_status ON ingestion_log(dataset, status, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_ingestion_checkpoint_status ON ingestion_checkpoint(dataset,status,batch_id)",
    "CREATE INDEX IF NOT EXISTS idx_quality_issue_open ON data_quality_issue(status, severity, dataset)",
)
