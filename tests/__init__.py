import unittest

from .test_base_commands import *  # noqa: F401,F403
from .test_paginated_commands import *  # noqa: F401,F403
from .test_discovery import *  # noqa: F401,F403
from .test_notifications import *  # noqa: F401,F403
from .test_alarm import *  # noqa: F401, F403
from .test_callback import *  # noqa: F401, F403

if __name__ == '__main__':
    unittest.main(verbosity=3)
