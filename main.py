import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get API Keys from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")

# Check if keys are present
if not TELEGRAM_BOT_TOKEN or not GOOGLE_AI_API_KEY:
    logger.error("Missing API keys! Set TELEGRAM_BOT_TOKEN and GOOGLE_AI_API_KEY environment variables.")
    exit(1)

# Configure Gemini
genai.configure(api_key=GOOGLE_AI_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-pro')

# Store conversation history
conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"👋 Hello {user.first_name}!\n\n"
        "I'm an AI-powered bot using Google's Gemini AI.\n"
        "Just send me any message and I'll respond intelligently!\n\n"
        "Commands:\n"
        "/start - Show this welcome message\n"
        "/help - Get help\n"
        "/clear - Clear conversation history"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 **How to use this bot:**\n\n"
        "• Simply send any message and I'll respond using AI\n"
        "• I remember our conversation context\n"
        "• Use /clear to start a fresh conversation\n\n"
        "**Powered by Google Gemini AI**"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history."""
    user_id = update.effective_user.id
    if user_id in conversations:
        conversations[user_id] = []
    await update.message.reply_text("✅ Conversation history cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages and generate AI responses."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Initialize conversation history for new users
    if user_id not in conversations:
        conversations[user_id] = []
    
    try:
        # Send typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Add user message to history
        conversations[user_id].append({"role": "user", "parts": [user_message]})
        
        # Keep only last 10 messages for context
        if len(conversations[user_id]) > 10:
            conversations[user_id] = conversations[user_id][-10:]
        
        # Generate response using Gemini
        chat = model.start_chat(history=conversations[user_id][:-1])
        response = chat.send_message(user_message)
        
        # Add AI response to history
        conversations[user_id].append({"role": "model", "parts": [response.text]})
        
        # Send response to user
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        error_message = "Sorry, I encountered an error. Please try again later."
        await update.message.reply_text(error_message)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    
    # Register message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting bot...")
    
    # Railway uses PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    
    # Get Railway URL
    railway_url = os.environ.get('RAILWAY_STATIC_URL', '')
    
    # Set webhook URL
    if railway_url:
        webhook_url = f"https://{railway_url}/{TELEGRAM_BOT_TOKEN}"
        logger.info(f"Setting webhook: {webhook_url}")
    else:
        webhook_url = None
        logger.warning("RAILWAY_STATIC_URL not set, webhook will not be configured")
    
    # Run the bot with webhook for Railway
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=webhook_url
    )
    
    logger.info("Bot is running!")

if __name__ == '__main__':
    main()
