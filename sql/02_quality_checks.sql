-- quality checks before promoting bronze → silver
-- run after load; empty result on the "should be empty" ones = good

-- check: null invoice dates
SELECT COUNT(*) AS null_invoice_dates
FROM stg_retail_raw
WHERE InvoiceDate IS NULL;

-- fee / postage codes still in raw (expect some — filter downstream)
SELECT StockCode, COUNT(*) AS lines, SUM(Quantity * Price) AS amount
FROM stg_retail_raw
WHERE StockCode IN ('POST','DOT','M','D','AMAZONFEE','BANK CHARGES','CRUK','PADS','B')
GROUP BY StockCode
ORDER BY lines DESC;

-- cancels with positive qty? usually shouldn't happen
SELECT COUNT(*) AS cancel_with_positive_qty
FROM stg_retail_raw
WHERE Invoice LIKE 'C%'
  AND Quantity > 0;

-- duplicate grain check (invoice + stock + qty + price + date + customer)
SELECT Invoice, StockCode, Quantity, Price, InvoiceDate, CustomerID, COUNT(*) AS dupes
FROM stg_retail_raw
GROUP BY Invoice, StockCode, Quantity, Price, InvoiceDate, CustomerID
HAVING COUNT(*) > 1
ORDER BY dupes DESC
LIMIT 50;

-- tiny countries — might bucket as "Other" in BI later
SELECT Country, COUNT(*) AS lines
FROM stg_retail_raw
GROUP BY Country
HAVING COUNT(*) < 20
ORDER BY lines;

-- price outliers (unit price > 500) — often manual adjustments
SELECT Invoice, StockCode, Description, Quantity, Price, CustomerID, Country
FROM stg_retail_raw
WHERE Price > 500
ORDER BY Price DESC
LIMIT 50;

-- check: null CustomerIDs before joining to RFM features
SELECT COUNT(*) AS null_customer_ids
FROM stg_retail_raw
WHERE CustomerID IS NULL;
