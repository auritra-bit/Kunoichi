import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserCommands(commands.Cog):
    """User-accessible commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ask", description="Ask a question based on this channel's knowledge base")
    async def ask(self, interaction: discord.Interaction, question: str):
        """Main command for users to ask questions"""
        await interaction.response.defer()
        
        try:
            channel_id = interaction.channel_id
            user_id = interaction.user.id
            
            # Check if channel has data
            channel_data = await self.bot.get_channel_data(channel_id)
            
            if channel_data is None:
                embed = discord.Embed(
                    title="❌ No Knowledge Base",
                    description="This channel doesn't have a knowledge base yet!\nAsk an admin to upload data using `/dataupload`.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check for rate limiting (simple implementation)
            if await self.is_rate_limited(user_id):
                await interaction.followup.send(
                    "⏱️ Please wait a moment before asking another question.",
                    ephemeral=True
                )
                return
            
            # Get user context for better responses
            user_context = self.bot.get_user_context(user_id)
            
            # Get AI response
            typing_message = await interaction.followup.send("🤔 Thinking...")
            
            answer = await self.bot.ask_groq(question, channel_data, user_context)
            
            # Create response embed
            embed = discord.Embed(
                title="💡 Answer",
                description=answer,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Asked by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            
            # Edit the typing message with the answer
            await typing_message.edit(content=None, embed=embed)
            
            # Update user context and stats
            self.bot.add_user_context(user_id, question)
            await self.bot.update_channel_stats(channel_id)
            await self.bot.log_question(channel_id, user_id, question, answer)
            
            logger.info(f"Question answered in channel {channel_id} by user {user_id}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error processing your question: {str(e)}")
            logger.error(f"Ask command error: {e}")
    
    @app_commands.command(name="help", description="Show help information for the bot")
    async def help(self, interaction: discord.Interaction):
        """Show help information"""
        embed = discord.Embed(
            title="📚 Study Guide Bot Help",
            description="Welcome to the Sunnie Study Cafe guide bot!",
            color=discord.Color.blue()
        )
        
        # User commands
        embed.add_field(
            name="👤 User Commands",
            value="• `/ask <question>` - Ask a question based on this channel's knowledge base\n• `/help` - Show this help message\n• `/stats` - View channel statistics",
            inline=False
        )
        
        # Admin commands
        embed.add_field(
            name="🛠️ Admin Commands",
            value="• `/setup` - Initialize bot\n• `/dataupload <file>` - Upload knowledge base\n• `/dataview` - View current data\n• `/datadelete` - Delete channel data\n• `/status` - Show bot status\n• `/update <file>` - Update knowledge base\n• `/debug` - Show debug info",
            inline=False
        )
        
        # Usage tips
        embed.add_field(
            name="💡 Tips",
            value="• Each channel has its own knowledge base\n• Ask specific questions for better answers\n• The bot remembers your recent questions for context\n• Admins can upload .txt files as knowledge bases",
            inline=False
        )
        
        embed.set_footer(text="Study hard and stay curious! 📖")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stats", description="View statistics for this channel")
    async def stats(self, interaction: discord.Interaction):
        """Show channel statistics"""
        await interaction.response.defer()
        
        try:
            channel_id = interaction.channel_id
            
            # Get channel stats from database
            conn = sqlite3.connect(self.bot.stats_db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM channel_stats WHERE channel_id = ?', (channel_id,))
            stats = cursor.fetchone()
            
            if not stats:
                embed = discord.Embed(
                    title="📊 Channel Statistics",
                    description="No statistics available for this channel yet.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get recent questions
            cursor.execute('''
                SELECT COUNT(*) as total_questions,
                       COUNT(DISTINCT user_id) as unique_users
                FROM question_history 
                WHERE channel_id = ?
            ''', (channel_id,))
            
            question_stats = cursor.fetchone()
            
            # Get top users
            cursor.execute('''
                SELECT user_id, COUNT(*) as question_count
                FROM question_history 
                WHERE channel_id = ?
                GROUP BY user_id
                ORDER BY question_count DESC
                LIMIT 5
            ''', (channel_id,))
            
            top_users = cursor.fetchall()
            conn.close()
            
            # Create embed
            embed = discord.Embed(
                title="📊 Channel Statistics",
                description=f"Statistics for <#{channel_id}>",
                color=discord.Color.blue()
            )
            
            # Basic stats
            channel_id_stat, questions_answered, data_size, last_updated, created_at = stats
            
            embed.add_field(
                name="📈 Overview",
                value=f"• Total questions: {question_stats[0] if question_stats else 0}\n• Unique users: {question_stats[1] if question_stats else 0}\n• Data size: {data_size:,} characters" if data_size else "No data uploaded",
                inline=False
            )
            
            # Timing info
            if last_updated:
                embed.add_field(
                    name="⏰ Last Activity",
                    value=f"Data updated: {last_updated[:19]}",
                    inline=True
                )
            
            # Top users
            if top_users:
                top_users_text = []
                for user_id, count in top_users:
                    user = self.bot.get_user(user_id)
                    username = user.display_name if user else f"User {user_id}"
                    top_users_text.append(f"• {username}: {count} questions")
                
                embed.add_field(
                    name="🏆 Top Users",
                    value="\n".join(top_users_text),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error getting statistics: {str(e)}")
            logger.error(f"Stats error: {e}")
    
    async def is_rate_limited(self, user_id: int) -> bool:
        """Simple rate limiting - 1 question per 5 seconds"""
        current_time = datetime.now()
        
        # Check if user has asked recently
        conn = sqlite3.connect(self.bot.stats_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp FROM question_history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            last_question_time = datetime.fromisoformat(result[0])
            time_diff = (current_time - last_question_time).total_seconds()
            
            if time_diff < 5:  # 5 second cooldown
                return True
        
        return False

async def setup(bot):
    await bot.add_cog(UserCommands(bot))