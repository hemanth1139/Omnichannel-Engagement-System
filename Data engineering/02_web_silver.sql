-- Databricks notebook source
-- MAGIC %md
-- MAGIC 02 - Web Silver Layer

-- COMMAND ----------


-- CELL 1: INPUT VALIDATION
-- 1. SAMPLE RAW BRONZE DATA

SELECT *

FROM workspace.bronze.web_activity

LIMIT 10;

-- 2. BASIC DATASET STATISTICS

SELECT

    COUNT(*) AS total_rows,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps,

    COUNT(DISTINCT web_event_id)
        AS unique_web_events,

    COUNT(DISTINCT session_id)
        AS unique_sessions

FROM workspace.bronze.web_activity;

-- 3. RAW EVENT DISTRIBUTION

SELECT

    event_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.bronze.web_activity

GROUP BY event_type

ORDER BY records DESC;

-- COMMAND ----------

-- CELL 2: BRONZE → SILVER STANDARDIZATION

CREATE OR REPLACE TABLE workspace.silver.web_activity AS

WITH cleaned AS (

    SELECT

        -- IDENTIFIERS
        

        CAST(web_event_id AS STRING)
            AS web_event_id,

        TRIM(CAST(hcp_id AS STRING))
            AS hcp_id,

        TRIM(CAST(session_id AS STRING))
            AS session_id,

        TRIM(CAST(campaign_id AS STRING))
            AS campaign_id,

        TRIM(CAST(drug_id AS STRING))
            AS drug_id,


        
        -- EVENT TYPE STANDARDIZATION
        

        CASE

            WHEN LOWER(TRIM(event_type)) = 'page_view'
                THEN 'page_view'

            WHEN LOWER(TRIM(event_type)) = 'content_view'
                THEN 'content_view'

            WHEN LOWER(TRIM(event_type)) = 'download'
                THEN 'download'

            WHEN LOWER(TRIM(event_type)) = 'video_start'
                THEN 'video_start'

            WHEN LOWER(TRIM(event_type)) = 'video_complete'
                THEN 'video_complete'

            ELSE NULL

        END AS event_type,


        
        -- TIMESTAMP STANDARDIZATION
        

        CAST(event_timestamp AS TIMESTAMP)
            AS event_timestamp,


        
        -- TEXT CLEANING
   

        NULLIF(
            TRIM(page_url),
            ''
        ) AS page_url,

        NULLIF(
            TRIM(content_id),
            ''
        ) AS content_id,

        NULLIF(
            TRIM(content_type),
            ''
        ) AS content_type,


        
        -- SESSION DURATION STANDARDIZATION
        -- Negative values become NULL
        

        CASE

            WHEN CAST(session_duration_seconds AS DOUBLE) >= 0

            THEN CAST(
                session_duration_seconds AS DOUBLE
            )

            ELSE NULL

        END AS session_duration_seconds,

        -- DEVICE TYPE STANDARDIZATION
        

        CASE

            WHEN LOWER(TRIM(device_type))
                IN ('desktop', 'mobile', 'tablet')

            THEN LOWER(TRIM(device_type))

            ELSE NULL

        END AS device_type,


        -- TRAFFIC SOURCE STANDARDIZATION
    

        CASE

            WHEN LOWER(TRIM(traffic_source))
                = 'email'

                THEN 'email'

            WHEN LOWER(TRIM(traffic_source))
                = 'organic search'

                THEN 'organic search'

            WHEN LOWER(TRIM(traffic_source))
                = 'direct'

                THEN 'direct'

            WHEN LOWER(TRIM(traffic_source))
                = 'professional referral'

                THEN 'professional referral'

            ELSE NULL

        END AS traffic_source,


        
        -- SOURCE SYSTEM
        

        NULLIF(
            TRIM(source_system),
            ''
        ) AS source_system,


       
        -- DUPLICATE HANDLING
       

        ROW_NUMBER() OVER (

            PARTITION BY web_event_id

            ORDER BY event_timestamp DESC

        ) AS rn


    FROM workspace.bronze.web_activity
)


SELECT

    web_event_id,
    hcp_id,
    session_id,
    campaign_id,
    drug_id,
    event_type,
    event_timestamp,
    page_url,
    content_id,
    content_type,
    session_duration_seconds,
    device_type,
    traffic_source,
    source_system

FROM cleaned

WHERE rn = 1

  AND hcp_id IS NOT NULL

  AND event_type IS NOT NULL

  AND event_timestamp IS NOT NULL;

