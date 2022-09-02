from email.policy import default
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, inspect
from database_settings import engine, Sheet_Instance
import os
import telebot

from binance.client import Client
import time
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
                
            
            
            session.commit()
        worksheetIDs.append(eachWorksheet.id)
    

    
    allSheetsNotOnGoogleQuery = session.query(Sheet_Instance).filter(Sheet_Instance.gid.not_in(worksheetIDs))
    allSheetsNotOnGoogle = allSheetsNotOnGoogleQuery.all()
    allSheetsNotOnGoogleQuery.delete()
    session.commit()

    for eachSheetNotOnGoogle in allSheetsNotOnGoogle:
        bot.send_message(main_chat_id, f"{eachSheetNotOnGoogle.sheet_name} Removed.")
        time.sleep(2)









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
            check_for_sheet_updates()
            time.sleep(1.5)
            try:
                client = Client(api_key=eachSheetInstance.api_key, api_secret=eachSheetInstance.api_secret, testnet=False)
            except Exception as e:
                bot.send_message(main_chat_id, f"Client not connecting. {e}", disable_web_page_preview=True)
                time.sleep(5)
                continue

            googleSheet = spreadsheet.worksheet(eachSheetInstance.sheet_name)


            sheetRows = get_sheet_rows(googleSheet)
            formulas = get_formulas_added(sheetRows)
            latest_timestamp = get_latest_timestamp(sheetRows, googleSheet)

            if latest_timestamp == "RESET":
                eachSheetInstance.active = False
                session.commit()
                bot.send_message(main_chat_id, f"Error!: \n\nThe 'Starting Time' format is wrong or an invalid date was used for sheet '{eachSheetInstance.sheet_name}'.\n\nDue to this error, the sheet has been disabled.\n please type this command to resume:\n`/poll {eachSheetInstance.sheet_name}`", disable_web_page_preview=True, parse_mode="Markdown")
                time.sleep(1)
                continue


            try:
                trades = client.get_my_trades(symbol=eachSheetInstance.symbol, startTime=latest_timestamp)
            except Exception as e:
                time.sleep(3)
                eachSheetInstance.active = False
                session.commit()
                bot.send_message(main_chat_id, f"Error!: {e}\n\nThis seems to relate to your Binance API Keys or Symbol Used for sheet '{eachSheetInstance.sheet_name}'.\n\nDue to this error, the sheet has been disabled.\nIf you have fixed the error, please type this command to resume:\n`/poll {eachSheetInstance.sheet_name}`", disable_web_page_preview=True, parse_mode="Markdown")
                time.sleep(3)
                continue
                
            filteredTrades = parse_trades(trades)
            update_google_sheet(googleSheet, filteredTrades, formulas, eachSheetInstance.notification_chat_id)
        
        except Exception as e:
            print(e)
            time.sleep(2)
            eachSheetInstance.active = False
            session.commit()
            bot.send_message(main_chat_id, f"Error!: {e}\n\n '{eachSheetInstance.sheet_name}'.\n\nDue to this error, the sheet has been disabled.\nIf you have fixed the error, please type this command to resume:\n`/poll {eachSheetInstance.sheet_name}`", disable_web_page_preview=True, parse_mode="Markdown")





        













def main():
    while True:
        try:

            with Session(bind=engine) as session:
                with session.begin():
                    check_for_sheet_updates(session)
                    poll_sheets(session)
                    time.sleep(3)
        except Exception as e:
            try:

                bot.send_message(main_chat_id, f"Error!: {e}", disable_web_page_preview=True)
                time.sleep(40)
            except:
                time.sleep(40)
                print("ERROR!")






if __name__ == "__main__":
    main()


