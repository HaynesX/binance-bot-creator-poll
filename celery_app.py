from celery import Celery
from email.policy import default
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, inspect
from database_settings import engine, Sheet_Instance
import telebot
from binance.client import Client
import time
import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import *
from itertools import zip_longest




app = Celery('celery_app',
             broker='redis://redis_main_container:6379/0',
             backend='redis://redis_main_container:6379/0')





scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("googleEnv/google.json", scope)
googleClient = gspread.authorize(creds)

# sh = googleClient.create('Binance Trades - DONT CHANGE NAME')
# print(sh.id)

spreadsheet = googleClient.open("Binance Trades - DONT CHANGE NAME")

# spreadsheet.share('haynesx10@gmail.com', perm_type='anyone', role='writer')

TELEGRAM_BINANCE_API_KEY = os.getenv('TELEGRAM_BINANCE_API_KEY')

API_KEY = TELEGRAM_BINANCE_API_KEY
bot = telebot.TeleBot(API_KEY)



main_chat_id = "-1001768606486"
# main_chat_id = "-1001748800899"














def check_for_sheet_updates(session):
    worksheet_list = spreadsheet.worksheets()



    worksheetIDs = []

    for eachWorksheet in worksheet_list:
        sheetInDatabase = session.query(Sheet_Instance).filter(Sheet_Instance.gid == eachWorksheet.id).first()
        if sheetInDatabase:
            if sheetInDatabase.sheet_name_lower != eachWorksheet.title.lower():
                sheetInDatabase.sheet_name_lower = eachWorksheet.title.lower()
            
            if sheetInDatabase.sheet_name != eachWorksheet.title:
                bot.send_message(main_chat_id, f"Sheet Name: '{sheetInDatabase.sheet_name}' Changed to '{eachWorksheet.title}'")
                sheetInDatabase.sheet_name = eachWorksheet.title
                
            
            
            # session.commit()
        worksheetIDs.append(eachWorksheet.id)
    

    
    allSheetsNotOnGoogleQuery = session.query(Sheet_Instance).filter(Sheet_Instance.gid.not_in(worksheetIDs))
    allSheetsNotOnGoogle = allSheetsNotOnGoogleQuery.all()
    allSheetsNotOnGoogleQuery.delete()
    # session.commit()

    for eachSheetNotOnGoogle in allSheetsNotOnGoogle:
        bot.send_message(main_chat_id, f"{eachSheetNotOnGoogle.sheet_name} Removed.")
        time.sleep(2)


















