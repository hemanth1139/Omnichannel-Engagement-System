-- Databricks notebook source
-- MAGIC %md
-- MAGIC 04 - Event Silver Layer

-- COMMAND ----------


-- 04 - EVENT SILVER
-- CELL 1: INPUT VALIDATION




-- 1. SAMPLE RAW BRONZE DATA


SELECT *

FROM workspace.bronze.event_activity

LIMIT 10;



-- 2. BASIC DATASET STATISTICS


SELECT

    COUNT(*) AS total_rows,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps,

    COUNT(DISTINCT event_activity_id)
        AS unique_event_activities,

    COUNT(DISTINCT event_id)
        AS unique_events

FROM workspace.bronze.event_activity;



-- 3. ACTIVITY TYPE DISTRIBUTION


SELECT

    event_activity_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.bronze.event_activity

GROUP BY event_activity_type

ORDER BY records DESC;



-- 4. EVENT TYPE DISTRIBUTION


SELECT

    event_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.bronze.event_activity

GROUP BY event_type

ORDER BY records DESC;

-- COMMAND ----------


-- 04 - EVENT SILVER
-- CELL 2: BRONZE → SILVER STANDARDIZATION


CREATE OR REPLACE TABLE workspace.silver.event_activity AS

WITH cleaned AS (

    SELECT

       
        -- IDENTIFIERS
       

        CAST(event_activity_id AS STRING)
            AS event_activity_id,

        TRIM(CAST(hcp_id AS STRING))
            AS hcp_id,

        TRIM(CAST(event_id AS STRING))
            AS event_id,

        TRIM(CAST(campaign_id AS STRING))
            AS campaign_id,

        TRIM(CAST(drug_id AS STRING))
            AS drug_id,


       
        -- EVENT NAME
       

        NULLIF(
            TRIM(event_name),
            ''
        ) AS event_name,


       
        -- EVENT TYPE STANDARDIZATION
       

        CASE

            WHEN LOWER(TRIM(event_type))
                = 'webinar'

            THEN 'Webinar'


            WHEN LOWER(TRIM(event_type))
                = 'medical education'

            THEN 'Medical Education'


            WHEN LOWER(TRIM(event_type))
                = 'product launch'

            THEN 'Product Launch'


            WHEN LOWER(TRIM(event_type))
                = 'expert panel'

            THEN 'Expert Panel'


            WHEN LOWER(TRIM(event_type))
                = 'clinical discussion'

            THEN 'Clinical Discussion'


            ELSE NULL

        END AS event_type,


       
        -- ACTIVITY TYPE STANDARDIZATION
       

        CASE

            WHEN LOWER(TRIM(event_activity_type))
                = 'registration'

            THEN 'registration'


            WHEN LOWER(TRIM(event_activity_type))
                = 'attendance'

            THEN 'attendance'


            ELSE NULL

        END AS event_activity_type,


       
        -- TIMESTAMP STANDARDIZATION
       

        CAST(activity_timestamp AS TIMESTAMP)
            AS activity_timestamp,


       
        -- REGISTRATION STATUS
       

        NULLIF(
            TRIM(registration_status),
            ''
        ) AS registration_status,


       
        -- ATTENDANCE STATUS
       

        CASE

            WHEN LOWER(TRIM(attendance_status))
                = 'attended'

            THEN 'Attended'


            WHEN LOWER(TRIM(attendance_status))
                = 'not applicable'

            THEN 'Not Applicable'


            ELSE NULL

        END AS attendance_status,


       
        -- ATTENDANCE DURATION
        --
        -- Negative values become NULL
       

        CASE

            WHEN CAST(
                attendance_duration_minutes AS DOUBLE
            ) >= 0

            THEN CAST(
                attendance_duration_minutes AS DOUBLE
            )

            ELSE NULL

        END AS attendance_duration_minutes,


       
        -- QUESTIONS ASKED
       

        CASE

            WHEN CAST(questions_asked AS DOUBLE) >= 0

            THEN CAST(
                questions_asked AS DOUBLE
            )

            ELSE NULL

        END AS questions_asked,


       
        -- POLL RESPONSES
       

        CASE

            WHEN CAST(poll_responses AS DOUBLE) >= 0

            THEN CAST(
                poll_responses AS DOUBLE
            )

            ELSE NULL

        END AS poll_responses,


       
        -- DEVICE TYPE
       

        CASE

            WHEN LOWER(TRIM(device_type))
                IN ('desktop', 'mobile', 'tablet')

            THEN LOWER(TRIM(device_type))

            ELSE NULL

        END AS device_type,


       
        -- SOURCE SYSTEM
       

        NULLIF(
            TRIM(source_system),
            ''
        ) AS source_system,


       
        -- DUPLICATE HANDLING
       

        ROW_NUMBER() OVER (

            PARTITION BY event_activity_id

            ORDER BY activity_timestamp DESC

        ) AS rn


    FROM workspace.bronze.event_activity
)


