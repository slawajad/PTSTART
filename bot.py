import re
import logging
import os
import paramiko
import asyncpg
from dotenv import load_dotenv
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, CallbackQueryHandler, CallbackContext

logging.basicConfig(filename='logfile.txt',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.DEBUG,
    encoding="utf-8")
logging.debug('Отладочная информация.')
logging.info('модуль logging')
logging.warning('Предупреждение')
logging.error('Произошла шибка')
logging.critical('Критическая ошибка')

ASK_PACKAGE = 0
MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def split_message(text: str, limit: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> list[str]:
    """Разделяет сообщение на части, чтобы оно не превышало максимальную длину."""
    return [text[i:i + limit] for i in range(0, len(text), limit)]

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Команда отменена.")
    return ConversationHandler.END

def ssh(command):
    host = os.getenv("RM_HOST")
    port = int(os.getenv("RM_PORT"))
    username = os.getenv("RM_USER")
    password = os.getenv("RM_PASSWORD")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if error:
            return f"Ошибка: {error}"
        else:
            return output
    except Exception as e:
        return f"Произошло исключение: {str(e)}"
    finally:
        client.close()


async def db_query(query: str, args=None, fetch=True):
    try:
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_DATABASE")
        )
        if fetch:
            result = await conn.fetch(query, *args) if args else await conn.fetch(query)
        else:
            await conn.execute(query, *args) if args else await conn.execute(query)
            result = True
        
        return result
    except Exception as error:
        print(f"Ошибка при работе с PostgreSQL: {error}")
        return False  
    finally:
        if conn:
            await conn.close()
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    user = update.effective_user
    await update.message.reply_text(f'Привет, {user.full_name}! Чтобы узнать, что умеет бот, введите /help')
    
async def help_command(update: Update, context):
    logging.info('Команда /help')
    await update.message.reply_text('В данном боте вы можете воспользоваться следующими командами: \
    \n/find_email - Поиск email-адреса в сообщении\
    \n/find_phone_number - Поиск мобильных номеров в сообщении\
    \n/verify_password - Проверка сложности пароля\
    \n/get_release - О релизе подключенной ОС по SSH\
    \n/get_uname - Об архитектуре процессора ОС по SSH\
    \n/get_uptime - Время запуска подключеннойОС по SSH\
    \n/get_df - Состояние файловой системы подключенной ОС по SSH\
    \n/get_free - Состояние оперативной памяти подключенной ОС по SSH\
    \n/get_mpstat - Информация о производительности подключенной ОС по SSH\
    \n/get_w - Работающие пользователи в подключенной ОС по SSH\
    \n/get_auths - 10 последних вошедших пользователей подключенной ОС по SSH\
    \n/get_critical - 5 последних критических событий подключенной ОС по SSH\
    \n/get_ps - Запущенные процессы подключенной ОС по SSH\
    \n/get_ss - Работающие порты подключенной ОС по SSH\
    \n/get_apt_list - Информация о загруженных пакетах  и поиск пакетов на подключенной ОС по SSH\
    \n/get_services - Работающие сервисы на подключенной ОС по SSH\
    \n/get_repl_logs - Возвращает логи репликации БД\
    \n/get_emails - Выводит таблицу номеров из БД\
    \n/get_phone_numbers - Выводит таблицу номеров из БД')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

