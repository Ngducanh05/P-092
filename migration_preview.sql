BEGIN;

-- Running upgrade f6a7b8c9d0e1 -> a7b8c9d0e1f2

DO $$
        DECLARE
            nonempty_count integer;
            multi_binding_count integer;
        BEGIN
            SELECT count(*) INTO nonempty_count
            FROM (SELECT 'tickets' AS table_name, count(*)::bigint AS row_count FROM public.tickets UNION ALL SELECT 'ticket_attachments' AS table_name, count(*)::bigint AS row_count FROM public.ticket_attachments UNION ALL SELECT 'ticket_attachment_upload_sessions' AS table_name, count(*)::bigint AS row_count FROM public.ticket_attachment_upload_sessions UNION ALL SELECT 'ai_analysis_runs' AS table_name, count(*)::bigint AS row_count FROM public.ai_analysis_runs UNION ALL SELECT 'ticket_scoring_results' AS table_name, count(*)::bigint AS row_count FROM public.ticket_scoring_results UNION ALL SELECT 'ticket_status_history' AS table_name, count(*)::bigint AS row_count FROM public.ticket_status_history UNION ALL SELECT 'notifications' AS table_name, count(*)::bigint AS row_count FROM public.notifications UNION ALL SELECT 'audit_logs' AS table_name, count(*)::bigint AS row_count FROM public.audit_logs UNION ALL SELECT 'ticket_assignments' AS table_name, count(*)::bigint AS row_count FROM public.ticket_assignments UNION ALL SELECT 'technician_skills' AS table_name, count(*)::bigint AS row_count FROM public.technician_skills UNION ALL SELECT 'technician_profiles' AS table_name, count(*)::bigint AS row_count FROM public.technician_profiles) counts
            WHERE row_count > 0;

            SELECT count(*) INTO multi_binding_count
            FROM (
                SELECT resident_id
                FROM public.resident_unit_memberships
                WHERE is_active = true
                GROUP BY resident_id
                HAVING count(*) > 1
            ) conflicts;

            IF nonempty_count > 0 OR multi_binding_count > 0 THEN
                RAISE EXCEPTION
                    'SELF_DEV_V2_CUTOVER_REQUIRES_MANUAL_DATA_MIGRATION: nonempty_operational_tables=%, multi_unit_residents=%',
                    nonempty_count, multi_binding_count;
            END IF;
        END $$;;

DO $$
        DECLARE p record;
        BEGIN
            FOR p IN
                SELECT schemaname, tablename, policyname
                FROM pg_policies
                WHERE schemaname='public'
            LOOP
                EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', p.policyname, p.schemaname, p.tablename);
            END LOOP;
        END $$;
        DROP VIEW IF EXISTS public.technician_ticket_view;
        DROP VIEW IF EXISTS public.resident_ticket_view;;

CREATE TYPE user_role_enum AS ENUM ('RESIDENT', 'COORDINATOR');

CREATE TYPE ticket_status_v2_enum AS ENUM ('NEW', 'WAITING_RESIDENT_INFO', 'APPROVED', 'IN_PROGRESS', 'COMPLETED', 'UNRESOLVABLE', 'CANCELLED');

CREATE TYPE classification_status_enum AS ENUM ('PENDING', 'PROCESSING', 'RESOLVED', 'MANUAL_REVIEW', 'FAILED');

CREATE TYPE severity_v2_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH');

CREATE TYPE attachment_type_enum AS ENUM ('ISSUE_ORIGINAL', 'RESIDENT_SUPPLEMENT');

CREATE TYPE image_quality_status_enum AS ENUM ('PENDING', 'READABLE', 'UNREADABLE');

CREATE TYPE analysis_run_status_enum AS ENUM ('RUNNING', 'SUCCEEDED', 'FAILED');

CREATE TYPE severity_source_enum AS ENUM ('VISION', 'TEXT_FALLBACK');

CREATE TYPE priority_level_enum AS ENUM ('P1', 'P2', 'P3');

