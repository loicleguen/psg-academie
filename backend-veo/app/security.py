from common.security import (
    make_get_current_user_from_token,
    make_require_coach_or_admin,
)

# Dépendances FastAPI prêtes à l'emploi pour backend-veo
# Pas de table User dans veo : on décode uniquement le token JWT
get_current_user = make_get_current_user_from_token()
require_coach_or_admin = make_require_coach_or_admin(get_current_user)