def poll_daily_profit(session):
    try:
        sheetInstances = session.query(Sheet_Instance).filter(Sheet_Instance.active == True).all()

        worksheet_list = spreadsheet.worksheets()

        worksheet_names_list = []

        worksheetsToUse = []

        for eachWorksheet in worksheet_list:
            worksheet_names_list.append(eachWorksheet.title)


        for eachSheet in sheetInstances:
            if f"{eachSheet.sheet_name} - Daily Profit" in worksheet_names_list and eachSheet.sheet_name in worksheet_names_list:
                dailyProfitWorksheet = spreadsheet.worksheet(f"{eachSheet.sheet_name} - Daily Profit")
                time.sleep(1)
                mainWorksheet = spreadsheet.worksheet(eachSheet.sheet_name)
                time.sleep(1)

                worksheetsToUse.append([mainWorksheet, dailyProfitWorksheet])
            else:
                if eachSheet.sheet_name in worksheet_names_list and f"{eachSheet.sheet_name} - Daily Profit" not in worksheet_names_list:
                    newDailyProfitWorksheet = spreadsheet.add_worksheet(title=f"{eachSheet.sheet_name} - Daily Profit", rows=1000, cols=20)
                    time.sleep(1)
                    newDailyProfitWorksheet.insert_row(["Date", "Daily Profit %", "TV Daily Profit %", "Difference"], 1, value_input_option='USER_ENTERED')
                    time.sleep(1)
                    mainWorksheet = spreadsheet.worksheet(eachSheet.sheet_name)
                    time.sleep(1)
                    worksheetsToUse.append([mainWorksheet, newDailyProfitWorksheet])
        

        for index, eachSetOfWorksheets in enumerate(worksheetsToUse, start=0):
            if index == 1:
                return

            
            dailyDates = eachSetOfWorksheets[1].col_values(1)
            dailyProfits = eachSetOfWorksheets[1].col_values(2)

            dailyCurrentDict = {}

            for index, eachDateProfitList in enumerate(list(zip_longest(dailyDates, dailyProfits)), start=0):
                if index == 0:
                    continue
                
                if eachDateProfitList[0] == None or eachDateProfitList[0] == "":
                    continue
                
                

                if "/" in eachDateProfitList[0]:                        
                    dailyCurrentDict[eachDateProfitList[0]] = {"Profit": 0.00, "Cell": f"B{index + 1}"}
                    
            

            allMainWorksheetRows = eachSetOfWorksheets[0].get_all_values()

            if len(allMainWorksheetRows) < 7:
                continue

            headerRow = allMainWorksheetRows[6]

            profitAndLossIndex = -1
            profitAndLossColumnName = "N/A"


            for index, eachColumnName in enumerate(headerRow, start=0):
                if "binanceprofit/loss" in eachColumnName.lower() or "p&l %" in eachColumnName.lower() or "p&l%" in eachColumnName.lower() or "profit and loss %" in eachColumnName.lower() or "binance profit/loss" in eachColumnName.lower() or "binance p&l %" in eachColumnName.lower():
                    profitAndLossIndex = index
                    profitAndLossColumnName = eachColumnName
                    break
            
            if profitAndLossIndex == -1 or profitAndLossColumnName == "N/A":
                continue
            
            mainWorksheetDates = eachSetOfWorksheets[0].col_values(1)
            mainWorksheetProfitLosses = eachSetOfWorksheets[0].col_values(profitAndLossIndex + 1)

            newDailyDict = {}

            for index, eachDateProfitList in enumerate(list(zip_longest(mainWorksheetDates, mainWorksheetProfitLosses)), start=0):
                if index in [0, 1, 2, 3, 4, 5, 6]:
                    continue
                
                if eachDateProfitList[0] == None or eachDateProfitList[0] == "":
                    continue
            

                if "/" in eachDateProfitList[0]:

                    try:
                        dateMonthYear = eachDateProfitList[0].split(" ")[0]
                    except:
                        continue


                    if eachDateProfitList[1] != None:
                        try:
                            profitValue = float(eachDateProfitList[1])
                        except ValueError:
                            profitValue = 0.00
                    else:
                        profitValue = 0.00
                    
                    if dateMonthYear in dailyCurrentDict:
                        dailyCurrentDict[dateMonthYear]["Profit"] += profitValue
                    else:
                        if dateMonthYear in newDailyDict:
                            newDailyDict[dateMonthYear] += profitValue
                        else:
                            newDailyDict[dateMonthYear] = profitValue
            


            for eachKey in dailyCurrentDict:
                eachSetOfWorksheets[1].update(dailyCurrentDict[eachKey]["Cell"], dailyCurrentDict[eachKey]["Profit"])
                time.sleep(1)
            
            new_rows_to_insert = []

            for eachKey in newDailyDict:
                new_rows_to_insert.append([eachKey, newDailyDict[eachKey], "", ""])

            
            if len(new_rows_to_insert) != 0:
                eachSetOfWorksheets[1].insert_rows(new_rows_to_insert, 2, value_input_option='USER_ENTERED')
                time.sleep(3)
            
            eachSetOfWorksheets[1].sort((1, 'des'))
            time.sleep(1)
    except Exception as e:
        bot.send_message(main_chat_id, f"ERROR on poll_daily_sheets:\n {e}")
        time.sleep(10)








