CREATE TYPE information_request_status_enum AS ENUM ('OPEN', 'RESPONDED', 'CLOSED');

CREATE TYPE notification_channel_enum AS ENUM ('PUSH', 'SMS', 'IN_APP');

CREATE TYPE notification_status_enum AS ENUM ('PENDING', 'SENT', 'FAILED', 'READ');

CREATE TABLE user_profiles (
    user_id UUID NOT NULL, 
    phone_e164 VARCHAR(20), 
    full_name VARCHAR(150), 
    role user_role_enum NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (user_id), 
    CONSTRAINT ck_user_profiles_phone_e164 CHECK (phone_e164 IS NULL OR phone_e164 ~ '^\+[1-9][0-9]{6,14}$')
);

CREATE UNIQUE INDEX ix_user_profiles_phone_e164 ON user_profiles (phone_e164);

CREATE INDEX ix_user_profiles_role_active ON user_profiles (role, is_active);

INSERT INTO public.user_profiles (user_id, phone_e164, full_name, role, is_active, created_at, updated_at)
        SELECT id, phone_number, full_name, 'RESIDENT'::user_role_enum, is_active, created_at, updated_at
        FROM public.residents;

        INSERT INTO public.user_profiles (user_id, phone_e164, full_name, role, is_active, created_at, updated_at)
        SELECT id, NULL, full_name, 'COORDINATOR'::user_role_enum, is_active, created_at, updated_at
        FROM public.bql_staff;;

DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='auth' AND table_name='users'
            ) THEN
                ALTER TABLE public.user_profiles
                ADD CONSTRAINT fk_user_profiles_auth_users
                FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
            END IF;
        END $$;;

