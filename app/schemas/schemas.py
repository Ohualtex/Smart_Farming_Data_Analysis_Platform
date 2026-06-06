"""
SFDAP Pydantic Şemaları — RE-EXPORT HUB
=======================================
Bu modül artık şemaları doğrudan tanımlamaz; domain bazlı alt modüllerden
(app/schemas/<domain>.py) TÜM isimleri re-export eden bir geriye-uyumluluk
katmanıdır. Eski `from app.schemas.schemas import X` importları aynen çalışır.

Şemalar domain dosyalarına bölünmüştür:
- base                → UtcDateTime, SqliteSafeInt, _serialize_utc, SQLITE_INT_MAX
- sensors             → Sensor / SensorReading
- weather             → WeatherData
- irrigation          → Irrigation + IrrigationPrediction
- fertilizer          → FertilizerRecommend / FertilizerSchedule
- alerts              → SystemAlert
- model_performance   → ModelPerformanceLog + drift/compare/timeseries
- farms               → Farm / Field / SoilAnalysis (CRUD + GET)
- health              → HealthCheckResponse
- dashboard           → Dashboard ('Çiftliğim') özet
- field_detail        → Tarla detay sayfası

Auth schema'ları `app/routers/auth.py` içinde tanımlıdır
(UserRegisterRequest, UserLoginRequest, TokenResponse, CurrentUserResponse).

EN: Backwards-compatibility hub re-exporting every name from the domain
sub-modules. Auth schemas live in app/routers/auth.py.
"""

from __future__ import annotations

from app.schemas.alerts import *  # noqa: F401,F403
from app.schemas.base import *  # noqa: F401,F403

# Wildcard import skips the leading-underscore helper; re-export it explicitly
# so the legacy `from app.schemas.schemas import _serialize_utc` keeps working.
from app.schemas.base import _serialize_utc  # noqa: F401
from app.schemas.dashboard import *  # noqa: F401,F403
from app.schemas.farms import *  # noqa: F401,F403
from app.schemas.fertilizer import *  # noqa: F401,F403
from app.schemas.field_detail import *  # noqa: F401,F403
from app.schemas.health import *  # noqa: F401,F403
from app.schemas.irrigation import *  # noqa: F401,F403
from app.schemas.model_performance import *  # noqa: F401,F403
from app.schemas.sensors import *  # noqa: F401,F403
from app.schemas.weather import *  # noqa: F401,F403
