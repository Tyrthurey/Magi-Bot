# cooldown_manager.py
import time
from collections import defaultdict


class CooldownManager:

  def __init__(self):
    # Nested dictionary; {user_id: {command_name: end_time_of_cooldown}}
    self.cooldowns = defaultdict(lambda: defaultdict(float))

  def set_cooldown(self, user_id, command_name, cooldown):
    """Set a cooldown for a specific command for a user."""
    self.cooldowns[user_id][command_name] = time.time() + cooldown

  def get_cooldown(self, user_id, command_name):
    """Get the remaining cooldown for a specific command for a user."""
    current_time = time.time()
    return max(self.cooldowns[user_id][command_name] - current_time, 0)

  def reduce_cooldown(self, user_id, command_name, reduction):
    """Reduce the cooldown for a specific command for a user."""
    current_time = time.time()
    if command_name in self.cooldowns[user_id]:
      self.cooldowns[user_id][command_name] = max(
          self.cooldowns[user_id][command_name] - reduction, current_time)

  def reduce_all_cooldowns(self, user_id, reduction):
    """Reduce the cooldowns for all commands for a user."""
    current_time = time.time()
    for command_name in self.cooldowns[user_id]:
      self.cooldowns[user_id][command_name] = max(
          self.cooldowns[user_id][command_name] - reduction, current_time)


# Export a singleton instance to be used by other modules
cooldown_manager_instance = CooldownManager()
