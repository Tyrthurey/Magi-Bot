"""
@bot.command(name="use", help="Uses an item.")
async def use(ctx, *, item: str):
  ITEM_NAME = 'health_potion'
  ITEM_ID = 1  # As per your Health Potion data

  if item.lower() != 'health potion':
    await ctx.send("You don't have that item to use.")
    return

  user_id = ctx.author.id

  # Get the user's health and max_health
  player_response = await bot.loop.run_in_executor(
      None,
      lambda: supabase.table('Players').select('health', 'max_health').eq(
          'discord_id', user_id).execute())

  if player_response.data:
    player_data = player_response.data[0]
    current_health = player_data['health']
    max_health = player_data['max_health']

    if current_health < max_health:
      # Check if the user has a health potion in inventory
      inventory_response = await bot.loop.run_in_executor(
          None, lambda: supabase.table('Inventory').select('quantity').eq(
              'item_id', ITEM_ID).eq('discord_id', user_id).execute())

      if inventory_response.data[0]['quantity'] > 0:
        # Decrease the potion count by one
        new_quantity = inventory_response.data[0]['quantity'] - 1
        await bot.loop.run_in_executor(
            None,
            lambda: supabase.table('Inventory').update({
                'quantity': new_quantity
            }).eq('item_id', ITEM_ID).eq('discord_id', user_id).execute())

        # Update the player's health to max_health
        await bot.loop.run_in_executor(
            None, lambda: supabase.table('Players').update({
                'health': max_health
            }).eq('discord_id', user_id).execute())

        await ctx.send(
            "You've used a health potion and your health is now full!")
      else:
        await ctx.send("You don't have any health potions.")
    else:
      await ctx.send("Your health is already full.")
  else:
    await ctx.send("You do not have a profile yet.")
"""
