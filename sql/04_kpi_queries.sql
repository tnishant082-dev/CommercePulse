-- KPI queries — same numbers as the dashboard cards
-- reconcile vs reports/kpi_summary.json after refresh

-- executive cards
SELECT
    ROUND(SUM(LineAmount), 2) AS Revenue,
    COUNT(DISTINCT Invoice) AS Orders,
    COUNT(DISTINCT CustomerID) AS Customers,
    ROUND(SUM(LineAmount) / COUNT(DISTINCT Invoice), 2) AS AOV
FROM v_fact_sales;

-- UK share (expect ~85%+)
SELECT
    ROUND(SUM(CASE WHEN Country = 'United Kingdom' THEN LineAmount ELSE 0 END)
          / SUM(LineAmount), 4) AS uk_revenue_share
FROM v_fact_sales;

-- monthly trend — Nov peaks expected for gift retail
SELECT YearMonth, Revenue, Orders, Customers, ROUND(AOV, 2) AS AOV
FROM v_mart_monthly
ORDER BY YearMonth;

-- top 10 countries
SELECT Country,
       ROUND(SUM(LineAmount), 2) AS Revenue,
       COUNT(DISTINCT Invoice) AS Orders
FROM v_fact_sales
GROUP BY Country
ORDER BY Revenue DESC
LIMIT 10;

-- top 15 products by revenue
SELECT StockCode,
       MAX(Description) AS Description,
       ROUND(SUM(LineAmount), 2) AS Revenue,
       COUNT(DISTINCT Invoice) AS Orders,
       SUM(Quantity) AS Units
FROM v_fact_sales
GROUP BY StockCode
ORDER BY Revenue DESC
LIMIT 15;

-- return rate (value)
SELECT
    ROUND((SELECT SUM(ReturnAmount) FROM v_fact_returns)
          / (SELECT SUM(LineAmount) FROM v_fact_sales), 4) AS return_rate;

-- guest checkout share of lines
SELECT ROUND(AVG(IsGuest), 4) AS guest_line_share
FROM v_fact_sales;

-- YoY on calendar years present in both sheets
SELECT
    YEAR(InvoiceDate) AS Yr,
    ROUND(SUM(LineAmount), 2) AS Revenue,
    COUNT(DISTINCT Invoice) AS Orders,
    COUNT(DISTINCT CustomerID) AS Customers
FROM v_fact_sales
WHERE YEAR(InvoiceDate) IN (2010, 2011)
GROUP BY YEAR(InvoiceDate)
ORDER BY Yr;

-- TODO: wrap AOV in a reusable view once BI team asks for it again
