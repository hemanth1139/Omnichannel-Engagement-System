-- Databricks notebook source
-- MAGIC %md
-- MAGIC 01 - Email Silver Layer

-- COMMAND ----------


--  INPUT VALIDATION
SELECT *
FROM workspace.bronze.email_activity
LIMIT 10;
-- Basic dataset statistics

SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT hcp_id) AS unique_hcps,
    COUNT(DISTINCT email_event_id) AS unique_email_events
FROM workspace.bronze.email_activity;
-- Check the raw event distribution

SELECT
    event_type,
    COUNT(*) AS records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.bronze.email_activity
GROUP BY event_type
ORDER BY records DESC;

-- COMMAND ----------


--  BRONZE → SILVER STANDARDIZATION
CREATE OR REPLACE TABLE workspace.silver.email_activity AS

WITH cleaned AS (

    SELECT
        -- IDENTIFIERS

        CAST(email_event_id AS STRING)
            AS email_event_id,
        TRIM(CAST(hcp_id AS STRING))
            AS hcp_id,
        TRIM(CAST(campaign_id AS STRING))
            AS campaign_id,
        TRIM(CAST(drug_id AS STRING))
            AS drug_id,
        TRIM(CAST(email_id AS STRING))
            AS email_id,
        -- EVENT TYPE STANDARDIZATION
        
        CASE

            WHEN LOWER(TRIM(event_type)) = 'delivered'
                THEN 'delivered'
            WHEN LOWER(TRIM(event_type)) = 'open'
                THEN 'open'
            WHEN LOWER(TRIM(event_type)) = 'click'
                THEN 'click'
            WHEN LOWER(TRIM(event_type)) = 'bounced'
                THEN 'bounced'

            ELSE NULL

        END AS event_type,
        -- TIMESTAMP STANDARDIZATION
        CAST(event_timestamp AS TIMESTAMP)
            AS event_timestamp,

        -- TEXT STANDARDIZATION
        NULLIF(
            TRIM(email_subject),
            ''
        ) AS email_subject,
        NULLIF(
            TRIM(url),
            ''
        ) AS url,
        -- DEVICE TYPE STANDARDIZATION
        CASE
            WHEN LOWER(TRIM(device_type))
                IN ('desktop', 'mobile', 'tablet')

            THEN LOWER(TRIM(device_type))
            ELSE NULL
        END AS device_type,
        -- DELIVERY STATUS STANDARDIZATION
        
        CASE
            WHEN LOWER(TRIM(delivery_status))
                IN ('delivered', 'bounced', 'failed')
            THEN LOWER(TRIM(delivery_status))
            ELSE NULL
        END AS delivery_status,
        -- SOURCE SYSTEM
    
        NULLIF(
            TRIM(source_system),
            ''
        ) AS source_system,

        -- DUPLICATE DETECTION
        ROW_NUMBER() OVER (

            PARTITION BY email_event_id
            ORDER BY event_timestamp DESC
        ) AS rn
    FROM workspace.bronze.email_activity
)
SELECT
    email_event_id,
    hcp_id,
    campaign_id,
    drug_id,
    email_id,
    event_type,
    event_timestamp,
    email_subject,
    url,
    device_type,
    delivery_status,
    source_system
FROM cleaned
WHERE rn = 1

  AND hcp_id IS NOT NULL

  AND event_type IS NOT NULL

  AND event_timestamp IS NOT NULL;

-- COMMAND ----------


--  STANDARDIZATION VALIDATION
-- ROW COUNT / HCP COUNT
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT hcp_id)
        AS unique_hcps,
    COUNT(DISTINCT email_event_id)
        AS unique_email_events

FROM workspace.silver.email_activity;

-- EVENT DISTRIBUTION
SELECT
    event_type,
    COUNT(*) AS records,
    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.email_activity
GROUP BY event_type
ORDER BY records DESC;
-- DUPLICATE EVENT ID CHECK
SELECT

    COUNT(*) AS duplicate_event_ids