CREATE TABLE buildings (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE TABLE floors (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    building_id UUID NOT NULL, 
    floor_code VARCHAR(50) NOT NULL, 
    display_name VARCHAR(100) NOT NULL, 
    adjacency_index INTEGER NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_floors_building_code UNIQUE (building_id, floor_code), 
    FOREIGN KEY(building_id) REFERENCES buildings (id) ON DELETE CASCADE
);

INSERT INTO buildings(code, name, is_active)
        SELECT DISTINCT building_code, building_code, true FROM units;

        INSERT INTO floors(building_id, floor_code, display_name, adjacency_index, is_active)
        SELECT b.id, u.floor, u.floor,
               dense_rank() OVER (
                   PARTITION BY b.id
                   ORDER BY
                       CASE
                           WHEN upper(u.floor) ~ '^B[0-9]+$' THEN 0
                           WHEN u.floor ~ '^[0-9]+$' THEN 1
                           ELSE 2
                       END,
                       CASE
                           WHEN upper(u.floor) ~ '^B[0-9]+$' THEN -substring(upper(u.floor) from 2)::integer
                           WHEN u.floor ~ '^[0-9]+$' THEN u.floor::integer
                           ELSE NULL
                       END,
                       u.floor
               )::integer,
               true
        FROM (SELECT DISTINCT building_code, floor FROM units) u
        JOIN buildings b ON b.code=u.building_code;;

ALTER TABLE units ADD COLUMN building_id_v2 UUID;

ALTER TABLE units ADD COLUMN floor_id_v2 UUID;

ALTER TABLE units ADD COLUMN unit_code VARCHAR(80);

ALTER TABLE units ADD COLUMN status VARCHAR(30);

UPDATE units u
        SET building_id_v2=b.id,
            floor_id_v2=f.id,
            unit_code=u.building_code || '-' || u.unit_number,
            status=CASE WHEN u.is_active THEN 'ACTIVE' ELSE 'INACTIVE' END
        FROM buildings b, floors f
        WHERE b.code=u.building_code
          AND f.building_id=b.id
          AND f.floor_code=u.floor;;

ALTER TABLE units ALTER COLUMN building_id_v2 SET NOT NULL;

ALTER TABLE units ALTER COLUMN floor_id_v2 SET NOT NULL;

ALTER TABLE units ALTER COLUMN unit_code SET NOT NULL;

ALTER TABLE units ALTER COLUMN status SET NOT NULL;

ALTER TABLE units ALTER COLUMN status SET DEFAULT 'ACTIVE';

ALTER TABLE units ADD CONSTRAINT fk_units_building_v2 FOREIGN KEY(building_id_v2) REFERENCES buildings (id) ON DELETE RESTRICT;

ALTER TABLE units ADD CONSTRAINT fk_units_floor_v2 FOREIGN KEY(floor_id_v2) REFERENCES floors (id) ON DELETE RESTRICT;

ALTER TABLE units ADD CONSTRAINT uq_units_building_code UNIQUE (building_id_v2, unit_code);

ALTER TABLE units DROP COLUMN building_code;

ALTER TABLE units DROP COLUMN floor;

ALTER TABLE units DROP COLUMN unit_number;

ALTER TABLE units DROP COLUMN is_active;

ALTER TABLE units RENAME building_id_v2 TO building_id;

ALTER TABLE units RENAME floor_id_v2 TO floor_id;

CREATE TABLE resident_profiles (
    user_id UUID NOT NULL, 
    unit_id UUID NOT NULL, 
    is_primary BOOLEAN DEFAULT false NOT NULL, 
    verified_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (user_id), 
    FOREIGN KEY(user_id) REFERENCES user_profiles (user_id) ON DELETE CASCADE, 
    FOREIGN KEY(unit_id) REFERENCES units (id) ON DELETE RESTRICT
);

CREATE INDEX ix_resident_profiles_unit ON resident_profiles (unit_id);

CREATE UNIQUE INDEX uq_resident_profiles_one_primary_per_unit ON resident_profiles (unit_id) WHERE is_primary = true;

INSERT INTO resident_profiles(user_id, unit_id, is_primary, verified_at)
        SELECT m.resident_id,
               m.unit_id,
               row_number() OVER (PARTITION BY m.unit_id ORDER BY m.linked_at, m.resident_id) = 1,
               m.linked_at
        FROM resident_unit_memberships m
        WHERE m.is_active=true;;

DROP TABLE IF EXISTS public.ticket_assignments CASCADE;

DROP TABLE IF EXISTS public.technician_skills CASCADE;

DROP TABLE IF EXISTS public.ticket_scoring_results CASCADE;

DROP TABLE IF EXISTS public.ai_analysis_runs CASCADE;

DROP TABLE IF EXISTS public.ticket_attachments CASCADE;

DROP TABLE IF EXISTS public.ticket_attachment_upload_sessions CASCADE;

DROP TABLE IF EXISTS public.ticket_status_history CASCADE;

DROP TABLE IF EXISTS public.notifications CASCADE;

DROP TABLE IF EXISTS public.audit_logs CASCADE;

DROP TABLE IF EXISTS public.tickets CASCADE;

DROP TABLE IF EXISTS public.technician_profiles CASCADE;

DROP TRIGGER IF EXISTS trg_residents_prevent_actor_profile_conflict ON public.residents;

DROP TRIGGER IF EXISTS trg_bql_staff_prevent_actor_profile_conflict ON public.bql_staff;

DROP FUNCTION IF EXISTS public.prevent_actor_profile_conflict();

DROP TABLE IF EXISTS public.resident_unit_memberships CASCADE;

DROP TABLE IF EXISTS public.residents CASCADE;

DROP TABLE IF EXISTS public.bql_staff CASCADE;

DROP TYPE IF EXISTS assignment_status_enum;

DROP TYPE IF EXISTS ticket_status_enum;

DROP TYPE IF EXISTS category_enum;

DROP TYPE IF EXISTS severity_enum;

DROP TYPE IF EXISTS priority_enum;

CREATE TABLE location_types (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    display_name VARCHAR(150) NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE TABLE locations (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    building_id UUID NOT NULL, 
    floor_id UUID NOT NULL, 
    location_type_id UUID NOT NULL, 
    unit_id UUID, 
    label VARCHAR(200) NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(building_id) REFERENCES buildings (id) ON DELETE CASCADE, 
    FOREIGN KEY(floor_id) REFERENCES floors (id) ON DELETE CASCADE, 
    FOREIGN KEY(location_type_id) REFERENCES location_types (id) ON DELETE RESTRICT, 
    FOREIGN KEY(unit_id) REFERENCES units (id) ON DELETE SET NULL
);

CREATE INDEX ix_locations_floor_type_active ON locations (floor_id, location_type_id, is_active);

CREATE TABLE categories (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    code VARCHAR(80) NOT NULL, 
    display_name VARCHAR(150) NOT NULL, 
    priority_ceiling priority_level_enum, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE TABLE scoring_rule_versions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    version VARCHAR(50) NOT NULL, 
    config JSONB NOT NULL, 
    is_active BOOLEAN DEFAULT false NOT NULL, 
    created_by UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (version)
);

CREATE INDEX ix_scoring_rule_versions_active ON scoring_rule_versions (is_active);

CREATE UNIQUE INDEX uq_scoring_rule_versions_one_active ON scoring_rule_versions (is_active) WHERE is_active = true;

CREATE TABLE tickets (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    reporter_user_id UUID NOT NULL, 
    source_unit_id UUID NOT NULL, 
    location_id UUID NOT NULL, 
    description TEXT, 
    status ticket_status_v2_enum DEFAULT 'NEW' NOT NULL, 
    classification_status classification_status_enum DEFAULT 'PENDING' NOT NULL, 
    category_id UUID, 
    priority priority_level_enum, 
    severity severity_v2_enum, 
    red_flag_detected BOOLEAN DEFAULT false NOT NULL, 
    score_total NUMERIC(7, 2), 
    sla_started_at TIMESTAMP WITH TIME ZONE, 
    sla_due_at TIMESTAMP WITH TIME ZONE, 
    approved_at TIMESTAMP WITH TIME ZONE, 
    started_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    cancelled_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    version INTEGER DEFAULT 1 NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(reporter_user_id) REFERENCES user_profiles (user_id) ON DELETE RESTRICT, 
    FOREIGN KEY(source_unit_id) REFERENCES units (id) ON DELETE RESTRICT, 
    FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE RESTRICT, 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE RESTRICT
);

CREATE INDEX ix_tickets_reporter_user_id ON tickets (reporter_user_id);

CREATE INDEX ix_tickets_source_unit_id ON tickets (source_unit_id);

CREATE INDEX ix_tickets_location_id ON tickets (location_id);

CREATE TABLE ticket_attachments (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    ticket_id UUID NOT NULL, 
    attachment_type attachment_type_enum DEFAULT 'ISSUE_ORIGINAL' NOT NULL, 
    storage_bucket VARCHAR(100) DEFAULT 'ticket-attachments' NOT NULL, 
    object_path VARCHAR(1024) NOT NULL, 
    mime_type VARCHAR(255), 
    size_bytes BIGINT, 
    sha256 VARCHAR(64), 
    image_quality_status image_quality_status_enum, 
    uploaded_by UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
    FOREIGN KEY(uploaded_by) REFERENCES user_profiles (user_id) ON DELETE RESTRICT
);

CREATE INDEX ix_ticket_attachments_ticket_id ON ticket_attachments (ticket_id);

CREATE TABLE ticket_attachment_upload_sessions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    owner_user_id UUID NOT NULL, 
    storage_path VARCHAR(1024) NOT NULL, 
    original_filename VARCHAR(255), 
    mime_type VARCHAR(255) NOT NULL, 
    file_size INTEGER NOT NULL, 
    status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    object_verified_at TIMESTAMP WITH TIME ZONE, 
    consumed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_ticket_attachment_upload_sessions_file_size_positive CHECK (file_size > 0), 
    CONSTRAINT ck_ticket_attachment_upload_sessions_mime_type CHECK (mime_type IN ('image/jpeg','image/png','image/webp')), 
    CONSTRAINT ck_ticket_attachment_upload_sessions_status CHECK (status IN ('pending','consumed','expired')), 
    FOREIGN KEY(owner_user_id) REFERENCES user_profiles (user_id) ON DELETE RESTRICT, 
    UNIQUE (storage_path)
);

CREATE INDEX ix_ticket_attachment_upload_sessions_owner_status ON ticket_attachment_upload_sessions (owner_user_id, status);

CREATE INDEX ix_ticket_attachment_upload_sessions_expires_at ON ticket_attachment_upload_sessions (expires_at);

CREATE TABLE ai_analysis_runs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    ticket_id UUID NOT NULL, 
    run_number INTEGER DEFAULT 1 NOT NULL, 
    text_model_version VARCHAR(100), 
    vision_model_version VARCHAR(100), 
    rule_version_id UUID, 
    input_hash VARCHAR(64), 
    text_categories JSONB DEFAULT '[]'::jsonb NOT NULL, 
    image_categories JSONB, 
    red_flag_text BOOLEAN DEFAULT false NOT NULL, 
    red_flag_signal BOOLEAN DEFAULT false NOT NULL, 
    severity severity_v2_enum, 
    severity_source severity_source_enum, 
    category_match BOOLEAN, 
    score_components JSONB, 
    score_total NUMERIC(7, 2), 
    priority_raw priority_level_enum, 
    priority_final priority_level_enum, 
    ceiling_applied BOOLEAN DEFAULT false NOT NULL, 
    status analysis_run_status_enum DEFAULT 'RUNNING' NOT NULL, 
    error_code VARCHAR(100), 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
    FOREIGN KEY(rule_version_id) REFERENCES scoring_rule_versions (id) ON DELETE SET NULL
);

