# Implementation Plan: Admin Manual User Registration

## Overview

Add a 3-step dialog flow (input_tg_id -> choosing_inbound -> confirm) allowing an admin to manually register a user by entering their tg_id, selecting an inbound, and confirming. On confirmation the system registers the user with server_id=2, caches them, saves the temporary inbound, and sends the welcome message (MSG_PREVIEW with trial activation button).

The feature closely mirrors AdminGenerateKeySG (5-step key generation wizard) but is simpler: no tariff selection, no key creation, and the confirm step doubles as the result screen.

---

## Files to create (4) and modify (8) -- see detailed steps below.

---

## Step 1 -- Define the StatesGroup

File: /home/claude/bot_3xui/states/admin.py  
File: /home/claude/bot_3xui/states/__init__.py

## Step 2 -- Create on-click handler

File: /home/claude/bot_3xui/getters/on_click/admin_manual_registration.py

## Step 3 -- Create MessageBuilder classes

File: /home/claude/bot_3xui/dialogs/windows/widgets/message/admin/manual_registration.py

## Step 4 -- Create KeyboardBuilder classes

File: /home/claude/bot_3xui/dialogs/windows/widgets/keybord/admin/manual_registration.py

## Step 5 -- Create DataGetter class

File: /home/claude/bot_3xui/dialogs/windows/getters/admin/manual_registration.py

## Step 6 -- Wire up exports

Files: __init__.py for message, keybord, getters admin packages

## Step 7 -- Register window configs

File: /home/claude/bot_3xui/dialogs/windows/__init__.py

## Step 8 -- Register in DI container

File: /home/claude/bot_3xui/services/conteiner/registrate/getters/admin.py

## Step 9 -- Add entry point button

File: /home/claude/bot_3xui/dialogs/windows/widgets/keybord/admin/panel.py