FROM (

    SELECT
        email_event_id

    FROM workspace.silver.email_activity

    GROUP BY email_event_id

    HAVING COUNT(*) > 1

);
--  NULL VALIDATION
SELECT
    SUM(
        CASE
            WHEN email_event_id IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_event_ids,
    SUM(
        CASE
            WHEN hcp_id IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_hcp_ids,
    SUM(
        CASE
            WHEN event_type IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_event_types,
    SUM(
        CASE
            WHEN event_timestamp IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_timestamps

FROM workspace.silver.email_activity;

-- COMMAND ----------


-- EMAIL ACTIVITY PROFILING
-- EVENT DISTRIBUTION

SELECT
    event_type,
    COUNT(*) AS records,
    COUNT(DISTINCT hcp_id)
        AS unique_hcps
FROM workspace.silver.email_activity
GROUP BY event_type
ORDER BY records DESC;
-- ACTIVITY DATE RANGE
SELECT

    MIN(event_timestamp)
        AS first_email_activity,

    MAX(event_timestamp)
        AS last_email_activity

FROM workspace.silver.email_activity;

-- HCP COVERAGE
SELECT
    COUNT(DISTINCT hcp_id)
        AS email_active_hcps

FROM workspace.silver.email_activity;
-- CLICKS WITHOUT OPENS

SELECT
    COUNT(*) AS clicks_without_open
FROM workspace.silver.email_activity
WHERE event_type = 'click'
  AND email_id NOT IN (
      SELECT DISTINCT email_id
      FROM workspace.silver.email_activity
      WHERE event_type = 'open'
        AND email_id IS NOT NULL

  );

-- COMMAND ----------


--  HCP-LEVEL EMAIL FEATURES
CREATE OR REPLACE TABLE workspace.silver.email_features AS
SELECT
    hcp_id,
    -- EMAIL VOLUME
    SUM(

        CASE
            WHEN event_type = 'delivered'
            THEN 1
            ELSE 0
        END

    ) AS emails_delivered,

    SUM(

        CASE
            WHEN event_type = 'bounced'
            THEN 1
            ELSE 0
        END

    ) AS emails_bounced,
    SUM(

        CASE
            WHEN event_type = 'open'
            THEN 1
            ELSE 0
        END

    ) AS email_opens,
    SUM(

        CASE
            WHEN event_type = 'click'
            THEN 1
            ELSE 0
        END

    ) AS email_clicks,
    -- OPEN RATE
    -- Open Rate = Opens / Deliver
    ROUND(
        SUM(
            CASE
                WHEN event_type = 'open'
                THEN 1
                ELSE 0
            END
        ) * 1.0

        /

        NULLIF(

            SUM(

                CASE
                    WHEN event_type = 'delivered'
                    THEN 1
                    ELSE 0
                END

            ),

            0

        ),

        4

    ) AS email_open_rate,
    -- CLICK RATE
    -- Click Rate = Clicks / Deliver
    ROUND(
        SUM(
            CASE
                WHEN event_type = 'click'
                THEN 1
                ELSE 0
            END
        ) * 1.0

        /
        NULLIF(
            SUM(
                CASE
                    WHEN event_type = 'delivered'
                    THEN 1
                    ELSE 0
                END
            ),

            0
        ),

        4

    ) AS email_click_rate,
    -- CLICK-TO-OPEN RATE (CTOR) CTOR = Clicks / Open

    ROUND(
        SUM(
            CASE
                WHEN event_type = 'click'
                THEN 1
                ELSE 0
            END
        ) * 1.0
        /
        NULLIF(
            SUM(
                CASE
                    WHEN event_type = 'open'
                    THEN 1
                    ELSE 0
                END

            ),
            0
        ),

        4

    ) AS email_ctor,
    -- LAST EMAIL ACTIVITY

    MAX(event_timestamp)
        AS last_email_activity,

    -- LAST EMAIL ENGAGEMENT
   
    MAX(
        CASE
            WHEN event_type IN ('open', 'click')
            THEN event_timestamp
        END
    ) AS last_email_engagement,

    -- DAYS SINCE LAST EMAIL ENGAGEMENT

    DATEDIFF(
        DATE('2026-08-16'),
        CAST(
            MAX(
                CASE
                    WHEN event_type IN ('open', 'click')
                    THEN event_timestamp
                END
            ) AS DATE
        )
    ) AS days_since_last_email_engagement,

    -- DAYS SINCE LAST EMAIL ACTIVITY

    DATEDIFF(
        DATE('2026-08-16'),
        CAST(
            MAX(event_timestamp)
            AS DATE

        )

    ) AS days_since_last_email_activity


FROM workspace.silver.email_activity

GROUP BY hcp_id;

-- COMMAND ----------


-- CELL 6: HCP COUNT VALIDATION




-- TOTAL HCPs


SELECT

    COUNT(*) AS total_hcp_records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.email_features;



-- DUPLICATE HCP CHECK


SELECT

    hcp_id,

    COUNT(*) AS records

FROM workspace.silver.email_features

GROUP BY hcp_id

HAVING COUNT(*) > 1;


-- COMPARE AGAINST HCP MASTER


SELECT

    COUNT(DISTINCT h.hcp_id)
        AS total_hcps,

    COUNT(DISTINCT e.hcp_id)
        AS email_active_hcps

FROM workspace.bronze.hcp_master h

LEFT JOIN workspace.silver.email_features e

    ON h.hcp_id = e.hcp_id;

-- COMMAND ----------



-- CELL 7: FEATURE VALIDATION



-- 1. VIEW SAMPLE FEATURES


SELECT

    hcp_id,

    emails_delivered,
    email_opens,
    email_clicks,
    email_open_rate,
    email_click_rate,
    email_ctor,
    last_email_activity,
    last_email_engagement,
    days_since_last_email_engagement,
    days_since_last_email_activity

FROM workspace.silver.email_features

ORDER BY hcp_id

LIMIT 10;



-- 2. CTOR RANGE


SELECT

    MIN(email_ctor)
        AS min_ctor,

    MAX(email_ctor)
        AS max_ctor,

    ROUND(
        AVG(email_ctor),
        4
    ) AS avg_ctor

FROM workspace.silver.email_features;


-- 3. OPEN RATE RANGE


SELECT

    MIN(email_open_rate)
        AS min_open_rate,

    MAX(email_open_rate)
        AS max_open_rate,

    ROUND(
        AVG(email_open_rate),
        4
    ) AS avg_open_rate

FROM workspace.silver.email_features;



-- 4. CLICK RATE RANGE


SELECT

    MIN(email_click_rate)
        AS min_click_rate,

    MAX(email_click_rate)
        AS max_click_rate,

    ROUND(
        AVG(email_click_rate),
        4
    ) AS avg_click_rate

FROM workspace.silver.email_features;



-- 5. CHECK FOR INVALID NEGATIVE RATES


SELECT

    COUNT(*) AS invalid_rate_records

FROM workspace.silver.email_features

WHERE email_open_rate < 0

   OR email_click_rate < 0

   OR email_ctor < 0;



-- 6. CHECK CTOR LOGIC


SELECT

    hcp_id,

    email_opens,

    email_clicks,

    email_ctor,

    ROUND(
        email_clicks * 1.0
        /
        NULLIF(email_opens, 0),
        4
    ) AS calculated_ctor

FROM workspace.silver.email_features

ORDER BY hcp_id

LIMIT 10;