#!/bin/bash

set -e

echo "🤖 LN Release Discord Bot - Setup Script"
echo "========================================="
echo ""

if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
DISCORD_TOKEN=your_discord_bot_token_here
BOT_TIMEZONE_DEFAULT=UTC
EOF
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env and add your Discord bot token"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✅ Docker and Docker Compose found"
    echo ""
    
    read -p "🚀 Start the bot now? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🏗️  Building and starting bot..."
        docker-compose up -d
        echo ""
        echo "✅ Bot is running!"
        echo ""
        echo "📋 View logs:"
        echo "   docker-compose logs -f bot"
        echo ""
        echo "🛑 Stop bot:"
        echo "   docker-compose down"
    fi
else
    echo "⚠️  Docker not found. Install Docker to use docker-compose deployment."
    echo ""
    
    if command -v python3 &> /dev/null; then
        echo "🐍 Python 3 found"
        read -p "📦 Install Python dependencies? (y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pip install -r requirements.txt
            echo ""
            echo "✅ Dependencies installed!"
            echo ""
            echo "🚀 Run the bot:"
            echo "   python3 -m lnrelease.bot"
        fi
    fi
fi

echo ""
echo "📚 Next steps:"
echo "   1. Edit .env and add your Discord token"
echo "   2. Invite bot to your server (see README.md)"
echo "   3. Run /set_channel in Discord"
echo ""
echo "📖 Documentation:"
echo "   - README.md      - Full documentation"
echo ""