CREATE INDEX ix_ai_analysis_runs_ticket_id ON ai_analysis_runs (ticket_id);

CREATE TABLE ticket_status_history (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    ticket_id UUID NOT NULL, 
    from_status ticket_status_v2_enum, 
    to_status ticket_status_v2_enum NOT NULL, 
    changed_by UUID, 
    reason VARCHAR(500), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
    FOREIGN KEY(changed_by) REFERENCES user_profiles (user_id) ON DELETE SET NULL
);

CREATE INDEX ix_ticket_status_history_ticket_created_at ON ticket_status_history (ticket_id, created_at);

CREATE TABLE information_requests (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    ticket_id UUID NOT NULL, 
    requested_by UUID NOT NULL, 
    request_message TEXT NOT NULL, 
    status information_request_status_enum DEFAULT 'OPEN' NOT NULL, 
    resident_response_text TEXT, 
    responded_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
    FOREIGN KEY(requested_by) REFERENCES user_profiles (user_id) ON DELETE RESTRICT
);

CREATE INDEX ix_information_requests_ticket_id ON information_requests (ticket_id);

CREATE TABLE incident_cases (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    category_id UUID NOT NULL, 
    building_id UUID NOT NULL, 
    status VARCHAR(30) DEFAULT 'OPEN' NOT NULL, 
    window_start TIMESTAMP WITH TIME ZONE NOT NULL, 
    window_end TIMESTAMP WITH TIME ZONE NOT NULL, 
    density_value INTEGER DEFAULT 1 NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE RESTRICT, 
    FOREIGN KEY(building_id) REFERENCES buildings (id) ON DELETE RESTRICT
);