FIND_PHONE, CONFIRM_PHONE = range(2)
async def find_phone_numbersCommand (update:Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    await update.message.reply_text('Введите текст для поиска телефонных номеров: ')
    return FIND_PHONE

async def find_phone_number(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    phone_regex = re.compile(r'(?:\+7|8)[- ]?(?:\(\d{3}\)|\d{3})[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}')
    found_numbers = phone_regex.findall(text)

    if not found_numbers:
        await update.message.reply_text("Телефонные номера не найдены.")
        return ConversationHandler.END
    
    formatted_existing_numbers = [format_phone_number(num) for num in found_numbers]
    existing_numbers = await check_existing_numbers(formatted_existing_numbers)
    new_numbers = [num for num in found_numbers if format_phone_number(num) not in existing_numbers]

    if not new_numbers:
        await update.message.reply_text("Все найденные номера уже сохранены в базе данных.")
        return ConversationHandler.END

    message_lines = [f"{i + 1}. {num}" for i, num in enumerate(found_numbers)]
    message = "Уникальные номера телефонов которых нет в базе:\n" + "\n".join(message_lines)
    context.user_data['data_to_save'] = new_numbers

    keyboard = [
        [InlineKeyboardButton("Сохранить", callback_data='save_phone'),
         InlineKeyboardButton("Отмена", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup)
    return CONFIRM_PHONE

async def check_existing_numbers(numbers):
    existing_numbers = []
    try:
        for number in numbers:
            query = "SELECT phone_number FROM phone_numbers WHERE phone_number = $1"
            result = await db_query(query, args=(number,), fetch=True)
            if result:
                existing_numbers.append(number)
    except Exception as e:
        print(f"Ошибка при проверке существующих номеров: {e}")
    return existing_numbers

def format_phone_number(number):
    digits = re.sub(r'\D', '', number)
    if digits.startswith('8'):
        formatted = f"8 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif digits.startswith('7'):
        formatted = f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    else:
        formatted = number
    return formatted

async def save_data(data):
    query = "INSERT INTO phone_numbers (phone_number) VALUES ($1)"
    try:
        for item in data:
            formatted_number = format_phone_number(item)
            result = await db_query(query, args=(formatted_number,), fetch=False)
            if not result:
                raise Exception("Failed to insert data")
        return True
    except Exception as e:
        print(f"Произошла ошибка при сохранении данных: {e}")
        return False

async def button_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'save_phone':
        data_to_save = context.user_data.get('data_to_save', [])
        if data_to_save:
            result = await save_data(data_to_save)
            if result:
                await query.edit_message_text("Телефонные номера сохранены!")
            else:
                await query.edit_message_text("Ошибка сохранения данных")
        else:
            await query.edit_message_text("Нет данных для сохранения")
        return ConversationHandler.END
    elif query.data == 'save_emails':
        emails_to_save = context.user_data.get('emails_to_save', [])
        if emails_to_save:
            result = await save_emails(emails_to_save)
            if result:
                await query.edit_message_text("Email-адреса сохранены!")
            else:
                await query.edit_message_text("Ошибка при сохранении email-адресов")
        else:
            await query.edit_message_text("Нет email-адресов для сохранения")
        return ConversationHandler.END
    elif query.data == 'cancel':
        await query.edit_message_text("Сохранение отменено")
        return ConversationHandler.END
    

FIND_EMAIL, CONFIRM_EMAIL = range(2)   
async def find_emailCommand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Введите текст для поиска email-адресов: ')
    return FIND_EMAIL

async def find_email(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    emailRegex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    email_list = emailRegex.findall(user_input)

    if not email_list:
        await update.message.reply_text('Email-адреса не найдены')
        return ConversationHandler.END

    existing_emails = await check_existing_emails(email_list)
    new_emails = [email for email in email_list if email not in existing_emails]

    if not new_emails:
        await update.message.reply_text('Все найденные email-адреса уже сохранены.')
        return ConversationHandler.END

    message_lines = [f"{i + 1}. {email}" for i, email in enumerate(new_emails)]
    message = "Уникальные email-адреса которых нет в базе:\n" + "\n".join(message_lines)
    context.user_data['emails_to_save'] = new_emails

    keyboard = [
        [InlineKeyboardButton("Сохранить", callback_data='save_emails'),
         InlineKeyboardButton("Отмена", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)
    return CONFIRM_EMAIL

async def check_existing_emails(emails):
    existing_emails = []
    try:
        for email in emails:
            query = "SELECT email FROM email_addresses WHERE email = $1"
            result = await db_query(query, args=(email,), fetch=True)
            if result:
                existing_emails.extend([record['email'] for record in result])
    except Exception as e:
        print(f"Ошибка при проверке существующих email-адресов: {e}")
    return existing_emails

async def save_emails(emails):
    query = "INSERT INTO email_addresses (email) VALUES ($1)"
    try:
        for email in emails:
            existing_emails = await check_existing_emails([email])
            if not existing_emails:
                result = await db_query(query, args=(email,), fetch=False)
                if not result:
                    raise Exception(f"Ошибка добавления email: {email}")
        return True
    except Exception as e:
        return False

ASK_PASSWORD = 1
async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запускает диалог для проверки сложности пароля."""
    await update.message.reply_text(
        "Пожалуйста, введите пароль. Чтобы выйти из проверки, отправьте команду /cancel."
    )
    return ASK_PASSWORD

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверяет сложность введенного пользователем пароля."""
    password = update.message.text

    if re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$', password):
        await update.message.reply_text("Пароль сложный")
    else:
        await update.message.reply_text("Пароль простой")

    return ASK_PASSWORD

async def get_release(update: Update, context: CallbackContext) -> None:
    command = "cat /etc/os-release"
    
    release_info = ssh(command)
  
    await update.message.reply_text(release_info)

async def get_uname(update: Update, context: CallbackContext) -> None:
    command = "uname -a"
    
    system_info = ssh(command)

    await update.message.reply_text(system_info)

async def get_uptime(update: Update, context: CallbackContext) -> None:
    command = "uptime"
    uptime_info = ssh(command)

    await update.message.reply_text(uptime_info)

async def get_df(update: Update, context: CallbackContext) -> None:
    command = "df -h"

    df_info = ssh(command)

    await update.message.reply_text(df_info)
  

async def get_free(update: Update, context: CallbackContext) -> None:
    command = "free -h"
    
    free_info = ssh(command)
 
    await update.message.reply_text(free_info)

async def get_mpstat(update: Update, context: CallbackContext) -> None:
    command = "mpstat"
  
    mpstat_info = ssh(command)
   
    await update.message.reply_text(mpstat_info)

async def get_w(update: Update, context: CallbackContext) -> None:
    command = "w"
 
    w_info = ssh(command)

    await update.message.reply_text(w_info)

async def get_auths(update: Update, context: CallbackContext) -> None:
    command = "last -i -n 10"
    auths_info = ssh(command)

    results = []
    for line in auths_info.splitlines():
        parts = line.split()
        
        if len(parts) < 5:
            continue
        user = parts[0]
        if user == "reboot" or user == "shutdown":
            
            kernel_version = parts[2]
            date_time_str = " ".join(parts[3:8])
            results.append(f"Перезагрузка/выключение системы (ядро {kernel_version}): {date_time_str}\n--")
        else:
           
            host = parts[2]
            date_time_str = " ".join(parts[3:7])  
            results.append(f"Пользователь: {user}\nIP/Хост: {host}\nВремя: {date_time_str}\n--")
    formatted_result = "\n".join(results) or "Нет данных о последних авторизациях."
    await update.message.reply_text(formatted_result)
    
async def get_critical(update: Update, context: CallbackContext) -> None: 
    command = "journalctl -r -p crit -n 5"

    critical_info = ssh(command)
    
    await update.message.reply_text(critical_info)

async def get_ps(update: Update, context: CallbackContext) -> None:
    command = "ps"

    ps_info = ssh(command)
   
    await update.message.reply_text(ps_info)

async def get_ss(update, context) -> None:
    command = "ss -n"  
    ss_info = ssh(command)

    results = []
    for line in ss_info.splitlines():
        parts = line.split()

        if len(parts) < 5 or parts[0] == "Netid":
            continue

        local_address = parts[4] if ":" in parts[4] else None
        peer_address = parts[5] if len(parts) > 5 and ":" in parts[5] else None

        if local_address is None or peer_address is None:
            continue

        netid = parts[0]  
        state = parts[1] 

        results.append(
            f"Тип сокета: {netid}\nСостояние: {state}\nЛокальный адрес: {local_address}\nУдаленный адрес: {peer_address}\n--\n"
        )

    ss_info_formatted = "\n".join(results) or "Нет данных о текущих портах."

    if len(ss_info_formatted) > MAX_TELEGRAM_MESSAGE_LENGTH:
        messages = split_message(ss_info_formatted)
        for msg in messages:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text(ss_info_formatted)

    return ConversationHandler.END

async def start_get_apt_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Введите 'all' для отображения всех пакетов или укажите название пакета."
    )
    return ASK_PACKAGE

async def get_apt_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает список установленных пакетов или информацию об одном пакете."""
    user_input = update.message.text.strip().lower()

    if user_input == "all":
        command = "dpkg-query -W -f='${binary:Package}\n'"
    else:
        command = f"dpkg-query -W -f='${{binary:Package}} ${{Version}}\n' {user_input}"
    apt_info = ssh(command)

    if len(apt_info) > MAX_TELEGRAM_MESSAGE_LENGTH:
        messages = split_message(apt_info)
        for msg in messages:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text(apt_info or "Информация не найдена.")

    return ConversationHandler.END

async def get_services(update: Update, context: CallbackContext) -> None:
    command = "systemctl list-units --type=service --state=running"

    services_info = ssh(command)
    results = []
    legend_found = False

    for line in services_info.splitlines():
        if line.startswith("UNIT") or not line.strip():
            continue

        if line.startswith("Legend:"):
            legend_found = True
            continue

        if legend_found:
            break

        parts = line.split()
        if len(parts) < 5 or parts[1] == "LOAD":
            continue

        unit = parts[0]  
        load = parts[1] 
        active = parts[2]
        sub = parts[3]
        description = " ".join(parts[4:])

        results.append(
            f"Сервис: {unit}\nЗагрузка: {load}\nСостояние: {active}\nСтатус: {sub}\nИнформация: {description}\n--"
        )

    services_info_formatted = "\n".join(results) or "Нет данных о текущих портах."
    if len(services_info_formatted) > MAX_TELEGRAM_MESSAGE_LENGTH:
        messages = split_message(services_info_formatted)
        for msg in messages:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text(services_info_formatted)

    return ConversationHandler.END

async def get_repl_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = "docker logs db_image"
    repl_logs_info = ssh(command)
    if repl_logs_info:
        log_lines = repl_logs_info.split('\n')

        for line in log_lines:

            if "repl" in line:

                await update.message.reply_text(line)
    else:
        await update.message.reply_text("Нет данных о репликации в логах.")
    return ConversationHandler.END
    

async def get_emails(update: Update, context: CallbackContext) -> None:
    query = "SELECT email FROM email_addresses;"
    emails = await db_query(query)
    clean_email = [email[0] for email in emails]
    formatted_emails = "\n".join([f"{i+1}. {email}" for i, email in enumerate(clean_email)])   

    await update.message.reply_text(formatted_emails)

async def get_phone_numbers(update: Update, context: CallbackContext) -> None:
    query = "SELECT phone_number FROM phone_numbers;"
    phones = await db_query(query)
    clean_phone = [phone[0] for phone in phones]
    formatted_phone = "\n".join([f"{i+1}. {phone}" for i, phone in enumerate(clean_phone)])   

    await update.message.reply_text(formatted_phone)


def main() -> None:

    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(os.getenv("TOKEN")).build()

    convHandlerFindPhoneNumbers = ConversationHandler(
    entry_points=[CommandHandler("find_phone_number", find_phone_numbersCommand)],
    states={
        FIND_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_phone_number)],
        CONFIRM_PHONE: [CallbackQueryHandler(button_handler, pattern='^(save_phone|cancel)$')],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

    convHandlerfind_email = ConversationHandler(
       entry_points=[CommandHandler("find_email", find_emailCommand)],
    states={
        FIND_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_email)],
        CONFIRM_EMAIL: [CallbackQueryHandler(button_handler, pattern='^(save_emails|cancel)$')],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

    conv_handlerget_apt_list = ConversationHandler(
        entry_points=[CommandHandler("get_apt_list", start_get_apt_list)],
        states={
            ASK_PACKAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_apt_list)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    conv_handlerverify_password = ConversationHandler(
        entry_points=[CommandHandler("verify_password", verify_password)],
        states={
            ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(convHandlerFindPhoneNumbers)
    application.add_handler(convHandlerfind_email)
    application.add_handler(conv_handlerverify_password)
    application.add_handler(conv_handlerget_apt_list)
    application.add_handler(CommandHandler("get_release", get_release))
    application.add_handler(CommandHandler("get_uname", get_uname))
    application.add_handler(CommandHandler("get_uptime", get_uptime))
    application.add_handler(CommandHandler("get_df", get_df))
    application.add_handler(CommandHandler("get_free", get_free))
    application.add_handler(CommandHandler("get_mpstat", get_mpstat))
    application.add_handler(CommandHandler("get_w", get_w))
    application.add_handler(CommandHandler("get_auths", get_auths))
    application.add_handler(CommandHandler("get_critical", get_critical))
    application.add_handler(CommandHandler("get_ps", get_ps))
    application.add_handler(CommandHandler("get_ss", get_ss))
    application.add_handler(CommandHandler("get_services", get_services))
    application.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    application.add_handler(CommandHandler("get_emails", get_emails))
    application.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()