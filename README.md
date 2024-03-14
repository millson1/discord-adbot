# discord-adbot
A discord selfbot that can use multiple tokens to advertise in a channel (For example, LFG channels)
It can also automatically reply to DM's, and it will only send that DM once to one user.

| **Note:**
| Automating user accounts is against the Discord ToS. This library is a proof of concept and I cannot recommend using it. Do so at your own risk.

# Usage
1. Install Python 3.12
2. Install Discord.py-self's development version and install additional packages
   
.. code:: sh

    $ git clone https://github.com/dolfies/discord.py-self
    $ cd discord.py-self
    $ python3 -m pip install -U .[voice]
    $ python3 -m pip install asyncio
2. Clone this repository

.. code:: sh

    $ git clone https://github.com/millson1/discord-adbot
3. Edit the Bots.py script with these changes:
   Specify your tokens like this ["token1", "token2", "token3] etc..
   
   Depending on your number of tokens, you can set the launch delay so that the selfbots will
   send with a perfect cooldown. If your channel you want to send in has a 2 hour cooldown and you have 3 tokens, keep it at 40.

4. Edit the discord_selfbot_script.py
   Set your message and the channel you wish to send in (Line 17 and 14, respectively)
   Set the DM respond message (or, if you don't want to use that just remove the on_message handler)

5. Start Bots.py!
