-- Databricks notebook source
-- MAGIC %md
-- MAGIC 05 - HCP Feature Unification

-- COMMAND ----------


-- CELL 1: FEATURE TABLE VALIDATION


-- EMAIL
SELECT
    'EMAIL' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.email_features;


-- WEB
SELECT
    'WEB' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.web_features;


-- VEEVA
SELECT
    'VEEVA' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.veeva_features;


-- EVENT
SELECT
    'EVENT' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.event_features;

-- COMMAND ----------


-- CELL 1: FEATURE TABLE VALIDATION

-- EMAIL
SELECT
    'EMAIL' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.email_features;


-- WEB
SELECT
    'WEB' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.web_features;


-- VEEVA
SELECT
    'VEEVA' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.veeva_features;


-- EVENT
SELECT
    'EVENT' AS channel,
    COUNT(*) AS hcp_records,
    COUNT(DISTINCT hcp_id) AS unique_hcps
FROM workspace.silver.event_features;

-- COMMAND ----------


-- 05 - UNIFIED FEATURE LAYER
-- CELL 3: UNIFIED TABLE VALIDATION




-- 1. ROW COUNT / HCP COUNT


SELECT

    COUNT(*) AS total_hcp_records,

    COUNT(DISTINCT hcp_id) AS unique_hcps

FROM workspace.silver.hcp_features_raw;



-- 2. DUPLICATE HCP CHECK


SELECT

    hcp_id,
    COUNT(*) AS records

FROM workspace.silver.hcp_features_raw

GROUP BY hcp_id

HAVING COUNT(*) > 1;



-- 3. CHANNEL COVERAGE


SELECT

    COUNT(*) AS total_hcps,

    SUM(
        CASE
            WHEN emails_delivered IS NOT NULL
            THEN 1
            ELSE 0
        END
    ) AS email_hcps,

    SUM(
        CASE
            WHEN total_web_events IS NOT NULL
            THEN 1
            ELSE 0
        END
    ) AS web_hcps,

    SUM(
        CASE
            WHEN total_veeva_interactions IS NOT NULL
            THEN 1
            ELSE 0
        END
    ) AS veeva_hcps,

    SUM(
        CASE
            WHEN total_event_activities IS NOT NULL
            THEN 1
            ELSE 0
        END
    ) AS event_hcps

FROM workspace.silver.hcp_features_raw;



-- 4. SAMPLE RECORDS


SELECT *

FROM workspace.silver.hcp_features_raw

ORDER BY hcp_id

LIMIT 10;

-- COMMAND ----------


-- 05 - UNIFIED FEATURE LAYER
-- CELL 4: MISSING VALUE HANDLING


CREATE OR REPLACE TABLE workspace.silver.hcp_features_complete AS