SELECT

    event_activity_id,
    hcp_id,
    event_id,
    campaign_id,
    drug_id,
    event_name,
    event_type,
    event_activity_type,
    activity_timestamp,
    registration_status,
    attendance_status,
    attendance_duration_minutes,
    questions_asked,
    poll_responses,
    device_type,
    source_system

FROM cleaned

WHERE rn = 1

  AND hcp_id IS NOT NULL

  AND event_activity_type IS NOT NULL

  AND activity_timestamp IS NOT NULL;

-- COMMAND ----------


-- 04 - EVENT SILVER
-- CELL 3: STANDARDIZATION VALIDATION




-- 1. ROW COUNT / HCP COUNT / EVENT COUNT


SELECT

    COUNT(*) AS total_rows,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps,

    COUNT(DISTINCT event_activity_id)
        AS unique_event_activities,

    COUNT(DISTINCT event_id)
        AS unique_events

FROM workspace.silver.event_activity;



-- 2. ACTIVITY TYPE DISTRIBUTION


SELECT

    event_activity_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.event_activity

GROUP BY event_activity_type

ORDER BY records DESC;



-- 3. EVENT TYPE DISTRIBUTION


SELECT

    event_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.event_activity

GROUP BY event_type

ORDER BY records DESC;



-- 4. DUPLICATE EVENT ACTIVITY CHECK


SELECT

    COUNT(*) AS duplicate_event_activity_ids

FROM (

    SELECT

        event_activity_id

    FROM workspace.silver.event_activity

    GROUP BY event_activity_id

    HAVING COUNT(*) > 1

);



-- 5. NULL VALIDATION


