from . import team as _team
from . import academy as _academy
from . import country as _country

from .team import TeamRead
from .academy import AcademyRead
from .country import CountryRead

# Make referenced names available in the modules where the models are defined
_team.AcademyRead = AcademyRead
_academy.CountryRead = CountryRead
_country.AcademyRead = AcademyRead

# Now rebuild/resolve forward refs
TeamRead.update_forward_refs()
AcademyRead.update_forward_refs()
CountryRead.update_forward_refs()
