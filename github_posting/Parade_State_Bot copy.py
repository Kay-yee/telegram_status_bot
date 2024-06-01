from typing import Final
from dotenv import load_dotenv
import telegram
import logging
import mysql.connector
import pandas as pd
import os
import prettytable as pt
from telegram.constants import ParseMode
from flask import Flask, request
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP,WMonthTelegramCalendar
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.ext import Updater, Application, CommandHandler, ConversationHandler, filters, ContextTypes,CallbackQueryHandler,MessageHandler,CallbackContext




logging.basicConfig(format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s, - %(lineno)d",
                    level = logging.INFO)
logger = logging.getLogger(__name__)


# THING TO IMPROVE
# Create a way for people to alter status
# Create a parade STate
# Send the parade state at set time.
# View the parade state and all the status for that day itself

FIRST,SECOND,THIRD,DURATION,START,NAMING,OTHERS = range(7)


def configure():
    load_dotenv()

TOKEN: Final = os.getenv("API_KEY")
URL: Final = os.getenv("URL")
#BOT_USERNAME: Final ='@Jinjjerebot'
bot = telegram.Bot(token=TOKEN)


app=Flask(__name__)


@app.route("/{}".format(TOKEN), methods=["POST"])
def respond():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    #chat_id = update.message.chat.id
    #msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode("utf-8").decode()

