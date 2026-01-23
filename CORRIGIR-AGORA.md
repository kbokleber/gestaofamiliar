# 🚀 CORREÇÃO RÁPIDA - TIMEZONE

## ⚡ SOLUÇÃO EM 2 COMANDOS

```powershell
# 1. Fazer backup
docker exec sistema-postgres pg_dump -U sistema_user sistema_db > backup.sql

# 2. Aplicar correção
docker exec -i sistema-postgres psql -U sistema_user -d sistema_db -c "
ALTER TABLE healthcare_medicalappointment ALTER COLUMN appointment_date TYPE TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE healthcare_medicalappointment ALTER COLUMN next_appointment TYPE TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE healthcare_medicalappointment ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE healthcare_medicalappointment ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
"

# 3. Reiniciar
.\stop.ps1
.\start.ps1
```

## ✅ TESTAR

Acesse: http://localhost:5173/healthcare/appointments-test

Deve mostrar **15:30** (não 18:30)

---

**Ou use o script automático**:
```powershell
.\fix-timezone-final.ps1
```