SELECT

    SUM(
        CASE
            WHEN event_activity_id IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_event_activity_ids,

    SUM(
        CASE
            WHEN hcp_id IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_hcp_ids,

    SUM(
        CASE
            WHEN event_activity_type IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_activity_types,

    SUM(
        CASE
            WHEN activity_timestamp IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_timestamps

FROM workspace.silver.event_activity;



-- 6. NEGATIVE VALUE CHECK


SELECT

    COUNT(*) AS invalid_negative_values

FROM workspace.silver.event_activity

WHERE attendance_duration_minutes < 0

   OR questions_asked < 0

   OR poll_responses < 0;

-- COMMAND ----------


-- 04 - EVENT SILVER
-- CELL 4: EVENT ACTIVITY PROFILING




-- 1. ACTIVITY TYPE DISTRIBUTION


SELECT

    event_activity_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.event_activity

GROUP BY event_activity_type

ORDER BY records DESC;



-- 2. EVENT TYPE DISTRIBUTION


SELECT

    event_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.event_activity

GROUP BY event_type

ORDER BY records DESC;



-- 3. ATTENDANCE STATUS


SELECT

    attendance_status,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.event_activity

GROUP BY attendance_status

ORDER BY records DESC;



-- 4. EVENT ACTIVITY DATE RANGE


SELECT

    MIN(activity_timestamp)
        AS first_event_activity,

    MAX(activity_timestamp)
        AS last_event_activity

FROM workspace.silver.event_activity;



-- 5. HCP COVERAGE


SELECT

    COUNT(DISTINCT hcp_id)
        AS event_active_hcps

FROM workspace.silver.event_activity;



-- 6. ATTENDANCE WITHOUT REGISTRATION


SELECT

    COUNT(*) AS attendance_without_registration

FROM workspace.silver.event_activity a

WHERE a.event_activity_type = 'attendance'

  AND NOT EXISTS (

      SELECT 1

      FROM workspace.silver.event_activity r

      WHERE r.hcp_id = a.hcp_id

        AND r.event_id = a.event_id

        AND r.event_activity_type = 'registration'

  );

-- COMMAND ----------


-- 04 - EVENT SILVER
-- CELL 5: HCP-LEVEL EVENT FEATURES


CREATE OR REPLACE TABLE workspace.silver.event_features AS

SELECT

    hcp_id,


   
    -- TOTAL EVENT ACTIVITY
   

    COUNT(*) AS total_event_activities,


   
    -- REGISTRATIONS
   

    SUM(

        CASE
            WHEN event_activity_type = 'registration'
            THEN 1
            ELSE 0
        END

    ) AS event_registrations,


   
    -- ATTENDANCE
   

    SUM(

        CASE
            WHEN event_activity_type = 'attendance'
            THEN 1
            ELSE 0
        END

    ) AS event_attendance,


   
    -- ATTENDANCE RATE
    --
    -- Attendance / Registrations
   

    COALESCE(

        ROUND(

            SUM(

                CASE
                    WHEN event_activity_type = 'attendance'
                    THEN 1
                    ELSE 0
                END

            ) * 1.0

            /

            NULLIF(

                SUM(

                    CASE
                        WHEN event_activity_type = 'registration'
                        THEN 1
                        ELSE 0
                    END

                ),

                0

            ),

            4

        ),

        0

    ) AS event_attendance_rate,


   
    -- AVERAGE ATTENDANCE DURATION
   

    COALESCE(

        ROUND(

            AVG(

                CASE

                    WHEN event_activity_type = 'attendance'

                    THEN attendance_duration_minutes

                END

            ),

            2

        ),

        0

    ) AS avg_event_attendance_duration,


   
    -- MAX ATTENDANCE DURATION
   

    COALESCE(

        MAX(

            CASE

                WHEN event_activity_type = 'attendance'

                THEN attendance_duration_minutes

            END

        ),

        0

    ) AS max_event_attendance_duration,


   
    -- TOTAL QUESTIONS ASKED
   

    COALESCE(

        SUM(

            CASE

                WHEN event_activity_type = 'attendance'

                THEN questions_asked

                ELSE 0

            END

        ),

        0

    ) AS event_questions,


   
    -- TOTAL POLL RESPONSES
   

    COALESCE(

        SUM(

            CASE

                WHEN event_activity_type = 'attendance'

                THEN poll_responses

                ELSE 0

            END

        ),

        0

    ) AS event_polls,


   
    -- LAST EVENT ACTIVITY
   

    MAX(activity_timestamp)

        AS last_event_activity,


   
    -- LAST EVENT ENGAGEMENT
    --
    -- Attendance is treated as meaningful engagement.
   

    MAX(

        CASE

            WHEN event_activity_type = 'attendance'

            THEN activity_timestamp

        END

    ) AS last_event_engagement,


   
    -- DAYS SINCE LAST EVENT ENGAGEMENT
   

    DATEDIFF(

        DATE('2026-08-16'),

        CAST(

            MAX(

                CASE

                    WHEN event_activity_type = 'attendance'

                    THEN activity_timestamp

                END

            )

            AS DATE

        )

    ) AS days_since_last_event_engagement,


   
    -- DAYS SINCE LAST EVENT ACTIVITY
   

    DATEDIFF(

        DATE('2026-08-16'),

        CAST(

            MAX(activity_timestamp)

            AS DATE

        )

    ) AS days_since_last_event_activity


FROM workspace.silver.event_activity

GROUP BY hcp_id;

-- COMMAND ----------


-- 04 - EVENT SILVER
-- CELL 6: HCP COUNT VALIDATION




-- 1. TOTAL HCP RECORDS


SELECT

    COUNT(*) AS total_hcp_records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.event_features;



-- 2. DUPLICATE HCP CHECK


SELECT

    hcp_id,

    COUNT(*) AS records

FROM workspace.silver.event_features

GROUP BY hcp_id

HAVING COUNT(*) > 1;



-- 3. COMPARE AGAINST HCP MASTER


SELECT

    COUNT(DISTINCT h.hcp_id)
        AS total_hcps,

    COUNT(DISTINCT e.hcp_id)
        AS event_active_hcps

FROM workspace.bronze.hcp_master h

LEFT JOIN workspace.silver.event_features e

    ON h.hcp_id = e.hcp_id;

-- COMMAND ----------


-- 04 - EVENT SILVER
-- CELL 7: FEATURE VALIDATION




-- 1. SAMPLE FEATURES


SELECT

    hcp_id,

    total_event_activities,

    event_registrations,

    event_attendance,

    event_attendance_rate,

    avg_event_attendance_duration,

    max_event_attendance_duration,

    event_questions,

    event_polls,

    last_event_activity,

    last_event_engagement,

    days_since_last_event_engagement,

    days_since_last_event_activity

FROM workspace.silver.event_features

ORDER BY hcp_id

LIMIT 10;



-- 2. ATTENDANCE RATE RANGE


SELECT

    MIN(event_attendance_rate)
        AS min_attendance_rate,

    MAX(event_attendance_rate)
        AS max_attendance_rate,

    ROUND(

        AVG(event_attendance_rate),

        4

    ) AS avg_attendance_rate

FROM workspace.silver.event_features;



-- 3. ATTENDANCE DURATION RANGE


SELECT

    MIN(avg_event_attendance_duration)
        AS min_avg_duration,

    MAX(avg_event_attendance_duration)
        AS max_avg_duration,

    ROUND(

        AVG(avg_event_attendance_duration),

        2

    ) AS overall_avg_duration

FROM workspace.silver.event_features;



-- 4. INVALID NEGATIVE VALUES


SELECT

    COUNT(*) AS invalid_event_records

FROM workspace.silver.event_features

WHERE total_event_activities < 0

   OR event_registrations < 0

   OR event_attendance < 0

   OR event_attendance_rate < 0

   OR avg_event_attendance_duration < 0

   OR max_event_attendance_duration < 0

   OR event_questions < 0

   OR event_polls < 0;



-- 5. ATTENDANCE RATE LOGIC VALIDATION


SELECT

    hcp_id,

    event_registrations,

    event_attendance,

    event_attendance_rate,

    ROUND(

        event_attendance * 1.0

        /

        NULLIF(
            event_registrations,
            0
        ),

        4

    ) AS calculated_attendance_rate

FROM workspace.silver.event_features

ORDER BY hcp_id

LIMIT 10;



-- 6. ATTENDANCE CANNOT EXCEED REGISTRATIONS


SELECT

    COUNT(*) AS invalid_attendance_records

FROM workspace.silver.event_features

WHERE event_attendance > event_registrations;