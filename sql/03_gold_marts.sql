-- gold marts — star schema for Power BI + ML features
-- fact grain: invoice line. dims: date, customer, product, country

CREATE OR REPLACE VIEW v_fact_sales AS
SELECT
    f.Invoice,
    f.StockCode,
    f.Description,
    f.Quantity,
    f.InvoiceDate,
    f.Price,
    f.CustomerID,
    f.Country,
    f.LineAmount,
    f.IsGuest,
    CAST(DATE_FORMAT(f.InvoiceDate, '%Y%m%d') AS UNSIGNED) AS DateKey
FROM v_stg_flags f
WHERE f.IsCancel = 0
  AND f.Quantity > 0
  AND f.Price > 0
  AND f.Description IS NOT NULL
  AND f.IsFeeCode = 0;

CREATE OR REPLACE VIEW v_dim_customer AS
SELECT
    CustomerID,
    MIN(InvoiceDate) AS FirstPurchase,
    MAX(InvoiceDate) AS LastPurchase,
    COUNT(DISTINCT Invoice) AS Orders,
    SUM(LineAmount) AS Revenue,
    -- most recent country (simple, not perfect)
    SUBSTRING_INDEX(GROUP_CONCAT(Country ORDER BY InvoiceDate DESC), ',', 1) AS Country
FROM v_fact_sales
WHERE CustomerID IS NOT NULL   -- check: null CustomerIDs before joining
GROUP BY CustomerID;

CREATE OR REPLACE VIEW v_dim_product AS
SELECT
    StockCode,
    SUBSTRING_INDEX(GROUP_CONCAT(Description ORDER BY InvoiceDate DESC), ',', 1) AS Description,
    COUNT(DISTINCT Invoice) AS Orders,
    SUM(Quantity) AS Units,
    SUM(LineAmount) AS Revenue,
    AVG(Price) AS AvgPrice
FROM v_fact_sales
GROUP BY StockCode;

CREATE OR REPLACE VIEW v_dim_country AS
SELECT DISTINCT Country
FROM v_fact_sales;

CREATE OR REPLACE VIEW v_dim_date AS
SELECT DISTINCT
    CAST(DATE_FORMAT(InvoiceDate, '%Y%m%d') AS UNSIGNED) AS DateKey,
    DATE(InvoiceDate) AS DateValue,
    YEAR(InvoiceDate) AS Year,
    MONTH(InvoiceDate) AS Month,
    DATE_FORMAT(InvoiceDate, '%Y-%m') AS YearMonth,
    QUARTER(InvoiceDate) AS Quarter
FROM v_fact_sales;

CREATE OR REPLACE VIEW v_mart_monthly AS
SELECT
    DATE_FORMAT(InvoiceDate, '%Y-%m') AS YearMonth,
    SUM(LineAmount) AS Revenue,
    COUNT(DISTINCT Invoice) AS Orders,
    COUNT(DISTINCT CustomerID) AS Customers,
    SUM(Quantity) AS Units,
    SUM(LineAmount) / COUNT(DISTINCT Invoice) AS AOV
FROM v_fact_sales
GROUP BY DATE_FORMAT(InvoiceDate, '%Y-%m')
ORDER BY YearMonth;

CREATE OR REPLACE VIEW v_fact_returns AS
SELECT
    Invoice,
    StockCode,
    Description,
    ABS(Quantity) AS ReturnQty,
    InvoiceDate,
    Price,
    CustomerID,
    Country,
    ABS(Quantity) * ABS(Price) AS ReturnAmount
FROM v_stg_flags
WHERE (IsCancel = 1 OR Quantity < 0)
  AND IsFeeCode = 0
  AND InvoiceDate IS NOT NULL;

-- TODO: index Country if country marts get slow