@app.task
def start_instance_task(messageID, messageText, messageChatID):
    with Session(bind=engine) as session:
        with session.begin():
            try:

                check_for_sheet_updates(session)



                try:
                    sheetName = messageText.split("/poll ")[1].lower()
                except Exception:
                    bot.send_message(messageChatID, "Invalid Command. Invalid Format.", reply_to_message_id=messageID)
                    return
                
                sheetByName = session.query(Sheet_Instance).filter(Sheet_Instance.sheet_name_lower == sheetName).first()
                if sheetByName:
                    sheetByName.active = True
                    # session.commit()
                    bot.send_message(messageChatID, f"Now Polling for Sheet: '{sheetByName.sheet_name}'", reply_to_message_id=messageID)
                    time.sleep(1)
                else:
                    time.sleep(1)
                    bot.send_message(messageChatID, "No such sheets exists. Please try again.", reply_to_message_id=messageID)
            except Exception as e:
                time.sleep(5)
                bot.send_message(main_chat_id, f"ERROR on poll: {e}")
                time.sleep(5)





@app.task
def set_notifications_task(messageID, messageText, messageChatID):
    with Session(bind=engine) as session:
        with session.begin():
            try:


                check_for_sheet_updates(session)



                try:
                    commandText = messageText.split("/set_notifications ")[1]

                    if "id=" not in commandText:
                        bot.send_message(messageChatID, "Please provide a telegram chat id. \nExample: 'id=-000434323'", reply_to_message_id=messageID)
                        return
                    
                    sheetName = commandText.split(" id=")[0]

                    telegramChatID = commandText.split(" id=")[1]
                    telegramChatID = telegramChatID.replace(" ", "").strip()

                    if len(telegramChatID) < 10:
                        bot.send_message(messageChatID, "Please provide a valid telegram chat id.", reply_to_message_id=messageID)
                        return
                    

                except:
                    bot.send_message(messageChatID, "Invalid Command. Invalid Format.", reply_to_message_id=messageID)
                    return
                

                sheetByName = session.query(Sheet_Instance).filter(Sheet_Instance.sheet_name_lower == sheetName.lower()).first()
                sheetByName.notification_chat_id = telegramChatID
                # session.commit()

                bot.send_message(main_chat_id, f"Notfication Chat Group Changed Successfully.")
            except Exception as e:
                time.sleep(5)
                bot.send_message(main_chat_id, f"ERROR on set_notif: {e}")
                time.sleep(5)









@app.task
def end_polling_task(messageID, messageText, messageChatID):
    with Session(bind=engine) as session:
        with session.begin():
            try:

                check_for_sheet_updates(session)
                time.sleep(1)



                try:
                    sheetName = messageText.split("/end ")[1].lower()
                except Exception:
                    bot.send_message(messageChatID, "Invalid Command. Invalid Format.", reply_to_message_id=messageID)
                    return
                
                sheetByName = session.query(Sheet_Instance).filter(Sheet_Instance.sheet_name_lower == sheetName).first()
                if sheetByName:
                    sheetByName.active = False
                    # session.commit()
                    bot.send_message(messageChatID, f"Polling Ended for Sheet: '{sheetByName.sheet_name}'", reply_to_message_id=messageID)
                    time.sleep(1)
                else:
                    time.sleep(1)
                    bot.send_message(messageChatID, "No such sheets exists. Please try again.", reply_to_message_id=messageID)
            except Exception as e:
                time.sleep(5)
                bot.send_message(main_chat_id, f"ERROR on end: {e}")
                time.sleep(5)






















