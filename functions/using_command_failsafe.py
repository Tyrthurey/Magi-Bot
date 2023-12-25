# cooldown_manager.py
import time
from collections import defaultdict


class UsingCommandFailsafe:

  def __init__(self):
    # Nested dictionary; {user_id: {command_name: end_time_of_cooldown}}
    self.last_used_command_times = defaultdict(lambda: defaultdict(float))

  def set_last_used_command_time(self, user_id, command_name, cooldown):
    """Set a cooldown for a specific command for a user."""
    self.last_used_command_times[user_id][command_name] = time.time(
    ) + cooldown

  def get_last_used_command_time(self, user_id, command_name):
    """Get the remaining cooldown for a specific command for a user."""
    current_time = time.time()
    return max(
        self.last_used_command_times[user_id][command_name] - current_time, 0)

  def reduce_last_used_command_time(self, user_id, command_name, reduction):
    """Reduce the cooldown for a specific command for a user."""
    current_time = time.time()
    if command_name in self.last_used_command_times[user_id]:
      self.last_used_command_times[user_id][command_name] = max(
          self.last_used_command_times[user_id][command_name] - reduction,
          current_time)

  def reduce_all_last_used_command_times(self, user_id, reduction):
    """Reduce the cooldowns for all commands for a user."""
    current_time = time.time()
    for command_name in self.last_used_command_times[user_id]:
      self.last_used_command_times[user_id][command_name] = max(
          self.last_used_command_times[user_id][command_name] - reduction,
          current_time)


# Export a singleton instance to be used by other modules
using_command_failsafe_instance = UsingCommandFailsafe()
