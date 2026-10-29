"""Russian button labels and keyboards for the administrator bot."""

LABELS = {
    'menu': '🏠 Главное меню', 'pending': '🧾 Проверить чеки',
    'credit': '💰 Пополнить баланс', 'finduser': '🔎 Найти пользователя',
    'history': '📜 История пополнений', 'stats': '📊 Статистика',
    'finance': '📈 Отчёт за неделю', 'paycontrol': '💳 Реквизиты',
    'cards': '🏦 Карты', 'expenses': '💸 Расходы', 'audit': '🗂 Журнал действий',
    'admins': '👥 Администраторы', 'help': '❓ Помощь',
    'cancel': '❌ Отмена', 'skip': '⏭ Без комментария',
    'addadmin': '➕ Добавить администратора', 'deladmin': '➖ Снять права',
}
PERMISSIONS = {
    'credit': 'balance.manage', 'pending': 'payments.view',
    'finduser': 'payments.view', 'history': 'reports.view', 'stats': 'reports.view',
    'finance': 'reports.view', 'paycontrol': 'cards.manage', 'cards': 'cards.manage',
    'expenses': 'expenses.manage', 'audit': 'audit.view', 'admins': 'admins.manage',
    'addadmin': 'admins.manage', 'deladmin': 'admins.manage',
}
MENU_TEXT = (
    '🏠 Панель администратора Dastyor\n\n'
    'Выберите раздел кнопкой ниже. Команды вводить не нужно.\n'
    '🧾 Проверяйте чеки и подтверждайте поступления.\n'
    '💰 Пополняйте баланс после проверки перевода.\n'
    '📈 Следите за поступлениями и расходами.'
)
HELP_TEXT = (
    '❓ Как пользоваться ботом\n\n'
    '🧾 «Проверить чеки» — открыть заявки и принять решение.\n'
    '💰 «Пополнить баланс» — выбрать пользователя, сумму и подтвердить.\n'
    '📈 «Отчёт за неделю» — посмотреть заявки, поступления и расходы.\n'
    '💳 «Реквизиты» — посмотреть или изменить данные для перевода.\n\n'
    '🏠 «Главное меню» — вернуться к разделам.\n'
    '❌ «Отмена» — прервать незавершённое действие.\n\n'
    'Сначала проверьте поступление денег в банковском приложении.'
)
TIERS = {'super': '👑 Полный доступ', 'finance': '💳 Финансы',
         'support': '🎧 Поддержка', 'readonly': '👁 Только просмотр'}

def button(action, label=None):
    return {'text': label or LABELS[action], 'callback_data': 'ui:' + action}

def navigation():
    return {'inline_keyboard': [[button('cancel'), button('menu')]]}

def menu(tier):
    rows = [('pending', 'credit'), ('finduser', 'history'), ('stats', 'finance'),
            ('paycontrol', 'cards'), ('expenses', 'audit'), ('admins', 'help')]
    if tier == 'support':
        allowed = {'pending', 'finduser', 'help'}
    elif tier == 'readonly':
        allowed = {'pending', 'finduser', 'history', 'stats', 'finance', 'audit', 'help'}
    elif tier == 'finance':
        allowed = set(LABELS) - {'admins', 'addadmin', 'deladmin'}
    else:
        allowed = set(LABELS) if tier == 'super' else {'help'}
    return {'inline_keyboard': [buttons for row in rows
                               if (buttons := [button(a) for a in row if a in allowed])]}

def shortcuts(tier):
    rows = [[{'text': LABELS['menu']}, {'text': LABELS['cancel']}]]
    if tier in ('super', 'finance'):
        rows.insert(0, [{'text': LABELS['pending']}, {'text': LABELS['credit']}])
    return {'keyboard': rows, 'resize_keyboard': True, 'is_persistent': True,
            'input_field_placeholder': 'Выберите действие или введите ответ'}

def context(state):
    rows = []
    if state.topup_stage == 'amount':
        rows.extend([[button('amount:' + str(n), f'{n} сомони') for n in (5, 10, 20)],
                     [button('amount:' + str(n), f'{n} сомони') for n in (50, 100)]])
    if state.topup_stage == 'note':
        rows.append([button('skip')])
    rows.extend(navigation()['inline_keyboard'])
    return {'inline_keyboard': rows}

def review(request_id):
    return {'inline_keyboard': [
        [{'text': '✅ Подтвердить', 'callback_data': 'pay:ok:' + request_id},
         {'text': '❌ Отклонить', 'callback_data': 'pay:no:' + request_id}],
        [{'text': '💵 Другая сумма', 'callback_data': 'pay:amt:' + request_id}],
        [{'text': '🔎 Доп. проверка', 'callback_data': 'pay:more:' + request_id}],
        [button('menu')],
    ]}
