-- Databricks notebook source
-- MAGIC %md
-- MAGIC 03 - Veeva Silver Layer

-- COMMAND ----------


-- CELL 1: INPUT VALIDATION




-- 1. SAMPLE RAW BRONZE DATA


SELECT *

FROM workspace.bronze.veeva_activity

LIMIT 10;



-- 2. BASIC DATASET STATISTICS


SELECT

    COUNT(*) AS total_rows,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps,

    COUNT(DISTINCT veeva_event_id)
        AS unique_veeva_events,

    COUNT(DISTINCT interaction_id)
        AS unique_interactions

FROM workspace.bronze.veeva_activity;



-- 3. RAW INTERACTION TYPE DISTRIBUTION


SELECT

    interaction_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.bronze.veeva_activity

GROUP BY interaction_type

ORDER BY records DESC;



-- 4. RAW INTERACTION STATUS DISTRIBUTION


SELECT

    interaction_status,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.bronze.veeva_activity

GROUP BY interaction_status

ORDER BY records DESC;

-- COMMAND ----------


-- 03 - VEEVA SILVER
-- CELL 2: BRONZE → SILVER STANDARDIZATION


CREATE OR REPLACE TABLE workspace.silver.veeva_activity AS

WITH cleaned AS (

    SELECT

       
        -- IDENTIFIERS
       

        CAST(veeva_event_id AS STRING)
            AS veeva_event_id,

        TRIM(CAST(hcp_id AS STRING))
            AS hcp_id,

        TRIM(CAST(interaction_id AS STRING))
            AS interaction_id,

        TRIM(CAST(campaign_id AS STRING))
            AS campaign_id,

        TRIM(CAST(drug_id AS STRING))
            AS drug_id,


       
        -- INTERACTION TYPE STANDARDIZATION
       

        CASE

            WHEN LOWER(TRIM(interaction_type))
                = 'in-person visit'

            THEN 'In-Person Visit'


            WHEN LOWER(TRIM(interaction_type))
                = 'phone call'

            THEN 'Phone Call'


            WHEN LOWER(TRIM(interaction_type))
                = 'virtual meeting'

            THEN 'Virtual Meeting'


            ELSE NULL

        END AS interaction_type,


       
        -- TIMESTAMP STANDARDIZATION
       

        CAST(interaction_timestamp AS TIMESTAMP)
            AS interaction_timestamp,


       
        -- INTERACTION DURATION
        --
        -- Negative duration is treated as NULL
       

        CASE

            WHEN CAST(
                interaction_duration_minutes AS DOUBLE
            ) >= 0

            THEN CAST(
                interaction_duration_minutes AS DOUBLE
            )

            ELSE NULL

        END AS interaction_duration_minutes,


       
        -- INTERACTION STATUS STANDARDIZATION
       

        CASE

            WHEN LOWER(TRIM(interaction_status))
                = 'completed'

            THEN 'Completed'


            WHEN LOWER(TRIM(interaction_status))
                = 'cancelled'

            THEN 'Cancelled'


            WHEN LOWER(TRIM(interaction_status))
                = 'no show'

            THEN 'No Show'


            ELSE NULL

        END AS interaction_status,


       
        -- TEXT CLEANING
       

        NULLIF(
            TRIM(interaction_purpose),
            ''
        ) AS interaction_purpose,

        NULLIF(
            TRIM(discussion_topic),
            ''
        ) AS discussion_topic,


       
        -- FOLLOW-UP STANDARDIZATION
       

        CASE

            WHEN LOWER(
                TRIM(
                    CAST(follow_up_required AS STRING)
                )
            ) IN ('true', '1', 'yes')

            THEN TRUE


            WHEN LOWER(
                TRIM(
                    CAST(follow_up_required AS STRING)
                )
            ) IN ('false', '0', 'no')

            THEN FALSE


            ELSE NULL

        END AS follow_up_required,


       
        -- FOLLOW-UP DATE
       

        CAST(follow_up_date AS DATE)
            AS follow_up_date,


       
        -- OTHER ATTRIBUTES
       

        NULLIF(
            TRIM(rep_id),
            ''
        ) AS rep_id,

        NULLIF(
            TRIM(territory),
            ''
        ) AS territory,

        NULLIF(
            TRIM(channel),
            ''
        ) AS channel,

        NULLIF(
            TRIM(source_system),
            ''
        ) AS source_system,


       
        -- DUPLICATE HANDLING
       

        ROW_NUMBER() OVER (

            PARTITION BY veeva_event_id

            ORDER BY interaction_timestamp DESC

        ) AS rn


    FROM workspace.bronze.veeva_activity
)


SELECT

    veeva_event_id,
    hcp_id,
    interaction_id,
    campaign_id,
    drug_id,
    interaction_type,
    interaction_timestamp,
    interaction_duration_minutes,
    interaction_status,
    interaction_purpose,
    discussion_topic,
    follow_up_required,
    follow_up_date,
    rep_id,
    territory,
    channel,
    source_system

