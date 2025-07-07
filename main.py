import discord
from discord.ext import commands, tasks
import asyncio
import os
import logging
from datetime import datetime
import json
from typing import Dict, Optional
import aiofiles
import aiohttp
from groq import AsyncGroq
import sqlite3
from pathlib import Path
import shutil
import re

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StudyGuideBot(commands.Bot):
    """Main bot class for the Study Guide Discord bot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        # Initialize components
        self.groq_client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
        self.user_context: Dict[int, list] = {}  # Store recent questions per user
        self.debug_data: Dict[int, dict] = {}  # Store debug info per channel
        self.stats_db_path = 'data/stats.db'
        
        # Profanity filter (basic words - expand as needed)
        self.profanity_words = {
            'fuck', 'shit', 'damn', 'bitch', 'ass', 'hell', 'crap'
        }
        
        # Setup database and folders
        self.setup_database()
        self.setup_folders()
        # DO NOT start background tasks here!

    async def setup_hook(self):
        """Called when the bot is starting up"""
        # Start background tasks here
        self.daily_backup.start()
        # Load cogs
        try:
            await self.load_extension('cogs.admin_commands')
            await self.load_extension('cogs.user_commands')
            logger.info("All cogs loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load cogs: {e}")

    def setup_database(self):
        """Initialize SQLite database for metadata and stats"""
        os.makedirs('data', exist_ok=True)
        
        conn = sqlite3.connect(self.stats_db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_stats (
                channel_id INTEGER PRIMARY KEY,
                questions_answered INTEGER DEFAULT 0,
                data_size INTEGER DEFAULT 0,
                last_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER,
                user_id INTEGER,
                question TEXT,
                answer TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_folders(self):
        """Create necessary folders"""
        folders = ['data', 'data/backups', 'logs']
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
    
    async def get_channel_data(self, channel_id: int) -> Optional[str]:
        """Load channel-specific knowledge base"""
        file_path = f'data/{channel_id}.txt'
        
        if not os.path.exists(file_path):
            return None
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return content.strip()
        except Exception as e:
            logger.error(f"Error reading channel data for {channel_id}: {e}")
            return None
    
    async def save_channel_data(self, channel_id: int, content: str) -> bool:
        """Save channel-specific knowledge base"""
        file_path = f'data/{channel_id}.txt'
        
        try:
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # Update database
            await self.update_channel_stats(channel_id, len(content))
            return True
        except Exception as e:
            logger.error(f"Error saving channel data for {channel_id}: {e}")
            return False
    
    async def update_channel_stats(self, channel_id: int, data_size: int = None):
        """Update channel statistics in database"""
        conn = sqlite3.connect(self.stats_db_path)
        cursor = conn.cursor()
        
        if data_size is not None:
            cursor.execute('''
                INSERT OR REPLACE INTO channel_stats 
                (channel_id, data_size, last_updated, questions_answered)
                VALUES (?, ?, ?, COALESCE(
                    (SELECT questions_answered FROM channel_stats WHERE channel_id = ?), 0
                ))
            ''', (channel_id, data_size, datetime.now(), channel_id))
        else:
            cursor.execute('''
                INSERT OR IGNORE INTO channel_stats (channel_id, questions_answered)
                VALUES (?, 0)
            ''', (channel_id,))
            
            cursor.execute('''
                UPDATE channel_stats 
                SET questions_answered = questions_answered + 1,
                    last_updated = ?
                WHERE channel_id = ?
            ''', (datetime.now(), channel_id))
        
        conn.commit()
        conn.close()
    
    async def ask_groq(self, question: str, channel_data: str, user_context: list = None) -> str:
        """Send question to Groq AI and get response"""
        try:
            # Build context
            context_text = ""
            if user_context:
                recent_questions = user_context[-3:]  # Last 3 questions for context
                context_text = f"Recent conversation context: {', '.join(recent_questions)}\n\n"
            
            # Build prompt
            prompt = f"""Act as a helpful study guide bot for the Sunnie Study Cafe Discord server. 
You should be friendly, concise, and helpful. Answer based on the provided channel data.

Channel Knowledge Base:
{channel_data}

{context_text}Current Question: {question}

Instructions:
- If the answer is directly in the knowledge base, use that information
- If not directly available, use reasoning and general knowledge to provide a helpful answer
- Keep responses concise but complete
- Use a friendly, encouraging tone
- Support markdown formatting in your response
- If you cannot answer at all, politely explain why

Answer:"""

            # Call Groq API
            response = await self.groq_client.chat.completions.create(
                model="llama3-8b-8192",  # Using free tier model
                messages=[
                    {"role": "system", "content": "You are a helpful study guide assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                top_p=0.9
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Apply profanity filter
            answer = self.filter_profanity(answer)
            
            return answer
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            return "Sorry, I'm having trouble accessing my AI service right now. Please try again later!"
    
    def filter_profanity(self, text: str) -> str:
        """Basic profanity filter for responses"""
        words = text.split()
        filtered_words = []
        
        for word in words:
            clean_word = re.sub(r'[^a-zA-Z]', '', word.lower())
            if clean_word in self.profanity_words:
                filtered_words.append('*' * len(word))
            else:
                filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    async def log_question(self, channel_id: int, user_id: int, question: str, answer: str):
        """Log question and answer for debugging and stats"""
        conn = sqlite3.connect(self.stats_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO question_history (channel_id, user_id, question, answer)
            VALUES (?, ?, ?, ?)
        ''', (channel_id, user_id, question, answer))
        
        conn.commit()
        conn.close()
        
        # Store debug data
        self.debug_data[channel_id] = {
            'question': question,
            'answer': answer,
            'timestamp': datetime.now(),
            'user_id': user_id
        }
    
    def get_user_context(self, user_id: int) -> list:
        """Get recent questions from user for context"""
        return self.user_context.get(user_id, [])
    
    def add_user_context(self, user_id: int, question: str):
        """Add question to user context"""
        if user_id not in self.user_context:
            self.user_context[user_id] = []
        
        self.user_context[user_id].append(question)
        
        # Keep only last 5 questions
        if len(self.user_context[user_id]) > 5:
            self.user_context[user_id] = self.user_context[user_id][-5:]
    
    @tasks.loop(hours=24)
    async def daily_backup(self):
        """Daily backup of all channel data"""
        try:
            backup_dir = f'data/backups/{datetime.now().strftime("%Y%m%d")}'
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup all channel data files
            data_files = [f for f in os.listdir('data') if f.endswith('.txt')]
            
            for file in data_files:
                src = f'data/{file}'
                dst = f'{backup_dir}/{file}'
                shutil.copy2(src, dst)
            
            # Backup database
            shutil.copy2(self.stats_db_path, f'{backup_dir}/stats.db')
            
            logger.info(f"Daily backup completed: {backup_dir}")
            
        except Exception as e:
            logger.error(f"Daily backup failed: {e}")
    
    @daily_backup.before_loop
    async def before_daily_backup(self):
        """Wait for bot to be ready before starting backup task"""
        await self.wait_until_ready()
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_application_command_error(self, interaction: discord.Interaction, error: Exception):
        """Handle slash command errors"""
        logger.error(f"Slash command error: {error}")
        
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An error occurred while processing your command. Please try again later.",
                ephemeral=True
            )

# Bot instance
bot = StudyGuideBot()

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables")
        exit(1)
    
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")