CREATE TABLE incident_case_members (
    case_id UUID NOT NULL, 
    ticket_id UUID NOT NULL, 
    source_unit_id UUID NOT NULL, 
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (case_id, ticket_id), 
    FOREIGN KEY(case_id) REFERENCES incident_cases (id) ON DELETE CASCADE, 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
    FOREIGN KEY(source_unit_id) REFERENCES units (id) ON DELETE RESTRICT
);

CREATE TABLE notifications (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    recipient_user_id UUID NOT NULL, 
    ticket_id UUID, 
    notification_type VARCHAR(100) NOT NULL, 
    channel notification_channel_enum DEFAULT 'IN_APP' NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    body TEXT NOT NULL, 
    payload JSONB DEFAULT '{}'::jsonb NOT NULL, 
    status notification_status_enum DEFAULT 'PENDING' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    sent_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(recipient_user_id) REFERENCES user_profiles (user_id) ON DELETE RESTRICT, 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE SET NULL
);

CREATE INDEX ix_notifications_recipient_status_created_at ON notifications (recipient_user_id, status, created_at);

CREATE INDEX ix_notifications_ticket_id ON notifications (ticket_id);

CREATE TABLE audit_logs (
    id BIGSERIAL NOT NULL, 
    actor_user_id UUID, 
    actor_role VARCHAR(50) DEFAULT 'SYSTEM' NOT NULL, 
    action VARCHAR(100) NOT NULL, 
    entity_type VARCHAR(100) NOT NULL, 
    entity_id UUID NOT NULL, 
    before_data JSONB, 
    after_data JSONB, 
    reason TEXT, 
    request_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(actor_user_id) REFERENCES user_profiles (user_id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_entity ON audit_logs (entity_type, entity_id, created_at);

CREATE INDEX ix_audit_logs_actor_created_at ON audit_logs (actor_user_id, created_at);

INSERT INTO categories(code, display_name, priority_ceiling) VALUES
          ('WATER_LEAK','RĂ² rá»‰ nÆ°á»›c',NULL),
          ('ELECTRICAL_SHORT','Cháº­p Ä‘iá»‡n',NULL),
          ('ELEVATOR','Thang mĂ¡y',NULL),
          ('SERIOUS_SECURITY_DISORDER','An ninh / gĂ¢y rá»‘i nghiĂªm trá»ng',NULL),
          ('LOCK_DOOR','KhĂ³a / cá»­a','P2'),
          ('HVAC','Äiá»u hĂ²a / thĂ´ng giĂ³','P2'),
          ('LOCAL_POWER_OUTAGE','Máº¥t Ä‘iá»‡n cá»¥c bá»™','P2'),
          ('STRUCTURAL_ISSUE','Sá»± cá»‘ káº¿t cáº¥u','P2'),
          ('COMMON_LIGHT','ÄĂ¨n khu vá»±c chung','P2'),
          ('ODOR_HYGIENE','MĂ¹i / vá»‡ sinh','P1'),
          ('NOISE_NEIGHBOR','Tiáº¿ng á»“n hĂ ng xĂ³m','P1');

        INSERT INTO location_types(code, display_name) VALUES
          ('CORRIDOR','HĂ nh lang'),
          ('FIRE_EXIT','Cáº§u thang / lá»‘i thoĂ¡t hiá»ƒm'),
          ('BASEMENT_PARKING','Háº§m / bĂ£i Ä‘á»— xe'),
          ('INSIDE_UNIT','BĂªn trong cÄƒn há»™'),
          ('MAIN_DOOR','Cá»­a chĂ­nh'),
          ('SECURITY_DOOR','Cá»­a an ninh');

        -- Floor-level canonical locations used by the Resident dropdown.
        INSERT INTO locations(building_id, floor_id, location_type_id, unit_id, label, is_active)
        SELECT f.building_id, f.id, lt.id, NULL, lt.display_name || ' - ' || f.display_name, true
        FROM floors f
        CROSS JOIN location_types lt
        WHERE lt.code IN ('CORRIDOR','FIRE_EXIT');

        INSERT INTO locations(building_id, floor_id, location_type_id, unit_id, label, is_active)
        SELECT f.building_id, f.id, lt.id, NULL, lt.display_name || ' - ' || f.display_name, true
        FROM floors f
        CROSS JOIN location_types lt
        WHERE lt.code='BASEMENT_PARKING'
          AND upper(f.floor_code) ~ '^B[0-9]+$';

        -- Unit-scoped locations. They cannot be selected for another unit because
        -- TicketService validates location.unit_id against the authenticated binding.
        INSERT INTO locations(building_id, floor_id, location_type_id, unit_id, label, is_active)
        SELECT u.building_id, u.floor_id, lt.id, u.id, lt.display_name || ' ' || u.unit_code, true
        FROM units u
        CROSS JOIN location_types lt
        WHERE lt.code IN ('INSIDE_UNIT','MAIN_DOOR','SECURITY_DOOR');;

INSERT INTO scoring_rule_versions(
            version,
            config,
            is_active
        )
        VALUES (
            'self-dev-v2.0.0',
            CAST('{"category_base": {"WATER_LEAK": 10, "ELECTRICAL_SHORT": 50, "ELEVATOR": 35, "SERIOUS_SECURITY_DISORDER": 40, "LOCK_DOOR": 25, "HVAC": 20, "LOCAL_POWER_OUTAGE": 25, "STRUCTURAL_ISSUE": 20, "COMMON_LIGHT": 10, "ODOR_HYGIENE": 10, "NOISE_NEIGHBOR": 10}, "location_bonus": {"LOCK_DOOR": {"MAIN_DOOR": 30, "SECURITY_DOOR": 30}, "COMMON_LIGHT": {"FIRE_EXIT": 25}}, "density": {"1": 0, "2-3": 15, "4+": 30, "categories": ["WATER_LEAK", "ELECTRICAL_SHORT"]}, "severity": {"LOW": 0, "MEDIUM": 10, "HIGH": 20}, "thresholds": {"P1": "<30", "P2": "30-59", "P3": ">=60"}, "sla_minutes": {"P3": 5, "P2": 180, "P1": 4320}}' AS jsonb),
            true
        );

CREATE INDEX idx_tickets_dashboard
        ON tickets (priority DESC, created_at ASC)
        WHERE status NOT IN ('COMPLETED','CANCELLED');
        CREATE INDEX idx_tickets_resident_history ON tickets (source_unit_id, created_at DESC);
        CREATE INDEX idx_tickets_category_window ON tickets (category_id, created_at DESC);
        CREATE INDEX idx_tickets_location_window ON tickets (location_id, created_at DESC);;

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

ALTER TABLE user_profiles FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE user_profiles FROM PUBLIC;

ALTER TABLE resident_profiles ENABLE ROW LEVEL SECURITY;

ALTER TABLE resident_profiles FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE resident_profiles FROM PUBLIC;

ALTER TABLE buildings ENABLE ROW LEVEL SECURITY;

ALTER TABLE buildings FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE buildings FROM PUBLIC;

ALTER TABLE floors ENABLE ROW LEVEL SECURITY;

ALTER TABLE floors FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE floors FROM PUBLIC;

ALTER TABLE units ENABLE ROW LEVEL SECURITY;

ALTER TABLE units FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE units FROM PUBLIC;

ALTER TABLE location_types ENABLE ROW LEVEL SECURITY;

ALTER TABLE location_types FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE location_types FROM PUBLIC;

ALTER TABLE locations ENABLE ROW LEVEL SECURITY;

ALTER TABLE locations FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE locations FROM PUBLIC;

ALTER TABLE categories ENABLE ROW LEVEL SECURITY;

ALTER TABLE categories FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE categories FROM PUBLIC;

ALTER TABLE scoring_rule_versions ENABLE ROW LEVEL SECURITY;

ALTER TABLE scoring_rule_versions FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE scoring_rule_versions FROM PUBLIC;

ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;

ALTER TABLE tickets FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE tickets FROM PUBLIC;

ALTER TABLE ticket_attachments ENABLE ROW LEVEL SECURITY;

ALTER TABLE ticket_attachments FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE ticket_attachments FROM PUBLIC;

ALTER TABLE ticket_attachment_upload_sessions ENABLE ROW LEVEL SECURITY;

ALTER TABLE ticket_attachment_upload_sessions FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE ticket_attachment_upload_sessions FROM PUBLIC;

ALTER TABLE ai_analysis_runs ENABLE ROW LEVEL SECURITY;

ALTER TABLE ai_analysis_runs FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE ai_analysis_runs FROM PUBLIC;

ALTER TABLE ticket_status_history ENABLE ROW LEVEL SECURITY;

ALTER TABLE ticket_status_history FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE ticket_status_history FROM PUBLIC;

ALTER TABLE information_requests ENABLE ROW LEVEL SECURITY;

ALTER TABLE information_requests FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE information_requests FROM PUBLIC;

ALTER TABLE incident_cases ENABLE ROW LEVEL SECURITY;

ALTER TABLE incident_cases FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE incident_cases FROM PUBLIC;

ALTER TABLE incident_case_members ENABLE ROW LEVEL SECURITY;

ALTER TABLE incident_case_members FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE incident_case_members FROM PUBLIC;

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

ALTER TABLE notifications FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE notifications FROM PUBLIC;

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE audit_logs FROM PUBLIC;

CREATE POLICY rls_user_profiles_select_own ON user_profiles
        FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));
        CREATE POLICY rls_resident_profiles_select_own ON resident_profiles
        FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));

        CREATE POLICY rls_units_catalog_select ON units FOR SELECT TO authenticated USING (true);
        CREATE POLICY rls_buildings_catalog_select ON buildings FOR SELECT TO authenticated USING (true);
        CREATE POLICY rls_floors_catalog_select ON floors FOR SELECT TO authenticated USING (true);
        CREATE POLICY rls_location_types_catalog_select ON location_types FOR SELECT TO authenticated USING (true);
        CREATE POLICY rls_locations_catalog_select ON locations FOR SELECT TO authenticated USING (is_active=true);
        CREATE POLICY rls_categories_catalog_select ON categories FOR SELECT TO authenticated USING (is_active=true);

        CREATE POLICY rls_tickets_resident_or_coordinator_select ON tickets
        FOR SELECT TO authenticated USING (
          EXISTS (
            SELECT 1 FROM user_profiles up
            WHERE up.user_id=(SELECT auth.uid()) AND up.is_active=true AND up.role='COORDINATOR'
          )
          OR source_unit_id IN (
            SELECT rp.unit_id FROM resident_profiles rp
            JOIN user_profiles up ON up.user_id=rp.user_id
            WHERE rp.user_id=(SELECT auth.uid()) AND up.is_active=true AND up.role='RESIDENT'
          )
        );
        CREATE POLICY rls_ticket_attachments_visible_ticket ON ticket_attachments
        FOR SELECT TO authenticated USING (
          EXISTS (SELECT 1 FROM tickets t WHERE t.id=ticket_attachments.ticket_id)
        );
        CREATE POLICY rls_ticket_status_history_visible_ticket ON ticket_status_history
        FOR SELECT TO authenticated USING (
          EXISTS (SELECT 1 FROM tickets t WHERE t.id=ticket_status_history.ticket_id)
        );
        CREATE POLICY rls_information_requests_visible_ticket ON information_requests
        FOR SELECT TO authenticated USING (
          EXISTS (SELECT 1 FROM tickets t WHERE t.id=information_requests.ticket_id)
        );
        CREATE POLICY rls_notifications_select_own ON notifications
        FOR SELECT TO authenticated USING (recipient_user_id=(SELECT auth.uid()));

        CREATE POLICY rls_upload_sessions_deny_client ON ticket_attachment_upload_sessions
        FOR ALL TO authenticated USING (false) WITH CHECK (false);
        CREATE POLICY rls_ai_runs_deny_client ON ai_analysis_runs
        FOR ALL TO authenticated USING (false) WITH CHECK (false);
        CREATE POLICY rls_scoring_rules_deny_client ON scoring_rule_versions
        FOR ALL TO authenticated USING (false) WITH CHECK (false);
        CREATE POLICY rls_incident_cases_deny_client ON incident_cases
        FOR ALL TO authenticated USING (false) WITH CHECK (false);
        CREATE POLICY rls_incident_members_deny_client ON incident_case_members
        FOR ALL TO authenticated USING (false) WITH CHECK (false);
        CREATE POLICY rls_audit_logs_deny_client ON audit_logs
        FOR ALL TO authenticated USING (false) WITH CHECK (false);;

UPDATE alembic_version SET version_num='a7b8c9d0e1f2' WHERE alembic_version.version_num = 'f6a7b8c9d0e1';

COMMIT;

