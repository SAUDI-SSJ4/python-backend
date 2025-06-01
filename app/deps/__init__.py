from app.deps.database import get_db
from app.deps.auth import (
    get_current_user,
    get_current_admin,
    get_current_academy_user,
    get_current_student,
    get_optional_current_user,
    require_admin,
    require_academy,
    require_student
) 