@app.task
def change_keys_task(messageID, messageText, messageChatID):
    with Session(bind=engine) as session:
        with session.begin():
            try:
                check_for_sheet_updates(session)
                time.sleep(1)
                try:
                    commandText = messageText.split("/changekeys ")[1]

                    sheetName = commandText.split(" key=")[0].replace("\n", "").replace("\t", "")
                    if "secret=" in sheetName:
                        sheetName = commandText.split(" secret=")[0].replace("\n", "").replace("\t", "")
                        if "key=" in sheetName:
                            bot.send_message(messageChatID, "Invalid Command. Invalid Format.", reply_to_message_id=messageID)
                            return
                    
                    sheetNameLower = sheetName.lower()
                    
            
            
                except:
                    bot.send_message(messageChatID, "Invalid Command. Please Try Again.", reply_to_message_id=messageID)
                    return
                

                if sheetNameLower.strip() == "" or sheetNameLower == " " or sheetNameLower.strip() == " " or len(sheetNameLower) < 2 or len(sheetNameLower.strip()) < 2:
                    bot.send_message(messageChatID, "Invalid Command. Sheet Name must be include characters and have a length more than 2.", reply_to_message_id=messageID)
                    return

                if len(sheetNameLower) > 50:
                    bot.send_message(messageChatID, "Invalid Command. Sheet Name must be less than 50 characters.", reply_to_message_id=messageID)
                    return


                if " symbol=" not in commandText:
                    bot.send_message(messageChatID, "Invalid Command. Please specifiy Binance Symbol like so: 'symbol=BTCBUSD' without quotation marks.", reply_to_message_id=messageID)
                    return
                    
                binance_api_key = commandText.split(" key=")[1].split(" ")[0]

                binance_api_secret = commandText.split(" secret=")[1].split(" ")[0]

                binance_symbol = commandText.split(" symbol=")[1].split(" ")[0]

                binance_symbol = binance_symbol.replace(" ", "").strip()
                binance_symbol = binance_symbol.upper()

                binance_api_secret = binance_api_secret.replace(" ", "").strip()
                binance_api_key = binance_api_key.replace(" ", "").strip()

                if len(binance_api_key) != 64:
                    bot.send_message(messageChatID, "Invalid API Key.", reply_to_message_id=messageID)
                    return
                    
                if len(binance_api_secret) != 64:
                    bot.send_message(messageChatID, "Invalid Secret Key.", reply_to_message_id=messageID)
                    return
                    
                if len(binance_symbol) < 3:
                    bot.send_message(messageChatID, "Invalid Symbol Key.", reply_to_message_id=messageID)
                    return
                

                sheetByName = session.query(Sheet_Instance).filter(Sheet_Instance.sheet_name_lower == sheetNameLower).first()
                if not sheetByName:
                    bot.send_message(messageChatID, "Invalid Command. Sheet does not exist. Please Try Again.", reply_to_message_id=messageID)
                    return
                
                try:
                    time.sleep(0.5)
                    client = Client(api_key=binance_api_key, api_secret=binance_api_secret, testnet=False)
                    trades = client.get_my_trades(symbol=binance_symbol, startTime=1661992588000)
                    time.sleep(0.5)
                except Exception as e:
                    time.sleep(3)
                    bot.send_message(main_chat_id, f"Error!: {e}\n\nThis seems to relate to your Binance API Keys. They are incorrect in some way. Please try again with working keys. Make sure permissions are correct!", disable_web_page_preview=True, parse_mode="HTML")
                    time.sleep(3)
                    return


                sheetByName.api_key = binance_api_key
                sheetByName.api_secret = binance_api_secret
                sheetByName.symbol = binance_symbol
                # session.commit()

                bot.send_message(messageChatID, "Successfully Changed Binance API Details!", reply_to_message_id=messageID)




            except:
                bot.send_message(messageChatID, "Invalid Command. Please Try Again.", reply_to_message_id=messageID)
                return
































