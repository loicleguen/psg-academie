from ..db.database import get_session
from ..models.user import User
from common.security import (
    make_get_current_user,
    make_require_coach_or_admin,
)

# Dépendances FastAPI prêtes à l'emploi pour backend-catapult
get_current_user = make_get_current_user(get_session, User)
require_coach_or_admin = make_require_coach_or_admin(get_current_user)
require_admin = require_coach_or_admin  # alias (admin est inclus dans coach_or_admin)