-- COMMAND ----------


-- CELL 3: STANDARDIZATION VALIDATION

--  ROW COUNT / HCP COUNT / EVENT COUNT


SELECT

    COUNT(*) AS total_rows,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps,

    COUNT(DISTINCT web_event_id)
        AS unique_web_events,

    COUNT(DISTINCT session_id)
        AS unique_sessions

FROM workspace.silver.web_activity;

--  EVENT DISTRIBUTIOn

SELECT

    event_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.web_activity

GROUP BY event_type

ORDER BY records DESC;



--  DUPLICATE WEB EVENT CHECK


SELECT

    COUNT(*) AS duplicate_web_event_ids

FROM (

    SELECT

        web_event_id

    FROM workspace.silver.web_activity

    GROUP BY web_event_id

    HAVING COUNT(*) > 1

);

--  NULL VALIDATION

SELECT

    SUM(
        CASE
            WHEN web_event_id IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_web_event_ids,

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

FROM workspace.silver.web_activity;

--  NEGATIVE SESSION DURATION CHECK

SELECT

    COUNT(*) AS negative_session_durations

FROM workspace.silver.web_activity

WHERE session_duration_seconds < 0;

-- COMMAND ----------


-- WEB ACTIVITY PROFILING


--  EVENT DISTRIBUTION
SELECT

    event_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.web_activity

GROUP BY event_type

ORDER BY records DESC;

-- TRAFFIC SOURCE DISTRIBUTION


SELECT

    traffic_source,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.web_activity

GROUP BY traffic_source

ORDER BY records DESC;


--  WEB ACTIVITY DATE RANGE

SELECT

    MIN(event_timestamp)
        AS first_web_activity,

    MAX(event_timestamp)
        AS last_web_activity

FROM workspace.silver.web_activity;

--  HCP COVERAGE

SELECT

    COUNT(DISTINCT hcp_id)
        AS web_active_hcps

FROM workspace.silver.web_activity;


-- SESSION VALIDATION

SELECT

    COUNT(DISTINCT session_id)
        AS unique_sessions,

    COUNT(
        DISTINCT CASE
            WHEN event_type = 'page_view'
            THEN session_id
        END
    ) AS sessions_with_page_view

FROM workspace.silver.web_activity;

-- COMMAND ----------


--  HCP-LEVEL WEB FEATURES


CREATE OR REPLACE TABLE workspace.silver.web_features AS

SELECT

    hcp_id,


   
    -- TOTAL WEB ACTIVITY

    COUNT(*) AS total_web_events,

    -- PAGE VIEWS
  

    SUM(

        CASE
            WHEN event_type = 'page_view'
            THEN 1
            ELSE 0
        END

    ) AS page_views,


    -- CONTENT VIEWS

    SUM(

        CASE
            WHEN event_type = 'content_view'
            THEN 1
            ELSE 0
        END

    ) AS content_views,



    -- DOWNLOADS
   

    SUM(

        CASE
            WHEN event_type = 'download'
            THEN 1
            ELSE 0
        END

    ) AS downloads,



    --  DOWNLOAD RATE
    -- Download Rate = Downloads / Content Views
    -- Measures how often content consumption results in a deeper action.
  

    ROUND(

        SUM(

            CASE
                WHEN event_type = 'download'
                THEN 1
                ELSE 0
            END

        ) * 1.0

        /

        NULLIF(

            SUM(

                CASE
                    WHEN event_type = 'content_view'
                    THEN 1
                    ELSE 0
                END

            ),

            0

        ),

        4

    ) AS download_rate,

    -- VIDEO STARTS
    SUM(

        CASE
            WHEN event_type = 'video_start'
            THEN 1
            ELSE 0
        END

    ) AS video_starts,

    -- VIDEO COMPLETIONS

    SUM(

        CASE
            WHEN event_type = 'video_complete'
            THEN 1
            ELSE 0
        END

    ) AS video_completions,

    -- VIDEO COMPLETION RATE
    -- Video Completions / Video Starts

    COALESCE(

        ROUND(

            SUM(

                CASE
                    WHEN event_type = 'video_complete'
                    THEN 1
                    ELSE 0
                END

            ) * 1.0

            /

            NULLIF(

                SUM(

                    CASE
                        WHEN event_type = 'video_start'
                        THEN 1
                        ELSE 0
                    END

                ),

                0

            ),

            4

        ),

        0

    ) AS video_completion_rate,

    -- UNIQUE SESSION

    COUNT(DISTINCT session_id)
        AS sessions,

    -- AVERAGE SESSION DURATION

    ROUND(

        AVG(session_duration_seconds),

        2

    ) AS avg_session_duration,

    -- LAST WEB ACTIVITY

    MAX(event_timestamp)
        AS last_web_activity,



    -- LAST WEB ENGAGEMENT
    -- Content view, download, video start or completion

    MAX(

        CASE

            WHEN event_type IN (

                'content_view',
                'download',
                'video_start',
                'video_complete'

            )

            THEN event_timestamp

        END

    ) AS last_web_engagement,

    -- DAYS SINCE LAST WEB ENGAGEMENT

    DATEDIFF(

        DATE('2026-08-16'),

        CAST(

            MAX(

                CASE

                    WHEN event_type IN (

                        'content_view',
                        'download',
                        'video_start',
                        'video_complete'

                    )

                    THEN event_timestamp

                END

            )

            AS DATE

        )

    ) AS days_since_last_web_engagement,

    -- DAYS SINCE LAST WEB ACTIVITY

    DATEDIFF(

        DATE('2026-08-16'),

        CAST(

            MAX(event_timestamp)

            AS DATE

        )

    ) AS days_since_last_web_activity


FROM workspace.silver.web_activity

GROUP BY hcp_id;

-- COMMAND ----------


--  HCP COUNT VALIDATION

-- 1. TOTAL HCP RECORDs

SELECT

    COUNT(*) AS total_hcp_records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.web_features;

-- 2. DUPLICATE HCP CHECK

SELECT

    hcp_id,

    COUNT(*) AS records

FROM workspace.silver.web_features

GROUP BY hcp_id

HAVING COUNT(*) > 1;

-- 3. COMPARE AGAINST HCP MASTER


SELECT

    COUNT(DISTINCT h.hcp_id)
        AS total_hcps,

    COUNT(DISTINCT w.hcp_id)
        AS web_active_hcps

FROM workspace.bronze.hcp_master h

LEFT JOIN workspace.silver.web_features w

    ON h.hcp_id = w.hcp_id;

-- COMMAND ----------


-- CELL 7: FEATURE VALIDATION

-- 1. VIEW SAMPLE FEATURES

SELECT

    hcp_id,

    page_views,
    content_views,
    downloads,

    -- ⭐ NEW
    download_rate,

    video_starts,
    video_completions,
    video_completion_rate,

    sessions,
    avg_session_duration,

    last_web_activity,
    last_web_engagement,

    days_since_last_web_engagement,
    days_since_last_web_activity

FROM workspace.silver.web_features

ORDER BY hcp_id

LIMIT 10;

-- 2. DOWNLOAD RATE RANGE

SELECT

    MIN(download_rate)
        AS min_download_rate,

    MAX(download_rate)
        AS max_download_rate,

    ROUND(
        AVG(download_rate),
        4
    ) AS avg_download_rate

FROM workspace.silver.web_features;


-- 3. VIDEO COMPLETION RATE RANGE

SELECT

    MIN(video_completion_rate)
        AS min_video_completion_rate,

    MAX(video_completion_rate)
        AS max_video_completion_rate,

    ROUND(
        AVG(video_completion_rate),
        4
    ) AS avg_video_completion_rate

FROM workspace.silver.web_features;

-- 4. SESSION DURATION RANGE

SELECT

    MIN(avg_session_duration)
        AS min_avg_session_duration,

    MAX(avg_session_duration)
        AS max_avg_session_duration,

    ROUND(
        AVG(avg_session_duration),
        2
    ) AS overall_avg_session_duration

FROM workspace.silver.web_features;


-- 5. INVALID NEGATIVE VALUES


SELECT

    COUNT(*) AS invalid_web_records

FROM workspace.silver.web_features

WHERE page_views < 0

   OR content_views < 0

   OR downloads < 0

   OR download_rate < 0

   OR video_starts < 0

   OR video_completions < 0

   OR video_completion_rate < 0

   OR avg_session_duration < 0;



-- 6. DOWNLOAD RATE LOGIC VALIDATION


SELECT

    hcp_id,

    content_views,

    downloads,

    download_rate,

    ROUND(

        downloads * 1.0
        /
        NULLIF(content_views, 0),

        4

    ) AS calculated_download_rate

FROM workspace.silver.web_features

ORDER BY hcp_id

LIMIT 10;