@app.task
def new_sheet_task(messageID, messageText, messageChatID):
    with Session(bind=engine) as session:
        with session.begin():
            try:

                try:
                    commandText = messageText.split("/new ")[1]

                    sheetName = commandText.split(" key=")[0].replace("\n", "").replace("\t", "")
                    if "secret=" in sheetName:
                        sheetName = commandText.split(" secret=")[0].replace("\n", "").replace("\t", "")
                        if "key=" in sheetName:
                            bot.send_message(messageChatID, "Invalid Command. Invalid Format.", reply_to_message_id=messageID)
                            return
                    

                    sheetNameLower = sheetName.lower()

                    if sheetNameLower.strip() == "" or sheetNameLower == " " or sheetNameLower.strip() == " " or len(sheetNameLower) < 2 or len(sheetNameLower.strip()) < 2:
                        bot.send_message(messageChatID, "Invalid Command. Sheet Name must be include characters and have a length more than 2.", reply_to_message_id=messageID)
                        return

                    if len(sheetNameLower) > 50:
                        bot.send_message(messageChatID, "Invalid Command. Sheet Name must be less than 50 characters.", reply_to_message_id=messageID)
                        return


                    if " key=" not in commandText:
                        bot.send_message(messageChatID, "Invalid Command. Please specifiy Binance API Key like so: 'key=iNpUtKeYhErE' without quotation marks.", reply_to_message_id=messageID)
                        return
                    
                    if " secret=" not in commandText:
                        bot.send_message(messageChatID, "Invalid Command. Please specifiy Binance Secret Key like so: 'secret=iNpUtSeCretHErE' without quotation marks.", reply_to_message_id=messageID)
                        return
                    
                    if " symbol=" not in commandText:
                        bot.send_message(messageChatID, "Invalid Command. Please specifiy Binance Symbol like so: 'symbol=BTCBUSD' without quotation marks.", reply_to_message_id=messageID)
                        return
                    
                    binance_api_key = commandText.split(" key=")[1].split(" ")[0]

                    binance_api_secret = commandText.split(" secret=")[1].split(" ")[0]

                    binance_symbol = commandText.split(" symbol=")[1].split(" ")[0]

                    binance_symbol = binance_symbol.replace(" ", "").strip()
                    binance_symbol = binance_symbol.upper()

                    binance_api_secret = binance_api_secret.replace(" ", "").strip()
                    binance_api_key = binance_api_key.replace(" ", "").strip()

                    if len(binance_api_key) != 64:
                        bot.send_message(messageChatID, "Invalid API Key.", reply_to_message_id=messageID)
                        return
                    
                    if len(binance_api_secret) != 64:
                        bot.send_message(messageChatID, "Invalid Secret Key.", reply_to_message_id=messageID)
                        return
                    
                    if len(binance_symbol) < 3:
                        bot.send_message(messageChatID, "Invalid Symbol Key.", reply_to_message_id=messageID)
                        return

                        
                    

                except:
                    bot.send_message(messageChatID, "Invalid Command. Invalid Format.", reply_to_message_id=messageID)
                


                check_for_sheet_updates(session)
                time.sleep(1)

                worksheet_list = spreadsheet.worksheets()

                


                worksheetNames = []

                for eachWorksheet in worksheet_list:
                    worksheetNames.append(eachWorksheet.title.lower())
                



                


                








                if sheetNameLower in worksheetNames:
                    bot.send_message(messageChatID, "Sheet Already Exists with this name. Please try again with a new name.", reply_to_message_id=messageID)
                    return


                

                sheetByName = session.query(Sheet_Instance).filter(Sheet_Instance.sheet_name_lower == sheetNameLower).first()
                if sheetByName:
                    bot.send_message(messageChatID, "Sheet Already Exists with this name. Please try again with a new name.", reply_to_message_id=messageID)
                    return
                
                sheetByApiKey = session.query(Sheet_Instance).filter(Sheet_Instance.api_key == binance_api_key).first()
                if sheetByApiKey:
                    bot.send_message(messageChatID, "Sheet Already Exists with this API Key. Please try again with a new API Key.", reply_to_message_id=messageID)
                    return
                
                sheetBySecretKey = session.query(Sheet_Instance).filter(Sheet_Instance.api_secret == binance_api_secret).first()
                if sheetBySecretKey:
                    bot.send_message(messageChatID, "Sheet Already Exists with this Secret Key. Please try again with a new Secret Key.", reply_to_message_id=messageID)
                    return
                

                try:
                    client = Client(api_key=binance_api_key, api_secret=binance_api_secret, testnet=False)
                    trades = client.get_my_trades(symbol=binance_symbol, startTime=1661992588000)
                except Exception as e:
                    time.sleep(3)
                    bot.send_message(main_chat_id, f"Error!: {e}\n\nThis seems to relate to your Binance API Details. They are incorrect in some way. Please try again with working keys and make sure the right symbol is used. Make sure permissions are correct!", disable_web_page_preview=True, parse_mode="HTML")
                    time.sleep(3)
                    return
                

                worksheet = spreadsheet.add_worksheet(title=sheetName, rows=1000, cols=40)
                time.sleep(0.5)
                set_row_height(worksheet, '1:1000', 20)
                time.sleep(0.5)
                set_column_width(worksheet, 'A:AN', 115)
                time.sleep(0.5)
                set_column_width(worksheet, 'G:AN', 155)


                rows = [
                    [sheetName, "", "", "", "", "", "", "Starting Time", "", "", "", "", "", "", "", "", "", "", "", ""],
                    ["", "", "", "", "", "", "", datetime.datetime.fromtimestamp(int(str(time.time()).split(".")[0]) * 1000 / 1000).strftime("%d/%m/%Y %H:%M:%S"), "", "", "", "", "", "", "", "", "", "", "", ""],
                    ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
                    ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
                    ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
                    ["", "", "", "", "", "", '"=CUSTOM EQUATION1"', '"=CUSTOM EQUATION2"', '"=CUSTOM EQUATION2"', '"=etc"', '"=etc"', "", "", "", "", "", "", "", "", ""],
                    ["Date Time", "Timestamp", "Trade Direction", "Qty", "QuoteQty", "Execution Price", "CUSTOM COLUMN1", "CUSTOM COLUMN2", "CUSTOM COLUMN3", "etc", "etc", "", "", "", "", "", "", "", "", ""]
                ]

                worksheet.append_rows(rows, value_input_option='USER_ENTERED')

                



                newSheetInstance = Sheet_Instance(api_key=binance_api_key, api_secret=binance_api_secret, symbol=binance_symbol, gid=worksheet.id, sheet_name=sheetName, sheet_name_lower=sheetNameLower, active=False)

                session.add(newSheetInstance)
                # session.commit()

                bot.send_message(messageChatID, f"Sheet has been created! ✅\nTo start polling binance for trades, type:\n`/poll {sheetName}`", parse_mode="Markdown", reply_to_message_id=messageID)
            except Exception as e:
                time.sleep(6)
                bot.send_message(main_chat_id, f"ERROR on NEWSHEET: {e}")