SELECT

    hcp_id,


    
    -- EMAIL
    

    COALESCE(emails_delivered, 0)
        AS emails_delivered,

    COALESCE(emails_bounced, 0)
        AS emails_bounced,

    COALESCE(email_opens, 0)
        AS email_opens,

    COALESCE(email_clicks, 0)
        AS email_clicks,

    COALESCE(email_open_rate, 0)
        AS email_open_rate,

    COALESCE(email_click_rate, 0)
        AS email_click_rate,

    COALESCE(email_ctor, 0)
        AS email_ctor,

    last_email_activity,
    last_email_engagement,

    COALESCE(
        days_since_last_email_engagement,
        227
    ) AS days_since_last_email_engagement,

    COALESCE(
        days_since_last_email_activity,
        227
    ) AS days_since_last_email_activity,


    
    -- WEB
    

    COALESCE(total_web_events, 0)
        AS total_web_events,

    COALESCE(page_views, 0)
        AS page_views,

    COALESCE(content_views, 0)
        AS content_views,

    COALESCE(downloads, 0)
        AS downloads,

    COALESCE(download_rate, 0)
        AS download_rate,

    COALESCE(video_starts, 0)
        AS video_starts,

    COALESCE(video_completions, 0)
        AS video_completions,

    COALESCE(video_completion_rate, 0)
        AS video_completion_rate,

    COALESCE(sessions, 0)
        AS sessions,

    COALESCE(avg_session_duration, 0)
        AS avg_session_duration,

    last_web_activity,
    last_web_engagement,

    COALESCE(
        days_since_last_web_engagement,
        227
    ) AS days_since_last_web_engagement,

    COALESCE(
        days_since_last_web_activity,
        227
    ) AS days_since_last_web_activity,


    
    -- VEEVA
    

    COALESCE(total_veeva_interactions, 0)
        AS total_veeva_interactions,

    COALESCE(in_person_visits, 0)
        AS in_person_visits,

    COALESCE(phone_calls, 0)
        AS phone_calls,

    COALESCE(virtual_meetings, 0)
        AS virtual_meetings,

    COALESCE(completed_interactions, 0)
        AS completed_interactions,

    COALESCE(cancelled_interactions, 0)
        AS cancelled_interactions,

    COALESCE(no_show_interactions, 0)
        AS no_show_interactions,

    COALESCE(
        avg_interaction_duration_minutes,
        0
    ) AS avg_interaction_duration_minutes,

    COALESCE(
        max_interaction_duration_minutes,
        0
    ) AS max_interaction_duration_minutes,

    COALESCE(followups_required, 0)
        AS followups_required,

    last_veeva_activity,
    last_veeva_engagement,

    COALESCE(
        days_since_last_veeva_engagement,
        227
    ) AS days_since_last_veeva_engagement,

    COALESCE(
        days_since_last_veeva_activity,
        227
    ) AS days_since_last_veeva_activity,


    
    -- EVENT
    

    COALESCE(total_event_activities, 0)
        AS total_event_activities,

    COALESCE(event_registrations, 0)
        AS event_registrations,

    COALESCE(event_attendance, 0)
        AS event_attendance,

    COALESCE(event_attendance_rate, 0)
        AS event_attendance_rate,

    COALESCE(
        avg_event_attendance_duration,
        0
    ) AS avg_event_attendance_duration,

    COALESCE(
        max_event_attendance_duration,
        0
    ) AS max_event_attendance_duration,

    COALESCE(event_questions, 0)
        AS event_questions,

    COALESCE(event_polls, 0)
        AS event_polls,

    last_event_activity,
    last_event_engagement,

    COALESCE(
        days_since_last_event_engagement,
        227
    ) AS days_since_last_event_engagement,

    COALESCE(
        days_since_last_event_activity,
        227
    ) AS days_since_last_event_activity


FROM workspace.silver.hcp_features_raw;

-- COMMAND ----------


-- CELL 4 VALIDATION


