import sys
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt
from panel import Ui_MainWindow
from qasync import QEventLoop, asyncSlot
from func import telegram_panel
from code_dialog import CodeDialog, AsyncMessageBox
from pyrogram import (Client,errors,enums)
import os, random, shutil, sqlite3, traceback , time , json , re
from datetime import datetime

os.makedirs('data', exist_ok=True)
os.makedirs('account', exist_ok=True)
os.makedirs('delete', exist_ok=True)


Status = False
Extract = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        
        self.ui.setupUi(self)
        self.setFixedSize(self.size())
        self.acclistupdate()
        self.ui.add_account.clicked.connect(self.add_account_proc)
        self.ui.remove_account_bot.clicked.connect(self.remove_account)
        self.ui.update_number_bot.clicked.connect(self.acclistupdate)
        self.ui.btn_start_forward.clicked.connect(self.forward_Channel)
        self.ui.btn_stop_forward.clicked.connect(self.disable_forward_Channel)
        self.ui.tab_account.currentChanged.connect(self.update_list_tab)
    
    
    
    def update_list_tab(self, index):
        if index == 0:
            r = telegram_panel.list_accounts()
            self.ui.list_account_ac.clear()
            self.ui.list_account_ac.addItems(r)
            self.ui.lcdNumber.display(len(r))
        if index == 1:
            r = telegram_panel.list_accounts()
            self.ui.combo_select_account.clear()
            self.ui.combo_select_account.addItems(r)
        return
    
    
    
    @asyncSlot()
    async def ask_code_dialog(self, title, label):
        dlg = CodeDialog(title, label, self)
        dlg.setModal(True)
        dlg.show()
        while dlg.result() == 0:
            await asyncio.sleep(0.1)

        if dlg.result() == 1:
            return dlg.get_value(), True
        else:
            return "", False
    
    
    @asyncSlot()
    async def show_async_message(self, title, message, icon=QMessageBox.Icon.Information):
        dlg = AsyncMessageBox(title, message, icon, self)
        dlg.show()

        while dlg.result is None:
            await asyncio.sleep(0.05)

        return dlg


    def do_long_task(self):
        dlg = QProgressDialog("Processing ...", None, 0, 0, self)
        dlg.setWindowTitle("Please wait.")
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)
        dlg.show()
        return dlg


    @asyncSlot()
    async def add_account_proc(self):
        phone = self.ui.account_input_add.text().strip()

        if len(phone) < 4:
            # QMessageBox.critical(self, "Wrong", "Phone number is too short.")
            await self.show_async_message("Wrong", "Phone number is too short.", icon=QMessageBox.Icon.Critical)

            return

        if not phone.startswith("+") or not phone[1:].isdigit():
            # QMessageBox.critical(self, "Wrong", "Phone number must start with '+' and contain only digits after it.")
            await self.show_async_message("Wrong", "Phone number must start with '+' and contain only digits after it.", icon=QMessageBox.Icon.Critical)
            return

        if phone == "+123456789":
            # QMessageBox.critical(self, "Wrong", "Sample phone number is not allowed.")
            await self.show_async_message("Wrong", "Sample phone number is not allowed.", icon=QMessageBox.Icon.Critical)
            return

        dlg = self.do_long_task()
        r = await telegram_panel.add_account(phone)
        dlg.close()

        if not r["status"]:
            # QMessageBox.critical(self, "Error", r["message"])
            await self.show_async_message("Error", str(r["message"]), icon=QMessageBox.Icon.Critical)
            return

        # ورود کد
        for _ in range(3):
            # text, ok = QInputDialog.getText(self, "Account login code", "Enter the 5-digit code:")
            text, ok = await self.ask_code_dialog( "Account login code", "Enter the 5-digit code:")
            for _ in range(10):
                if not ok:
                    break
                if text.isdigit() and len(text) == 5:
                    break
                else:
                    # text, ok = QInputDialog.getText(self, "Account login code", "Enter the 5-digit code:")
                    text, ok = await self.ask_code_dialog( "Account login code", "Enter the 5-digit code:")

            if not ok:
                await telegram_panel.cancel_acc(r["cli"], r["phone"])
                # QMessageBox.critical(self, "Error", "Canceled by user.")
                await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
                return

            dlg = self.do_long_task()
            rs = await telegram_panel.get_code(r["cli"], r["phone"], r["code_hash"], text)
            dlg.close()

            if rs["status"]:
                # QMessageBox.information(self, "Success", rs["message"])
                await self.show_async_message("Success", rs["message"], icon=QMessageBox.Icon.Information)
                telegram_panel.make_json_data(r["phone"], r["api_id"], r["api_hash"], r["proxy"], "")
                return

            if rs["message"] == "invalid_code":
                # QMessageBox.critical(self, "Error", "Invalid code.")
                await self.show_async_message("Error", "Invalid code.", icon=QMessageBox.Icon.Critical)
                continue

            if rs["message"] == "FA2":
                for _ in range(3):
                    # text, ok = QInputDialog.getText(self, "Account password", "Enter the password:")
                    text, ok = await self.ask_code_dialog("Account password", "Enter the password:")
                    if not ok:
                        await telegram_panel.cancel_acc(r["cli"], r["phone"])
                        # QMessageBox.critical(self, "Error", "Canceled by user.")
                        await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
                        return

                    dlg = self.do_long_task()
                    rsp = await telegram_panel.get_password(r["cli"], r["phone"], text)
                    dlg.close()

                    if rsp["status"]:
                        # QMessageBox.information(self, "Success", rsp["message"])
                        await self.show_async_message("Success", rsp["message"], icon=QMessageBox.Icon.Information)
                        telegram_panel.make_json_data(r["phone"], r["api_id"], r["api_hash"], r["proxy"], text)
                        return

                    if rsp["message"] == "invalid_password":
                        # QMessageBox.critical(self, "Error", "Invalid password.")
                        await self.show_async_message("Error", "Invalid password.", icon=QMessageBox.Icon.Critical)
                        continue
                    else:
                        # QMessageBox.critical(self, "Error", rsp["message"])
                        await self.show_async_message("Error", rsp["message"], icon=QMessageBox.Icon.Critical)
                        return

            if rs["message"]:
                # QMessageBox.critical(self, "Error", rs["message"])
                await self.show_async_message("Error", rs["message"], icon=QMessageBox.Icon.Critical)
                return

        try:await telegram_panel.cancel_acc(r["cli"], r["phone"])
        except:pass
        # QMessageBox.critical(self, "Error", "Canceled by user.")
        await self.show_async_message("Error", "Canceled by user.", icon=QMessageBox.Icon.Critical)
        return

    def remove_account(self):
        phone = self.ui.remove_account_input.text().strip()
        if phone in telegram_panel.list_accounts():
            telegram_panel.remove_account(phone)
            QMessageBox.information(self, "Success", "Account removed.")
        else:
            QMessageBox.critical(self, "Error", "Account not found.")
        return
    

    def acclistupdate(self,log=True):
        r = telegram_panel.list_accounts()
        self.ui.list_account_ac.clear()
        self.ui.list_account_ac.addItems(r)
        self.ui.lcdNumber.display(len(r))
        if not log:
            QMessageBox.information(self, "Success", "Account list updated.")
        return
    
        
    
    @asyncSlot()
    async def disable_forward_Channel(self):
        global Extract
        if Extract:
            Extract = False
            self.ui.lbl_status.setText("Status: Inactive")
            # QMessageBox.information(self, "Success", "Extraction stopped.")
            await self.show_async_message("Success", "Extraction stopped.", icon=QMessageBox.Icon.Information)
        else:
            # QMessageBox.critical(self, "Error", "Extraction is not active.")
            await self.show_async_message("Error", "Extraction is not active.", icon=QMessageBox.Icon.Critical)
        return
        
    
    @asyncSlot()
    async def forward_Channel(self):
        global Extract
        
        self.ui.forward_log.clear()
        self.ui.forward_log.setReadOnly(True)
        
        if len(telegram_panel.list_accounts()) == 0:
            # QMessageBox.critical(self, "Error", "No accounts found.")
            await self.show_async_message("Error", "No accounts found.", icon=QMessageBox.Icon.Critical)
            return
        if Extract:
            # QMessageBox.critical(self, "Error", "Already extracting.")
            await self.show_async_message("Error", "Already extracting.", icon=QMessageBox.Icon.Critical)
            return
        
        phone = self.ui.combo_select_account.currentText()
        
        fromchat = self.ui.source_channel_input.text().strip()
        forchat = self.ui.dest_channel_input.text().strip()
        if telegram_panel.is_valid_telegram_link(fromchat) or fromchat.startswith("-100") and fromchat.replace("-100","").isdigit() and telegram_panel.is_valid_telegram_link(forchat) or forchat.startswith("-100") and forchat.replace("-100","").isdigit():
            Extract = True
            self.ui.lbl_status.setText("Status: Active")
            asyncio.create_task(self.forward_proc(phone,fromchat,forchat))
        else:
            # QMessageBox.critical(self, "Error", "Invalid Telegram link.")
            await self.show_async_message("Error", "Invalid Telegram link.", icon=QMessageBox.Icon.Critical)
        return
    
    
    async def forward_proc(self,phone , fromchat , forchat):
        global Extract
        
        
        self.ui.forward_log.appendPlainText("Extracting {}...".format(phone))
        data = telegram_panel.get_json_data(phone)
        proxy = await telegram_panel.get_proxy(data["proxy"])
        cli = Client('account/{}'.format(phone), data["api_id"], data["api_hash"], proxy=proxy[0])
        await asyncio.wait_for(cli.connect() , 15)
        self.ui.forward_log.appendPlainText("Connected to {}.".format(phone))
        if fromchat.startswith("-100") :
            chtd = int(fromchat)
            join = await telegram_panel.get_chat(cli,chtd)
        else:
            join = await telegram_panel.Join(cli,fromchat)
        if forchat.startswith("-100") :
            chtdfor = int(forchat)
            joinfor = await telegram_panel.get_chat(cli,chtdfor)
        else:
            joinfor = await telegram_panel.Join(cli,forchat)
        if len(join) != 3 and len(joinfor) != 3:
            Extract = False
            try:await cli.disconnect()
            except:pass
            # QMessageBox.critical(self, "Error", "Failed to join the channel.")
            self.ui.forward_log.appendPlainText("Failed to join the channel.\n{}".format(join[0]))
            await self.show_async_message("Error", "Failed to join the channel.", icon=QMessageBox.Icon.Critical)
            return
        chat= await cli.get_chat(join[0])
        chatfor = await cli.get_chat(joinfor[0])
        async for messagae in cli.get_chat_history(chat_id=chat.id,limit=1):
            ofss = messagae.id
            countmsg = messagae.id
        ana_count = 0
        okmsg = 0
        badmsg = 0
        #self.ui.forward_log.appendPlainText("Number of chat messages: {}".format(countmsg))
        for _ in range(10):
            if ofss == 1:break
            if Extract == False:break
            try:
                async for messagae in cli.get_chat_history(chat_id=chat.id,max_id=ofss,limit=countmsg):
                    if Extract == False:break
                    ofss = messagae.id
                    if ofss == 1:break
                    ana_count += 1
                    try:
                        if messagae.text:
                            sent_message = await cli.send_message(
                                chat_id=chatfor.id,
                                text=messagae.text,
                                entities=messagae.entities,
                                disable_web_page_preview=True
                            )
                        
                        elif messagae.photo:
                            path = await messagae.download()
                            
                            sent_message = await cli.send_photo(
                                chat_id=chatfor.id,
                                photo=path,
                                caption=messagae.caption,
                                caption_entities=messagae.caption_entities,
                            )
                            os.remove(path)
                        
                        elif messagae.video:
                            path = await messagae.download()
                            sent_message = await cli.send_video(
                                chat_id=chatfor.id,
                                video=path,
                                caption=messagae.caption,
                                caption_entities=messagae.caption_entities,
                                duration=messagae.video.duration,
                                width=messagae.video.width,
                                height=messagae.video.height,
                                # thumb=messagae.video.thumbs[0].file_id if messagae.video.thumbs else None,
                                # supports_streaming=True
                            )
                            os.remove(path)
                        
                        elif messagae.document:
                            path = await messagae.download()
                            
                            sent_message = await cli.send_document(
                                chat_id=chatfor.id,
                                document=path,
                                caption=messagae.caption,
                                caption_entities=messagae.caption_entities,
                            )
                            os.remove(path)
                        
                        elif messagae.audio:
                            path = await messagae.download()
                            
                            sent_message = await cli.send_audio(
                                chat_id=chatfor.id,
                                audio=path,
                                caption=messagae.caption,
                                caption_entities=messagae.caption_entities,
                                duration=messagae.audio.duration,
                                performer=messagae.audio.performer,
                                title=messagae.audio.title,
                                # thumb=messagae.audio.thumbs[0].file_id if messagae.audio.thumbs else None,
                            )
                            os.remove(path)
                        
                        elif messagae.animation:
                            path = await messagae.download()
                            
                            sent_message = await cli.send_animation(
                                chat_id=chatfor.id,
                                animation=path,
                                caption=messagae.caption,
                                caption_entities=messagae.caption_entities,
                                duration=messagae.animation.duration,
                                width=messagae.animation.width,
                                height=messagae.animation.height,
                                # thumb=messagae.animation.thumbs[0].file_id if messagae.animation.thumbs else None,
                            )
                            os.remove(path)
                        
                        elif messagae.voice:
                            path = await messagae.download()
                            
                            sent_message = await cli.send_voice(
                                chat_id=chatfor.id,
                                voice=path,
                                caption=messagae.caption,
                                caption_entities=messagae.caption_entities,
                                duration=messagae.voice.duration,
                            )
                            os.remove(path)
                        else:
                            await messagae.copy(chatfor.id)
                        okmsg += 1
                    except Exception as e:
                        badmsg += 1
                        self.ui.forward_log.appendPlainText("Error : [{}]".format(e))
                    self.ui.success_count.display(okmsg)
                    self.ui.failed_count.display(badmsg)
                    self.ui.total_count.display(ana_count)
                    self.ui.forward_log.appendPlainText("[{}] {}".format(ana_count,messagae.id))
                        
                    await asyncio.sleep(0.1)
            except errors.FloodWait as e:
                self.ui.forward_log.appendPlainText("FloodWait: {}".format(e.value))
                await asyncio.sleep(e.value + random.randint(10, 35))    
            except Exception as e:
                self.ui.forward_log.appendPlainText("Error: {}".format(e))
                break
                
        Extract = False
        self.ui.lbl_status.setText("Status: Disactive")
        await cli.disconnect()
        self.ui.forward_log.appendPlainText("Disconnected from {}.".format(phone))
        self.ui.forward_log.appendPlainText("Extracted {} Massages.".format(ana_count))
        await self.show_async_message("Success", "Extracted {} Massages.".format(ana_count), icon=QMessageBox.Icon.Information)
        return
    
    def safe_filename(slef, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = name.strip().replace(' ', '_')
        return name or 'file'

                
if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()
