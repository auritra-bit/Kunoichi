# 🤖 Study Guide Discord Bot

A production-ready Discord bot that serves as an AI-powered study guide for your Discord server. Each channel can have its own knowledge base, and users can ask questions that are answered using Groq's AI models.

## ✨ Features

### 👤 User Commands
- `/ask <question>` - Ask questions based on the channel's knowledge base
- `/help` - Show bot usage instructions
- `/stats` - View channel statistics

### 🛠️ Admin Commands
- `/setup` - Initialize bot data folders and database
- `/dataupload <file>` - Upload a .txt file as the channel's knowledge base
- `/dataview` - View current channel data
- `/datadelete` - Delete the channel's knowledge base
- `/status` - Show bot status and statistics
- `/update <file>` - Update/replace the channel's knowledge base
- `/debug` - View debug information for troubleshooting

### 🧠 AI Features
- **Channel-specific knowledge bases**: Each channel has its own data file
- **Context awareness**: Remembers recent user questions for better responses
- **Smart reasoning**: Uses Groq AI to provide helpful answers even when data doesn't directly contain the answer
- **Profanity filtering**: Basic content filtering for responses
- **Rate limiting**: Prevents spam (5-second cooldown between questions)

### 📊 Advanced Features
- **Statistics tracking**: Question counts, user activity, channel usage
- **Daily backups**: Automatic daily backup of all data
- **Debug mode**: Detailed logging and debug information
- **File size limits**: 10MB maximum for uploaded files
- **Database storage**: SQLite for metadata and statistics

## 🚀 Quick Setup

### 1. Prerequisites
- Python 3.8+
- Discord Bot Token
- Groq API Key (free tier available)

### 2. Installation

```bash
# Clone or download the bot files
git clone <repository-url>
cd study-guide-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your tokens
nano .env
```

Add your tokens to `.env`:
```
DISCORD_TOKEN=your_discord_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section
4. Create a bot and copy the token
5. Enable "Message Content Intent" under "Privileged Gateway Intents"
6. Go to "OAuth2" > "URL Generator"
7. Select scopes: `bot` and `applications.commands`
8. Select permissions: `Send Messages`, `Use Slash Commands`, `Read Message History`
9. Use the generated URL to invite the bot to your server

### 5. Groq API Setup

1. Go to [Groq Console](https://console.groq.com/)
2. Create a free account
3. Generate an API key
4. Copy the key to your `.env` file

### 6. Run the Bot

```bash
python main.py
```

## 📁 Project Structure

```
study-guide-bot/
├── main.py                 # Main bot file
├── cogs/
│   ├── __init__.py
│   ├── admin_commands.py   # Admin slash commands
│   └── user_commands.py    # User slash commands
├── data/                   # Knowledge base files
│   ├── backups/           # Daily backups
│   └── {channel_id}.txt   # Channel-specific data
├── logs/                  # Log files
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## 💡 Usage Guide

### For Admins

1. **Initial Setup**
   ```
   /setup
   ```
   Run this once to initialize the bot.

2. **Upload Knowledge Base**
   ```
   /dataupload <file.txt>
   ```
   Upload a .txt file containing study materials, FAQs, or any text content.

3. **Manage Data**
   ```
   /dataview     # View current data
   /datadelete   # Delete data
   /update       # Replace data
   /status       # Check bot status
   ```

### For Users

1. **Ask Questions**
   ```
   /ask What is photosynthesis?
   ```

2. **Get Help**
   ```
   /help
   ```

3. **View Statistics**
   ```
   /stats
   ```

## 🔧 Advanced Configuration

### Database Schema

The bot uses SQLite with these tables:
- `channel_stats`: Channel statistics and metadata
- `question_history`: Question and answer history

### File Limits

- Maximum file size: 10MB
- Supported formats: .txt files only
- Encoding: UTF-8

### Rate Limiting

- 5-second cooldown between questions per user
- Prevents API abuse and spam

## 🌐 Free Hosting Options

This bot is designed to work with free hosting services:

### Recommended Platforms

1. **Railway** (Free tier: 512MB RAM, 1GB storage)
2. **Render** (Free tier: 512MB RAM, sleeps after 15min)
3. **Heroku** (Free tier discontinued, but alternatives exist)
4. **Fly.io** (Free tier: 256MB RAM, 1GB storage)
5. **Discloud** (Discord bot hosting)

### Deployment Tips

- Use environment variables for secrets
- Enable logging for debugging
- Set up automatic restarts
- Monitor resource usage

## 📋 Environment Variables

Required environment variables:

```bash
DISCORD_TOKEN=your_discord_bot_token
GROQ_API_KEY=your_groq_api_key
```

## 🛠️ Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if bot is online
   - Verify slash commands are synced
   - Check bot permissions

2. **AI not working**
   - Verify Groq API key
   - Check internet connection
   - Review debug logs

3. **File upload fails**
   - Check file size (max 10MB)
   - Ensure .txt format
   - Verify UTF-8 encoding

### Debug Mode

Use `/debug` command to see:
- Last AI prompt and response
- Error messages
- Timing information

### Logs

Check `bot.log` for detailed logging:
```bash
tail -f bot.log
```

## 🔒 Security Features

- **Admin-only commands**: Sensitive operations require admin permissions
- **File validation**: Strict file type and size checking
- **Rate limiting**: Prevents abuse and spam
- **Input sanitization**: Basic profanity filtering
- **Error handling**: Graceful error handling and logging

## 🚀 Production Considerations

### Performance
- Efficient async/await usage
- Database connection pooling
- File I/O optimization
- Memory management

### Reliability
- Comprehensive error handling
- Automatic daily backups
- Graceful shutdown handling
- Health monitoring

### Security
- Environment variable usage
- Input validation
- Permission checking
- Audit logging

## 📈 Monitoring

The bot provides built-in monitoring:
- Question statistics
- Channel usage data
- Error logging
- Performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Use the `/debug` command
4. Check Discord bot permissions

## 🎯 Future Enhancements

Potential improvements:
- Multi-language support
- Voice command integration
- Advanced analytics
- Custom AI model training
- Integration with study platforms

---

**Made with ❤️ for the Sunnie Study Cafe Discord community**