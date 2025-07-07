import discord
from discord.ext import commands
from discord import app_commands
import os
import sqlite3
from datetime import datetime
import logging
import aiofiles
from typing import Optional

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    """Admin-only commands for managing the bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
    
    def is_admin(self, user: discord.Member) -> bool:
        """Check if user has admin permissions"""
        return user.guild_permissions.administrator or user.guild_permissions.manage_guild
    
    @app_commands.command(name="setup", description="Initialize the bot data folder and database")
    async def setup(self, interaction: discord.Interaction):
        """Setup command to initialize bot"""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Create necessary directories
            os.makedirs('data', exist_ok=True)
            os.makedirs('data/backups', exist_ok=True)
            os.makedirs('logs', exist_ok=True)
            
            # Initialize database
            self.bot.setup_database()
            
            embed = discord.Embed(
                title="✅ Setup Complete",
                description="Bot has been successfully initialized!",
                color=discord.Color.green()
            )
            embed.add_field(name="Folders Created", value="• data/\n• data/backups/\n• logs/", inline=False)
            embed.add_field(name="Database", value="SQLite database initialized", inline=False)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Setup completed by {interaction.user}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Setup failed: {str(e)}")
            logger.error(f"Setup failed: {e}")
    
    @app_commands.command(name="dataupload", description="Upload a knowledge base file for this channel")
    async def dataupload(self, interaction: discord.Interaction, file: discord.Attachment):
        """Upload knowledge base data for the current channel"""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Validate file
            if file.size > self.max_file_size:
                await interaction.followup.send(
                    f"❌ File too large! Maximum size is {self.max_file_size // (1024*1024)}MB"
                )
                return
            
            if not file.filename.endswith('.txt'):
                await interaction.followup.send("❌ Please upload a .txt file only")
                return
            
            # Download and save file
            content = await file.read()
            text_content = content.decode('utf-8')
            
            # Save to channel-specific file
            channel_id = interaction.channel_id
            success = await self.bot.save_channel_data(channel_id, text_content)
            
            if success:
                # Generate summary
                summary = self.generate_summary(text_content)
                
                embed = discord.Embed(
                    title="✅ Knowledge Base Updated",
                    description=f"Successfully uploaded data for <#{channel_id}>",
                    color=discord.Color.green()
                )
                embed.add_field(name="File Size", value=f"{len(text_content):,} characters", inline=True)
                embed.add_field(name="Lines", value=f"{text_content.count(chr(10)) + 1:,}", inline=True)
                embed.add_field(name="Summary", value=summary, inline=False)
                
                await interaction.followup.send(embed=embed)
                logger.info(f"Data uploaded for channel {channel_id} by {interaction.user}")
            else:
                await interaction.followup.send("❌ Failed to save the file. Please try again.")
                
        except UnicodeDecodeError:
            await interaction.followup.send("❌ Invalid file encoding. Please use UTF-8 encoded text files.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error uploading file: {str(e)}")
            logger.error(f"Data upload error: {e}")
    
    @app_commands.command(name="dataview", description="View the current knowledge base for this channel")
    async def dataview(self, interaction: discord.Interaction):
        """View current channel data"""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            channel_id = interaction.channel_id
            content = await self.bot.get_channel_data(channel_id)
            
            if content is None:
                await interaction.followup.send("❌ No data found for this channel. Use `/dataupload` to add some!")
                return
            
            # Truncate content for display
            display_content = content[:1500] + "..." if len(content) > 1500 else content
            
            embed = discord.Embed(
                title="📄 Channel Knowledge Base",
                description=f"Data for <#{channel_id}>",
                color=discord.Color.blue()
            )
            embed.add_field(name="Size", value=f"{len(content):,} characters", inline=True)
            embed.add_field(name="Lines", value=f"{content.count(chr(10)) + 1:,}", inline=True)
            embed.add_field(name="Preview", value=f"```\n{display_content}\n```", inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error viewing data: {str(e)}")
            logger.error(f"Data view error: {e}")
    
    @app_commands.command(name="datadelete", description="Delete the knowledge base for this channel")
    async def datadelete(self, interaction: discord.Interaction):
        """Delete channel knowledge base"""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            channel_id = interaction.channel_id
            file_path = f'data/{channel_id}.txt'
            
            if not os.path.exists(file_path):
                await interaction.followup.send("❌ No data found for this channel.")
                return
            
            # Delete file
            os.remove(file_path)
            
            # Update database
            conn = sqlite3.connect(self.bot.stats_db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM channel_stats WHERE channel_id = ?', (channel_id,))
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="🗑️ Data Deleted",
                description=f"Knowledge base for <#{channel_id}> has been deleted.",
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Data deleted for channel {channel_id} by {interaction.user}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error deleting data: {str(e)}")
            logger.error(f"Data delete error: {e}")
    
    @app_commands.command(name="status", description="Show bot status and channel data information")
    async def status(self, interaction: discord.Interaction):
        """Show bot status"""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Get channel data info
            conn = sqlite3.connect(self.bot.stats_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM channel_stats ORDER BY questions_answered DESC')
            stats = cursor.fetchall()
            conn.close()
            
            embed = discord.Embed(
                title="📊 Bot Status",
                description="Current bot status and statistics",
                color=discord.Color.blue()
            )
            
            # Bot info
            embed.add_field(
                name="Bot Info",
                value=f"• Guilds: {len(self.bot.guilds)}\n• Users: {len(self.bot.users)}\n• Latency: {round(self.bot.latency * 1000)}ms",
                inline=True
            )
            
            # Memory usage
            data_files = [f for f in os.listdir('data') if f.endswith('.txt')]
            total_size = sum(os.path.getsize(f'data/{f}') for f in data_files)
            
            embed.add_field(
                name="Storage",
                value=f"• Channels with data: {len(data_files)}\n• Total data size: {total_size:,} bytes",
                inline=True
            )
            
            # Channel stats
            if stats:
                channels_info = []
                for stat in stats[:10]:  # Show top 10 channels
                    channel_id, questions, data_size, last_updated, created_at = stat
                    channel = self.bot.get_channel(channel_id)
                    channel_name = channel.name if channel else f"Unknown ({channel_id})"
                    channels_info.append(f"• #{channel_name}: {questions} questions")
                
                embed.add_field(
                    name="Top Channels",
                    value="\n".join(channels_info) if channels_info else "No data yet",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error getting status: {str(e)}")
            logger.error(f"Status error: {e}")
    
    @app_commands.command(name="update", description="Update/replace the knowledge base for this channel")
    async def update(self, interaction: discord.Interaction, file: discord.Attachment):
        """Update channel knowledge base (alias for dataupload)"""
        # This is essentially the same as dataupload but with different messaging
        await self.dataupload(interaction, file)
    
    @app_commands.command(name="debug", description="Show debug information for this channel")
    async def debug(self, interaction: discord.Interaction):
        """Show debug information"""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            channel_id = interaction.channel_id
            debug_info = self.bot.debug_data.get(channel_id)
            
            if not debug_info:
                await interaction.followup.send("❌ No debug information available for this channel.")
                return
            
            embed = discord.Embed(
                title="🐛 Debug Information",
                description=f"Last AI interaction for <#{channel_id}>",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="Question", 
                value=debug_info['question'][:500] + "..." if len(debug_info['question']) > 500 else debug_info['question'],
                inline=False
            )
            
            embed.add_field(
                name="Answer", 
                value=debug_info['answer'][:500] + "..." if len(debug_info['answer']) > 500 else debug_info['answer'],
                inline=False
            )
            
            embed.add_field(
                name="Timestamp", 
                value=debug_info['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                inline=True
            )
            
            embed.add_field(
                name="User", 
                value=f"<@{debug_info['user_id']}>",
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error getting debug info: {str(e)}")
            logger.error(f"Debug error: {e}")
    
    def generate_summary(self, content: str) -> str:
        """Generate a simple summary of the uploaded content"""
        lines = content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        if not non_empty_lines:
            return "Empty file"
        
        # Simple summary based on content structure
        summary_parts = []
        
        # Check for common patterns
        if any(line.startswith('#') for line in non_empty_lines):
            summary_parts.append("Contains headers/sections")
        
        if any('?' in line for line in non_empty_lines):
            summary_parts.append("Contains questions")
        
        if any(line.startswith('-') or line.startswith('*') or line.startswith('•') for line in non_empty_lines):
            summary_parts.append("Contains bullet points")
        
        if len(non_empty_lines) > 100:
            summary_parts.append("Large document")
        elif len(non_empty_lines) > 20:
            summary_parts.append("Medium document")
        else:
            summary_parts.append("Small document")
        
        # First line preview
        first_line = non_empty_lines[0][:100] + "..." if len(non_empty_lines[0]) > 100 else non_empty_lines[0]
        
        if summary_parts:
            return f"{', '.join(summary_parts)}\n\nPreview: {first_line}"
        else:
            return f"Preview: {first_line}"

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))