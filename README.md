YouTube Live Chat AI Bot

An intelligent, real-time YouTube Live Chat automation system that detects relevant questions and replies with AI-generated answers.
Built with YouTube Data API + AI pipeline + smart filtering, this bot ensures only meaningful interactions are handled while ignoring spam and casual messages.

Features:
1.   Smart Question Detection:
          Filters out spam, emojis, and casual messages
          Uses keyword + context-based relevance detection
2.   AI-Powered Replies
          Generates accurate and contextual answers via API
3.   Real-Time Processing
          Continuously polls live chat and responds instantly
4.   Stream Context Awareness
          Uses stream title + description + custom context to improve replies
5.   Duplicate Message Handling
          Tracks seen messages to avoid repeated replies
6.   User Cooldown System
          Prevents spam replies to the same user
7.   Structured Logging
          JSON logs for replies, skipped messages, and error

Working:
          Live Chat Message
                    ↓
          Relevance Filter (Keyword + Context)
                    ↓
          If Relevant → AI Response Generator
                    ↓
          Trim to YouTube Limit (200 chars)
                    ↓
          Send Reply via YouTube API
                    ↓
          Log Action (Replied / Skipped / Error)


Project Structure:
youtube-ai-bot/
│
├── main.py              
├── chat_handler.py      
├── ai_engine.py         
├── api_client.py        
├── context_manager.py   
├── logger.py            
├── config.py            
├── oauth_setup.py       
├── id_generate.py       
│
├── requirements.txt     
├── .env                 
├── client_secret.json   
├── token.json           
│
├── seen_msgs.json       
├── chat_log.json        