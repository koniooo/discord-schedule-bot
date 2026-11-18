"""Timing of the weekly vote.

The single source of truth for both the bot and its schedules.
"""

from datetime import timedelta

# Until the schedules are built from this module, also update them by hand.
VOTE_DURATION = timedelta(days=2)
