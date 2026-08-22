-- staging for Online Retail II (both year sheets)
-- MySQL 8-ish / close to ANSI

CREATE TABLE IF NOT EXISTS stg_retail_raw (
    Invoice       VARCHAR(20)  NOT NULL,
    StockCode     VARCHAR(20),
    Description   VARCHAR(255),
    Quantity      INT,
    InvoiceDate   DATETIME,
    Price         DECIMAL(12,4),
    CustomerID    INT NULL,          -- check: null CustomerIDs before joining
    Country       VARCHAR(60),
    SourceSheet   VARCHAR(20)
);

-- keep cancels + fee codes here so we can audit them later
CREATE OR REPLACE VIEW v_stg_flags AS
SELECT
    Invoice,
    StockCode,
    Description,
    Quantity,
    InvoiceDate,
    Price,
    CustomerID,
    Country,
    SourceSheet,
    Quantity * Price AS LineAmount,
    CASE WHEN Invoice LIKE 'C%' THEN 1 ELSE 0 END AS IsCancel,
    CASE WHEN StockCode IN ('POST','DOT','M','D','AMAZONFEE','BANK CHARGES','CRUK','PADS','B')
         THEN 1 ELSE 0 END AS IsFeeCode,
    CASE WHEN CustomerID IS NULL THEN 1 ELSE 0 END AS IsGuest
FROM stg_retail_raw;

-- TODO: index Country if this gets slow on full refresh