@app.route("/setwebhook", methods=["GET", "POST"])
def set_webhook():
    # we use the bot object to link the bot to our app which live
    # in the link provided by URL
    s = bot.setWebhook("{URL}{HOOK}".format(URL=URL, HOOK=TOKEN))
    # something to let us know things work
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type == 'group':
        return ConversationHandler.END
    #context.chat_data['status'] = None
    context.chat_data['chat_id'] = update.message.chat_id
    #global chat_id
    #chat_id = update.message.chat_id

    db = mysql.connector.connect(
    host = "localhost",
    user = "root",
    passwd= "joefrkmbreaxh",
    database = "parade_state")
    
    mycursor = db.cursor()
    mycursor.execute("SELECT tele_id FROM Person")
    if update.message.chat_id not in [y[0] for y in [x for x in mycursor]]:
        await get_unique_names(context.chat_data['chat_id'])
        mycursor.close()
        db.close()
        return NAMING
    else:
        mycursor.close()
        db.close()
        keyboard = [
        [
            InlineKeyboardButton("RSO", callback_data="RSO"),      
        ],
        [
            InlineKeyboardButton("RSI", callback_data="RSI"),      
        ],
        [
            InlineKeyboardButton("LL", callback_data="LL"),  
        ],
        [
            InlineKeyboardButton("OL", callback_data="OL"),
        ],
        [
            InlineKeyboardButton("MA", callback_data="MA"),
        ],
        [
            InlineKeyboardButton("MC", callback_data="MC"),
        ],
        [
            InlineKeyboardButton("OTHERS", callback_data="OTHERS"),
        ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please choose:", reply_markup=reply_markup)
        return FIRST

async def start_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    logging.info("activated...")
    #chat_id = query.message.chat_id
    #global status
    #status = query.data
    context.chat_data['status'] = query.data
    #print(status)
    logging.info(context.chat_data.get('status'))
    if context.chat_data.get('status') == "RSI" or context.chat_data.get('status') == "RSO":
        await query.edit_message_text(f"Pick date to {query.data}")
        await calendar(query,context)
        return SECOND
    elif context.chat_data.get('status') == "OTHERS":
        await query.edit_message_text("Enter the details for you status")
        return OTHERS
    else:
        await duration(query,context)
        return DURATION

    
async def others_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #global status    
    text: str = update.message.text
    logging.info("Received Message")
    logging.info("Status: Others")
    await duration(update,context)
    context.chat_data['status'] = text
    return DURATION


'''async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query'''

async def am_pm(context):
    keyboard = [
        [
            InlineKeyboardButton("AM", callback_data="AM"),      
        ],
        [
            InlineKeyboardButton("PM", callback_data="PM"),      
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(context.chat_data['chat_id'],"Select Time:", reply_markup=reply_markup)


async def am_pm_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("am and pm button activated")
    query = update.callback_query
    report_sick_time = query.data
    await bot.edit_message_text(f"Time of {context.chat_data['status']}: {report_sick_time} ",
                                query.message.chat.id,
                                query.message.message_id)
    db = mysql.connector.connect(
    host = "localhost",
    user = "root",
    passwd= "joefrkmbreaxh",
    database = "parade_state"
)
    mycursor = db.cursor()
    mycursor.execute("Insert INTO status_log(tele_id,status,date,duration) VALUES(%s,%s,%s,%s)",
                     (context.chat_data['chat_id'],context.chat_data['status'],context.chat_data['result'],report_sick_time))
    db.commit()
    mycursor.close()
    db.close()
    await bot.send_message(context.chat_data['chat_id'],"/continue to input next status\n\n\n /end to close bot")
    return START
    
async def duration(update,context):
    keyboard = [
        [
            InlineKeyboardButton("FULLDAY", callback_data="Fullday"),      
        ],
        [
            InlineKeyboardButton("HALFDAY AM", callback_data="AM"),      
        ],
        [
            InlineKeyboardButton("HALFDAY PM",  callback_data = "PM"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if context.chat_data.get('status') == "OTHERS":
        logging.info(f"Asking for date of {context.chat_data.get('status')}")
        await bot.send_message(update.message.chat_id,"Select...",
                                reply_markup = reply_markup)
    else:
        #logging.info(f"Asking for date of {status}")
        await bot.edit_message_text("Select ...",
                                update.message.chat.id,
                                update.message.message_id,                                
                                reply_markup=reply_markup)


async def duration_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("duration button")
    query = update.callback_query
    #global Duration 
    context.chat_data['Duration'] = query.data
    await calendar(query,context)
    return SECOND
    
async def calendar(query,context):
    calendar, step = WMonthTelegramCalendar().build()
    await bot.edit_message_text(f"Select date for {context.chat_data.get('status')}:",
                                query.message.chat.id,
                                query.message.message_id,
                                reply_markup=calendar)


async def calendar_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #global result
    logging.info(f"Calendar button for current status:{context.chat_data.get('status')}")
    query = update.callback_query
    context.chat_data['result'], key, step = WMonthTelegramCalendar().process(query.data)
    if not context.chat_data.get('result') and key:
        await bot.edit_message_text(f"Select {LSTEP[step]}",
                              query.message.chat.id,
                              query.message.message_id,
                              reply_markup=key)
    else:
        context.chat_data['result'] = context.chat_data['result'].strftime("%d %B %Y")
        await bot.edit_message_text(f"Date of {context.chat_data['status']}: {context.chat_data['result']}",
                                  query.message.chat.id,
                                  query.message.message_id)

        if context.chat_data.get('status') == "RSO" or context.chat_data.get('status') == "RSI":
            logging.info("asking for am or pm")
            await am_pm(context)
            return THIRD
        else:
            logging.info("Displaying time of status")
            await bot.send_message(query.message.chat.id,f"Time of {context.chat_data['status']}: ({context.chat_data['Duration']})")
            # tele_id, status, date ,duration
            db = mysql.connector.connect(
    host = "localhost",
    user = "root",
    passwd= "joefrkmbreaxh",
    database = "parade_state"
)
            mycursor = db.cursor()
            mycursor.execute("Insert INTO status_log(tele_id,status,date,duration) VALUES(%s,%s,%s,%s)",
                             (context.chat_data['chat_id'],context.chat_data['status'],context.chat_data['result'],context.chat_data['Duration']))
            db.commit()
            mycursor.close()
            db.close()
            #mycursor.execute("INSERT INTO Person(name) VALUES(%s)",('example',))
            #db.commit()
            await bot.send_message(context.chat_data['chat_id'],f"/continue to input next status\n\n\n /end to close bot")
            return START



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text("Use /start to test this bot.\nUse /end to close the bot.\nUse /restart to restart the bot")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global status
    status = None
    logger.info("User %s canceled the conversation")
    await update.message.reply_text("Welcome to telebot.\nPress /start to add status.")
    return ConversationHandler.END 

async def display_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = mysql.connector.connect(
    host = "localhost",
    user = "root",
    passwd= "joefrkmbreaxh",
    database = "parade_state"
)
    mycursor = db.cursor()
    #logging.debug("A debug Logging Message")
    mycursor.execute(f"SELECT * FROM status_log where tele_id = {update.message.chat_id} order by date")
    list1 = [x[2] for x in mycursor]
    mycursor.close()
    mycursor = db.cursor()
    mycursor.execute(f"SELECT * FROM status_log where tele_id = {update.message.chat_id} order by date")
    list2 = [x[3] for x in mycursor]
    mycursor.close()
    mycursor = db.cursor()
    mycursor.execute(f"SELECT * FROM status_log where tele_id = {update.message.chat_id} order by date")
    list3 = [x[4] for x in mycursor]
    df = pd.DataFrame({'DATE' : list2,
                    'DURATION': list3,
                    'STATUS' : list1,})
    mycursor.close()
    db.close()
    await bot.send_message(update.message.chat_id,f'```{df}```', parse_mode=ParseMode.MARKDOWN_V2)



async def get_unique_names(chat_id):
    await bot.send_message(chat_id,"Enter your rank and Name. (This can only be done once and cannot be changed)")

async def receiving_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.message.text
    logging.info("Received Message")
    logging.info(f"Name of User:{text}")

    db = mysql.connector.connect(
    host = "localhost",
    user = "root",
    passwd= "joefrkmbreaxh",
    database = "parade_state")

    mycursor = db.cursor()
    mycursor.execute("INSERT INTO Person(name,tele_id) VALUES(%s,%s)",(str(text),int(context.chat_data['chat_id'])))
    db.commit()
    mycursor.close()
    db.close()
    print("well done")
    await bot.send_message(context.chat_data['chat_id'],"Welcome to telebot.\nPress /start to add status.")
    return ConversationHandler.END

#updater.dispatcher.add_handler(conv_handler)
#updater.idle()

if __name__ == '__main__':
    logging.info('starting bot...')
    app.run(threaded=True)


    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    
    states={
    
        FIRST:[CallbackQueryHandler(start_button)],
        SECOND: [CallbackQueryHandler(calendar_button)],
        THIRD: [CallbackQueryHandler(am_pm_button)],
        DURATION: [CallbackQueryHandler(duration_button)],
        START : [CommandHandler('continue', start)],
        NAMING: [MessageHandler(filters.TEXT & (~ filters.COMMAND),receiving_name)],
        OTHERS: [MessageHandler(filters.TEXT & (~ filters.COMMAND),others_status)],
    },
    fallbacks=[CommandHandler('end', cancel_command),CommandHandler("restart", start)],

)

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", display_command))