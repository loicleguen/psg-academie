from . import team as _team
from . import academy as _academy
from . import country as _country
from . import user as _user

from .team import TeamRead
from .academy import AcademyRead
from .country import CountryRead
from .user import UserRead

# Make referenced names available in the modules where the models are defined
_team.AcademyRead = AcademyRead
_academy.CountryRead = CountryRead
_country.AcademyRead = AcademyRead
_team.UserRead = UserRead

# Now rebuild/resolve forward refs
TeamRead.update_forward_refs()
AcademyRead.update_forward_refs()
CountryRead.update_forward_refs()
UserRead.update_forward_refs()