FROM cleaned

WHERE rn = 1

  AND hcp_id IS NOT NULL

  AND interaction_type IS NOT NULL

  AND interaction_timestamp IS NOT NULL;

-- COMMAND ----------


-- 03 - VEEVA SILVER
-- CELL 3: STANDARDIZATION VALIDATION




-- 1. ROW COUNT / HCP COUNT / EVENT COUNT


SELECT

    COUNT(*) AS total_rows,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps,

    COUNT(DISTINCT veeva_event_id)
        AS unique_veeva_events,

    COUNT(DISTINCT interaction_id)
        AS unique_interactions

FROM workspace.silver.veeva_activity;



-- 2. INTERACTION TYPE DISTRIBUTION


SELECT

    interaction_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.veeva_activity

GROUP BY interaction_type

ORDER BY records DESC;



-- 3. INTERACTION STATUS DISTRIBUTION


SELECT

    interaction_status,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.veeva_activity

GROUP BY interaction_status

ORDER BY records DESC;



-- 4. DUPLICATE EVENT CHECK


SELECT

    COUNT(*) AS duplicate_veeva_event_ids

FROM (

    SELECT

        veeva_event_id

    FROM workspace.silver.veeva_activity

    GROUP BY veeva_event_id

    HAVING COUNT(*) > 1

);



-- 5. NULL VALIDATION


