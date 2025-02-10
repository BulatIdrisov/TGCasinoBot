import os
from functools import wraps

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
import db as db
import keyboards as kb
import casino

load_dotenv()
bot = Bot(os.getenv('TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot,storage=storage)
ADMIN_ID = os.getenv('ADMIN_ID')
async def on_startup(_):
    await db.db_start()
    print('Бот успешно запущен!')

# проверка пользователя на админа
def is_admin(user_id: int) -> bool:
    return user_id == int(ADMIN_ID)

# Декоратор для проверки прав администратора
def admin_only(handler):
    @wraps(handler)
    async def wrapper(message: types.Message, *args, **kwargs):
        if is_admin(message.from_user.id):
            return await handler(message, *args, **kwargs)
        else:
            await message.answer("У вас недостаточно прав для выполнения данной команды.", reply_markup=kb.main)
    return wrapper

class NewOrder(StatesGroup):
    message = State()
    replenish_ID = State()
    replenish_balance = State()
    game = State()
    message_to_user_id = State()
    message_to_user_text = State()

# Основной обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await db.cmd_start_db(message.from_user.id, message.from_user.first_name)
    keyboard = kb.main_admin if is_admin(message.from_user.id) else kb.main
    await message.answer(
        f'{message.from_user.first_name}, Добро пожаловать в казинак!\n'
        '(Если при нажатии на кнопку ставки ничего не происходит, то введите команду /start)',
        reply_markup=keyboard
    )
# Сообщение админу
@dp.message_handler(text='Сообщение админу')
async def message(message: types.Message):
    await NewOrder.message.set()
    await message.answer("Напишите сообщение",reply_markup=kb.cancel)

@dp.message_handler(state=NewOrder.message)
async def message_op(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await message.answer("Отмена!", reply_markup=kb.main)
        await state.finish()
    else:
        user_id = message.from_user.id
        username = message.from_user.username
        await state.finish()
        await message.answer("Сообщение успешно отправлено!", reply_markup=kb.main)
        await bot.send_message(ADMIN_ID,f'Новое сообщение! {message.text}\nОт пользователя: @{username} (ID: {user_id})',reply_markup=kb.main_admin)
# Сообщение пользователю(доступно только админу)
@dp.message_handler(text='Сообщение')
@admin_only
async def message_to_user(message: types.Message):
        await NewOrder.message_to_user_id.set()
        await message.answer("Введите ID", reply_markup=kb.cancel)

@dp.message_handler(state=NewOrder.message_to_user_id)
@admin_only
async def message_to_user(message: types.Message,state: FSMContext):
        if message.text in db.users_id_array():
            await state.update_data(message_to_user_id=message.text)
            await NewOrder.message_to_user_text.set()
            await message.answer("Напишите сообщение", reply_markup=kb.cancel)
        else:
            if message.text == 'Отмена':
                await message.answer("Отмена!", reply_markup=kb.main_admin)
                await state.finish()
            else:
                await message.answer("Такого ID не существует", reply_markup=kb.cancel)

@dp.message_handler(state = NewOrder.message_to_user_text)
async def message_op_admin(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await message.answer("Отмена!", reply_markup=kb.main_admin)
        await state.finish()
    else:
        await message.answer("Сообщение успешно отправлено!", reply_markup=kb.main_admin)
        data = await state.get_data()
        message_to_user_id = data.get('message_to_user_id')
        await bot.send_message(message_to_user_id,f'Новое сообщение от админа! {message.text}')
        await state.finish()
# Пополнение(доступно только админу)
@dp.message_handler(text='Пополнение')
@admin_only
async def replenish2(message: types.Message):
    await NewOrder.replenish_ID.set()
    await message.answer("Введите ID", reply_markup=kb.main_admin)

@dp.message_handler(state = NewOrder.replenish_ID)
@admin_only
async def replenish_id(message: types.Message,state: FSMContext):
    if message.text == 'Отмена':
        await message.answer("Отмена!", reply_markup=kb.main_admin)
        await state.finish()
    else:
        await state.update_data(id=message.text)
        await NewOrder.replenish_balance.set()
        await message.answer("Введите сумму")

@dp.message_handler(state=NewOrder.replenish_balance)
@admin_only
async def replenish_balance(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await message.answer("Отмена!", reply_markup=kb.main_admin)
        await state.finish()
    else:
        user_data = await state.get_data()
        user_id = user_data['id']
        balance_sum = message.text
        db.replenish(user_id, balance_sum)
        await message.answer(f"Успешное пополнение баланса пользователя: {user_id} на {balance_sum}", reply_markup=kb.main_admin)
        await bot.send_message(user_id, f"Ваш баланс успешно пополнен на {balance_sum}")
        await state.finish()

# Играть вводит пользователя в состояние игры
@dp.message_handler(text='Играть')
async def game(message: types.Message):
    await NewOrder.game.set()
    await message.answer(f'Выберите ставку или введите свою! \nВаш баланс: {db.balance(message.from_user.id)}', reply_markup=kb.game)

@dp.message_handler(state=NewOrder.game)
async def bet(message: types.Message, state: FSMContext):
    keyboard = kb.main_admin if is_admin(message.from_user.id) else kb.main
    if message.text == 'Выйти':
        await message.answer("Выход в главное меню!", reply_markup=keyboard)
        await state.finish()
    else:
        try:
            user_bet = int(message.text)
            result = casino.bet(user_bet)
            sum = result[0]
            slots = result[1]
            if db.balance(message.from_user.id) - user_bet >= 0:
                if sum > 0:
                    await db.update_balance(message.from_user.id, sum)
                    await message.answer(f"Аппарат показал: {slots}\nВы выиграли: {sum}", reply_markup=kb.game)
                    await message.answer(f"Ваш баланс: {db.balance(message.from_user.id)}")
                else:
                    await db.update_balance(message.from_user.id, sum)
                    await message.answer(f"Аппарат показал: {slots}\nВы проиграли: {abs(sum)}", reply_markup=kb.game)
                    await message.answer(f"Ваш баланс: {db.balance(message.from_user.id)}")
            else:
                await message.answer(f"Недостаточно денег на балансе: {db.balance(message.from_user.id)}")
        except ValueError:
            await message.answer("Пожалуйста, введите целое число.")
# Рейтинг
@dp.message_handler(text='Рейтинг')
async def rating(message: types.Message):
    keyboard = kb.main_admin if is_admin(message.from_user.id) else kb.main
    await message.answer(db.rating(), reply_markup=keyboard)

# Список пользователей(только для админа)
@dp.message_handler(text='Список')
@admin_only
async def list(message: types.Message):
        await message.answer(db.users())



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

