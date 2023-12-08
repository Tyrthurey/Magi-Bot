# settings_manager.py

# A cache to store settings
settings_cache = {}


def get_settings_cache(server_id):
  return settings_cache.get(server_id, {})


def update_settings_cache_here(server_id, new_settings):
  current_settings = settings_cache.get(server_id, {})
  updated_settings = {**current_settings, **new_settings}
  settings_cache[server_id] = updated_settings