# -------------------------------------




























































def get_sheet_rows(sheet):
    sheetRows = sheet.get_all_values()
    return sheetRows


def get_latest_timestamp(sheetRows, sheet):
    latest_timestamp = sheetRows[1][7]
    try:
        latest_timestamp = int((str((datetime.datetime.strptime(latest_timestamp, "%d/%m/%Y %H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp()) * 1000)).split(".")[0])
    except:
        timestampInt = int(str(time.time()).split(".")[0]) * 1000
        resetTimestamp = datetime.datetime.fromtimestamp(timestampInt / 1000).strftime("%d/%m/%Y %H:%M:%S")
        sheet.update('H2', resetTimestamp)
        time.sleep(0.5)
        latest_timestamp = "RESET"

    if len(sheetRows) >= 8:
        for x in range(7, len(sheetRows)):
            if len(str(sheetRows[x][1])) == 13 and str(sheetRows[x][1]) != "":
                latest_timestamp = int(sheetRows[x][1]) + 1
                break
    
    
    return latest_timestamp




def parse_trades(trades):
    filteredTrades = {}
    for eachTrade in trades:
        if eachTrade["time"] not in filteredTrades:
            filteredTrades[eachTrade["time"]] = {"raw_trades": [eachTrade]}
        else:
            filteredTrades[eachTrade["time"]]["raw_trades"].append(eachTrade)
    

    for eachTradeTimestamp in filteredTrades:
        rawTrades = filteredTrades[eachTradeTimestamp]["raw_trades"]
        side = ""
        executionPricesToQuantity = []
        totalQtySize = 0
        totalQuoteQtySize = 0

        for index, eachRawTrade in enumerate(rawTrades, start=0):
            if index == 0:
                if eachRawTrade["isBuyer"] == False:
                    side = "Sell"
                else:
                    side = "Buy"
            
            executionPricesToQuantity.append([float(eachRawTrade["price"]), float(eachRawTrade["qty"]), float(eachRawTrade["quoteQty"])])
            totalQtySize += float(eachRawTrade["qty"])
            totalQuoteQtySize += float(eachRawTrade["quoteQty"])
        
        partTwoCalculationQty = 0
        partTwoCalculationQuoteQty = 0

        for eachExecPriceToQuantity in executionPricesToQuantity:
            partTwoCalculationQty += (eachExecPriceToQuantity[1] / eachExecPriceToQuantity[0])
            partTwoCalculationQuoteQty += (eachExecPriceToQuantity[2] / eachExecPriceToQuantity[0])
        
        averageExecutionPriceBasedOnQty = totalQtySize / partTwoCalculationQty
        averageExecutionPriceBasedOnQuoteQty = totalQuoteQtySize / partTwoCalculationQuoteQty

        filteredTrades[eachTradeTimestamp]["side"] = side
        filteredTrades[eachTradeTimestamp]["totalOrderSizeQty"] = totalQtySize
        filteredTrades[eachTradeTimestamp]["avgExecPriceQty"] = round(averageExecutionPriceBasedOnQty, 8)
        filteredTrades[eachTradeTimestamp]["totalOrderSizeQuoteQty"] = totalQuoteQtySize
        filteredTrades[eachTradeTimestamp]["avgExecPriceQuoteQty"] = round(averageExecutionPriceBasedOnQuoteQty, 8)
    

    return filteredTrades



def get_formulas_added(sheetRows):
    formulas = []
    for x in range(6, len(sheetRows[2])):
        formula = sheetRows[5][x]
        if len(formula) >= 2:
            if formula[0] == '"':
                formula = formula[1:]
            if formula[len(formula)-1] == '"':
                formula = formula[:-1]


        # formula = sheetRows[5][x].replace('"', "")
        formulas.append(formula)
    
    return formulas



def update_google_sheet(sheet, filteredTrades, formulas, telegram_chat_id):
    if len(filteredTrades) == 0:
        return
    
    rows = []
    for eachTradeTimestamp in filteredTrades:
        side = filteredTrades[eachTradeTimestamp]["side"]
        totalOrderSizeQty = filteredTrades[eachTradeTimestamp]["totalOrderSizeQty"]
        avgExecutionPriceQty = filteredTrades[eachTradeTimestamp]["avgExecPriceQty"]
        totalOrderSizeQuoteQty = filteredTrades[eachTradeTimestamp]["totalOrderSizeQuoteQty"]

        created_at = datetime.datetime.fromtimestamp(eachTradeTimestamp / 1000)
        created_at_string = created_at.strftime("%d/%m/%Y %H:%M:%S")



        row = [created_at_string, eachTradeTimestamp, side, totalOrderSizeQty, totalOrderSizeQuoteQty, avgExecutionPriceQty]

        for eachFormula in formulas:
            row.append(eachFormula)

        rows.append(row)
    
    for eachRow in rows:
        time.sleep(2)
        sheet.insert_row(eachRow, 8, value_input_option='USER_ENTERED')
    
    if len(rows) > 5:
        bot.send_message(telegram_chat_id, f"Sheet: {sheet.title}\n\nMore Than 5 Trades Added ✅", parse_mode="HTML")
        time.sleep(2)
    else:
        for eachRow in rows:
            tgMessage = f"""<b>{sheet.title}</b>\n\n  <b>Side: {eachRow[2]}</b>\n  <b>Price: {round(eachRow[5], 4)}</b>\n  <b>Qty: {round(eachRow[3], 10)}</b>\n  <b>Quote Qty: {round(eachRow[4], 7)}</b>\n\n{eachRow[0]}\n<b><a href="https://docs.google.com/spreadsheets/d/1BW-MPL4W-EcRSc_gPq6s8Dk5iGyaoTFoxYh7UlifOSk/edit#gid={sheet.id}">Google Sheet</a></b>"""
            bot.send_message(telegram_chat_id, tgMessage, parse_mode="HTML", disable_web_page_preview=True)
            time.sleep(3)







def poll_sheets(session):
    time.sleep(1)
    sheetInstances = session.query(Sheet_Instance).filter(Sheet_Instance.active == True).all()

    for eachSheetInstance in sheetInstances:
        try:

            print(f"Polling for:  {eachSheetInstance.sheet_name}")
            check_for_sheet_updates(session)
            time.sleep(1.5)
            try:
                client = Client(api_key=eachSheetInstance.api_key, api_secret=eachSheetInstance.api_secret, testnet=False)
            except Exception as e:
                # bot.send_message(main_chat_id, f"Client not connecting. {e}", disable_web_page_preview=True)
                sheetInstance = session.query(Sheet_Instance).filter(Sheet_Instance.id == eachSheetInstance.id).first()
                sheetInstance.active = False
                bot.send_message(main_chat_id, f"Error!: {e}\n\nThis seems to relate to your Binance API Keys Used for sheet '{eachSheetInstance.sheet_name}'.\n\nDue to this error, the sheet has been disabled.\nIf you have fixed the error, please type this command to resume:\n`/poll {eachSheetInstance.sheet_name}`", disable_web_page_preview=True, parse_mode="Markdown")
                time.sleep(5)
                
                return

            googleSheet = spreadsheet.worksheet(eachSheetInstance.sheet_name)


            sheetRows = get_sheet_rows(googleSheet)
            formulas = get_formulas_added(sheetRows)
            latest_timestamp = get_latest_timestamp(sheetRows, googleSheet)

            if latest_timestamp == "RESET":
                sheetInstance = session.query(Sheet_Instance).filter(Sheet_Instance.id == eachSheetInstance.id).first()
                sheetInstance.active = False
                # session.commit()
                bot.send_message(main_chat_id, f"Error!: \n\nThe 'Starting Time' format is wrong or an invalid date was used for sheet '{eachSheetInstance.sheet_name}'.\n\nDue to this error, the sheet has been disabled and the suggested time has been reset on the spreadsheet.\n If you are happy with the time on spreadsheet, please type this command to resume:\n`/poll {eachSheetInstance.sheet_name}`", disable_web_page_preview=True, parse_mode="Markdown")
                time.sleep(1)
                return


            try:
                trades = client.get_my_trades(symbol=eachSheetInstance.symbol, startTime=latest_timestamp)
            except Exception as e:
                time.sleep(3)
                sheetInstance = session.query(Sheet_Instance).filter(Sheet_Instance.id == eachSheetInstance.id).first()
                sheetInstance.active = False
                # session.commit()
                bot.send_message(main_chat_id, f"Error!: {e}\n\nThis seems to relate to your Binance API Keys or Symbol Used for sheet '{eachSheetInstance.sheet_name}'.\n\nDue to this error, the sheet has been disabled.\nIf you have fixed the error, please type this command to resume:\n`/poll {eachSheetInstance.sheet_name}`", disable_web_page_preview=True, parse_mode="Markdown")
                time.sleep(3)
                return
                
            filteredTrades = parse_trades(trades)
            update_google_sheet(googleSheet, filteredTrades, formulas, eachSheetInstance.notification_chat_id)
        
        except Exception as e:
            print(e)
            time.sleep(2)
            sheetInstance = session.query(Sheet_Instance).filter(Sheet_Instance.id == eachSheetInstance.id).first()
            sheetInstance.active = False
            print("error active")
            # session.commit()
            
            bot.send_message(main_chat_id, f"Error!: {e}\n\n '{eachSheetInstance.sheet_name}'.\n\nDue to this error, the sheet has been disabled.\nIf you have fixed the error, please type this command to resume:\n`/poll {eachSheetInstance.sheet_name}`", disable_web_page_preview=True, parse_mode="Markdown")
            return




        






@app.task
def poll_task():
    with Session(bind=engine) as session:
        with session.begin():
            check_for_sheet_updates(session)
            poll_daily_profit(session)
            poll_sheets(session)
            time.sleep(5)































if __name__ == '__main__':
    app.start()