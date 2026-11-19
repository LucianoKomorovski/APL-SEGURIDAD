-- SOLO proyecto nuevo dedicado a APL. Ejecutar como postgres en SQL Editor.
-- Primero desactivar Data API en el panel. No usar Supabase Auth para APL.
-- No crea tablas: eso corresponde a manage.py migrate.
BEGIN;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated, service_role;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES FROM anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon, authenticated, service_role;
COMMIT;
-- Después de migrate volver a ejecutar y verificar: debe devolver cero filas.
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee IN ('anon', 'authenticated', 'service_role');
