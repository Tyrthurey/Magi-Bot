from nextcord.ext import commands
import time
import nextcord


def decrease_all_user_cooldowns(bot, user_id, seconds):
  """Decrease all cooldowns for a user by a certain number of seconds."""
  for command in bot.commands:
    if not hasattr(command, '_buckets'):
      continue

    # Get the bucket for this command and user
    bucket = command._buckets.get_bucket(user_id)
    if bucket and bucket._last:  # Check if the bucket and the last usage timestamp exist
      # Decrease the last usage time by the specified seconds
      bucket._last -= seconds
      # Ensure that we don't go negative, which could cause issues
      if bucket._last < 0:
        bucket._last = 0


# You would call this function in your bot code like this:
# decrease_all_user_cooldowns(bot, user_id, seconds)