SELECT

    SUM(
        CASE
            WHEN veeva_event_id IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_veeva_event_ids,

    SUM(
        CASE
            WHEN hcp_id IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_hcp_ids,

    SUM(
        CASE
            WHEN interaction_type IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_interaction_types,

    SUM(
        CASE
            WHEN interaction_timestamp IS NULL
            THEN 1
            ELSE 0
        END
    ) AS null_timestamps

FROM workspace.silver.veeva_activity;



-- 6. NEGATIVE DURATION CHECK


SELECT

    COUNT(*) AS negative_durations

FROM workspace.silver.veeva_activity

WHERE interaction_duration_minutes < 0;

-- COMMAND ----------


-- 03 - VEEVA SILVER
-- CELL 4: VEEVA ACTIVITY PROFILING




-- 1. INTERACTION TYPE DISTRIBUTION


SELECT

    interaction_type,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.veeva_activity

GROUP BY interaction_type

ORDER BY records DESC;



-- 2. INTERACTION STATUS DISTRIBUTION


SELECT

    interaction_status,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.veeva_activity

GROUP BY interaction_status

ORDER BY records DESC;



-- 3. FOLLOW-UP DISTRIBUTION


SELECT

    follow_up_required,

    COUNT(*) AS records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.veeva_activity

GROUP BY follow_up_required

ORDER BY records DESC;



-- 4. ACTIVITY DATE RANGE


SELECT

    MIN(interaction_timestamp)
        AS first_veeva_activity,

    MAX(interaction_timestamp)
        AS last_veeva_activity

FROM workspace.silver.veeva_activity;



-- 5. HCP COVERAGE


SELECT

    COUNT(DISTINCT hcp_id)
        AS veeva_active_hcps

FROM workspace.silver.veeva_activity;



-- 6. COMPLETION RATE CHECK


SELECT

    COUNT(*) AS total_interactions,

    SUM(
        CASE
            WHEN interaction_status = 'Completed'
            THEN 1
            ELSE 0
        END
    ) AS completed_interactions,

    ROUND(

        SUM(
            CASE
                WHEN interaction_status = 'Completed'
                THEN 1
                ELSE 0
            END
        ) * 1.0

        /

        NULLIF(COUNT(*), 0),

        4

    ) AS overall_completion_rate

FROM workspace.silver.veeva_activity;

-- COMMAND ----------


-- 03 - VEEVA SILVER
-- CELL 5: HCP-LEVEL VEEVA FEATURES


CREATE OR REPLACE TABLE workspace.silver.veeva_features AS

SELECT

    hcp_id,


   
    -- TOTAL INTERACTIONS
   

    COUNT(*) AS total_veeva_interactions,


   
    -- INTERACTION TYPE COUNTS
   

    SUM(

        CASE
            WHEN interaction_type = 'In-Person Visit'
            THEN 1
            ELSE 0
        END

    ) AS in_person_visits,


    SUM(

        CASE
            WHEN interaction_type = 'Phone Call'
            THEN 1
            ELSE 0
        END

    ) AS phone_calls,


    SUM(

        CASE
            WHEN interaction_type = 'Virtual Meeting'
            THEN 1
            ELSE 0
        END

    ) AS virtual_meetings,


   
    -- INTERACTION STATUS
   

    SUM(

        CASE
            WHEN interaction_status = 'Completed'
            THEN 1
            ELSE 0
        END

    ) AS completed_interactions,


    SUM(

        CASE
            WHEN interaction_status = 'Cancelled'
            THEN 1
            ELSE 0
        END

    ) AS cancelled_interactions,


    SUM(

        CASE
            WHEN interaction_status = 'No Show'
            THEN 1
            ELSE 0
        END

    ) AS no_show_interactions,


   
    -- AVERAGE DURATION
   

    ROUND(

        AVG(interaction_duration_minutes),

        2

    ) AS avg_interaction_duration_minutes,


   
    -- MAXIMUM DURATION
   

    MAX(interaction_duration_minutes)

        AS max_interaction_duration_minutes,


   
    -- FOLLOW-UPS
   

    SUM(

        CASE
            WHEN follow_up_required = TRUE
            THEN 1
            ELSE 0
        END

    ) AS followups_required,


   
    -- LAST ACTIVITY
   

    MAX(interaction_timestamp)
        AS last_veeva_activity,


   
    -- LAST ENGAGEMENT
    --
    -- Completed interactions are treated as meaningful
    -- engagement.
   

    MAX(

        CASE

            WHEN interaction_status = 'Completed'

            THEN interaction_timestamp

        END

    ) AS last_veeva_engagement,


   
    -- DAYS SINCE LAST VEEVA ENGAGEMENT
   

    DATEDIFF(

        DATE('2026-08-16'),

        CAST(

            MAX(

                CASE

                    WHEN interaction_status = 'Completed'

                    THEN interaction_timestamp

                END

            )

            AS DATE

        )

    ) AS days_since_last_veeva_engagement,


   
    -- DAYS SINCE LAST VEEVA ACTIVITY
   

    DATEDIFF(

        DATE('2026-08-16'),

        CAST(

            MAX(interaction_timestamp)

            AS DATE

        )

    ) AS days_since_last_veeva_activity


FROM workspace.silver.veeva_activity

GROUP BY hcp_id;

-- COMMAND ----------


-- 03 - VEEVA SILVER
-- CELL 6: HCP COUNT VALIDATION




-- 1. TOTAL HCP RECORDS


SELECT

    COUNT(*) AS total_hcp_records,

    COUNT(DISTINCT hcp_id)
        AS unique_hcps

FROM workspace.silver.veeva_features;



-- 2. DUPLICATE HCP CHECK


SELECT

    hcp_id,

    COUNT(*) AS records

FROM workspace.silver.veeva_features

GROUP BY hcp_id

HAVING COUNT(*) > 1;



-- 3. COMPARE AGAINST HCP MASTER


SELECT

    COUNT(DISTINCT h.hcp_id)
        AS total_hcps,

    COUNT(DISTINCT v.hcp_id)
        AS veeva_active_hcps

FROM workspace.bronze.hcp_master h

LEFT JOIN workspace.silver.veeva_features v

    ON h.hcp_id = v.hcp_id;

-- COMMAND ----------


-- 03 - VEEVA SILVER
-- CELL 7: FEATURE VALIDATION




-- 1. SAMPLE FEATURES


SELECT

    hcp_id,

    total_veeva_interactions,

    in_person_visits,
    phone_calls,
    virtual_meetings,

    completed_interactions,
    cancelled_interactions,
    no_show_interactions,

    avg_interaction_duration_minutes,
    max_interaction_duration_minutes,

    followups_required,

    last_veeva_activity,
    last_veeva_engagement,

    days_since_last_veeva_engagement,
    days_since_last_veeva_activity

FROM workspace.silver.veeva_features

ORDER BY hcp_id

LIMIT 10;



-- 2. INTERACTION DURATION RANGE


SELECT

    MIN(avg_interaction_duration_minutes)
        AS min_avg_duration,

    MAX(avg_interaction_duration_minutes)
        AS max_avg_duration,

    ROUND(
        AVG(avg_interaction_duration_minutes),
        2
    ) AS overall_avg_duration

FROM workspace.silver.veeva_features;



-- 3. COMPLETION RATE


SELECT

    hcp_id,

    total_veeva_interactions,

    completed_interactions,

    ROUND(

        completed_interactions * 1.0

        /

        NULLIF(
            total_veeva_interactions,
            0
        ),

        4

    ) AS veeva_completion_rate

FROM workspace.silver.veeva_features

ORDER BY hcp_id

LIMIT 10;



-- 4. NEGATIVE VALUE CHECK


SELECT

    COUNT(*) AS invalid_veeva_records

FROM workspace.silver.veeva_features

WHERE total_veeva_interactions < 0

   OR in_person_visits < 0

   OR phone_calls < 0

   OR virtual_meetings < 0

   OR completed_interactions < 0

   OR cancelled_interactions < 0

   OR no_show_interactions < 0

   OR avg_interaction_duration_minutes < 0

   OR followups_required < 0;



-- 5. INTERACTION COUNT CONSISTENCY


SELECT

    hcp_id,

    total_veeva_interactions,

    (
        in_person_visits
        + phone_calls
        + virtual_meetings
    ) AS calculated_total_interactions

FROM workspace.silver.veeva_features

WHERE total_veeva_interactions != (

    in_person_visits
    + phone_calls
    + virtual_meetings

)

ORDER BY hcp_id;