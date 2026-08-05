-- practice joins / windows on retail data
-- intermediate SQL drills — not part of the production mart path

-- 1) customers + their order counts (inner join practice)
SELECT
    c.CustomerID,
    c.Country,
    COUNT(DISTINCT f.Invoice) AS Orders,
    ROUND(SUM(f.LineAmount), 2) AS Revenue
FROM v_dim_customer c
INNER JOIN v_fact_sales f
    ON c.CustomerID = f.CustomerID
GROUP BY c.CustomerID, c.Country
ORDER BY Revenue DESC
LIMIT 20;

-- 2) left join: products that never sold? (expect empty on this extract)
SELECT p.StockCode, p.Description
FROM v_dim_product p
LEFT JOIN v_fact_sales f
    ON p.StockCode = f.StockCode
WHERE f.StockCode IS NULL;

-- 3) running monthly revenue (window)
SELECT
    YearMonth,
    Revenue,
    ROUND(SUM(Revenue) OVER (ORDER BY YearMonth), 2) AS CumulativeRevenue,
    ROUND(Revenue - LAG(Revenue) OVER (ORDER BY YearMonth), 2) AS MoM_Change
FROM v_mart_monthly
ORDER BY YearMonth;

-- 4) rank countries within each year
SELECT
    YEAR(f.InvoiceDate) AS Yr,
    f.Country,
    ROUND(SUM(f.LineAmount), 2) AS Revenue,
    RANK() OVER (
        PARTITION BY YEAR(f.InvoiceDate)
        ORDER BY SUM(f.LineAmount) DESC
    ) AS CountryRank
FROM v_fact_sales f
GROUP BY YEAR(f.InvoiceDate), f.Country
ORDER BY Yr, CountryRank
LIMIT 30;

-- 5) customers who bought in UK and also abroad (self-join-ish via HAVING)
SELECT
    CustomerID,
    COUNT(DISTINCT Country) AS Countries,
    GROUP_CONCAT(DISTINCT Country ORDER BY Country SEPARATOR ', ') AS CountryList
FROM v_fact_sales
WHERE CustomerID IS NOT NULL   -- check: null CustomerIDs before joining
GROUP BY CustomerID
HAVING COUNT(DISTINCT Country) > 1
ORDER BY Countries DESC
LIMIT 25;

-- TODO: try a CTE version of #3 once I'm comfortable with WITH