SELECT

    COUNT(*) AS total_hcps,

    SUM(
        CASE
            WHEN emails_delivered IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_email_features,

    SUM(
        CASE
            WHEN content_views IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_web_features,

    SUM(
        CASE
            WHEN total_veeva_interactions IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_veeva_features,

    SUM(
        CASE
            WHEN total_event_activities IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_event_features,

    SUM(
        CASE
            WHEN days_since_last_email_engagement IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_email_recency,

    SUM(
        CASE
            WHEN days_since_last_web_engagement IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_web_recency,

    SUM(
        CASE
            WHEN days_since_last_veeva_engagement IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_veeva_recency,

    SUM(
        CASE
            WHEN days_since_last_event_engagement IS NULL
            THEN 1 ELSE 0
        END
    ) AS null_event_recency

FROM workspace.silver.hcp_features_complete;

-- COMMAND ----------


-- 05 - UNIFIED FEATURE LAYER
-- CELL 5: FEATURE NORMALIZATION


CREATE OR REPLACE TABLE workspace.silver.hcp_features_normalized AS

WITH stats AS (

    SELECT

        
        -- EMAIL
        

        MIN(emails_delivered) AS min_email_delivered,
        MAX(emails_delivered) AS max_email_delivered,

        MIN(email_open_rate) AS min_email_open_rate,
        MAX(email_open_rate) AS max_email_open_rate,

        MIN(email_click_rate) AS min_email_click_rate,
        MAX(email_click_rate) AS max_email_click_rate,

        MIN(email_ctor) AS min_email_ctor,
        MAX(email_ctor) AS max_email_ctor,

        MIN(days_since_last_email_engagement)
            AS min_email_recency,

        MAX(days_since_last_email_engagement)
            AS max_email_recency,


        
        -- WEB
        

        MIN(content_views)
            AS min_web_content_views,

        MAX(content_views)
            AS max_web_content_views,

        MIN(download_rate)
            AS min_web_download_rate,

        MAX(download_rate)
            AS max_web_download_rate,

        MIN(video_completion_rate)
            AS min_video_completion_rate,

        MAX(video_completion_rate)
            AS max_video_completion_rate,

        MIN(avg_session_duration)
            AS min_avg_session_duration,

        MAX(avg_session_duration)
            AS max_avg_session_duration,

        MIN(days_since_last_web_engagement)
            AS min_web_recency,

        MAX(days_since_last_web_engagement)
            AS max_web_recency,


        
        -- VEEVA
        

        MIN(completed_interactions)
            AS min_completed_interactions,

        MAX(completed_interactions)
            AS max_completed_interactions,

        MIN(
            completed_interactions * 1.0
            /
            NULLIF(total_veeva_interactions, 0)
        ) AS min_veeva_completion_rate,

        MAX(
            completed_interactions * 1.0
            /
            NULLIF(total_veeva_interactions, 0)
        ) AS max_veeva_completion_rate,

        MIN(avg_interaction_duration_minutes)
            AS min_veeva_duration,

        MAX(avg_interaction_duration_minutes)
            AS max_veeva_duration,

        MIN(days_since_last_veeva_engagement)
            AS min_veeva_recency,

        MAX(days_since_last_veeva_engagement)
            AS max_veeva_recency,


        
        -- EVENT
        

        MIN(event_attendance)
            AS min_event_attendance,

        MAX(event_attendance)
            AS max_event_attendance,

        MIN(event_attendance_rate)
            AS min_event_attendance_rate,

        MAX(event_attendance_rate)
            AS max_event_attendance_rate,

        MIN(avg_event_attendance_duration)
            AS min_event_duration,

        MAX(avg_event_attendance_duration)
            AS max_event_duration,

        MIN(event_questions)
            AS min_event_questions,

        MAX(event_questions)
            AS max_event_questions,

        MIN(event_polls)
            AS min_event_polls,

        MAX(event_polls)
            AS max_event_polls,

        MIN(days_since_last_event_engagement)
            AS min_event_recency,

        MAX(days_since_last_event_engagement)
            AS max_event_recency

    FROM workspace.silver.hcp_features_complete
)


SELECT

    f.hcp_id,


    ====
    -- EMAIL
    ====

    CASE
        WHEN s.max_email_delivered =
             s.min_email_delivered
        THEN 0

        ELSE
            (
                f.emails_delivered
                - s.min_email_delivered
            ) * 1.0
            /
            (
                s.max_email_delivered
                - s.min_email_delivered
            )
    END AS norm_email_delivered,


    CASE
        WHEN s.max_email_open_rate =
             s.min_email_open_rate
        THEN 0

        ELSE
            (
                f.email_open_rate
                - s.min_email_open_rate
            ) * 1.0
            /
            (
                s.max_email_open_rate
                - s.min_email_open_rate
            )
    END AS norm_email_open_rate,


    CASE
        WHEN s.max_email_click_rate =
             s.min_email_click_rate
        THEN 0

        ELSE
            (
                f.email_click_rate
                - s.min_email_click_rate
            ) * 1.0
            /
            (
                s.max_email_click_rate
                - s.min_email_click_rate
            )
    END AS norm_email_click_rate,


    CASE
        WHEN s.max_email_ctor =
             s.min_email_ctor
        THEN 0

        ELSE
            (
                f.email_ctor
                - s.min_email_ctor
            ) * 1.0
            /
            (
                s.max_email_ctor
                - s.min_email_ctor
            )
    END AS norm_email_ctor,


    -- RECENCY: fewer days = higher score

    CASE
        WHEN s.max_email_recency =
             s.min_email_recency
        THEN 0

        ELSE
            1 -

            (
                f.days_since_last_email_engagement
                - s.min_email_recency
            ) * 1.0
            /
            (
                s.max_email_recency
                - s.min_email_recency
            )
    END AS norm_email_recency,


    ====
    -- WEB
    ====

    CASE
        WHEN s.max_web_content_views =
             s.min_web_content_views
        THEN 0

        ELSE
            (
                f.content_views
                - s.min_web_content_views
            ) * 1.0
            /
            (
                s.max_web_content_views
                - s.min_web_content_views
            )
    END AS norm_web_content_views,


    -- DOWNLOAD RATE

    CASE
        WHEN s.max_web_download_rate =
             s.min_web_download_rate
        THEN 0

        ELSE
            (
                f.download_rate
                - s.min_web_download_rate
            ) * 1.0
            /
            (
                s.max_web_download_rate
                - s.min_web_download_rate
            )
    END AS norm_web_download_rate,


    CASE
        WHEN s.max_video_completion_rate =
             s.min_video_completion_rate
        THEN 0

        ELSE
            (
                f.video_completion_rate
                - s.min_video_completion_rate
            ) * 1.0
            /
            (
                s.max_video_completion_rate
                - s.min_video_completion_rate
            )
    END AS norm_video_completion_rate,


    CASE
        WHEN s.max_avg_session_duration =
             s.min_avg_session_duration
        THEN 0

        ELSE
            (
                f.avg_session_duration
                - s.min_avg_session_duration
            ) * 1.0
            /
            (
                s.max_avg_session_duration
                - s.min_avg_session_duration
            )
    END AS norm_avg_session_duration,


    -- RECENCY: fewer days = higher score

    CASE
        WHEN s.max_web_recency =
             s.min_web_recency
        THEN 0

        ELSE
            1 -

            (
                f.days_since_last_web_engagement
                - s.min_web_recency
            ) * 1.0
            /
            (
                s.max_web_recency
                - s.min_web_recency
            )
    END AS norm_web_recency,


    ====
    -- VEEVA
    ====

    CASE
        WHEN s.max_completed_interactions =
             s.min_completed_interactions
        THEN 0

        ELSE
            (
                f.completed_interactions
                - s.min_completed_interactions
            ) * 1.0
            /
            (
                s.max_completed_interactions
                - s.min_completed_interactions
            )
    END AS norm_completed_interactions,


    CASE
        WHEN s.max_veeva_completion_rate =
             s.min_veeva_completion_rate
        THEN 0

        ELSE
            (
                (
                    f.completed_interactions * 1.0
                    /
                    NULLIF(
                        f.total_veeva_interactions,
                        0
                    )
                )
                - s.min_veeva_completion_rate
            ) * 1.0
            /
            (
                s.max_veeva_completion_rate
                - s.min_veeva_completion_rate
            )
    END AS norm_veeva_completion_rate,


    CASE
        WHEN s.max_veeva_duration =
             s.min_veeva_duration
        THEN 0

        ELSE
            (
                f.avg_interaction_duration_minutes
                - s.min_veeva_duration
            ) * 1.0
            /
            (
                s.max_veeva_duration
                - s.min_veeva_duration
            )
    END AS norm_veeva_duration,


    -- RECENCY: fewer days = higher score

    CASE
        WHEN s.max_veeva_recency =
             s.min_veeva_recency
        THEN 0

        ELSE
            1 -

            (
                f.days_since_last_veeva_engagement
                - s.min_veeva_recency
            ) * 1.0
            /
            (
                s.max_veeva_recency
                - s.min_veeva_recency
            )
    END AS norm_veeva_recency,


    ====
    -- EVENT
    ====

    CASE
        WHEN s.max_event_attendance =
             s.min_event_attendance
        THEN 0

        ELSE
            (
                f.event_attendance
                - s.min_event_attendance
            ) * 1.0
            /
            (
                s.max_event_attendance
                - s.min_event_attendance
            )
    END AS norm_event_attendance,


    CASE
        WHEN s.max_event_attendance_rate =
             s.min_event_attendance_rate
        THEN 0

        ELSE
            (
                f.event_attendance_rate
                - s.min_event_attendance_rate
            ) * 1.0
            /
            (
                s.max_event_attendance_rate
                - s.min_event_attendance_rate
            )
    END AS norm_event_attendance_rate,


    CASE
        WHEN s.max_event_duration =
             s.min_event_duration
        THEN 0

        ELSE
            (
                f.avg_event_attendance_duration
                - s.min_event_duration
            ) * 1.0
            /
            (
                s.max_event_duration
                - s.min_event_duration
            )
    END AS norm_event_duration,


    CASE
        WHEN s.max_event_questions =
             s.min_event_questions
        THEN 0

        ELSE
            (
                f.event_questions
                - s.min_event_questions
            ) * 1.0
            /
            (
                s.max_event_questions
                - s.min_event_questions
            )
    END AS norm_event_questions,


    CASE
        WHEN s.max_event_polls =
             s.min_event_polls
        THEN 0

        ELSE
            (
                f.event_polls
                - s.min_event_polls
            ) * 1.0
            /
            (
                s.max_event_polls
                - s.min_event_polls
            )
    END AS norm_event_polls,


    -- RECENCY: fewer days = higher score

    CASE
        WHEN s.max_event_recency =
             s.min_event_recency
        THEN 0

        ELSE
            1 -

            (
                f.days_since_last_event_engagement
                - s.min_event_recency
            ) * 1.0
            /
            (
                s.max_event_recency
                - s.min_event_recency
            )
    END AS norm_event_recency


FROM workspace.silver.hcp_features_complete f

CROSS JOIN stats s;

-- COMMAND ----------


-- 05 - UNIFIED FEATURE LAYER
-- CELL 6: NORMALIZATION VALIDATION


SELECT

   
    -- EMAIL
   

    MIN(norm_email_delivered) AS min_email_delivered,
    MAX(norm_email_delivered) AS max_email_delivered,

    MIN(norm_email_open_rate) AS min_email_open_rate,
    MAX(norm_email_open_rate) AS max_email_open_rate,

    MIN(norm_email_click_rate) AS min_email_click_rate,
    MAX(norm_email_click_rate) AS max_email_click_rate,

    MIN(norm_email_ctor) AS min_email_ctor,
    MAX(norm_email_ctor) AS max_email_ctor,

    MIN(norm_email_recency) AS min_email_recency,
    MAX(norm_email_recency) AS max_email_recency,


   
    -- WEB
   

    MIN(norm_web_content_views) AS min_web_content_views,
    MAX(norm_web_content_views) AS max_web_content_views,

    MIN(norm_web_download_rate) AS min_web_download_rate,
    MAX(norm_web_download_rate) AS max_web_download_rate,

    MIN(norm_video_completion_rate)
        AS min_video_completion_rate,

    MAX(norm_video_completion_rate)
        AS max_video_completion_rate,

    MIN(norm_avg_session_duration)
        AS min_avg_session_duration,

    MAX(norm_avg_session_duration)
        AS max_avg_session_duration,

    MIN(norm_web_recency)
        AS min_web_recency,

    MAX(norm_web_recency)
        AS max_web_recency,


   
    -- VEEVA
   

    MIN(norm_completed_interactions)
        AS min_completed_interactions,

    MAX(norm_completed_interactions)
        AS max_completed_interactions,

    MIN(norm_veeva_completion_rate)
        AS min_veeva_completion_rate,

    MAX(norm_veeva_completion_rate)
        AS max_veeva_completion_rate,

    MIN(norm_veeva_duration)
        AS min_veeva_duration,

    MAX(norm_veeva_duration)
        AS max_veeva_duration,

    MIN(norm_veeva_recency)
        AS min_veeva_recency,

    MAX(norm_veeva_recency)
        AS max_veeva_recency,


   
    -- EVENT
   

    MIN(norm_event_attendance)
        AS min_event_attendance,

    MAX(norm_event_attendance)
        AS max_event_attendance,

    MIN(norm_event_attendance_rate)
        AS min_event_attendance_rate,

    MAX(norm_event_attendance_rate)
        AS max_event_attendance_rate,

    MIN(norm_event_duration)
        AS min_event_duration,

    MAX(norm_event_duration)
        AS max_event_duration,

    MIN(norm_event_questions)
        AS min_event_questions,

    MAX(norm_event_questions)
        AS max_event_questions,

    MIN(norm_event_polls)
        AS min_event_polls,

    MAX(norm_event_polls)
        AS max_event_polls,

    MIN(norm_event_recency)
        AS min_event_recency,

    MAX(norm_event_recency)
        AS max_event_recency

FROM workspace.silver.hcp_features_normalized;

-- COMMAND ----------


-- 05 - UNIFIED FEATURE LAYER
-- CELL 7: FINAL UNIFIED FEATURE DATASET


CREATE OR REPLACE TABLE workspace.silver.hcp_features_final AS

SELECT

    n.hcp_id,


    -- EMAIL BUSINESS FEATURES

    c.emails_delivered,
    c.emails_bounced,
    c.email_opens,
    c.email_clicks,
    c.email_open_rate,
    c.email_click_rate,
    c.email_ctor,
    c.days_since_last_email_engagement,


    -- WEB BUSINESS FEATURES

    c.total_web_events,
    c.page_views,
    c.content_views,
    c.downloads,
    c.download_rate,
    c.video_starts,
    c.video_completions,
    c.video_completion_rate,
    c.sessions,
    c.avg_session_duration,
    c.days_since_last_web_engagement,


    -- VEEVA BUSINESS FEATURES

    c.total_veeva_interactions,
    c.in_person_visits,
    c.phone_calls,
    c.virtual_meetings,
    c.completed_interactions,
    c.cancelled_interactions,
    c.no_show_interactions,
    c.avg_interaction_duration_minutes,
    c.max_interaction_duration_minutes,
    c.followups_required,
    c.days_since_last_veeva_engagement,


    -- EVENT BUSINESS FEATURES

    c.total_event_activities,
    c.event_registrations,
    c.event_attendance,
    c.event_attendance_rate,
    c.avg_event_attendance_duration,
    c.max_event_attendance_duration,
    c.event_questions,
    c.event_polls,
    c.days_since_last_event_engagement,


    -- NORMALIZED EMAIL FEATURES

    n.norm_email_delivered,
    n.norm_email_open_rate,
    n.norm_email_click_rate,
    n.norm_email_ctor,
    n.norm_email_recency,


    -- NORMALIZED WEB FEATURES

    n.norm_web_content_views,
    n.norm_web_download_rate,
    n.norm_video_completion_rate,
    n.norm_avg_session_duration,
    n.norm_web_recency,


    -- NORMALIZED VEEVA FEATURES

    n.norm_completed_interactions,
    n.norm_veeva_completion_rate,
    n.norm_veeva_duration,
    n.norm_veeva_recency,


    -- NORMALIZED EVENT FEATURES

    n.norm_event_attendance,
    n.norm_event_attendance_rate,
    n.norm_event_duration,
    n.norm_event_questions,
    n.norm_event_polls,
    n.norm_event_recency


FROM workspace.silver.hcp_features_normalized n

INNER JOIN workspace.silver.hcp_features_complete c

    ON n.hcp_id = c.hcp_id;

-- COMMAND ----------


-- CELL 7: FINAL TABLE VALIDATION


SELECT

    COUNT(*) AS total_rows,

    COUNT(DISTINCT hcp_id) AS unique_hcps

FROM workspace.silver.hcp_features_final;


SELECT *

FROM workspace.silver.hcp_features_final

ORDER BY hcp_id

LIMIT 10;